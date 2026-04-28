import os
import unicodedata

from flask import (
    Flask,
    abort,
    has_request_context,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
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


TRANSLATIONS = {
    "en": {
        "access_link": "Access link",
        "access_links": "Access links",
        "add_at_least_one_participant": "Add at least one participant before creating expenses.",
        "add_expense": "Add expense",
        "admin": "Admin",
        "admin_link": "Admin link",
        "actions": "Actions",
        "amount": "Amount",
        "amount_placeholder": "amount",
        "approve": "Approve",
        "approved": "approved",
        "cancel": "Cancel",
        "cancel_table_edit": "Cancel table edit",
        "closed": "closed",
        "concerned_participants": "Concerned participants",
        "confirm_creation_password": "Confirm creation password",
        "confirm_password": "Confirm password",
        "create_new_session": "Create new session",
        "create_session": "Create session",
        "create_session_intro": "Start a weekend, trip, or shared event and generate admin and viewer links.",
        "create_session_password_help": "Enter the creation password to open the session setup page.",
        "created_at": "Created at",
        "creation_password": "Creation password",
        "delete": "Delete",
        "delete_expense": "Delete expense",
        "delete_session_password_placeholder": "Type password then Enter",
        "demo_expense_brunch": "Brunch",
        "demo_expense_groceries": "Groceries",
        "demo_expense_museum": "Museum",
        "demo_expense_parking": "Parking",
        "demo_readonly_alert": "Read-only demo: forms and actions are disabled.",
        "demo_readonly_text": "This page shows the viewer interface with example data.",
        "demo_session_title": "Demo weekend",
        "demo_viewer": "View viewer demo",
        "duplicate": "Duplicate",
        "duplicate_expense": "Duplicate expense",
        "edit": "Edit",
        "edit_expense": "Edit expense",
        "edit_expenses_table": "Edit expenses table",
        "expense": "Expense",
        "expense_name_placeholder": "expense name",
        "expenses": "Expenses",
        "feature_admin_body": "Viewers can submit expenses, while the admin keeps control to approve, reject, or correct them.",
        "feature_admin_title": "Admin validation",
        "feature_links_body": "No accounts for participants: each session has one admin link and one viewer link.",
        "feature_links_title": "Secure links",
        "feature_participants_body": "Each person keeps their emoji, balance, and place in the expense table.",
        "feature_participants_title": "Readable participants",
        "feature_reimbursements_body": "Nikount calculates who should pay whom, with fewer transactions.",
        "feature_reimbursements_title": "Reimbursements",
        "footer_message": "If Nikount is useful to you, you can support the project by offering me a",
        "freeze": "Freeze",
        "frozen": "frozen",
        "hero_clear_reimbursements": "clear reimbursements",
        "hero_copy": "A small app to track group expenses, see who paid what, and calculate reimbursements simply.",
        "hero_example": "Example",
        "hero_friends": "4 friends",
        "hero_kicker": "Weekends, trips, temporary shared places",
        "hero_weekend": "1 weekend",
        "index_title": "Nikount",
        "new_creation_password": "New creation password",
        "new_session": "New session",
        "no_expenses_yet": "No expenses yet.",
        "no_participants_yet": "No participants yet.",
        "no_reimbursements_needed": "No reimbursements needed.",
        "no_sessions_yet": "No sessions yet.",
        "open": "open",
        "open_superadmin_page": "Open superadmin page",
        "paid_by": "Paid by",
        "participant": "participant",
        "participants": "Participants",
        "password": "Password",
        "pays": "pays",
        "pending": "pending",
        "reimbursement_done": "Reimbursement done",
        "reimbursement_expense": "reimbursement",
        "reimbursements": "Reimbursements",
        "reject": "Reject",
        "rejected": "rejected",
        "reopen": "Reopen",
        "remove_participant": "Remove participant",
        "save_expenses": "Save expenses",
        "save_password": "Save password",
        "session_closed_alert": "Session is closed. All reimbursements are done.",
        "session_created": "Session created",
        "session_frozen_alert": "Session is frozen. Only reimbursements can be marked as done.",
        "session_total": "Session total",
        "sessions": "Sessions",
        "set_creation_password": "Set creation password",
        "set_creation_password_help": "Choose the password that will protect new session creation.",
        "set_superadmin_password": "Set superadmin password",
        "status": "Status",
        "submitted_by": "Submitted by",
        "superadmin": "Superadmin",
        "superadmin_access": "Superadmin access",
        "superadmin_access_help": "Enter the shared password to open the superadmin page.",
        "superadmin_overview": "Overview of every session with direct access links and totals.",
        "superadmin_setup_help": "This password will protect access to the global session list.",
        "title": "Title",
        "to": "to",
        "total_amount": "Total amount",
        "unknown": "Unknown",
        "use_semicolon_placeholder": "Use \";\" to add multiple participants at once",
        "viewer": "Viewer",
        "viewer_expense_alert": "Viewer expenses are submitted for admin approval.",
        "viewer_link": "Viewer link",
        "who_paid": "Who paid?",
        "payer": "payer",
        "error_amount_invalid": "Amount must be a valid positive number.",
        "error_concerned_required": "Select at least one concerned participant.",
        "error_expense_name_required": "Expense name is required.",
        "error_invalid_amount_for": "Invalid amount for {expense_name}.",
        "error_participant_cannot_remove": "{participant_name} cannot be removed because this participant is already used in one or more expenses.",
        "error_participant_name_required": "Participant name is required.",
        "error_participant_names_invalid": "Participant names can only contain letters, numbers, spaces, apostrophes, and hyphens. Please enter them again.",
        "error_password_required": "Password is required.",
        "error_passwords_do_not_match": "Passwords do not match.",
        "error_payer_required": "Please select who paid the expense.",
        "error_select_concerned_for": "Select at least one concerned participant for {expense_name}.",
        "error_select_payer_for": "Select who paid {expense_name}.",
        "error_title_required": "Title is required.",
        "error_unique_emoji_limit": "No more unique participant emojis are available for this session. Please remove a participant before adding a new one.",
        "error_wrong_password": "Wrong password.",
        "error_wrong_password_session_not_deleted": "Wrong password. Session was not deleted.",
    },
    "fr": {
        "access_link": "Lien d'accès",
        "access_links": "Liens d'accès",
        "add_at_least_one_participant": "Ajoutez au moins un participant avant de créer des dépenses.",
        "add_expense": "Ajouter une dépense",
        "admin": "Admin",
        "admin_link": "Lien admin",
        "actions": "Actions",
        "amount": "Montant",
        "amount_placeholder": "montant",
        "approve": "Approuver",
        "approved": "approuvée",
        "cancel": "Annuler",
        "cancel_table_edit": "Annuler l'édition du tableau",
        "closed": "clôturée",
        "concerned_participants": "Participants concernés",
        "confirm_creation_password": "Confirmer le mot de passe de création",
        "confirm_password": "Confirmer le mot de passe",
        "create_new_session": "Créer une session",
        "create_session": "Créer la session",
        "create_session_intro": "Démarrez un week-end, un voyage ou un événement partagé et générez les liens admin et visiteur.",
        "create_session_password_help": "Entrez le mot de passe de création pour ouvrir la page de configuration d'une session.",
        "created_at": "Créée le",
        "creation_password": "Mot de passe de création",
        "delete": "Supprimer",
        "delete_expense": "Supprimer la dépense",
        "delete_session_password_placeholder": "Tapez le mot de passe puis Entrée",
        "demo_expense_brunch": "Brunch",
        "demo_expense_groceries": "Courses",
        "demo_expense_museum": "Musée",
        "demo_expense_parking": "Parking",
        "demo_readonly_alert": "Démo en lecture seule : les formulaires et actions sont désactivés.",
        "demo_readonly_text": "Cette page montre l'interface d'une session visiteur avec des données d'exemple.",
        "demo_session_title": "Démo week-end",
        "demo_viewer": "Voir la démo visiteur",
        "duplicate": "Dupliquer",
        "duplicate_expense": "Dupliquer la dépense",
        "edit": "Modifier",
        "edit_expense": "Modifier la dépense",
        "edit_expenses_table": "Modifier le tableau des dépenses",
        "expense": "Dépense",
        "expense_name_placeholder": "nom de la dépense",
        "expenses": "Dépenses",
        "feature_admin_body": "Les visiteurs peuvent proposer des dépenses, et l'admin garde la main pour approuver, rejeter ou corriger.",
        "feature_admin_title": "Validation admin",
        "feature_links_body": "Pas de comptes pour les participants : chaque session a un lien admin et un lien visiteur.",
        "feature_links_title": "Liens sécurisés",
        "feature_participants_body": "Chaque personne garde son emoji, son solde, et sa place dans le tableau des dépenses.",
        "feature_participants_title": "Participants lisibles",
        "feature_reimbursements_body": "Nikount calcule qui doit payer qui, avec moins de transactions.",
        "feature_reimbursements_title": "Remboursements",
        "footer_message": "Si Nikount vous est utile, vous pouvez soutenir le projet en m'offrant un",
        "freeze": "Figer",
        "frozen": "figée",
        "hero_clear_reimbursements": "des remboursements clairs",
        "hero_copy": "Une petite application pour noter les dépenses d'un groupe, savoir qui a payé quoi, puis calculer simplement les remboursements.",
        "hero_example": "Exemple",
        "hero_friends": "4 amis",
        "hero_kicker": "Week-ends, voyages, colocs temporaires",
        "hero_weekend": "1 week-end",
        "index_title": "Nikount",
        "new_creation_password": "Nouveau mot de passe de création",
        "new_session": "Nouvelle session",
        "no_expenses_yet": "Aucune dépense pour le moment.",
        "no_participants_yet": "Aucun participant pour le moment.",
        "no_reimbursements_needed": "Aucun remboursement nécessaire.",
        "no_sessions_yet": "Aucune session pour le moment.",
        "open": "ouverte",
        "open_superadmin_page": "Ouvrir la page superadmin",
        "paid_by": "Payé par",
        "participant": "participant",
        "participants": "Participants",
        "password": "Mot de passe",
        "pays": "paie",
        "pending": "en attente",
        "reimbursement_done": "Remboursement fait",
        "reimbursement_expense": "remboursement",
        "reimbursements": "Remboursements",
        "reject": "Rejeter",
        "rejected": "rejetée",
        "reopen": "Réouvrir",
        "remove_participant": "Supprimer le participant",
        "save_expenses": "Enregistrer les dépenses",
        "save_password": "Enregistrer le mot de passe",
        "session_closed_alert": "La session est clôturée. Tous les remboursements sont faits.",
        "session_created": "Session créée",
        "session_frozen_alert": "La session est figée. Seuls les remboursements peuvent être marqués comme faits.",
        "session_total": "Total de la session",
        "sessions": "Sessions",
        "set_creation_password": "Définir le mot de passe de création",
        "set_creation_password_help": "Choisissez le mot de passe qui protégera la création de nouvelles sessions.",
        "set_superadmin_password": "Définir le mot de passe superadmin",
        "status": "Statut",
        "submitted_by": "Soumis par",
        "superadmin": "Superadmin",
        "superadmin_access": "Accès superadmin",
        "superadmin_access_help": "Entrez le mot de passe partagé pour ouvrir la page superadmin.",
        "superadmin_overview": "Vue d'ensemble de toutes les sessions avec les liens directs et les totaux.",
        "superadmin_setup_help": "Ce mot de passe protégera l'accès à la liste globale des sessions.",
        "title": "Titre",
        "to": "à",
        "total_amount": "Montant total",
        "unknown": "Inconnu",
        "use_semicolon_placeholder": "Utilisez \";\" pour ajouter plusieurs participants",
        "viewer": "Visiteur",
        "viewer_expense_alert": "Les dépenses des visiteurs sont soumises à validation admin.",
        "viewer_link": "Lien visiteur",
        "who_paid": "Qui a payé ?",
        "payer": "payeur",
        "error_amount_invalid": "Le montant doit être un nombre positif valide.",
        "error_concerned_required": "Sélectionnez au moins un participant concerné.",
        "error_expense_name_required": "Le nom de la dépense est requis.",
        "error_invalid_amount_for": "Montant invalide pour {expense_name}.",
        "error_participant_cannot_remove": "{participant_name} ne peut pas être supprimé car ce participant est déjà utilisé dans une ou plusieurs dépenses.",
        "error_participant_name_required": "Le nom du participant est requis.",
        "error_participant_names_invalid": "Les noms des participants ne peuvent contenir que des lettres, chiffres, espaces, apostrophes et traits d'union. Merci de les saisir à nouveau.",
        "error_password_required": "Le mot de passe est requis.",
        "error_passwords_do_not_match": "Les mots de passe ne correspondent pas.",
        "error_payer_required": "Sélectionnez la personne qui a payé la dépense.",
        "error_select_concerned_for": "Sélectionnez au moins un participant concerné pour {expense_name}.",
        "error_select_payer_for": "Sélectionnez qui a payé {expense_name}.",
        "error_title_required": "Le titre est requis.",
        "error_unique_emoji_limit": "Il n'y a plus d'emoji participant unique disponible pour cette session. Supprimez un participant avant d'en ajouter un nouveau.",
        "error_wrong_password": "Mot de passe incorrect.",
        "error_wrong_password_session_not_deleted": "Mot de passe incorrect. La session n'a pas été supprimée.",
    },
}


def get_current_language():
    if not has_request_context():
        return "en"

    for language, quality in request.accept_languages:
        if quality <= 0:
            continue

        primary_language = language.split("-", 1)[0].lower()
        if primary_language == "fr":
            return "fr"
        if primary_language == "en":
            return "en"

    return "en"


def translate(key, **kwargs):
    language = get_current_language()
    text = TRANSLATIONS.get(language, TRANSLATIONS["en"]).get(
        key, TRANSLATIONS["en"].get(key, key)
    )
    if kwargs:
        return text.format(**kwargs)
    return text


@app.after_request
def add_language_header(response):
    response.headers["Content-Language"] = get_current_language()
    response.vary.add("Accept-Language")
    return response


@app.context_processor
def inject_static_version():
    styles_path = os.path.join(app.root_path, "static", "styles.css")
    try:
        static_version = int(os.path.getmtime(styles_path))
    except OSError:
        static_version = 1
    return {
        "current_language": get_current_language(),
        "static_version": static_version,
        "format_cents": format_cents,
        "t": translate,
    }


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
    separator = "," if get_current_language() == "fr" else "."
    return f"{euros}{separator}{cents:02d}\u20ac"


def format_signed_cents(amount_cents):
    absolute_amount_cents = abs(amount_cents)
    euros = absolute_amount_cents // 100
    cents = absolute_amount_cents % 100

    if cents == 0:
        amount_text = f"{euros}\u20ac"
    else:
        separator = "," if get_current_language() == "fr" else "."
        amount_text = f"{euros}{separator}{cents:02d}\u20ac"

    if amount_cents > 0:
        return f"+ {amount_text}"
    if amount_cents < 0:
        return f"-{amount_text}"
    return "0\u20ac"


def parse_amount_cents(amount):
    try:
        amount_cents = int(round(float(amount.replace(",", ".")) * 100))
    except ValueError:
        return None

    if amount_cents < 0:
        return None
    return amount_cents


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
    expenses_table_error=None,
    expenses_edit_mode=False,
    demo_mode=False,
):
    session = sync_session_status(session)
    participants = list_participants(session["public_id"])
    expenses = list_expenses(session["public_id"])
    session_total_cents = sum(
        expense["amount_cents"]
        for expense in expenses
        if expense["status"] != "rejected" and expense["name"].lower() != "reimbursement"
    )
    session_average_cents = 0
    if participants:
        session_average_cents = round(session_total_cents / len(participants))
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
                    expense["payer_name"] or translate("unknown"),
                    record_value(expense, "payer_emoji"),
                )
                if expense["payer_name"]
                else translate("unknown"),
                "concerned_display_names": [
                    participant_label(item["name"], record_value(item, "emoji"))
                    for item in expense["concerned_names"]
                ],
            }
        )
    default_concerned = [participant["public_id"] for participant in participants]

    if expense_concerned is None:
        expense_concerned = default_concerned
    expenses_edit_mode = (
        expenses_edit_mode and role == "admin" and session["status"] == "open"
    )

    return render_template(
        "session_access.html",
        session=session,
        session_total_text=format_cents(session_total_cents),
        session_average_text=format_cents(session_average_cents),
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
        expenses_table_error=expenses_table_error,
        expenses_edit_mode=expenses_edit_mode,
        demo_mode=demo_mode,
    )


