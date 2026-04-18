import hashlib
import pandas as pd
from pathlib import Path


COLUMN_MAP = {
    "Transaction Date": "date",
    "Post Date": "post_date",
    "Description": "description",
    "Category": "chase_category",
    "Type": "type",
    "Amount": "amount",
}


def _make_hash(row: pd.Series) -> str:
    unique_string = f"{row['date']}|{row['amount']}|{row['description']}"
    return hashlib.md5(unique_string.encode()).hexdigest()


def parse(filepath: str | Path) -> pd.DataFrame:
    df = pd.read_csv(filepath)

    # Validate expected columns are present
    missing = set(COLUMN_MAP.keys()) - set(df.columns)
    if missing:
        raise ValueError(f"Chase credit CSV missing expected columns: {missing}")

    # Drop Memo column if present - always empty
    df = df.drop(columns=["Memo"], errors="ignore")

    # Rename to normalized schema
    df = df.rename(columns=COLUMN_MAP)

    # Parse dates
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y").dt.strftime("%Y-%m-%d")
    df["post_date"] = pd.to_datetime(df["post_date"], format="%m/%d/%Y").dt.strftime("%Y-%m-%d")

    # Flip amount sign so purchases are positive, payments/returns are negative
    df["amount"] = df["amount"] * -1

    # Drop any rows with no amount
    df = df.dropna(subset=["amount"])

    # Add metadata
    df["account_name"] = "Chase Credit"
    df["account_type"] = "credit"
    df["transaction_type"] = None  # not provided by Chase credit export
    df["balance"] = None           # not provided by Chase credit export
    df["hash"] = df.apply(_make_hash, axis=1)

    return df[["date", "post_date", "description", "amount", "type", "balance",
               "transaction_type", "chase_category", "account_name", "account_type", "hash"]]