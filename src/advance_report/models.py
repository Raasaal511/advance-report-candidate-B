from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from advance_report.money import ZERO, money


@dataclass(frozen=True)
class Contract:
    contract_id: str
    contractor: str
    amount: Decimal
    signed_at: date


@dataclass(frozen=True)
class Work:
    work_id: str
    contract_id: str
    title: str
    price: Decimal
    status_dump: str
    completed_at: date | None
    cancelled_at: date | None

    def status_as_of(self, as_of: date) -> str:
        if self.cancelled_at is not None and self.cancelled_at <= as_of:
            return "cancelled"
        if self.completed_at is not None and self.completed_at <= as_of:
            return "done"
        return "planned"

    def obligation(self, as_of: date) -> Decimal:
        if self.status_as_of(as_of) == "cancelled":
            return ZERO
        return self.price


@dataclass(frozen=True)
class Payment:
    payment_id: str
    contract_id: str
    work_id: str | None
    purpose: str
    amount: Decimal
    status: str
    created_at: date
    paid_at: date | None
    refunded_at: date | None

    def effective_paid(self, as_of: date) -> Decimal:
        """Сколько реально у подрядчика на дату."""
        if self.status == "queued":
            return ZERO
        if self.paid_at is None or self.paid_at > as_of:
            return ZERO
        if self.status == "refunded":
            if self.refunded_at is not None and self.refunded_at <= as_of:
                return ZERO
        return self.amount


@dataclass
class WorkLine:
    work: Work
    status: str
    price: Decimal
    obligation: Decimal
    paid: Decimal

    @property
    def remaining(self) -> Decimal:
        left = self.obligation - self.paid
        return left if left > ZERO else ZERO


@dataclass
class ContractLine:
    contract: Contract
    work_lines: list[WorkLine]
    paid_total: Decimal
    unallocated_surplus: Decimal

    @property
    def obligation_total(self) -> Decimal:
        return sum((w.obligation for w in self.work_lines), ZERO)

    @property
    def remaining_total(self) -> Decimal:
        return sum((w.remaining for w in self.work_lines), ZERO)
