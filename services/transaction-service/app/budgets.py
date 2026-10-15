from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .categorizer import RULES
from .dates import MONTH_PATTERN, month_range
from .db import get_db
from .models import Budget, Transaction
from .schemas import BudgetIn, BudgetOut, BudgetReport, BudgetStatus

router = APIRouter(prefix="/budgets", tags=["budgets"])

TOTAL = "Total"                                   # budget for all spending together
VALID_CATEGORIES = [*RULES.keys(), "Other", TOTAL]
WARNING_AT = 80.0                                 # percent of the budget that triggers a warning


def normalize_category(name: str) -> str:
    """'food' -> 'Food'. Unknown names get an error that lists the valid ones,
    so an AI agent can read it and correct itself."""
    for valid in VALID_CATEGORIES:
        if valid.lower() == name.strip().lower():
            return valid
    raise HTTPException(
        status_code=400,
        detail=f"Unknown category '{name}'. Valid categories: {', '.join(VALID_CATEGORIES)}",
    )


@router.put("/{category}", response_model=BudgetOut)
def set_budget(category: str, payload: BudgetIn, db: Session = Depends(get_db)):
    """Create the budget for a category, or update it if it already exists."""
    category = normalize_category(category)
    budget = db.scalar(select(Budget).where(Budget.category == category))
    if budget:
        budget.monthly_limit = payload.monthly_limit
    else:
        budget = Budget(category=category, monthly_limit=payload.monthly_limit)
        db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@router.get("", response_model=list[BudgetOut])
def list_budgets(db: Session = Depends(get_db)):
    return db.scalars(select(Budget).order_by(Budget.category)).all()


@router.delete("/{category}", status_code=204)
def delete_budget(category: str, db: Session = Depends(get_db)):
    category = normalize_category(category)
    budget = db.scalar(select(Budget).where(Budget.category == category))
    if not budget:
        raise HTTPException(status_code=404, detail=f"No budget set for {category}.")
    db.delete(budget)
    db.commit()
    return Response(status_code=204)


@router.get("/status", response_model=BudgetReport)
def budget_status(
    month: str = Query(..., pattern=MONTH_PATTERN, description="YYYY-MM"),
    db: Session = Depends(get_db),
):
    """For every budget: how much was spent in this month and how much is left."""
    start, end = month_range(month)
    rows = db.execute(
        select(Transaction.category, func.sum(Transaction.amount))
        .where(Transaction.txn_date >= start, Transaction.txn_date < end)
        .group_by(Transaction.category)
    ).all()
    spent_by_category = {(cat or "Uncategorized"): float(total) for cat, total in rows}
    total_spent = sum(spent_by_category.values())

    report = []
    for budget in db.scalars(select(Budget).order_by(Budget.category)).all():
        limit = float(budget.monthly_limit)
        spent = total_spent if budget.category == TOTAL else spent_by_category.get(budget.category, 0.0)
        percent = round(spent / limit * 100, 1)
        if spent > limit:
            status = "exceeded"
        elif percent >= WARNING_AT:
            status = "warning"
        else:
            status = "ok"
        report.append(BudgetStatus(
            category=budget.category,
            monthly_limit=limit,
            spent=round(spent, 2),
            remaining=round(limit - spent, 2),
            percent_used=percent,
            status=status,
        ))
    return BudgetReport(month=month, budgets=report)