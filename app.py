import os
import unicodedata

from flask import Flask, abort, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from db import (
    delete_session,
    delete_expense,
    delete_participant,
    get_expense,
    get_metadata_value,
    get_participant,
    get_approved_expenses_for_reimbursements,
    get_or_create_superadmin_token,
    get_session_by_public_id,
    get_session_by_token,
    init_app,
    init_db,
    insert_expense,
    insert_participant,
    insert_session,
    list_sessions,
    list_expenses,
    list_participants,
    participant_is_used,
    set_metadata_value,
    update_session_status,
    update_expense,
    update_expense_status,
)


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "FLASK_SECRET_KEY", "dev-secret-key-change-me"
)
init_app(app)

with app.app_context():
    init_db()


def record_value(record, key, default=None):
    try:
        return record[key]
    except (KeyError, IndexError, TypeError):
        return default


def participant_label(name, emoji):
    if emoji:
        return f"{emoji} {name}"
    return name


def compute_reimbursements(participants, expenses):
    balances = {participant["public_id"]: 0 for participant in participants}
    names = {
        participant["public_id"]: participant_label(
            participant["name"], record_value(participant, "emoji")
        )
        for participant in participants
    }

    for expense in expenses:
        concerned_participants = expense["concerned_participants"]
        if not concerned_participants:
            continue

        payer_id = expense["payer_participant_public_id"]
        amount_cents = expense["amount_cents"]

        balances[payer_id] += amount_cents

        share_cents = amount_cents // len(concerned_participants)
        remainder_cents = amount_cents % len(concerned_participants)

        for index, participant in enumerate(concerned_participants):
            participant_share = share_cents
            if index < remainder_cents:
                participant_share += 1
            balances[participant["participant_public_id"]] -= participant_share

    creditors = []
    debtors = []

    for participant_id, balance_cents in balances.items():
        if balance_cents > 0:
            creditors.append(
                {
                    "participant_public_id": participant_id,
                    "name": names[participant_id],
                    "balance_cents": balance_cents,
                }
            )
        elif balance_cents < 0:
            debtors.append(
                {
                    "participant_public_id": participant_id,
                    "name": names[participant_id],
                    "balance_cents": -balance_cents,
                }
            )

    creditors.sort(key=lambda item: (-item["balance_cents"], item["name"]))
    debtors.sort(key=lambda item: (-item["balance_cents"], item["name"]))

    reimbursements = []
    creditor_index = 0
    debtor_index = 0

    while creditor_index < len(creditors) and debtor_index < len(debtors):
        creditor = creditors[creditor_index]
        debtor = debtors[debtor_index]
        transfer_cents = min(creditor["balance_cents"], debtor["balance_cents"])

        reimbursements.append(
            {
                "from_participant_public_id": debtor["participant_public_id"],
                "from_name": debtor["name"],
                "to_participant_public_id": creditor["participant_public_id"],
                "to_name": creditor["name"],
                "amount_cents": transfer_cents,
            }
        )

        creditor["balance_cents"] -= transfer_cents
        debtor["balance_cents"] -= transfer_cents

        if creditor["balance_cents"] == 0:
            creditor_index += 1
        if debtor["balance_cents"] == 0:
            debtor_index += 1

    return reimbursements


def compute_participant_balances(participants, expenses):
    balances = {participant["public_id"]: 0 for participant in participants}

    for expense in expenses:
        concerned_participants = expense["concerned_participants"]
        if not concerned_participants:
            continue

        payer_id = expense["payer_participant_public_id"]
        amount_cents = expense["amount_cents"]

        balances[payer_id] += amount_cents

        share_cents = amount_cents // len(concerned_participants)
        remainder_cents = amount_cents % len(concerned_participants)

        for index, participant in enumerate(concerned_participants):
            participant_share = share_cents
            if index < remainder_cents:
                participant_share += 1
            balances[participant["participant_public_id"]] -= participant_share

    participant_balances = []
    for participant in participants:
        balance_cents = balances[participant["public_id"]]
        participant_balances.append(
            {
                "public_id": participant["public_id"],
                "name": participant["name"],
                "emoji": record_value(participant, "emoji", ""),
                "balance_cents": balance_cents,
                "balance_text": format_signed_cents(balance_cents),
                "balance_class": get_balance_class(balance_cents),
            }
        )

    participant_balances.sort(
        key=lambda item: (item["balance_cents"], item["name"].lower())
    )
    return participant_balances


