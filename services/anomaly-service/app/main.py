import os
from datetime import date

import httpx
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from sklearn.ensemble import IsolationForest

TRANSACTION_SERVICE_URL = os.environ.get(
    "TRANSACTION_SERVICE_URL", "http://transaction-service:8000"
)

MIN_TRANSACTIONS = 10       # Isolation Forest needs some history to learn what "normal" is
MIN_CATEGORY_SIZE = 5       # a category needs this many transactions to have a trustworthy "typical" amount
CONTAMINATION = 0.1         # we expect roughly 10% of transactions to be unusual
MIN_TIMES_TYPICAL = 3.0     # guardrail: only flag spends at least 3x the typical amount
MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"

app = FastAPI(title="SmartSpend - Anomaly Service")


class FlaggedTransaction(BaseModel):
    id: int
    txn_date: date
    description: str
    amount: float
    category: str | None
    anomaly_score: float  # higher = more unusual
    reason: str


class AnomalyResult(BaseModel):
    month: str
    trained_on: int
    flagged: list[FlaggedTransaction]
    message: str | None = None


async def fetch_all_transactions() -> list[dict]:
    try:
        async with httpx.AsyncClient(base_url=TRANSACTION_SERVICE_URL, timeout=10) as client:
            response = await client.get("/transactions", params={"limit": 1000})
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Transaction service error: {exc}")


def typical_amounts(amounts: np.ndarray, categories: list[str]) -> tuple[np.ndarray, list[str]]:
    """For every transaction, find the 'typical' amount to compare it against.

    Rs 2,000 is normal for Transport but not for Food, so we prefer the median of the
    transaction's own category. But a category with only a few transactions has no
    trustworthy median (with 2 transactions it is just the midpoint between them), so
    those are compared against your overall median instead.

    Returns the typical amount per transaction and the basis used ("Food" or "overall").
    """
    overall = float(np.median(amounts))
    reference: dict[str, float] = {}
    basis_of: dict[str, str] = {}
    for cat in set(categories):
        mask = np.array([c == cat for c in categories])
        if mask.sum() >= MIN_CATEGORY_SIZE:
            reference[cat] = float(np.median(amounts[mask]))
            basis_of[cat] = cat
        else:
            reference[cat] = overall
            basis_of[cat] = "overall"

    typical = np.array([reference[c] for c in categories])
    return typical, [basis_of[c] for c in categories]


def build_features(amounts: np.ndarray, typical: np.ndarray) -> np.ndarray:
    """Two features per transaction:
    1. log of the amount (so 35,000 vs 2,600 is a sensible gap, not a huge one)
    2. log of amount / typical amount (how many times bigger than normal it is)
    """
    return np.column_stack([np.log1p(amounts), np.log(amounts / typical)])


def explain(amount: float, typical: float, basis: str) -> str:
    what = "transaction" if basis == "overall" else f"{basis} transaction"
    return f"Rs {amount:,.2f} is {amount / typical:.1f}x your typical {what} (about Rs {typical:,.2f})."


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/anomalies", response_model=AnomalyResult)
async def anomalies(month: str = Query(..., pattern=MONTH_PATTERN, description="YYYY-MM")):
    """Find unusually large transactions in a month.

    The model is trained on ALL your transactions (so it learns your normal),
    then we report the unusual ones that fall in the requested month.
    """
    txns = await fetch_all_transactions()

    if len(txns) < MIN_TRANSACTIONS:
        return AnomalyResult(
            month=month,
            trained_on=len(txns),
            flagged=[],
            message=f"Not enough history: need at least {MIN_TRANSACTIONS} transactions, have {len(txns)}.",
        )

    amounts = np.array([float(t["amount"]) for t in txns])
    categories = [t["category"] or "Uncategorized" for t in txns]
    typical, basis = typical_amounts(amounts, categories)
    X = build_features(amounts, typical)

    model = IsolationForest(n_estimators=200, contamination=CONTAMINATION, random_state=42)
    model.fit(X)
    is_outlier = model.predict(X) == -1      # -1 means "unusual"
    scores = -model.score_samples(X)         # flip the sign so higher = more unusual

    flagged = []
    for i, t in enumerate(txns):
        if not t["txn_date"].startswith(month):
            continue
        # The model flags a fixed share of transactions even when everything is normal,
        # and it also flags unusually SMALL ones. We only want materially large spends.
        if is_outlier[i] and amounts[i] >= typical[i] * MIN_TIMES_TYPICAL:
            flagged.append(FlaggedTransaction(
                id=t["id"],
                txn_date=t["txn_date"],
                description=t["description"],
                amount=float(amounts[i]),
                category=t["category"],
                anomaly_score=round(float(scores[i]), 3),
                reason=explain(float(amounts[i]), float(typical[i]), basis[i]),
            ))

    flagged.sort(key=lambda f: f.anomaly_score, reverse=True)
    return AnomalyResult(month=month, trained_on=len(txns), flagged=flagged)