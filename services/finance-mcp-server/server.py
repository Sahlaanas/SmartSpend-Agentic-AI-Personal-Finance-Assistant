import os

import httpx
from mcp.server.fastmcp import FastMCP

TRANSACTION_SERVICE_URL = os.environ.get(
    "TRANSACTION_SERVICE_URL", "http://transaction-service:8000"
)
ANOMALY_SERVICE_URL = os.environ.get("ANOMALY_SERVICE_URL", "http://anomaly-service:8000")

mcp = FastMCP("SmartSpend Finance", host="0.0.0.0", port=8002)


async def _get(path: str, params: dict | None = None):
    """Call the transaction-service. Errors become tool errors the agent can read."""
    async with httpx.AsyncClient(base_url=TRANSACTION_SERVICE_URL, timeout=10) as client:
        response = await client.get(path, params=params)
        response.raise_for_status()
        return response.json()


def _percent_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None  # can't divide by zero: the category is new this month
    return round((current - previous) / previous * 100, 1)


@mcp.tool()
async def get_transactions(
    month: str | None = None,
    category: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """List individual transactions, newest first.

    Args:
        month: Only this month, formatted YYYY-MM (for example 2026-10). Optional.
        category: Only this category, for example Food, Groceries, Transport,
            Shopping, Bills, Entertainment, Health, Rent or Other. Optional.
        limit: Maximum number of transactions to return (1-1000).
    """
    params = {"limit": limit}
    if month:
        params["month"] = month
    if category:
        params["category"] = category
    return await _get("/transactions", params)


@mcp.tool()
async def get_monthly_summary(month: str) -> dict:
    """Get total spending for one month with a per-category breakdown.

    Args:
        month: The month, formatted YYYY-MM (for example 2026-10).
    """
    return await _get("/summary/monthly", {"month": month})


@mcp.tool()
async def get_category_expenses(month: str, category: str) -> dict:
    """Get total spending and the individual transactions for one category in one month.

    Args:
        month: The month, formatted YYYY-MM (for example 2026-10).
        category: The category name, for example Food or Shopping.
    """
    transactions = await _get(
        "/transactions", {"month": month, "category": category, "limit": 1000}
    )
    total = sum(float(t["amount"]) for t in transactions)
    return {
        "month": month,
        "category": category,
        "total": round(total, 2),
        "count": len(transactions),
        "transactions": transactions,
    }


@mcp.tool()
async def compare_months(month: str, previous_month: str) -> dict:
    """Compare spending between two months, in total and per category.

    Use this to answer questions like "why did I spend more this month?".
    Categories are sorted by the size of the change, biggest first.

    Args:
        month: The month to look at, formatted YYYY-MM.
        previous_month: The month to compare against, formatted YYYY-MM.
    """
    current = await _get("/summary/monthly", {"month": month})
    previous = await _get("/summary/monthly", {"month": previous_month})

    cur = {c["category"]: c["total"] for c in current["categories"]}
    prev = {c["category"]: c["total"] for c in previous["categories"]}

    categories = []
    for name in set(cur) | set(prev):
        c, p = cur.get(name, 0.0), prev.get(name, 0.0)
        categories.append({
            "category": name,
            "current": c,
            "previous": p,
            "difference": round(c - p, 2),
            "percent_change": _percent_change(c, p),
        })
    categories.sort(key=lambda x: abs(x["difference"]), reverse=True)

    return {
        "month": month,
        "previous_month": previous_month,
        "total_current": current["total"],
        "total_previous": previous["total"],
        "difference": round(current["total"] - previous["total"], 2),
        "percent_change": _percent_change(current["total"], previous["total"]),
        "categories": categories,
    }

@mcp.tool()
async def detect_unusual_expenses(month: str) -> dict:
    """Find unusually large transactions in a month, with an explanation for each.

    Uses a machine-learning model trained on the user's whole spending history.
    Use this when the user asks about unusual, suspicious, surprising or one-off expenses.
    If the result has a message (for example "not enough history"), tell the user.

    Args:
        month: The month, formatted YYYY-MM (for example 2026-10).
    """
    async with httpx.AsyncClient(base_url=ANOMALY_SERVICE_URL, timeout=15) as client:
        response = await client.get("/anomalies", params={"month": month})
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def create_budget(category: str, monthly_limit: float) -> dict:
    """Create or update the monthly spending budget for one category.

    The budget applies to every month. Calling this again for the same category
    replaces the old limit.

    Args:
        category: One of Groceries, Food, Transport, Shopping, Bills, Entertainment,
            Health, Rent or Other. Use "Total" for a budget on all spending together.
        monthly_limit: The limit per month in rupees. Must be greater than 0.
    """
    async with httpx.AsyncClient(base_url=TRANSACTION_SERVICE_URL, timeout=10) as client:
        response = await client.put(f"/budgets/{category}", json={"monthly_limit": monthly_limit})
    if response.status_code >= 400:
        # Pass the service's explanation to the agent (it lists the valid categories)
        raise ValueError(str(response.json().get("detail", response.text)))
    return response.json()


@mcp.tool()
async def get_budget_status(month: str) -> dict:
    """Check every budget against the actual spending of one month.

    For each budget this returns the limit, the amount spent, the amount remaining
    and a status: "ok", "warning" (80% or more used) or "exceeded".
    Use this when the user asks whether they are within budget, or to warn them
    about categories that are close to or over their limit.

    Args:
        month: The month, formatted YYYY-MM (for example 2026-10).
    """
    return await _get("/budgets/status", {"month": month})

if __name__ == "__main__":
    mcp.run(transport="streamable-http")