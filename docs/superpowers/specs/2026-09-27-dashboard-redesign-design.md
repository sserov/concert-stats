# Dashboard Redesign Spec

Техническое задание: redesign concert-stats/dashboard.html

## 1. Цель

Переделать текущий dashboard из набора независимых Plotly-графиков в интерактивный editorial-style data explorer.

Основная задача пользователя: исследовать изменение концертного репертуара двух московских залов по сезонам и сравнивать отдельных композиторов между собой и между залами.

Существующий data pipeline, JSON schema и scraping не изменять без необходимости.

## 2. Ограничения

Сохранить:

- Python 3.13; build_dashboard.py; dashboard_template.html; data/dataset.json
- самодостаточность dashboard.html (открытие локально, без backend/runtime server)
- Plotly 3.0.1 CDN либо заменить библиотеку только после отдельного согласования
- все существующие данные и фильтры

Добавить JS/CSS можно в template.

## 3. Page structure

**Header.** Title: «Музыкальный репертуар Москвы». Subtitle: «Московская филармония · Московская консерватория · сезоны 2016/17—2026/27». Description: «Как менялась программа двух московских концертных площадок за последнее десятилетие». Ссылка «О проекте».

**Global controls** (sticky при scroll):

- Hall selector, segmented control: Оба / Московская филармония / Московская консерватория
- Season range: От 2016/17 — До 2026/27
- Composer search: autocomplete; выбор добавляет композитора в selection. Selection: чипы [Композитор ×], максимум 6.

## 4. KPI section

Четыре значения: концерты; композиторы; identified-program coverage; концерты без распознанного композитора. Пересчитываются для текущего фильтра. Без крупных цветных карточек.

## 5. Main trend chart

Title: «Как меняется популярность композиторов». Default — 5 наиболее частых композиторов текущего фильтра; пользователь может добавлять/удалять, максимум 6. Metric selector: Доля (default) / Количество. Share = composer_concerts / all_concerts в рамках текущего фильтра. X — сезон, Y — % или целое. Hover: сезон, композитор, значение, число концертов, разбивка по залам (если «Оба»), юбилейный статус. Jubilee annotations компактные, без толстых вертикальных dashed lines на всю высоту.

## 6. Composer ranking

Title: «Кто звучит чаще всего». Таблица (не bar chart). Колонки: Композитор, Доля, Количество, Изменение к первому сезону, Sparkline. Сортировка. Клик по строке → композитор в main trend. Поиск → фильтр таблицы.

## 7. Composer heatmap

Title: «Репертуар по сезонам». Default metric: «Доля концертов сезона, %», toggle Доля/Количество. Default rows: Top 15. Кнопка «Показать ещё». Search-selected композиторы присутствуют в heatmap даже вне Top 15. X — сезоны, Y — композиторы. Текущий сезон 2026/27 визуально incomplete.

## 8. Hall comparison

Title: «Один композитор — два зала». Selector композитора. Две серии: Филармония / Консерватория. Metric: share by default. Summary: Филармония X% / Консерватория Y%.

## 9. Composer detail drawer

Клик по композитору в любом месте → правый drawer (desktop) / full-screen sheet (mobile). Содержимое: имя, годы жизни, всего концертов, доля, тренд, разбивка по залам, юбилейные отметки, таблица по сезонам, опционально список концертов из dataset. Без перезагрузки страницы.

## 10. Coverage section

Title: «Насколько полны данные». Поясняющие метки: partial Philharmonic coverage before 2019; COVID period; current incomplete season. Текст явно указывает, что абсолютные количества по годам зависят от охвата источников.

## 11. Data interpretation

Compact methodology note: «Для сравнения сезонов основной показатель — доля концертов, а не абсолютное количество. Охват источников различается по годам; данные Московской филармонии до 2019 года частично восстановлены через Wayback Machine.» Рядом с релевантной визуализацией и в «О проекте».

## 12. Visual design

Background warm off-white. Serif для крупных заголовков, sans-serif для UI/данных. Палитра: background #F7F5F0, text #22211F, muted #77736B, grid #DDD9D0, philharmonic #8C2635, conservatory #536B63, jubilee #A77A2B. Не использовать Plotly default categorical palette и rainbow. Heatmap — сдержанная sequential palette с адекватным контрастом.

## 13. Layout

Desktop: max-width 1440px, padding 32–48px. Main chart значительно больше второстепенных визуализаций. Не каждую секцию в отдельной bordered card — иерархия через whitespace и типографику. Mobile: одна колонка, sticky filters, горизонтально скроллящийся heatmap, drawer full-screen, чарты ресайзятся без горизонтального скролла страницы. Breakpoints ~1200/900/600.

## 14. Interactions

Все фильтры обновляют всю страницу. Синхронизация: ranking click → composer selected → main trend updated → heatmap row highlighted → hall comparison updated. Клик по линии/точке/строке heatmap открывает тот же composer detail. Hover работает на тач через tap. Без full-page reloads.

## 15. Current season

2026/27 помечен «текущий сезон», рендерится иначе. Tooltip: «Сезон продолжается; данные неполные».

## 16. COVID period

2020/21 и затронутые периоды — лёгкая фоновая аннотация. Не искажать шкалу, не скрывать данные.

## 17. Performance

~24.6k концертов. Предагрегировать в build_dashboard.py, а не агрегировать raw events в браузере. В HTML: window.DATASET, window.AGGREGATES. Рекомендуемые структуры: season_totals, composer_totals, composer_by_season, composer_by_hall, composer_by_season_by_hall, coverage_by_season, jubilees. Raw events остаются для drill-down. Страница интерактивна без видимой задержки.

## 18. Accessibility

Достаточный контраст; информация не кодируется только цветом; клавиатурная доступность контролов; видимый focus state; aria-labels; текстовые summary у чартов; touch targets ≥ 40px.

## 19. Technical separation

Бизнес-логика не в конфигурации чартов. Структура: state → selectors → aggregations → view-model → render. Функции: getFilteredData(), getComposerRanking(), getComposerTrend(), getHeatmap(), getHallComparison(), getCoverage(), renderKPIs(), renderTrend(), renderRanking(), renderHeatmap(), renderHallComparison(), openComposerDrawer().

## 20. Важное семантическое правило

Каждая визуализация с историческим сравнением чётко различает абсолютное количество концертов и долю всех концертов выбранного scope. Default — share. Абсолютные количества вторичны.

## 21. Критерий готовности

- Сразу при загрузке понятно: это историческое сравнение двух залов.
- Одна явно доминирующая визуализация.
- Выбор композитора отражается по всему дашборду.
- Сравнение до 6 композиторов; переключение % / абсолютные числа.
- Сравнение Филармония vs Консерватория для композитора.
- Heatmap читаем без 30+ строк по умолчанию.
- Текущий сезон и неполнота данных визуально явные.
- Ограничения покрытия видны до выводов из абсолютных количеств.
- Работает на desktop и mobile.
- Плотный Plotly-default legend не требуется для чтения чартов.
- Существующий dataset не меняется (кроме производных агрегатов).
