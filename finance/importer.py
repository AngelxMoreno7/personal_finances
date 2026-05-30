import pandas as pd
from finance.db import get_connection, init_db
from finance.categorizer import categorize, get_category_for_subcategory
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
    cursor.execute("SELECT id FROM categories WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        return row["id"]
    cursor.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    return cursor.lastrowid


def _get_or_create_subcategory(cursor, name: str, color: str, category_id: int) -> int:
    cursor.execute("SELECT id FROM subcategories WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        return row["id"]
    cursor.execute(
        "INSERT INTO subcategories (name, color, category_id) VALUES (?, ?, ?)",
        (name, color, category_id)
    )
    return cursor.lastrowid


def _insert_transactions(df: pd.DataFrame) -> tuple[int, int]:
    conn = get_connection()
    cursor = conn.cursor()

    from finance.categorizer import load_categories
    all_subcategories = load_categories()

    inserted = 0
    skipped = 0

    for _, row in df.iterrows():
        row = row.where(pd.notna(row), None).to_dict()

        # Check for duplicate
        cursor.execute("SELECT id FROM transactions WHERE hash = ?", (row["hash"],))
        if cursor.fetchone():
            skipped += 1
            continue

        account_id = _get_or_create_account(
            cursor, row["account_name"], row["account_type"]
        )

        subcategory_name = categorize(
            description=row["description"],
            amount=row.get("amount"),
            chase_category=row.get("chase_category"),
            amex_category=row.get("amex_category"),
        )

        category_name = get_category_for_subcategory(subcategory_name)

        category_id = _get_or_create_category(cursor, category_name)

        subcat_config = all_subcategories.get(subcategory_name, {})
        color = subcat_config.get("color", "#BDC3C7")
        subcategory_id = _get_or_create_subcategory(cursor, subcategory_name, color, category_id)

        cursor.execute("""
            INSERT INTO transactions (
                date, description, amount, type, balance,
                transaction_type, post_date, chase_category, amex_category,
                city_state, reference, account_id, subcategory_id, manually_categorized, hash
            ) VALUES (
                :date, :description, :amount, :type, :balance,
                :transaction_type, :post_date, :chase_category, :amex_category,
                :city_state, :reference, :account_id, :subcategory_id, :manually_categorized, :hash
            )
        """, {
            "date":                 row["date"],
            "description":          row["description"],
            "amount":               row["amount"],
            "type":                 row.get("type"),
            "balance":              row.get("balance"),
            "transaction_type":     row.get("transaction_type"),
            "post_date":            row.get("post_date"),
            "chase_category":       row.get("chase_category"),
            "amex_category":        row.get("amex_category"),
            "city_state":           row.get("city_state"),
            "reference":            row.get("reference"),
            "account_id":           account_id,
            "subcategory_id":       subcategory_id,
            "manually_categorized": 0,
            "hash":                 row["hash"],
        })
        inserted += 1

    conn.commit()
    conn.close()
    return inserted, skipped


def import_file(filepath: str, source: str) -> tuple[int, int]:
    if source not in PARSERS:
        raise ValueError(f"Unknown source '{source}'. Must be one of: {list(PARSERS.keys())}")

    init_db()
    parse = PARSERS[source]
    df = parse(filepath)
    return _insert_transactions(df)