CREATE TABLE IF NOT EXISTS sessions (
    public_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open', 'frozen', 'closed')),
    admin_token TEXT NOT NULL UNIQUE,
    viewer_token TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS expenses (
    public_id TEXT PRIMARY KEY,
    session_public_id TEXT NOT NULL,
    submitted_by_role TEXT NOT NULL CHECK (submitted_by_role IN ('admin', 'viewer')),
    payer_participant_public_id TEXT,
    name TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_public_id) REFERENCES sessions (public_id),
    FOREIGN KEY (payer_participant_public_id) REFERENCES participants (public_id)
);

CREATE TABLE IF NOT EXISTS participants (
    public_id TEXT PRIMARY KEY,
    session_public_id TEXT NOT NULL,
    name TEXT NOT NULL,
    emoji TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_public_id) REFERENCES sessions (public_id)
);

CREATE TABLE IF NOT EXISTS expense_participants (
    expense_public_id TEXT NOT NULL,
    participant_public_id TEXT NOT NULL,
    PRIMARY KEY (expense_public_id, participant_public_id),
    FOREIGN KEY (expense_public_id) REFERENCES expenses (public_id),
    FOREIGN KEY (participant_public_id) REFERENCES participants (public_id)
);

CREATE TABLE IF NOT EXISTS app_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
