import hashlib
import pandas as pd
from pathlib import Path


COLUMN_MAP = {
    "Details":          "date",
    "Posting Date":     "description",
    "Description":      "amount",
    "Amount":           "type",
    "Type":             "balance",
    "Balance":          "transaction_type",
    "Check or Slip #":  "check_number",
}


def _make_hash(row: pd.Series) -> str:
    unique_string = f"{row['date']}|{row['amount']}|{row['description']}"
    return hashlib.md5(unique_string.encode()).hexdigest()


def parse(filepath: str | Path) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    df["transaction_type"] = df.index  # DEBIT/CREDIT lives here
    df = df.reset_index(drop=True)

    # Validate expected columns are present
    missing = set(COLUMN_MAP.keys()) - set(df.columns)
    if missing:
        raise ValueError(f"Chase checking CSV missing expected columns: {missing}")

    # Rename to normalized schema
    df = df.rename(columns=COLUMN_MAP)

    # Parse date
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y").dt.strftime("%Y-%m-%d")

    # Drop any rows with no amount (sometimes Chase adds blank trailing rows)
    df = df.dropna(subset=["amount"])

    # Add metadata
    df["account_name"] = "Chase Checking"
    df["account_type"] = "checking"
    df["hash"] = df.apply(_make_hash, axis=1)

    return df[["date", "description", "amount", "type", "balance",
           "transaction_type", "account_name", "account_type", "hash"]]