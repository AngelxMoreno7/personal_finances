import hashlib
import pandas as pd
from pathlib import Path


EXCLUDE_TYPES = {"Standard Transfer", "Merchant Transfer", "Charge"}


def _parse_amount(amount_str: str) -> float | None:
    """Convert '+ $20.00' or '- $35.00' to float. Positive = received, negative = sent."""
    if pd.isna(amount_str):
        return None
    cleaned = str(amount_str).replace("$", "").replace(",", "").replace(" ", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _make_hash(row: pd.Series) -> str:
    unique_string = f"venmo|{row['venmo_id']}|{row['amount']}"
    return hashlib.md5(unique_string.encode()).hexdigest()


def _format_description(row: pd.Series) -> str:
    note = str(row.get("note", "")).strip()
    from_user = str(row.get("from", "")).strip()
    to_user = str(row.get("to", "")).strip()
    amount = row["amount"]

    # After sign flip, negative = received, positive = sent
    if amount > 0:
        # Money sent — show who received it
        counterparty = f"To: {to_user}" if to_user and to_user.lower() not in ("nan", "none", "") else ""
    else:
        # Money received — show who sent it
        counterparty = f"From: {from_user}" if from_user and from_user.lower() not in ("nan", "none", "") else ""

    parts = []
    if note and note.lower() not in ("nan", "none", ""):
        parts.append(note)
    if counterparty:
        parts.append(counterparty)

    return " · ".join(parts) if parts else "Venmo Transaction"


def parse(filepath: str | Path) -> pd.DataFrame:
    # Venmo CSVs have 2 junk rows before the real header
    df = pd.read_csv(filepath, skiprows=2, dtype={"ID": str})

    # Drop the leading unnamed column
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    # Rename columns to safe names
    df = df.rename(columns={
        "ID":             "venmo_id",
        "Datetime":       "date",
        "Type":           "type",
        "Status":         "status",
        "Note":           "note",
        "From":           "from",
        "To":             "to",
        "Amount (total)": "amount_raw",
    })

    # Keep only the columns we need
    keep = ["venmo_id", "date", "type", "status", "note", "from", "to", "amount_raw"]
    df = df[[c for c in keep if c in df.columns]]

    # Drop rows with no ID (header artifacts, balance rows, footer rows)
    df = df.dropna(subset=["venmo_id"])
    df = df[df["venmo_id"].astype(str).str.strip().str.match(r"^\d+$")]

    # Exclude transfers to bank and other non-purchase types
    df = df[~df["type"].isin(EXCLUDE_TYPES)]

    # Only keep completed transactions
    df = df[df["status"] == "Complete"]

    # Parse amount
    df["amount"] = df["amount_raw"].apply(_parse_amount)
    df["amount"] = df["amount"] * -1  # flip so sent = positive, received = negative
    df = df.dropna(subset=["amount"])
    df = df[df["amount"] != 0]

    # Parse date
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    # Build description
    df["description"] = df.apply(_format_description, axis=1)

    # Add metadata
    df["account_name"] = "Venmo"
    df["account_type"] = "venmo"
    df["transaction_type"] = df["amount"].apply(lambda x: "DEBIT" if x < 0 else "CREDIT")
    df["balance"] = None
    df["post_date"] = None
    df["chase_category"] = None
    df["amex_category"] = None
    df["hash"] = df.apply(_make_hash, axis=1)

    return df[[
        "date", "post_date", "description", "amount", "type", "balance",
        "transaction_type", "chase_category", "amex_category",
        "account_name", "account_type", "hash"
    ]]