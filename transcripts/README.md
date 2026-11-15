# Транскрипты

Рабочая сессия — в `cursor-session.md` (Cursor / Composer).

Если нужна отдельная сессия в Claude Code, из корня репозитория:

```bash
claude
```

Промпт для ревью:

```text
Проект уже готов. Прочитай README.md и DECISIONS.md, запусти
PYTHONPATH=src python3 -m unittest discover -s tests -v
и коротко скажи, что проверил и какие риски в допущениях.
```

Экспорт сессии положи рядом, например `claude-export.md`.
