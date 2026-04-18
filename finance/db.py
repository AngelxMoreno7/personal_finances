import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "db" / "finance.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL UNIQUE,
            account_type TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS categories (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT NOT NULL UNIQUE,
            color TEXT
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            date             TEXT NOT NULL,
            description      TEXT NOT NULL,
            amount           REAL NOT NULL,
            transaction_type TEXT,
            type             TEXT,
            balance          REAL,
            post_date        TEXT,
            chase_category   TEXT,
            amex_category    TEXT,
            city_state       TEXT,
            reference        TEXT,
            account_id       INTEGER REFERENCES accounts(id),
            category_id      INTEGER REFERENCES categories(id),
            hash             TEXT NOT NULL UNIQUE
        );
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")