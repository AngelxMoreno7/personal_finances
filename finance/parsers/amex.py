import hashlib
import pandas as pd
from pathlib import Path


# Columns always present
REQUIRED_COLUMNS = ["Date", "Description", "Amount", "Category"]

# Extra columns Amex includes when you select full export
EXTRA_COLUMNS = [
    "Extended Details",
    "Appears On Your Statement As",
    "Address",
    "Zip Code",
    "Country",
    "Reference",
    "City/State",
]

# Of the extras, only these are worth keeping
KEEP_EXTRA = ["City/State", "Reference"]


def _make_hash(row: pd.Series) -> str:
    # Use Reference number if available for stronger deduplication
    ref = row.get("reference", row["description"])
    unique_string = f"{row['date']}|{row['amount']}|{ref}"
    return hashlib.md5(unique_string.encode()).hexdigest()


def parse(filepath: str | Path) -> pd.DataFrame:
    df = pd.read_csv(filepath)

    # Validate required columns are present
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Amex CSV missing expected columns: {missing}")

    # Drop extra columns we don't care about, ignore if not present
    drop_cols = [c for c in EXTRA_COLUMNS if c in df.columns and c not in KEEP_EXTRA]
    df = df.drop(columns=drop_cols)

    # Rename to normalized schema
    rename_map = {
        "Date": "date",
        "Description": "description",
        "Amount": "amount",
        "Category": "amex_category",
        "City/State": "city_state",
        "Reference": "reference",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Parse date
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y").dt.strftime("%Y-%m-%d")

    # Drop any rows with no amount
    df = df.dropna(subset=["amount"])

    # Add metadata
    df["account_name"] = "Amex Credit"
    df["account_type"] = "credit"
    df["transaction_type"] = None
    df["type"] = None
    df["balance"] = None
    df["post_date"] = None
    df["chase_category"] = None
    df["hash"] = df.apply(_make_hash, axis=1)

    # Only include city_state and reference if they were in the export
    optional = [c for c in ["city_state", "reference"] if c in df.columns]

    return df[["date", "post_date", "description", "amount", "type", "balance",
               "transaction_type", "chase_category", "amex_category",
               "account_name", "account_type", "hash"] + optional]