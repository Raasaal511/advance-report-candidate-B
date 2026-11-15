# Транскрипты

В задании просят экспорт сессии Claude Code (`/export`).

Основная реализация сделана в Cursor (Composer). Claude Code CLI на машине сейчас без логина (`Not logged in · Please run /login`), поэтому настоящего `/export` из этой среды нет.

## Как получить настоящий `/export` за 2–3 минуты

1. В терминале из корня репозитория:
   ```bash
   cd /path/to/advance-report-candidate-B
   claude
   ```
2. Если попросит — `/login`.
3. Вставь промпт:
   ```text
   Проект уже готов. Прочитай README.md и DECISIONS.md, запусти
   PYTHONPATH=src python3 -m unittest discover -s tests -v
   и коротко скажи, что проверил и какие риски в допущениях.
   Ничего не ломай без причины.
   ```
4. После ответа: `/export` → сохрани файл сюда, например:
   `transcripts/claude-export.md`
5. Закоммить и запушь.

Файл `cursor-session.md` рядом — честный лог работы в Cursor, не подмена `/export`.
