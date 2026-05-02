import pandas as pd
from finance.db import get_connection, init_db
from finance.categorizer import categorize
from finance.parsers import chase_checking, chase_credit, amex, venmo

PARSERS = {
    "chase_checking": chase_checking.parse,
    "chase_credit":   chase_credit.parse,
    "amex":           amex.parse,
    "venmo":          venmo.parse,
}


def _get_or_create_account(cursor, name: str, account_type: str) -> int:
    cursor.execute("SELECT id FROM accounts WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        return row["id"]
    cursor.execute(
        "INSERT INTO accounts (name, account_type) VALUES (?, ?)",
        (name, account_type)
    )
    return cursor.lastrowid


def _get_or_create_category(cursor, name: str) -> int:
    from finance.categorizer import load_categories
    cursor.execute("SELECT id FROM categories WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        return row["id"]
    # Look up color from yaml if available
    categories = load_categories()
    color = categories.get(name, {}).get("color", "#BDC3C7")
    cursor.execute(
        "INSERT INTO categories (name, color) VALUES (?, ?)",
        (name, color)
    )
    return cursor.lastrowid


def _insert_transactions(df: pd.DataFrame) -> tuple[int, int]:
    """
    Inserts a normalized dataframe into the database.
    Returns (inserted_count, skipped_count).
    """
    conn = get_connection()
    cursor = conn.cursor()

    inserted = 0
    skipped = 0

    for _, row in df.iterrows():
        row = row.where(pd.notna(row), None).to_dict()
        # Check for duplicate via hash
        cursor.execute("SELECT id FROM transactions WHERE hash = ?", (row["hash"],))
        if cursor.fetchone():
            skipped += 1
            continue

        account_id = _get_or_create_account(
            cursor, row["account_name"], row["account_type"]
        )

        category_name = categorize(
            description=row["description"],
            amount=row.get("amount"),
            chase_category=row.get("chase_category"),
            amex_category=row.get("amex_category"),
        )
        category_id = _get_or_create_category(cursor, category_name)

        cursor.execute("""
            INSERT INTO transactions (
                date, description, amount, type, balance,
                transaction_type, post_date, chase_category, amex_category,
                city_state, reference, account_id, category_id, hash
            ) VALUES (
                :date, :description, :amount, :type, :balance,
                :transaction_type, :post_date, :chase_category, :amex_category,
                :city_state, :reference, :account_id, :category_id, :hash
            )
        """, {
            "date":             row["date"],
            "description":      row["description"],
            "amount":           row["amount"],
            "type":             row.get("type"),
            "balance":          row.get("balance"),
            "transaction_type": row.get("transaction_type"),
            "post_date":        row.get("post_date"),
            "chase_category":   row.get("chase_category"),
            "amex_category":    row.get("amex_category"),
            "city_state":       row.get("city_state"),
            "reference":        row.get("reference"),
            "account_id":       account_id,
            "category_id":      category_id,
            "hash":             row["hash"],
        })
        inserted += 1

    conn.commit()
    conn.close()
    return inserted, skipped


def import_file(filepath: str, source: str) -> tuple[int, int]:
    """
    Main entry point. Parse a CSV file and import into the database.

    Args:
        filepath: path to the CSV file
        source:   one of 'chase_checking', 'chase_credit', 'amex'

    Returns:
        (inserted_count, skipped_count)
    """
    if source not in PARSERS:
        raise ValueError(f"Unknown source '{source}'. Must be one of: {list(PARSERS.keys())}")

    init_db()

    parse = PARSERS[source]
    df = parse(filepath)

    inserted, skipped = _insert_transactions(df)
    return inserted, skipped