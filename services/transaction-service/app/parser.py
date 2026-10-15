import io
from decimal import Decimal

import pandas as pd

from .categorizer import categorize

DATE_COLS = ["date", "txn date", "transaction date", "value date"]
DESC_COLS = ["description", "narration", "particulars", "details", "remarks"]
AMOUNT_COLS = ["amount"]
DEBIT_COLS = ["debit", "withdrawal", "withdrawal amt.", "withdrawals", "debit amount"]


def _find(columns: list[str], candidates: list[str]) -> str | None:
    for c in candidates:
        if c in columns:
            return c
    return None


def _to_number(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.replace(r"[₹,\s]", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce")


def parse_statement(filename: str, content: bytes) -> list[dict]:
    name = filename.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content))
    elif name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(content))
    else:
        raise ValueError("Unsupported file type. Upload a .csv, .xlsx or .xls file.")

    df.columns = [str(c).strip().lower() for c in df.columns]
    cols = list(df.columns)

    date_col = _find(cols, DATE_COLS)
    desc_col = _find(cols, DESC_COLS)
    debit_col = _find(cols, DEBIT_COLS)
    amount_col = _find(cols, AMOUNT_COLS)

    if not date_col or not desc_col or not (debit_col or amount_col):
        raise ValueError(
            "Could not find the needed columns. Need a date column, a description column "
            f"and an amount (or debit) column. Found: {cols}"
        )

    # Bank statements in India use dd/mm/yyyy, so dayfirst=True
    df["_date"] = pd.to_datetime(df[date_col], dayfirst=True, errors="coerce")

    if debit_col:
        # Separate debit/credit columns: only debits are expenses
        df["_amount"] = _to_number(df[debit_col])
    else:
        amounts = _to_number(df[amount_col])
        # If the file has negative amounts, negatives are expenses and positives are income
        df["_amount"] = amounts.abs().where(amounts < 0) if (amounts < 0).any() else amounts

    df = df.dropna(subset=["_date", "_amount"])
    df = df[df["_amount"] > 0]

    rows = []
    for _, r in df.iterrows():
        description = str(r[desc_col]).strip()[:255]
        rows.append({
            "txn_date": r["_date"].date(),
            "description": description,
            "amount": Decimal(str(round(float(r["_amount"]), 2))),
            "category": categorize(description),
        })
    return rows