# concert-stats

Статистика композиторов в концертах Московской филармонии (meloman.ru) и
консерватории (mosconsv.ru), сезоны 2016/17–2025/26.

## Запуск

    uv sync
    uv run python -m concert_stats.scrape_mosconsv --start 2016-01-01 --end 2026-09-26
    uv run python -m concert_stats.discover_meloman --from 2016 --to 2026
    uv run python -m concert_stats.scrape_meloman
    uv run python -m concert_stats.build_dataset
    uv run python -m concert_stats.build_dashboard
    open dashboard.html

Скрапинг возобновляемый: сырые ответы кэшируются в `data/raw/`, повторный запуск
докачивает только недостающее. Инкрементальное обновление — теми же командами с
новой датой `--end`.

Тесты: `uv run pytest -q`. Линтеры: `uv run ruff check src tests`.

## Данные

- `data/*/events.jsonl` — события по источникам.
- `data/dataset.json` — объединённый датасет с композиторами и сезонами.
- `data/review_unknown.txt` — кандидаты на пополнение словаря композиторов.
- `dashboard.html` — дашборд (самодостаточный файл).
