# scripts/recategorize.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from finance.db import get_connection, init_db
from finance.categorizer import categorize

def recategorize_all():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.id, t.description, t.chase_category, t.amex_category
        FROM transactions t
    """)
    rows = cursor.fetchall()

    updated = 0
    for row in rows:
        category_name = categorize(
            description=row["description"],
            chase_category=row["chase_category"],
            amex_category=row["amex_category"],
        )

        # Get or create category
        cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
        cat_row = cursor.fetchone()
        if cat_row:
            category_id = cat_row["id"]
        else:
            from finance.categorizer import load_categories
            categories = load_categories()
            color = categories.get(category_name, {}).get("color", "#BDC3C7")
            cursor.execute(
                "INSERT INTO categories (name, color) VALUES (?, ?)",
                (category_name, color)
            )
            category_id = cursor.lastrowid

        cursor.execute(
            "UPDATE transactions SET category_id = ? WHERE id = ?",
            (category_id, row["id"])
        )
        updated += 1

    conn.commit()
    conn.close()
    print(f"Recategorized {updated} transactions.")

if __name__ == "__main__":
    recategorize_all()