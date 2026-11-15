CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    is_admin boolean NOT NULL DEFAULT False,
    user_role TEXT NOT NULL DEFAULT buyer,
    UserName TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);