def format_cents(amount_cents):
    euros = amount_cents // 100
    cents = amount_cents % 100
    if cents == 0:
        return f"{euros}\u20ac"
    return f"{euros}.{cents:02d}\u20ac"


def format_signed_cents(amount_cents):
    absolute_amount_cents = abs(amount_cents)
    euros = absolute_amount_cents // 100
    cents = absolute_amount_cents % 100

    if cents == 0:
        amount_text = f"{euros}\u20ac"
    else:
        amount_text = f"{euros},{cents:02d}\u20ac"

    if amount_cents > 0:
        return f"+ {amount_text}"
    if amount_cents < 0:
        return f"-{amount_text}"
    return "0\u20ac"


def get_balance_class(amount_cents):
    if amount_cents < 0:
        return "balance-negative"
    if amount_cents > 0:
        return "balance-positive"
    return "balance-neutral"


def get_reimbursements(session_public_id):
    participants, expenses = get_approved_expenses_for_reimbursements(session_public_id)
    return compute_reimbursements(participants, expenses)


def sync_session_status(session):
    if session["status"] != "frozen":
        return session

    if get_reimbursements(session["public_id"]):
        return session

    update_session_status(session["public_id"], "closed")
    refreshed_session = get_session_by_public_id(session["public_id"])
    return refreshed_session or session


def is_valid_participant_name(name):
    allowed_extra_characters = {" ", "'", "-"}

    for character in name:
        if character in allowed_extra_characters:
            continue
        if character.isdigit():
            continue
        if unicodedata.category(character).startswith("L"):
            continue
        return False

    return True


def can_edit_expense(role, expense):
    if role == "admin":
        return True
    return expense["submitted_by_role"] == "viewer"


def get_superadmin_password_hash():
    return get_metadata_value("superadmin_password_hash")


def has_superadmin_password():
    return get_superadmin_password_hash() is not None


def is_superadmin_password_valid(password):
    password_hash = get_superadmin_password_hash()
    if password_hash is None:
        return False
    return check_password_hash(password_hash, password)


def get_create_session_password_hash():
    return get_metadata_value("create_session_password_hash")


def has_create_session_password():
    return get_create_session_password_hash() is not None


def is_create_session_password_valid(password):
    password_hash = get_create_session_password_hash()
    if password_hash is None:
        return False
    return check_password_hash(password_hash, password)


def render_session_page(
    session,
    role,
    token,
    participant_error=None,
    participant_name="",
    expense_error=None,
    expense_name="",
    expense_amount="",
    expense_payer="",
    expense_concerned=None,
    expense_form_mode="create",
    editing_expense_id=None,
):
    session = sync_session_status(session)
    participants = list_participants(session["public_id"])
    expenses = list_expenses(session["public_id"])
    session_total_cents = sum(
        expense["amount_cents"]
        for expense in expenses
        if expense["status"] != "rejected" and expense["name"].lower() != "reimbursement"
    )
    approved_participants, approved_expenses = get_approved_expenses_for_reimbursements(
        session["public_id"]
    )
    reimbursements = compute_reimbursements(approved_participants, approved_expenses)
    overview_participants = compute_participant_balances(
        approved_participants, approved_expenses
    )
    participant_name_by_public_id = {
        participant["public_id"]: participant_label(
            participant["name"], record_value(participant, "emoji")
        )
        for participant in participants
    }

    display_expenses = []
    for expense in expenses:
        display_expenses.append(
            {
                **expense,
                "payer_display_name": participant_label(
                    expense["payer_name"] or "Unknown",
                    record_value(expense, "payer_emoji"),
                )
                if expense["payer_name"]
                else "Unknown",
                "concerned_display_names": [
                    participant_label(item["name"], record_value(item, "emoji"))
                    for item in expense["concerned_names"]
                ],
            }
        )
    default_concerned = [participant["public_id"] for participant in participants]

    if expense_concerned is None:
        expense_concerned = default_concerned

    return render_template(
        "session_access.html",
        session=session,
        session_total_text=format_cents(session_total_cents),
        role=role,
        token=token,
        participants=participants,
        participant_name_by_public_id=participant_name_by_public_id,
        overview_participants=overview_participants,
        expenses=display_expenses,
        reimbursements=reimbursements,
        participant_error=participant_error,
        participant_name=participant_name,
        expense_error=expense_error,
        expense_name=expense_name,
        expense_amount=expense_amount,
        expense_payer=expense_payer,
        expense_concerned=expense_concerned,
        expense_form_mode=expense_form_mode,
        editing_expense_id=editing_expense_id,
    )