def build_demo_page_data():
    participants = [
        {"public_id": "demo-alice", "name": "Alice", "emoji": "\U0001F98A"},
        {"public_id": "demo-bob", "name": "Bob", "emoji": "\U0001F43C"},
        {"public_id": "demo-chloe", "name": "Chloe", "emoji": "\U0001F427"},
        {"public_id": "demo-nora", "name": "Nora", "emoji": "\U0001F422"},
    ]
    participant_by_id = {
        participant["public_id"]: participant for participant in participants
    }

    demo_expenses = [
        {
            "public_id": "demo-expense-1",
            "name": translate("demo_expense_groceries"),
            "amount_cents": 8460,
            "payer_participant_public_id": "demo-alice",
            "concerned_participant_public_ids": [
                "demo-alice",
                "demo-bob",
                "demo-chloe",
                "demo-nora",
            ],
        },
        {
            "public_id": "demo-expense-2",
            "name": translate("demo_expense_parking"),
            "amount_cents": 1800,
            "payer_participant_public_id": "demo-bob",
            "concerned_participant_public_ids": ["demo-alice", "demo-bob"],
        },
        {
            "public_id": "demo-expense-3",
            "name": translate("demo_expense_brunch"),
            "amount_cents": 6300,
            "payer_participant_public_id": "demo-chloe",
            "concerned_participant_public_ids": [
                "demo-alice",
                "demo-bob",
                "demo-chloe",
                "demo-nora",
            ],
        },
        {
            "public_id": "demo-expense-4",
            "name": translate("demo_expense_museum"),
            "amount_cents": 3600,
            "payer_participant_public_id": "demo-nora",
            "concerned_participant_public_ids": [
                "demo-bob",
                "demo-chloe",
                "demo-nora",
            ],
        },
    ]

    approved_expenses = []
    display_expenses = []
    for expense in demo_expenses:
        payer = participant_by_id[expense["payer_participant_public_id"]]
        concerned_participants = [
            participant_by_id[participant_public_id]
            for participant_public_id in expense["concerned_participant_public_ids"]
        ]
        approved_expenses.append(
            {
                "public_id": expense["public_id"],
                "amount_cents": expense["amount_cents"],
                "payer_participant_public_id": expense[
                    "payer_participant_public_id"
                ],
                "concerned_participants": [
                    {
                        "participant_public_id": participant["public_id"],
                        "name": participant["name"],
                        "emoji": participant["emoji"],
                    }
                    for participant in concerned_participants
                ],
            }
        )
        display_expenses.append(
            {
                **expense,
                "status": "approved",
                "submitted_by_role": "admin",
                "payer_display_name": participant_label(
                    payer["name"], payer["emoji"]
                ),
                "concerned_display_names": [
                    participant_label(participant["name"], participant["emoji"])
                    for participant in concerned_participants
                ],
            }
        )

    session_total_cents = sum(expense["amount_cents"] for expense in demo_expenses)
    session_average_cents = round(session_total_cents / len(participants))
    return {
        "session": {
            "title": translate("demo_session_title"),
            "status": "open",
        },
        "role": "viewer",
        "token": "demo",
        "participants": participants,
        "participant_name_by_public_id": {
            participant["public_id"]: participant_label(
                participant["name"], participant["emoji"]
            )
            for participant in participants
        },
        "overview_participants": compute_participant_balances(
            participants, approved_expenses
        ),
        "expenses": display_expenses,
        "reimbursements": compute_reimbursements(participants, approved_expenses),
        "participant_error": None,
        "participant_name": "",
        "expense_error": None,
        "expense_name": "",
        "expense_amount": "",
        "expense_payer": "",
        "expense_concerned": [participant["public_id"] for participant in participants],
        "expense_form_mode": "create",
        "editing_expense_id": None,
        "expenses_table_error": None,
        "expenses_edit_mode": False,
        "session_total_text": format_cents(session_total_cents),
        "session_average_text": format_cents(session_average_cents),
        "demo_mode": True,
    }


