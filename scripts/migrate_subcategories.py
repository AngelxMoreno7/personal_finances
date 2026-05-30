import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
from finance.db import get_connection, DB_PATH


def migrate():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Create categories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

    # 2. Create subcategories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subcategories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            color       TEXT,
            category_id INTEGER REFERENCES categories(id)
        )
    """)

    # 3. Migrate existing categories table rows into subcategories
    cursor.execute("SELECT id, name, color FROM categories")
    old_cats = cursor.fetchall()

    for row in old_cats:
        cursor.execute("""
            INSERT OR IGNORE INTO subcategories (id, name, color)
            VALUES (?, ?, ?)
        """, (row["id"], row["name"], row["color"]))

    # 4. Rename category_id to subcategory_id in transactions
    # SQLite doesn't support renaming columns directly so we recreate the table
    cursor.executescript("""
        ALTER TABLE transactions RENAME TO transactions_old;

        CREATE TABLE transactions (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            date                 TEXT NOT NULL,
            description          TEXT NOT NULL,
            amount               REAL NOT NULL,
            transaction_type     TEXT,
            type                 TEXT,
            balance              REAL,
            post_date            TEXT,
            chase_category       TEXT,
            amex_category        TEXT,
            city_state           TEXT,
            reference            TEXT,
            account_id           INTEGER REFERENCES accounts(id),
            subcategory_id       INTEGER REFERENCES subcategories(id),
            manually_categorized INTEGER DEFAULT 0,
            hash                 TEXT NOT NULL UNIQUE
        );

        INSERT INTO transactions
        SELECT
            id, date, description, amount, transaction_type, type, balance,
            post_date, chase_category, amex_category, city_state, reference,
            account_id, category_id, manually_categorized, hash
        FROM transactions_old;

        DROP TABLE transactions_old;
    """)

    # 5. Drop old categories table and replace with new one
    cursor.executescript("""
        DROP TABLE categories;

        CREATE TABLE categories (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
    """)

    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    migrate()