@app.route("/")
def index():
    return render_template(
        "index.html",
        error=None,
        setup_mode=not has_create_session_password(),
    )


def can_create_session():
    return session.get("can_create_session", False)


@app.route("/unlock-session-creation", methods=["POST"])
def unlock_session_creation():
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not has_create_session_password():
        if not password:
            return render_template(
                "index.html",
                error="Password is required.",
                setup_mode=True,
            )
        if password != confirm_password:
            return render_template(
                "index.html",
                error="Passwords do not match.",
                setup_mode=True,
            )

        set_metadata_value(
            "create_session_password_hash", generate_password_hash(password)
        )
        session["can_create_session"] = True
        return redirect(url_for("new_session"))

    if not is_create_session_password_valid(password):
        return render_template(
            "index.html",
            error="Wrong password.",
            setup_mode=False,
        )

    session["can_create_session"] = True
    return redirect(url_for("new_session"))


@app.route("/sessions/new", methods=["GET", "POST"])
def new_session():
    if not can_create_session():
        return redirect(url_for("index"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()

        if not title:
            return render_template(
                "new_session.html",
                error="Title is required.",
                title=title,
                description=description,
            )

        session_public_id = insert_session(title=title, description=description)
        return redirect(
            url_for("session_created", session_public_id=session_public_id)
        )

    return render_template("new_session.html", error=None, title="", description="")


@app.route("/sessions/<session_public_id>/created")
def session_created(session_public_id):
    session = get_session_by_public_id(session_public_id)
    if session is None:
        abort(404)

    return render_template(
        "session_created.html",
        session=session,
        superadmin_access_url=f"{request.url_root}superadmin-access",
    )


@app.route("/superadmin-access", methods=["GET", "POST"])
def superadmin_access():
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not has_superadmin_password():
            if not password:
                return render_template(
                    "superadmin_access.html",
                    error="Password is required.",
                    setup_mode=True,
                )
            if password != confirm_password:
                return render_template(
                    "superadmin_access.html",
                    error="Passwords do not match.",
                    setup_mode=True,
                )

            set_metadata_value(
                "superadmin_password_hash", generate_password_hash(password)
            )
            return redirect(
                url_for("superadmin", token=get_or_create_superadmin_token())
            )
        if is_superadmin_password_valid(password):
            return redirect(
                url_for("superadmin", token=get_or_create_superadmin_token())
            )
        return render_template(
            "superadmin_access.html",
            error="Wrong password.",
            setup_mode=False,
        )

    return render_template(
        "superadmin_access.html",
        error=None,
        setup_mode=not has_superadmin_password(),
    )


@app.route("/superadmin/<token>")
def superadmin(token):
    superadmin_token = get_or_create_superadmin_token()
    if token != superadmin_token:
        abort(404)

    sessions = list_sessions()
    return render_template(
        "superadmin.html",
        sessions=sessions,
        superadmin_token=superadmin_token,
        delete_error=None,
    )


@app.route("/superadmin/<token>/sessions/<session_public_id>/delete", methods=["POST"])
def delete_session_view(token, session_public_id):
    superadmin_token = get_or_create_superadmin_token()
    if token != superadmin_token:
        abort(404)

    session = get_session_by_public_id(session_public_id)
    if session is None:
        abort(404)

    password = request.form.get("password", "")
    if not is_superadmin_password_valid(password):
        sessions = list_sessions()
        return render_template(
            "superadmin.html",
            sessions=sessions,
            superadmin_token=superadmin_token,
            delete_error="Wrong password. Session was not deleted.",
        )

    delete_session(session_public_id)
    return redirect(url_for("superadmin", token=token))


@app.route("/s/<token>")
def session_access(token):
    session, role = get_session_by_token(token)
    if session is None:
        abort(404)

    return render_session_page(session=session, role=role, token=token)


@app.route("/s/<token>/participants", methods=["POST"])
def add_participant(token):
    session, role = get_session_by_token(token)
    if session is None:
        abort(404)
    if role != "admin":
        abort(403)
    if session["status"] != "open":
        abort(403)

    participant_name = request.form.get("name", "").strip()
    if not participant_name:
        return render_session_page(
            session=session,
            role=role,
            token=token,
            participant_error="Participant name is required.",
            participant_name=participant_name,
        )

    participant_names = [
        name.strip() for name in participant_name.split(";") if name.strip()
    ]

    if not participant_names:
        return render_session_page(
            session=session,
            role=role,
            token=token,
            participant_error="Participant name is required.",
            participant_name=participant_name,
        )

    invalid_names = [name for name in participant_names if not is_valid_participant_name(name)]
    if invalid_names:
        return render_session_page(
            session=session,
            role=role,
            token=token,
            participant_error=(
                "Participant names can only contain letters, numbers, spaces, "
                "apostrophes, and hyphens. Please enter them again."
            ),
            participant_name=participant_name,
        )

    try:
        for name in participant_names:
            insert_participant(session["public_id"], name)
    except ValueError:
        return render_session_page(
            session=session,
            role=role,
            token=token,
            participant_error=(
                "No more unique animal emojis are available for this session. "
                "Please remove a participant before adding a new one."
            ),
            participant_name=participant_name,
        )

    return redirect(url_for("session_access", token=token))


@app.route("/s/<token>/participants/<participant_public_id>/delete", methods=["POST"])
def remove_participant(token, participant_public_id):
    session, role = get_session_by_token(token)
    if session is None:
        abort(404)
    if role != "admin":
        abort(403)
    if session["status"] != "open":
        abort(403)

    participant = get_participant(session["public_id"], participant_public_id)
    if participant is None:
        abort(404)

    if participant_is_used(session["public_id"], participant_public_id):
        return render_session_page(
            session=session,
            role=role,
            token=token,
            participant_error=(
                f"{participant['name']} cannot be removed because this participant "
                "is already used in one or more expenses."
            ),
        )

    delete_participant(session["public_id"], participant_public_id)
    return redirect(url_for("session_access", token=token))


@app.route("/s/<token>/expenses", methods=["POST"])
def add_expense(token):
    session, role = get_session_by_token(token)
    if session is None:
        abort(404)
    if session["status"] != "open":
        abort(403)

    participants = list_participants(session["public_id"])

    expense_name = request.form.get("name", "").strip()
    expense_amount = request.form.get("amount", "").strip()
    expense_payer = request.form.get("payer_participant_public_id", "").strip()
    expense_concerned = request.form.getlist("concerned_participant_public_ids")

    if not expense_name:
        return render_session_page(
            session=session,
            role=role,
            token=token,
            expense_error="Expense name is required.",
            expense_name=expense_name,
            expense_amount=expense_amount,
            expense_payer=expense_payer,
            expense_concerned=expense_concerned,
        )

    try:
        amount_cents = int(round(float(expense_amount) * 100))
    except ValueError:
        amount_cents = -1

    if amount_cents < 0:
        return render_session_page(
            session=session,
            role=role,
            token=token,
            expense_error="Amount must be a valid positive number.",
            expense_name=expense_name,
            expense_amount=expense_amount,
            expense_payer=expense_payer,
            expense_concerned=expense_concerned,
        )

    payer = get_participant(session["public_id"], expense_payer)
    if payer is None:
        return render_session_page(
            session=session,
            role=role,
            token=token,
            expense_error="Please select who paid the expense.",
            expense_name=expense_name,
            expense_amount=expense_amount,
            expense_payer=expense_payer,
            expense_concerned=expense_concerned,
        )

    valid_participant_ids = {participant["public_id"] for participant in participants}
    selected_participant_ids = [
        participant_public_id
        for participant_public_id in expense_concerned
        if participant_public_id in valid_participant_ids
    ]

    if not selected_participant_ids:
        return render_session_page(
            session=session,
            role=role,
            token=token,
            expense_error="Select at least one concerned participant.",
            expense_name=expense_name,
            expense_amount=expense_amount,
            expense_payer=expense_payer,
            expense_concerned=expense_concerned,
        )

    insert_expense(
        session_public_id=session["public_id"],
        name=expense_name,
        amount_cents=amount_cents,
        payer_participant_public_id=expense_payer,
        concerned_participant_public_ids=selected_participant_ids,
        submitted_by_role=role,
    )
    return redirect(url_for("session_access", token=token))


@app.route("/s/<token>/expenses/<expense_public_id>/edit")
def edit_expense(token, expense_public_id):
    session, role = get_session_by_token(token)
    if session is None:
        abort(404)

    expense = get_expense(session["public_id"], expense_public_id)
    if expense is None:
        abort(404)
    if not can_edit_expense(role, expense):
        abort(403)
    return render_session_page(
        session=session,
        role=role,
        token=token,
        expense_name=expense["name"],
        expense_amount=f"{expense['amount_cents'] / 100:.2f}",
        expense_payer=expense["payer_participant_public_id"] or "",
        expense_concerned=expense["concerned_participant_public_ids"],
        expense_form_mode="edit",
        editing_expense_id=expense["public_id"],
    )


@app.route("/s/<token>/expenses/<expense_public_id>/update", methods=["POST"])
def update_expense_view(token, expense_public_id):
    session, role = get_session_by_token(token)
    if session is None:
        abort(404)
    if session["status"] != "open":
        abort(403)

    original_expense = get_expense(session["public_id"], expense_public_id)
    if original_expense is None:
        abort(404)
    if not can_edit_expense(role, original_expense):
        abort(403)

    participants = list_participants(session["public_id"])

    expense_name = request.form.get("name", "").strip()
    expense_amount = request.form.get("amount", "").strip()
    expense_payer = request.form.get("payer_participant_public_id", "").strip()
    expense_concerned = request.form.getlist("concerned_participant_public_ids")

    if not expense_name:
        return render_session_page(
            session=session,
            role=role,
            token=token,
            expense_error="Expense name is required.",
            expense_name=expense_name,
            expense_amount=expense_amount,
            expense_payer=expense_payer,
            expense_concerned=expense_concerned,
            expense_form_mode="edit",
            editing_expense_id=expense_public_id,
        )

    try:
        amount_cents = int(round(float(expense_amount) * 100))
    except ValueError:
        amount_cents = -1

    if amount_cents < 0:
        return render_session_page(
            session=session,
            role=role,
            token=token,
            expense_error="Amount must be a valid positive number.",
            expense_name=expense_name,
            expense_amount=expense_amount,
            expense_payer=expense_payer,
            expense_concerned=expense_concerned,
            expense_form_mode="edit",
            editing_expense_id=expense_public_id,
        )

    payer = get_participant(session["public_id"], expense_payer)
    if payer is None:
        return render_session_page(
            session=session,
            role=role,
            token=token,
            expense_error="Please select who paid the expense.",
            expense_name=expense_name,
            expense_amount=expense_amount,
            expense_payer=expense_payer,
            expense_concerned=expense_concerned,
            expense_form_mode="edit",
            editing_expense_id=expense_public_id,
        )

    valid_participant_ids = {participant["public_id"] for participant in participants}
    selected_participant_ids = [
        participant_public_id
        for participant_public_id in expense_concerned
        if participant_public_id in valid_participant_ids
    ]

    if not selected_participant_ids:
        return render_session_page(
            session=session,
            role=role,
            token=token,
            expense_error="Select at least one concerned participant.",
            expense_name=expense_name,
            expense_amount=expense_amount,
            expense_payer=expense_payer,
            expense_concerned=expense_concerned,
            expense_form_mode="edit",
            editing_expense_id=expense_public_id,
        )

    update_expense(
        session_public_id=session["public_id"],
        expense_public_id=expense_public_id,
        name=expense_name,
        amount_cents=amount_cents,
        payer_participant_public_id=expense_payer,
        concerned_participant_public_ids=selected_participant_ids,
    )
    return redirect(url_for("session_access", token=token))


@app.route("/s/<token>/expenses/<expense_public_id>/approve", methods=["POST"])
def approve_expense(token, expense_public_id):
    session, role = get_session_by_token(token)
    if session is None:
        abort(404)
    if role != "admin":
        abort(403)
    if session["status"] != "open":
        abort(403)

    expense = get_expense(session["public_id"], expense_public_id)
    if expense is None:
        abort(404)

    update_expense_status(session["public_id"], expense_public_id, "approved")
    return redirect(url_for("session_access", token=token))


@app.route("/s/<token>/expenses/<expense_public_id>/reject", methods=["POST"])
def reject_expense(token, expense_public_id):
    session, role = get_session_by_token(token)
    if session is None:
        abort(404)
    if role != "admin":
        abort(403)
    if session["status"] != "open":
        abort(403)

    expense = get_expense(session["public_id"], expense_public_id)
    if expense is None:
        abort(404)

    update_expense_status(session["public_id"], expense_public_id, "rejected")
    return redirect(url_for("session_access", token=token))


@app.route("/s/<token>/expenses/<expense_public_id>/delete", methods=["POST"])
def delete_expense_view(token, expense_public_id):
    session, role = get_session_by_token(token)
    if session is None:
        abort(404)
    if role != "admin":
        abort(403)
    if session["status"] != "open":
        abort(403)

    expense = get_expense(session["public_id"], expense_public_id)
    if expense is None:
        abort(404)

    delete_expense(session["public_id"], expense_public_id)
    return redirect(url_for("session_access", token=token))


@app.route("/s/<token>/reimbursements/done", methods=["POST"])
def mark_reimbursement_done(token):
    session, role = get_session_by_token(token)
    if session is None:
        abort(404)
    session = sync_session_status(session)
    if session["status"] != "frozen":
        abort(403)

    payer_participant_public_id = request.form.get(
        "payer_participant_public_id", ""
    ).strip()
    concerned_participant_public_id = request.form.get(
        "concerned_participant_public_id", ""
    ).strip()
    amount_cents_raw = request.form.get("amount_cents", "").strip()

    payer = get_participant(session["public_id"], payer_participant_public_id)
    concerned_participant = get_participant(
        session["public_id"], concerned_participant_public_id
    )

    if payer is None or concerned_participant is None:
        abort(400)

    try:
        amount_cents = int(amount_cents_raw)
    except ValueError:
        abort(400)

    if amount_cents <= 0:
        abort(400)

    insert_expense(
        session_public_id=session["public_id"],
        name="reimbursement",
        amount_cents=amount_cents,
        payer_participant_public_id=payer_participant_public_id,
        concerned_participant_public_ids=[concerned_participant_public_id],
        submitted_by_role=role,
        status="approved",
    )
    update_session_status(session["public_id"], "frozen")
    return redirect(url_for("session_access", token=token))


@app.route("/s/<token>/close", methods=["POST"])
def close_session(token):
    session, role = get_session_by_token(token)
    if session is None:
        abort(404)
    if role != "admin":
        abort(403)
    if session["status"] != "open":
        abort(403)

    update_session_status(session["public_id"], "frozen")
    return redirect(url_for("session_access", token=token))


@app.route("/s/<token>/reopen", methods=["POST"])
def reopen_session(token):
    session, role = get_session_by_token(token)
    if session is None:
        abort(404)
    if role != "admin":
        abort(403)
    if session["status"] != "frozen":
        abort(403)

    update_session_status(session["public_id"], "open")
    return redirect(url_for("session_access", token=token))


if __name__ == "__main__":
    init_db()
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
    )
