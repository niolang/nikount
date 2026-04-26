import secrets
import sqlite3
from pathlib import Path
from uuid import uuid4

from flask import g


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "nikount.db"
ANIMAL_EMOJIS = [
    "\U0001F436",
    "\U0001F431",
    "\U0001F42D",
    "\U0001F439",
    "\U0001F430",
    "\U0001F98A",
    "\U0001F43B",
    "\U0001F43C",
    "\U0001F428",
    "\U0001F42F",
    "\U0001F981",
    "\U0001F42E",
    "\U0001F437",
    "\U0001F438",
    "\U0001F435",
    "\U0001F414",
    "\U0001F427",
    "\U0001F426",
    "\U0001F989",
    "\U0001F986",
    "\U0001F984",
    "\U0001F419",
    "\U0001F422",
    "\U0001F42C",
    "\U0001F98B",
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)


def init_db():
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        schema_path = BASE_DIR / "schema.sql"
        with open(schema_path, "r", encoding="utf-8") as schema_file:
            connection.executescript(schema_file.read())
        ensure_unique_participant_emojis(connection)
        connection.commit()
    finally:
        connection.close()


def generate_public_id():
    return str(uuid4())


def generate_token():
    return secrets.token_urlsafe(32)


def get_used_participant_emojis(connection, session_public_id, excluded_public_id=None):
    if excluded_public_id:
        rows = connection.execute(
            """
            SELECT emoji
            FROM participants
            WHERE session_public_id = ?
              AND public_id != ?
              AND emoji IS NOT NULL
              AND emoji != ''
            """,
            (session_public_id, excluded_public_id),
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT emoji
            FROM participants
            WHERE session_public_id = ?
              AND emoji IS NOT NULL
              AND emoji != ''
            """,
            (session_public_id,),
        ).fetchall()

    return {row[0] for row in rows}


def choose_unique_participant_emoji(connection, session_public_id, excluded_public_id=None):
    used_emojis = get_used_participant_emojis(
        connection, session_public_id, excluded_public_id
    )
    available_emojis = [emoji for emoji in ANIMAL_EMOJIS if emoji not in used_emojis]

    if not available_emojis:
        raise ValueError("No unique participant emoji available for this session.")

    return secrets.choice(available_emojis)


def ensure_unique_participant_emojis(connection):
    session_rows = connection.execute(
        """
        SELECT public_id
        FROM sessions
        """
    ).fetchall()

    for session_row in session_rows:
        session_public_id = session_row[0]
        participant_rows = connection.execute(
            """
            SELECT public_id, emoji
            FROM participants
            WHERE session_public_id = ?
            ORDER BY created_at ASC, name ASC, public_id ASC
            """,
            (session_public_id,),
        ).fetchall()

        used_emojis = set()
        for participant_row in participant_rows:
            participant_public_id = participant_row[0]
            emoji = participant_row[1]

            if emoji and emoji in ANIMAL_EMOJIS and emoji not in used_emojis:
                used_emojis.add(emoji)
                continue

            available_emojis = [
                candidate for candidate in ANIMAL_EMOJIS if candidate not in used_emojis
            ]
            if not available_emojis:
                raise ValueError("No unique participant emoji available for this session.")

            new_emoji = secrets.choice(available_emojis)
            connection.execute(
                """
                UPDATE participants
                SET emoji = ?
                WHERE public_id = ?
                """,
                (new_emoji, participant_public_id),
            )
            used_emojis.add(new_emoji)


def get_or_create_superadmin_token():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            """
            SELECT value
            FROM app_metadata
            WHERE key = 'superadmin_token'
            """
        ).fetchone()

        if row is not None:
            return row["value"]

        token = generate_token()
        connection.execute(
            """
            INSERT INTO app_metadata (key, value)
            VALUES ('superadmin_token', ?)
            """,
            (token,),
        )
        connection.commit()
        return token
    finally:
        connection.close()


def get_metadata_value(key):
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            """
            SELECT value
            FROM app_metadata
            WHERE key = ?
            """,
            (key,),
        ).fetchone()
        if row is None:
            return None
        return row["value"]
    finally:
        connection.close()


def set_metadata_value(key, value):
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        connection.execute(
            """
            INSERT INTO app_metadata (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        connection.commit()
    finally:
        connection.close()


def list_sessions():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        return connection.execute(
            """
            SELECT s.public_id, s.title, s.description, s.status,
                   s.admin_token, s.viewer_token, s.created_at,
                   COALESCE(SUM(CASE WHEN e.status != 'rejected' THEN e.amount_cents ELSE 0 END), 0) AS total_amount_cents
            FROM sessions s
            LEFT JOIN expenses e ON e.session_public_id = s.public_id
            GROUP BY s.public_id, s.title, s.description, s.status,
                     s.admin_token, s.viewer_token, s.created_at
            ORDER BY s.created_at DESC, s.title ASC
            """
        ).fetchall()
    finally:
        connection.close()


def delete_session(session_public_id):
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        connection.execute(
            """
            DELETE FROM expense_participants
            WHERE expense_public_id IN (
                SELECT public_id
                FROM expenses
                WHERE session_public_id = ?
            )
            """,
            (session_public_id,),
        )
        connection.execute(
            """
            DELETE FROM expenses
            WHERE session_public_id = ?
            """,
            (session_public_id,),
        )
        connection.execute(
            """
            DELETE FROM participants
            WHERE session_public_id = ?
            """,
            (session_public_id,),
        )
        cursor = connection.execute(
            """
            DELETE FROM sessions
            WHERE public_id = ?
            """,
            (session_public_id,),
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()


def insert_session(title, description):
    session_public_id = generate_public_id()
    admin_token = generate_token()
    viewer_token = generate_token()

    connection = sqlite3.connect(DATABASE_PATH)
    try:
        connection.execute(
            """
            INSERT INTO sessions (
                public_id,
                title,
                description,
                status,
                admin_token,
                viewer_token
            )
            VALUES (?, ?, ?, 'open', ?, ?)
            """,
            (
                session_public_id,
                title,
                description,
                admin_token,
                viewer_token,
            ),
        )
        connection.commit()
    finally:
        connection.close()

    return session_public_id


def get_session_by_public_id(session_public_id):
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            """
            SELECT public_id, title, description, status, admin_token, viewer_token,
                   created_at
            FROM sessions
            WHERE public_id = ?
            """,
            (session_public_id,),
        ).fetchone()
        return row
    finally:
        connection.close()


def get_session_by_token(token):
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        session = connection.execute(
            """
            SELECT public_id, title, description, status, admin_token, viewer_token,
                   created_at
            FROM sessions
            WHERE admin_token = ? OR viewer_token = ?
            """,
            (token, token),
        ).fetchone()

        if session is None:
            return None, None

        role = "admin" if session["admin_token"] == token else "viewer"
        return session, role
    finally:
        connection.close()


def update_session_status(session_public_id, status):
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        cursor = connection.execute(
            """
            UPDATE sessions
            SET status = ?
            WHERE public_id = ?
            """,
            (status, session_public_id),
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()


def list_participants(session_public_id):
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        return connection.execute(
            """
            SELECT public_id, name, emoji, created_at
            FROM participants
            WHERE session_public_id = ?
            ORDER BY created_at ASC, name ASC
            """,
            (session_public_id,),
        ).fetchall()
    finally:
        connection.close()


def insert_participant(session_public_id, name):
    participant_public_id = generate_public_id()

    connection = sqlite3.connect(DATABASE_PATH)
    try:
        emoji = choose_unique_participant_emoji(connection, session_public_id)
        connection.execute(
            """
            INSERT INTO participants (public_id, session_public_id, name, emoji)
            VALUES (?, ?, ?, ?)
            """,
            (participant_public_id, session_public_id, name, emoji),
        )
        connection.commit()
    finally:
        connection.close()

    return participant_public_id


def get_participant(session_public_id, participant_public_id):
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        return connection.execute(
            """
            SELECT public_id, name, emoji
            FROM participants
            WHERE session_public_id = ? AND public_id = ?
            """,
            (session_public_id, participant_public_id),
        ).fetchone()
    finally:
        connection.close()


def participant_is_used(session_public_id, participant_public_id):
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        payer_row = connection.execute(
            """
            SELECT 1
            FROM expenses
            WHERE session_public_id = ? AND payer_participant_public_id = ?
            LIMIT 1
            """,
            (session_public_id, participant_public_id),
        ).fetchone()

        if payer_row is not None:
            return True

        concerned_row = connection.execute(
            """
            SELECT 1
            FROM expense_participants ep
            JOIN expenses e ON e.public_id = ep.expense_public_id
            WHERE e.session_public_id = ? AND ep.participant_public_id = ?
            LIMIT 1
            """,
            (session_public_id, participant_public_id),
        ).fetchone()

        return concerned_row is not None
    finally:
        connection.close()


def delete_participant(session_public_id, participant_public_id):
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        cursor = connection.execute(
            """
            DELETE FROM participants
            WHERE session_public_id = ? AND public_id = ?
            """,
            (session_public_id, participant_public_id),
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()


def delete_expense(session_public_id, expense_public_id):
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        connection.execute(
            """
            DELETE FROM expense_participants
            WHERE expense_public_id = ?
            """,
            (expense_public_id,),
        )
        cursor = connection.execute(
            """
            DELETE FROM expenses
            WHERE session_public_id = ? AND public_id = ?
            """,
            (session_public_id, expense_public_id),
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()


def insert_expense(
    session_public_id,
    name,
    amount_cents,
    payer_participant_public_id,
    concerned_participant_public_ids,
    submitted_by_role,
    status=None,
):
    expense_public_id = generate_public_id()
    if status is None:
        status = "approved" if submitted_by_role == "admin" else "pending"

    connection = sqlite3.connect(DATABASE_PATH)
    try:
        connection.execute(
            """
            INSERT INTO expenses (
                public_id,
                session_public_id,
                submitted_by_role,
                name,
                amount_cents,
                status,
                payer_participant_public_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                expense_public_id,
                session_public_id,
                submitted_by_role,
                name,
                amount_cents,
                status,
                payer_participant_public_id,
            ),
        )

        for participant_public_id in concerned_participant_public_ids:
            connection.execute(
                """
                INSERT INTO expense_participants (
                    expense_public_id,
                    participant_public_id
                )
                VALUES (?, ?)
                """,
                (expense_public_id, participant_public_id),
            )

        connection.commit()
    finally:
        connection.close()

    return expense_public_id


def list_expenses(session_public_id):
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        expense_rows = connection.execute(
            """
            SELECT e.public_id, e.name, e.amount_cents, e.status,
                   e.created_at, e.submitted_by_role, payer.name AS payer_name,
                   payer.emoji AS payer_emoji
            FROM expenses e
            LEFT JOIN participants payer
                ON payer.public_id = e.payer_participant_public_id
            WHERE e.session_public_id = ?
            ORDER BY e.created_at DESC
            """,
            (session_public_id,),
        ).fetchall()

        concerned_rows = connection.execute(
            """
            SELECT ep.expense_public_id, p.name, p.emoji
            FROM expense_participants ep
            JOIN participants p ON p.public_id = ep.participant_public_id
            JOIN expenses e ON e.public_id = ep.expense_public_id
            WHERE e.session_public_id = ?
            ORDER BY p.name ASC
            """,
            (session_public_id,),
        ).fetchall()
    finally:
        connection.close()

    concerned_by_expense = {}
    for row in concerned_rows:
        concerned_by_expense.setdefault(row["expense_public_id"], []).append(
            {
                "name": row["name"],
                "emoji": row["emoji"],
            }
        )

    expenses = []
    for row in expense_rows:
        expenses.append(
            {
                "public_id": row["public_id"],
                "name": row["name"],
                "amount_cents": row["amount_cents"],
                "status": row["status"],
                "created_at": row["created_at"],
                "submitted_by_role": row["submitted_by_role"],
                "payer_name": row["payer_name"],
                "payer_emoji": row["payer_emoji"],
                "concerned_names": concerned_by_expense.get(row["public_id"], []),
            }
        )

    return expenses


def get_expense(session_public_id, expense_public_id):
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        expense_row = connection.execute(
            """
            SELECT public_id, name, amount_cents, status,
                   payer_participant_public_id, created_at, submitted_by_role
            FROM expenses
            WHERE session_public_id = ? AND public_id = ?
            """,
            (session_public_id, expense_public_id),
        ).fetchone()

        if expense_row is None:
            return None

        concerned_rows = connection.execute(
            """
            SELECT participant_public_id
            FROM expense_participants
            WHERE expense_public_id = ?
            ORDER BY participant_public_id ASC
            """,
            (expense_public_id,),
        ).fetchall()
    finally:
        connection.close()

    return {
        "public_id": expense_row["public_id"],
        "name": expense_row["name"],
        "amount_cents": expense_row["amount_cents"],
        "status": expense_row["status"],
        "payer_participant_public_id": expense_row["payer_participant_public_id"],
        "created_at": expense_row["created_at"],
        "submitted_by_role": expense_row["submitted_by_role"],
        "concerned_participant_public_ids": [
            row["participant_public_id"] for row in concerned_rows
        ],
    }


def update_expense(
    session_public_id,
    expense_public_id,
    name,
    amount_cents,
    payer_participant_public_id,
    concerned_participant_public_ids,
):
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        cursor = connection.execute(
            """
            UPDATE expenses
            SET name = ?,
                amount_cents = ?,
                payer_participant_public_id = ?
            WHERE session_public_id = ? AND public_id = ?
            """,
            (
                name,
                amount_cents,
                payer_participant_public_id,
                session_public_id,
                expense_public_id,
            ),
        )

        if cursor.rowcount == 0:
            connection.rollback()
            return False

        connection.execute(
            """
            DELETE FROM expense_participants
            WHERE expense_public_id = ?
            """,
            (expense_public_id,),
        )

        for participant_public_id in concerned_participant_public_ids:
            connection.execute(
                """
                INSERT INTO expense_participants (
                    expense_public_id,
                    participant_public_id
                )
                VALUES (?, ?)
                """,
                (expense_public_id, participant_public_id),
            )

        connection.commit()
        return True
    finally:
        connection.close()


def update_expense_status(session_public_id, expense_public_id, status):
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        cursor = connection.execute(
            """
            UPDATE expenses
            SET status = ?
            WHERE session_public_id = ? AND public_id = ?
            """,
            (status, session_public_id, expense_public_id),
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()


def get_approved_expenses_for_reimbursements(session_public_id):
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        expense_rows = connection.execute(
            """
            SELECT e.public_id, e.amount_cents, e.payer_participant_public_id,
                   payer.name AS payer_name, payer.emoji AS payer_emoji
            FROM expenses e
            JOIN participants payer
                ON payer.public_id = e.payer_participant_public_id
            WHERE e.session_public_id = ? AND e.status = 'approved'
            ORDER BY e.created_at ASC, e.public_id ASC
            """,
            (session_public_id,),
        ).fetchall()

        participant_rows = connection.execute(
            """
            SELECT public_id, name, emoji
            FROM participants
            WHERE session_public_id = ?
            ORDER BY name ASC, public_id ASC
            """,
            (session_public_id,),
        ).fetchall()

        concerned_rows = connection.execute(
            """
            SELECT ep.expense_public_id, ep.participant_public_id, p.name, p.emoji
            FROM expense_participants ep
            JOIN participants p ON p.public_id = ep.participant_public_id
            JOIN expenses e ON e.public_id = ep.expense_public_id
            WHERE e.session_public_id = ? AND e.status = 'approved'
            ORDER BY ep.expense_public_id ASC, p.name ASC, p.public_id ASC
            """,
            (session_public_id,),
        ).fetchall()
    finally:
        connection.close()

    concerned_by_expense = {}
    for row in concerned_rows:
        concerned_by_expense.setdefault(row["expense_public_id"], []).append(
            {
                "participant_public_id": row["participant_public_id"],
                "name": row["name"],
                "emoji": row["emoji"],
            }
        )

    expenses = []
    for row in expense_rows:
        expenses.append(
            {
                "public_id": row["public_id"],
                "amount_cents": row["amount_cents"],
                "payer_participant_public_id": row["payer_participant_public_id"],
                "payer_name": row["payer_name"],
                "payer_emoji": row["payer_emoji"],
                "concerned_participants": concerned_by_expense.get(row["public_id"], []),
            }
        )

    participants = [
        {"public_id": row["public_id"], "name": row["name"], "emoji": row["emoji"]}
        for row in participant_rows
    ]

    return participants, expenses
