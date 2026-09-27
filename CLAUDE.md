# concert-stats — правила проекта

Культурный data-журнализм, НЕ generic BI-дашборд. Цель: исследовать, как менялся
репертуар Московской филармонии (meloman.ru) и Московской консерватории
(mosconsv.ru) по сезонам. Живой результат: https://sserov.github.io/concert-stats/

## Стек

- Python 3.13, всегда `uv` (не pip): `uv sync`, `uv run <cmd>`
- Тесты `uv run pytest -q`; линт `uv run ruff check src tests` + `ruff format`
- Дашборд: vanilla JS (без сборщика), Plotly **точно** `plotly-3.0.1.min.js` с
  `cdn.plot.ly` (wildcard-версии отдают 403 — не «обновлять» версию)
- JS-логика дашборда: `src/concert_stats/dashboard_app.js`, чистые селекторы
  тестируются `node --test tests/js` (обёртка: `tests/test_js.py`)
- Деплой: GitHub Actions → GitHub Pages из `docs/` (workflow `pages.yml`)

## Конвейер

scrape_mosconsv / discover_meloman + scrape_meloman → `data/*/events.jsonl` →
build_dataset (`data/dataset.json`: дедуп по source+date+нормализованному title,
сезоны сентябрь–июнь) → aggregates → build_dashboard → `docs/index.html`.

- Скрапинг вежливый (0,3 с пауза), кэш sha1 в `data/raw/` — возобновляемый.
- meloman отдаёт неполную TLS-цепочку — уже закрыто `truststore` в `fetcher.py`;
  curl к нему без `-k` не работает, это нормально.
- В `data/` в git лежит только `dataset.json`; остальное — gitignored артефакты.

## Семантика данных (не нарушать)

- Основная метрика — **доля концертов (%)**, абсолютные количества вторичны:
  охват источников растёт по сезонам и ломает абсолютные сравнения.
- Делитель доли — концерты **текущего зала-фильтра** (per-hall season totals в
  AGGREGATES), не общие.
- Один концерт = одна строка; «концерт с композитором» ≠ «число произведений».
- У композитора сезон без концертов → `null` (разрыв линии) в долях; в counts — 0.
- `2026/27` — текущий неполный сезон: помечать «(тек.)» + «Сезон продолжается;
  данные неполные» на каждой поверхности (trend, heatmap, halls, drawer, coverage).
- Ковид 2019/20–2020/21 — бледная фоновая полоса, не искажать шкалу.
- Ограничения покрытия обязательны видны до выводов из абсолютных чисел:
  meloman до 2018/19 частичный (Wayback), 2015/16 усечён срезом, meloman 2025/26
  частичный захват.

## Дашборд

- Desktop-only (1440×900+; мобильная версия не нужна — решение владельца).
- Самодостаточный `docs/index.html`: открывается локально по file://, без сервера.
- JSON инкладывается с экранированием `</` → `<\/` (`_embed` в build_dashboard);
  НИКОГДА не инкладывать неотэкранированный JSON с пользовательскими строками.
- Plotly-события (`plotly_click`) вешать только после первого `newPlot`
  (внутри `.then()`); на не-плотах `.on` не существует — старый фатальный баг.
- Числа ru-RU (запятая-десятичная), разницы долей в «п.п.».
- Палитра задана в шаблоне (`:root` + PALETTE в app.js): филармония `#8C2635`,
  консерватория `#536B63`, юбилей `#A77A2B`. Никаких Plotly-default и радуги.

## Известные грабли окружения

- Headless Chrome не читает `~/Documents` (macOS TCC): для скриншотов копировать
  в `/tmp` и открывать `file:///tmp/...`. Проверка рендера: dump-dom + счётчик
  `<svg` + injected error-listener (grep JSERR).
- Bash-хук блокирует `git push` в main — работать через ветку + PR; мерж своих
  PR требует явного одобрения владельца.
- Крупные HTTP-вызовы из Bash перехватывает context-mode — использовать
  ctx_execute/ctx_fetch_and_index.
- `actionlint` не установлен; SHAs экшенов проверять через `gh api
  repos/actions/<a>/git/ref/tags/<tag>` (не по памяти).

## Качество

- TDD: тест сначала, увидеть RED, потом GREEN. Новая логика — с тестом.
- Python: ≤100 строк/функция, абсолютные импорты, docstrings на нетривиальное.
- Коммиты: imperative subject ≤72, в конце `Co-Authored-By: Claude Code
  <noreply@anthropic.com>`; PR-описания заканчиваются `🤖 Generated with
  [Claude Code](https://claude.com/claude-code)`.
- Отчёт «сделано» только с доказательствами: pytest/ruff вывод, скриншот,
  dump-dom — не «должно работать».
