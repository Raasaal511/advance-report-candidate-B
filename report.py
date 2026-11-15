#!/usr/bin/env python3
"""Отчёт: выплачено и остаток по работам и договорам на дату."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


MONEY = Decimal("0.01")


def money(value: str | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def parse_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


@dataclass
class Contract:
    contract_id: str
    contractor: str
    amount: Decimal
    signed_at: date


@dataclass
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
            return money(0)
        return self.price


@dataclass
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
        """Сколько реально «висит» у подрядчика на дату."""
        if self.status == "queued":
            return money(0)
        if self.paid_at is None or self.paid_at > as_of:
            return money(0)
        if self.status == "refunded":
            if self.refunded_at is not None and self.refunded_at <= as_of:
                return money(0)
        return self.amount


def load_contracts(path: Path) -> dict[str, Contract]:
    rows: dict[str, Contract] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows[row["contract_id"]] = Contract(
                contract_id=row["contract_id"],
                contractor=row["contractor"],
                amount=money(row["amount"]),
                signed_at=parse_date(row["signed_at"]),  # type: ignore[arg-type]
            )
    return rows


def load_works(path: Path) -> list[Work]:
    works: list[Work] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            works.append(
                Work(
                    work_id=row["work_id"],
                    contract_id=row["contract_id"],
                    title=row["title"],
                    price=money(row["price"]),
                    status_dump=row["status"],
                    completed_at=parse_date(row["completed_at"]),
                    cancelled_at=parse_date(row["cancelled_at"]),
                )
            )
    return works


def load_payments(path: Path) -> list[Payment]:
    payments: list[Payment] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            work_id = (row.get("work_id") or "").strip() or None
            payments.append(
                Payment(
                    payment_id=row["payment_id"],
                    contract_id=row["contract_id"],
                    work_id=work_id,
                    purpose=row["purpose"],
                    amount=money(row["amount"]),
                    status=row["status"],
                    created_at=parse_date(row["created_at"]),  # type: ignore[arg-type]
                    paid_at=parse_date(row["paid_at"]),
                    refunded_at=parse_date(row["refunded_at"]),
                )
            )
    return payments


def allocation_order(works: list[Work], as_of: date) -> list[Work]:
    """Сначала принятые (по дате приёмки), потом остальные (по id). Отменённые в конце."""

    def key(w: Work) -> tuple:
        status = w.status_as_of(as_of)
        if status == "done":
            return (0, w.completed_at or date.min, w.work_id)
        if status == "planned":
            return (1, date.max, w.work_id)
        return (2, date.max, w.work_id)

    return sorted(works, key=key)


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
        return left if left > 0 else money(0)

    @property
    def overpaid(self) -> Decimal:
        extra = self.paid - self.obligation
        return extra if extra > 0 else money(0)


@dataclass
class ContractLine:
    contract: Contract
    work_lines: list[WorkLine]
    paid_total: Decimal
    unallocated_surplus: Decimal

    @property
    def obligation_total(self) -> Decimal:
        return sum((w.obligation for w in self.work_lines), money(0))

    @property
    def remaining_total(self) -> Decimal:
        return sum((w.remaining for w in self.work_lines), money(0))


def build_report(
    contracts: dict[str, Contract],
    works: list[Work],
    payments: list[Payment],
    as_of: date,
) -> list[ContractLine]:
    works_by_contract: dict[str, list[Work]] = defaultdict(list)
    for w in works:
        works_by_contract[w.contract_id].append(w)

    paid_direct: dict[str, Decimal] = defaultdict(lambda: money(0))
    paid_pool: dict[str, Decimal] = defaultdict(lambda: money(0))
    paid_total_by_contract: dict[str, Decimal] = defaultdict(lambda: money(0))

    for p in payments:
        eff = p.effective_paid(as_of)
        if eff == 0:
            continue
        paid_total_by_contract[p.contract_id] += eff
        if p.work_id:
            paid_direct[p.work_id] += eff
        else:
            paid_pool[p.contract_id] += eff

    result: list[ContractLine] = []
    for contract_id in sorted(contracts.keys()):
        contract = contracts[contract_id]
        c_works = works_by_contract.get(contract_id, [])
        paid_map: dict[str, Decimal] = {
            w.work_id: paid_direct.get(w.work_id, money(0)) for w in c_works
        }
        pool = paid_pool.get(contract_id, money(0))

        for w in allocation_order(c_works, as_of):
            obl = w.obligation(as_of)
            already = paid_map[w.work_id]
            if already >= obl:
                continue
            need = obl - already
            take = need if need <= pool else pool
            paid_map[w.work_id] = already + take
            pool -= take
            if pool == 0:
                break

        # Если прямые платежи + пул не разложились полностью — остаток на договоре
        surplus = pool
        # Переплата по работе (прямые платежи выше обязательства) тоже считаем surplus
        for w in c_works:
            obl = w.obligation(as_of)
            if paid_map[w.work_id] > obl:
                surplus += paid_map[w.work_id] - obl
                paid_map[w.work_id] = obl

        work_lines = [
            WorkLine(
                work=w,
                status=w.status_as_of(as_of),
                price=w.price,
                obligation=w.obligation(as_of),
                paid=paid_map[w.work_id],
            )
            for w in sorted(c_works, key=lambda x: x.work_id)
        ]
        result.append(
            ContractLine(
                contract=contract,
                work_lines=work_lines,
                paid_total=paid_total_by_contract.get(contract_id, money(0)),
                unallocated_surplus=surplus,
            )
        )
    return result


def fmt(value: Decimal) -> str:
    return f"{value:.2f}"


def print_report(lines: list[ContractLine], as_of: date, out) -> None:
    out.write(f"Отчёт на дату {as_of.isoformat()}\n")
    out.write("=" * 72 + "\n\n")
    for cl in lines:
        c = cl.contract
        out.write(f"Договор {c.contract_id} — {c.contractor}\n")
        out.write(f"  Сумма договора: {fmt(c.amount)}\n")
        out.write(f"  Обязательства по работам на дату: {fmt(cl.obligation_total)}\n")
        out.write(f"  Выплачено (эффективно): {fmt(cl.paid_total)}\n")
        out.write(f"  Осталось оплатить: {fmt(cl.remaining_total)}\n")
        if cl.unallocated_surplus > 0:
            out.write(
                f"  Из них не разнесено / сверх обязательств работ: {fmt(cl.unallocated_surplus)}\n"
            )
        out.write("\n")
        out.write(
            f"  {'work_id':<8} {'status':<10} {'price':>12} {'paid':>12} {'left':>12}  title\n"
        )
        for wl in cl.work_lines:
            out.write(
                f"  {wl.work.work_id:<8} {wl.status:<10} {fmt(wl.price):>12} "
                f"{fmt(wl.paid):>12} {fmt(wl.remaining):>12}  {wl.work.title}\n"
            )
        out.write("\n")


def write_csv(lines: list[ContractLine], as_of: date, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "as_of",
                "contract_id",
                "contractor",
                "work_id",
                "title",
                "status",
                "price",
                "obligation",
                "paid",
                "remaining",
                "contract_amount",
                "contract_obligation",
                "contract_paid",
                "contract_remaining",
                "contract_surplus",
            ]
        )
        for cl in lines:
            for wl in cl.work_lines:
                writer.writerow(
                    [
                        as_of.isoformat(),
                        cl.contract.contract_id,
                        cl.contract.contractor,
                        wl.work.work_id,
                        wl.work.title,
                        wl.status,
                        fmt(wl.price),
                        fmt(wl.obligation),
                        fmt(wl.paid),
                        fmt(wl.remaining),
                        fmt(cl.contract.amount),
                        fmt(cl.obligation_total),
                        fmt(cl.paid_total),
                        fmt(cl.remaining_total),
                        fmt(cl.unallocated_surplus),
                    ]
                )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Отчёт по авансам на дату")
    parser.add_argument(
        "--date",
        required=True,
        help="Дата отчёта YYYY-MM-DD (например 2026-11-10)",
    )
    parser.add_argument(
        "--data",
        default="data",
        help="Папка с contracts.csv, works.csv, payments.csv",
    )
    parser.add_argument(
        "--csv",
        default="",
        help="Путь для CSV-отчёта (опционально)",
    )
    args = parser.parse_args(argv)

    as_of = parse_date(args.date)
    if as_of is None:
        print("Некорректная дата", file=sys.stderr)
        return 2

    data = Path(args.data)
    contracts = load_contracts(data / "contracts.csv")
    works = load_works(data / "works.csv")
    payments = load_payments(data / "payments.csv")

    report = build_report(contracts, works, payments, as_of)
    print_report(report, as_of, sys.stdout)

    if args.csv:
        write_csv(report, as_of, Path(args.csv))
        print(f"CSV сохранён: {args.csv}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
