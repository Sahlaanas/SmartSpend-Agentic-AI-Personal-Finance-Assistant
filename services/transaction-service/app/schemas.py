from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TransactionCreate(BaseModel):
    txn_date: date
    description: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    category: str | None = Field(default=None, max_length=50)


class TransactionOut(TransactionCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class UploadResult(BaseModel):
    imported: int
    skipped_duplicates: int
    by_category: dict[str, int]


class CategoryTotal(BaseModel):
    category: str
    total: float
    count: int


class MonthlySummary(BaseModel):
    month: str
    total: float
    count: int
    categories: list[CategoryTotal]



class BudgetIn(BaseModel):
    monthly_limit: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class BudgetOut(BaseModel):
    category: str
    monthly_limit: float
    model_config = ConfigDict(from_attributes=True)


class BudgetStatus(BaseModel):
    category: str
    monthly_limit: float
    spent: float
    remaining: float        # negative when the budget is exceeded
    percent_used: float
    status: str             # "ok", "warning" (80% or more used) or "exceeded"


class BudgetReport(BaseModel):
    month: str
    budgets: list[BudgetStatus]