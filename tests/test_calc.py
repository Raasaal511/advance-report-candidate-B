from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from advance_report.calc import build_report
from advance_report.loaders import load_dataset
from advance_report.models import Contract, Payment, Work
from advance_report.money import money

DATA = Path(__file__).resolve().parents[1] / "data"
AS_OF = date(2026, 11, 10)


class CalcTests(unittest.TestCase):
    def test_control_date_contract_totals(self) -> None:
        contracts, works, payments = load_dataset(DATA)
        report = {
            line.contract.contract_id: line
            for line in build_report(contracts, works, payments, AS_OF)
        }

        self.assertEqual(report["D-1"].paid_total, money("315000"))
        self.assertEqual(report["D-1"].remaining_total, money("185000"))
        self.assertEqual(report["D-1"].obligation_total, money("500000"))

        self.assertEqual(report["D-2"].paid_total, money("75000"))
        self.assertEqual(report["D-2"].remaining_total, money("15000"))

    def test_cancelled_work_has_zero_obligation(self) -> None:
        contracts, works, payments = load_dataset(DATA)
        report = build_report(contracts, works, payments, AS_OF)
        w13 = next(
            wl
            for cl in report
            if cl.contract.contract_id == "D-1"
            for wl in cl.work_lines
            if wl.work.work_id == "W-13"
        )
        self.assertEqual(w13.status, "cancelled")
        self.assertEqual(w13.obligation, money(0))
        self.assertEqual(w13.remaining, money(0))

    def test_work_after_as_of_is_planned(self) -> None:
        contracts, works, payments = load_dataset(DATA)
        report = build_report(contracts, works, payments, AS_OF)
        w23 = next(
            wl
            for cl in report
            if cl.contract.contract_id == "D-2"
            for wl in cl.work_lines
            if wl.work.work_id == "W-23"
        )
        self.assertEqual(w23.status, "planned")
        self.assertEqual(w23.paid, money("25000"))
        self.assertEqual(w23.remaining, money("15000"))

    def test_refunded_and_queued_excluded(self) -> None:
        _, _, payments = load_dataset(DATA)
        by_id = {p.payment_id: p for p in payments}
        self.assertEqual(by_id["P-2"].effective_paid(AS_OF), money(0))
        self.assertEqual(by_id["P-4"].effective_paid(AS_OF), money(0))
        self.assertEqual(by_id["P-8"].effective_paid(AS_OF), money(0))
        self.assertEqual(by_id["P-1"].effective_paid(AS_OF), money("300000"))

    def test_paid_equals_allocated_plus_surplus(self) -> None:
        contracts, works, payments = load_dataset(DATA)
        for line in build_report(contracts, works, payments, AS_OF):
            allocated = sum((wl.paid for wl in line.work_lines), Decimal("0.00"))
            self.assertEqual(allocated + line.unallocated_surplus, line.paid_total)

    def test_before_refund_includes_erroneous_payment(self) -> None:
        """На 05.09.2026 P-2 ещё не возвращён — в выплачено D-1 входит 350000."""
        contracts, works, payments = load_dataset(DATA)
        as_of = date(2026, 9, 5)
        report = {
            line.contract.contract_id: line
            for line in build_report(contracts, works, payments, as_of)
        }
        self.assertEqual(report["D-1"].paid_total, money("350000"))
        self.assertEqual(report["D-1"].remaining_total, money("250000"))
        self.assertEqual(report["D-1"].obligation_total, money("600000"))
        self.assertEqual(report["D-2"].paid_total, money(0))

    def test_after_late_payment_d2_covered_with_surplus(self) -> None:
        """На 15.11.2026 P-8 и приёмка W-23: D-2 закрыт, сверх обязательств +5000."""
        contracts, works, payments = load_dataset(DATA)
        as_of = date(2026, 11, 15)
        report = {
            line.contract.contract_id: line
            for line in build_report(contracts, works, payments, as_of)
        }
        self.assertEqual(report["D-2"].paid_total, money("95000"))
        self.assertEqual(report["D-2"].remaining_total, money(0))
        self.assertEqual(report["D-2"].unallocated_surplus, money("5000"))
        w23 = next(wl for wl in report["D-2"].work_lines if wl.work.work_id == "W-23")
        self.assertEqual(w23.status, "done")
        self.assertEqual(w23.remaining, money(0))

    def test_direct_payment_sticks_to_work(self) -> None:
        work = Work(
            work_id="W-X",
            contract_id="D-X",
            title="test",
            price=money("100"),
            status_dump="done",
            completed_at=date(2026, 1, 1),
            cancelled_at=None,
        )
        contract = Contract("D-X", "X", money("100"), date(2026, 1, 1))
        payment = Payment(
            payment_id="P-X",
            contract_id="D-X",
            work_id="W-X",
            purpose="materials",
            amount=money("40"),
            status="paid",
            created_at=date(2026, 1, 2),
            paid_at=date(2026, 1, 3),
            refunded_at=None,
        )
        line = build_report({"D-X": contract}, [work], [payment], date(2026, 2, 1))[0]
        self.assertEqual(line.work_lines[0].paid, money("40"))
        self.assertEqual(line.work_lines[0].remaining, money("60"))


if __name__ == "__main__":
    unittest.main()
