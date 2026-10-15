from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .budgets import router as budgets_router
from .dates import MONTH_PATTERN, month_range
from .db import Base, engine, get_db
from .models import Transaction
from .parser import parse_statement
from .schemas import (
    CategoryTotal,
    MonthlySummary,
    TransactionCreate,
    TransactionOut,
    UploadResult,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fine for learning. Later you'll replace this with Alembic migrations.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="SmartSpend - Transaction Service", lifespan=lifespan)
app.include_router(budgets_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/transactions", response_model=TransactionOut, status_code=201)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    txn = Transaction(**payload.model_dump())
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


@app.post("/transactions/upload", response_model=UploadResult)
async def upload_statement(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        rows = parse_statement(file.filename or "", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not rows:
        raise HTTPException(status_code=400, detail="No expense rows found in the file.")

    # Skip rows that already exist (same date, description and amount),
    # so uploading the same statement twice doesn't double your spending.
    first = min(r["txn_date"] for r in rows)
    last = max(r["txn_date"] for r in rows)
    existing = set(
        db.execute(
            select(Transaction.txn_date, Transaction.description, Transaction.amount)
            .where(Transaction.txn_date >= first, Transaction.txn_date <= last)
        ).all()
    )

    imported = 0
    skipped = 0
    by_category: dict[str, int] = {}
    for r in rows:
        if (r["txn_date"], r["description"], r["amount"]) in existing:
            skipped += 1
            continue
        db.add(Transaction(**r))
        imported += 1
        by_category[r["category"]] = by_category.get(r["category"], 0) + 1

    db.commit()
    return UploadResult(imported=imported, skipped_duplicates=skipped, by_category=by_category)


@app.get("/transactions", response_model=list[TransactionOut])
def list_transactions(
    month: str | None = Query(None, pattern=MONTH_PATTERN, description="YYYY-MM"),
    category: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    stmt = select(Transaction).order_by(Transaction.txn_date.desc(), Transaction.id.desc())

    if month:
        start, end = month_range(month)
        stmt = stmt.where(Transaction.txn_date >= start, Transaction.txn_date < end)
    if category:
        stmt = stmt.where(Transaction.category == category)

    return db.scalars(stmt.limit(limit)).all()


@app.get("/summary/monthly", response_model=MonthlySummary)
def monthly_summary(
    month: str = Query(..., pattern=MONTH_PATTERN, description="YYYY-MM"),
    db: Session = Depends(get_db),
):
    """Total spending for one month, split by category (biggest first)."""
    start, end = month_range(month)
    rows = db.execute(
        select(Transaction.category, func.sum(Transaction.amount), func.count())
        .where(Transaction.txn_date >= start, Transaction.txn_date < end)
        .group_by(Transaction.category)
    ).all()

    categories = sorted(
        (CategoryTotal(category=cat or "Uncategorized", total=float(total), count=count)
         for cat, total, count in rows),
        key=lambda c: c.total,
        reverse=True,
    )
    return MonthlySummary(
        month=month,
        total=round(sum(c.total for c in categories), 2),
        count=sum(c.count for c in categories),
        categories=categories,
    )