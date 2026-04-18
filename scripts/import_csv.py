import argparse
import sys
from pathlib import Path

# Make sure the project root is on the path so `finance` package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from finance.importer import import_file


def main():
    parser = argparse.ArgumentParser(
        description="Import a bank CSV file into the personal finance database."
    )
    parser.add_argument(
        "filepath",
        type=str,
        help="Path to the CSV file to import"
    )
    parser.add_argument(
        "source",
        type=str,
        choices=["chase_checking", "chase_credit", "amex"],
        help="Which bank/account this CSV came from"
    )

    args = parser.parse_args()

    filepath = Path(args.filepath)
    if not filepath.exists():
        print(f"Error: file not found: {filepath}")
        sys.exit(1)

    print(f"Importing {filepath.name} as {args.source}...")

    inserted, skipped = import_file(str(filepath), args.source)

    print(f"Done. {inserted} transactions inserted, {skipped} skipped (duplicates).")


if __name__ == "__main__":
    main()