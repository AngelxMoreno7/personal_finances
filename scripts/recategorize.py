import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from finance.db import get_connection
from finance.categorizer import categorize, get_category_for_subcategory, load_categories


def recategorize_all():
    conn = get_connection()
    cursor = conn.cursor()

    all_subcategories = load_categories()

    cursor.execute("""
        SELECT t.id, t.description, t.amount, t.chase_category, t.amex_category, t.subcategory_id
        FROM transactions t
        WHERE t.manually_categorized = 0
    """)
    rows = cursor.fetchall()

    updated = 0
    unchanged = 0

    for row in rows:
        subcategory_name = categorize(
            description=row["description"],
            amount=row["amount"],
            chase_category=row["chase_category"],
            amex_category=row["amex_category"],
        )

        category_name = get_category_for_subcategory(subcategory_name)

        # Get or create category
        cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
        cat_row = cursor.fetchone()
        if cat_row:
            category_id = cat_row["id"]
        else:
            cursor.execute("INSERT INTO categories (name) VALUES (?)", (category_name,))
            category_id = cursor.lastrowid

        # Get or create subcategory
        cursor.execute("SELECT id FROM subcategories WHERE name = ?", (subcategory_name,))
        subcat_row = cursor.fetchone()
        if subcat_row:
            subcategory_id = subcat_row["id"]
        else:
            color = all_subcategories.get(subcategory_name, {}).get("color", "#BDC3C7")
            cursor.execute(
                "INSERT INTO subcategories (name, color, category_id) VALUES (?, ?, ?)",
                (subcategory_name, color, category_id)
            )
            subcategory_id = cursor.lastrowid

        # Update subcategory's category_id in case it changed
        cursor.execute(
            "UPDATE subcategories SET category_id = ? WHERE id = ?",
            (category_id, subcategory_id)
        )

        if subcategory_id != row["subcategory_id"]:
            cursor.execute(
                "UPDATE transactions SET subcategory_id = ? WHERE id = ?",
                (subcategory_id, row["id"])
            )
            updated += 1
        else:
            unchanged += 1

    conn.commit()
    conn.close()
    print(f"Done. {updated} transactions recategorized, {unchanged} unchanged.")


if __name__ == "__main__":
    recategorize_all()