from __future__ import annotations

import csv
from pathlib import Path

from advance_report.models import Contract, Payment, Work
from advance_report.money import money, parse_date


def load_contracts(path: Path) -> dict[str, Contract]:
    rows: dict[str, Contract] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            signed = parse_date(row["signed_at"])
            if signed is None:
                raise ValueError(f"У договора {row['contract_id']} нет signed_at")
            rows[row["contract_id"]] = Contract(
                contract_id=row["contract_id"],
                contractor=row["contractor"],
                amount=money(row["amount"]),
                signed_at=signed,
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
            created = parse_date(row["created_at"])
            if created is None:
                raise ValueError(f"У платежа {row['payment_id']} нет created_at")
            payments.append(
                Payment(
                    payment_id=row["payment_id"],
                    contract_id=row["contract_id"],
                    work_id=work_id,
                    purpose=row["purpose"],
                    amount=money(row["amount"]),
                    status=row["status"],
                    created_at=created,
                    paid_at=parse_date(row["paid_at"]),
                    refunded_at=parse_date(row["refunded_at"]),
                )
            )
    return payments


def load_dataset(data_dir: Path) -> tuple[dict[str, Contract], list[Work], list[Payment]]:
    return (
        load_contracts(data_dir / "contracts.csv"),
        load_works(data_dir / "works.csv"),
        load_payments(data_dir / "payments.csv"),
    )
