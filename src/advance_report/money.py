from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

MONEY = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value: str | Decimal | int) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def parse_date(value: str | None) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def fmt(value: Decimal) -> str:
    return f"{value:.2f}"
