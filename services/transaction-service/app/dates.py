from datetime import date

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


def month_range(month: str) -> tuple[date, date]:
    """'2026-10' -> (2026-10-01, 2026-11-01). The end date is exclusive."""
    year, mon = map(int, month.split("-"))
    start = date(year, mon, 1)
    end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)
    return start, end