@app.route("/")
def index():
    return render_template(
        "index.html",
        error=None,
        setup_mode=not has_create_session_password(),
    )


@app.route("/demo")
def demo():
    return render_template("session_access.html", **build_demo_page_data())


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
                error=translate("error_password_required"),
                setup_mode=True,
            )
        if password != confirm_password:
            return render_template(
                "index.html",
                error=translate("error_passwords_do_not_match"),
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
            error=translate("error_wrong_password"),
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

        if not title:
            return render_template(
                "new_session.html",
                error=translate("error_title_required"),
                title=title,
            )

        session_public_id = insert_session(title=title)
        return redirect(
            url_for("session_created", session_public_id=session_public_id)
        )

    return render_template("new_session.html", error=None, title="")


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
                    error=translate("error_password_required"),
                    setup_mode=True,
                )
            if password != confirm_password:
                return render_template(
                    "superadmin_access.html",
                    error=translate("error_passwords_do_not_match"),
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
            error=translate("error_wrong_password"),
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
            delete_error=translate("error_wrong_password_session_not_deleted"),
        )

    delete_session(session_public_id)
    return redirect(url_for("superadmin", token=token))


@app.route("/s/<token>")
def session_access(token):
    session, role = get_session_by_token(token)
    if session is None:
        abort(404)

    return render_session_page(
        session=session,
        role=role,
        token=token,
        expenses_edit_mode=request.args.get("edit_expenses") == "1",
    )


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
            participant_error=translate("error_participant_name_required"),
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
            participant_error=translate("error_participant_name_required"),
            participant_name=participant_name,
        )

    invalid_names = [name for name in participant_names if not is_valid_participant_name(name)]
    if invalid_names:
        return render_session_page(
            session=session,
            role=role,
            token=token,
            participant_error=translate("error_participant_names_invalid"),
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
            participant_error=translate("error_unique_emoji_limit"),
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
            participant_error=translate(
                "error_participant_cannot_remove",
                participant_name=participant["name"],
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
            expense_error=translate("error_expense_name_required"),
            expense_name=expense_name,
            expense_amount=expense_amount,
            expense_payer=expense_payer,
            expense_concerned=expense_concerned,
        )

    amount_cents = parse_amount_cents(expense_amount)
    if amount_cents is None:
        return render_session_page(
            session=session,
            role=role,
            token=token,
            expense_error=translate("error_amount_invalid"),
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
            expense_error=translate("error_payer_required"),
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
            expense_error=translate("error_concerned_required"),
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


@app.route("/s/<token>/expenses/<expense_public_id>/duplicate", methods=["POST"])
def duplicate_expense(token, expense_public_id):
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

    insert_expense(
        session_public_id=session["public_id"],
        name=original_expense["name"],
        amount_cents=original_expense["amount_cents"],
        payer_participant_public_id=original_expense[
            "payer_participant_public_id"
        ],
        concerned_participant_public_ids=original_expense[
            "concerned_participant_public_ids"
        ],
        submitted_by_role=role,
    )
    return redirect(url_for("session_access", token=token))


@app.route("/s/<token>/expenses/bulk-update", methods=["POST"])
def bulk_update_expenses(token):
    session, role = get_session_by_token(token)
    if session is None:
        abort(404)
    if role != "admin":
        abort(403)
    if session["status"] != "open":
        abort(403)

    participants = list_participants(session["public_id"])
    valid_participant_ids = {participant["public_id"] for participant in participants}
    expenses = list_expenses(session["public_id"])
    updates = []

    for expense in expenses:
        expense_public_id = expense["public_id"]
        amount_raw = request.form.get(f"amount_{expense_public_id}", "").strip()
        payer_participant_public_id = request.form.get(
            f"payer_{expense_public_id}", ""
        ).strip()
        concerned_participant_public_ids = request.form.getlist(
            f"concerned_{expense_public_id}"
        )

        amount_cents = parse_amount_cents(amount_raw)
        if amount_cents is None:
            return render_session_page(
                session=session,
                role=role,
                token=token,
                expenses_table_error=translate(
                    "error_invalid_amount_for", expense_name=expense["name"]
                ),
                expenses_edit_mode=True,
            )

        if payer_participant_public_id not in valid_participant_ids:
            return render_session_page(
                session=session,
                role=role,
                token=token,
                expenses_table_error=translate(
                    "error_select_payer_for", expense_name=expense["name"]
                ),
                expenses_edit_mode=True,
            )

        selected_participant_ids = [
            participant_public_id
            for participant_public_id in concerned_participant_public_ids
            if participant_public_id in valid_participant_ids
        ]
        if not selected_participant_ids:
            return render_session_page(
                session=session,
                role=role,
                token=token,
                expenses_table_error=translate(
                    "error_select_concerned_for", expense_name=expense["name"]
                ),
                expenses_edit_mode=True,
            )

        updates.append(
            {
                "expense_public_id": expense_public_id,
                "name": expense["name"],
                "amount_cents": amount_cents,
                "payer_participant_public_id": payer_participant_public_id,
                "concerned_participant_public_ids": selected_participant_ids,
            }
        )

    for update in updates:
        update_expense(
            session_public_id=session["public_id"],
            expense_public_id=update["expense_public_id"],
            name=update["name"],
            amount_cents=update["amount_cents"],
            payer_participant_public_id=update["payer_participant_public_id"],
            concerned_participant_public_ids=update[
                "concerned_participant_public_ids"
            ],
        )

    return redirect(url_for("session_access", token=token))


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
            expense_error=translate("error_expense_name_required"),
            expense_name=expense_name,
            expense_amount=expense_amount,
            expense_payer=expense_payer,
            expense_concerned=expense_concerned,
            expense_form_mode="edit",
            editing_expense_id=expense_public_id,
        )

    amount_cents = parse_amount_cents(expense_amount)
    if amount_cents is None:
        return render_session_page(
            session=session,
            role=role,
            token=token,
            expense_error=translate("error_amount_invalid"),
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
            expense_error=translate("error_payer_required"),
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
            expense_error=translate("error_concerned_required"),
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
