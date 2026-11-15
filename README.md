# Отчёт: аванс по договору

Скрипт читает CSV из `data/` и считает на дату: по каждой работе — цена, выплачено, осталось; по договору — итоги.

Python 3.10+, зависимостей нет.

## Запуск

```bash
python3 report.py --date 2026-11-10 --data data
```

CSV на диск:

```bash
python3 report.py --date 2026-11-10 --data data --csv report-2026-11-10.csv
```

Допущения — в `DECISIONS.md`. Короткая записка бухгалтеру — `ACCOUNTANT.md`.
