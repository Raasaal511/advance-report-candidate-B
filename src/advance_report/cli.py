from __future__ import annotations

import argparse
import sys
from pathlib import Path

from advance_report.calc import build_report
from advance_report.formatters import print_report, write_csv
from advance_report.loaders import load_dataset
from advance_report.money import parse_date


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="advance-report",
        description="Отчёт по авансам договоров на дату",
    )
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    as_of = parse_date(args.date)
    if as_of is None:
        print("Некорректная дата. Ожидается YYYY-MM-DD.", file=sys.stderr)
        return 2

    data = Path(args.data)
    if not data.is_dir():
        print(f"Папка данных не найдена: {data}", file=sys.stderr)
        return 2

    contracts, works, payments = load_dataset(data)
    report = build_report(contracts, works, payments, as_of)
    print_report(report, as_of, sys.stdout)

    if args.csv:
        csv_path = Path(args.csv)
        write_csv(report, as_of, csv_path)
        print(f"CSV сохранён: {csv_path}", file=sys.stderr)

    return 0
