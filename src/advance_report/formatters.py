from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import TextIO

from advance_report.models import ContractLine
from advance_report.money import fmt


def print_report(lines: list[ContractLine], as_of: date, out: TextIO) -> None:
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
                f"  Не разнесено / сверх обязательств работ: {fmt(cl.unallocated_surplus)}\n"
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
    path.parent.mkdir(parents=True, exist_ok=True)
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
