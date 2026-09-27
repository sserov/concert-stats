# Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Перестроить dashboard.html в editorial-style data explorer по ТЗ (`docs/superpowers/specs/2026-09-27-dashboard-redesign-design.md`): доминирующий trend chart, синхронизированные секции, drawer, share-first семантика.

**Architecture:** Предагрегаты считаются в Python (`aggregates.py`) и инкладятся в HTML как `window.AGGREGATES`; raw concerts остаются как `window.DATASET` (без `program_text` — для drill-down достаточно id/source/date/season/title/hall/composers). Весь JS живёт в `src/concert_stats/dashboard_app.js` (UTM-guard exports для node:test), инкладится в template через placeholder `__APP__`. Слои JS: state → selectors (чистые, тестируемые в node) → view-model → render (Plotly/DOM). CSS — в `<style>` template, дизайн-токены из ТЗ.

**Tech Stack:** Python 3.13 + uv + pytest; vanilla JS (ES2020, без сборщика), Plotly 3.0.1 CDN, `node --test` (Node 22 builtin) для JS-юнитов, запускаемых из pytest.

**Spec:** `docs/superpowers/specs/2026-09-27-dashboard-redesign-design.md`

## Global Constraints

- dashboard.html самодостаточен: открывается локально, без server/build на стороне просмотра.
- Plotly только `https://cdn.plot.ly/plotly-3.0.1.min.js` (точная версия — wildcard даёт 403).
- Палитра: bg `#F7F5F0`, text `#22211F`, muted `#77736B`, grid `#DDD9D0`, филармония `#8C2635`, консерватория `#536B63`, юбилей `#A77A2B`. Никаких Plotly-default categorical и rainbow.
- Default metric везде — **доля** (% концертов), абсолютные количества — вторичны.
- Не трогать: scrape-скрипты, composers.py, dataset.json (schema неизменен; в dashboard.json-встройку добавляются только производные AGGREGATES).
- `ruff check` + `ruff format` + `pytest -q` чисто после каждой задачи.
- Все тексты UI на русском.
- Один concert = одна строка; composer_concerts = число концертов сезона, где композитор встречается (не число произведений).

## Review Focus

1. **Пустой выбор/нет данных**: сезон-диапазон, где у композитора 0 концертов → линия с разрывом (null), не ноль; деление на 0 сезонов → пустой чарт, не NaN.
2. **Доля vs количество при фильтре зала**: share обязан считаться в рамках текущего hall-фильтра (делитель — концерты этого зала), иначе сравнение залов врёт. Тест: getComposerTrend при hall=meloman.
3. **Максимум 6 выбранных**: 7-й чип не добавляется ни через autocomplete, ни через ranking click, ни через heatmap click; UI показывает, почему.
4. **Неполный текущий сезон 2026/27** не должен выглядеть как обвал репертуара: пометка «текущий сезон» везде (trend axis, heatmap колонка, coverage) + tooltip «Сезон продолжается; данные неполные».
5. **`</script>` внутри инлайненных данных**: имена/заголовки с `<` `>` не должны ломать страницу — JSON-встройка через `json.dumps(..., ensure_ascii=False)` уже безопасна для `</script>`? НЕТ: последовательность `</script>` внутри JSON-строки закрывает тег. Пайплайн обязан экранировать `</` → `<\/` (тест на фиксстуре с `</script>` в title).

Тесты на каждый пункт добавлены в задачи-владельцы (Task 3: №1–2; Task 3/5: №3; Task 6/8: №4; Task 2: №5).

---

### Task 1: Агрегаты в Python

**Files:**
- Create: `src/concert_stats/aggregates.py`
- Modify: `src/concert_stats/build_dashboard.py`
- Test: `tests/test_aggregates.py`

**Interfaces:**
- Consumes: `dataset["concerts"]` (поля `source`, `date`, `season`, `hall`, `title`, `program_text`, `composers`), `dataset["composers"]` (cid → `{name, born, died}`).
- Produces: `compute_aggregates(ds: dict) -> dict` со схемой ниже; `build_dashboard.main()` встраивает результат как `window.AGGREGATES`.

AGGREGATES schema (все ключи-сезоны — строки `"2016/17"`):

```python
{
    "seasons": ["2016/17", ..., "2026/27"],           # sorted
    "current_season": "2026/27",                       # последний, помечается incomplete
    "season_totals": {                                 # делители для share
        "2016/17": {"total": 1234, "with_text": 900, "with_composers": 700,
                    "meloman": {"total": 600, "with_text": 400, "with_composers": 300},
                    "mosconsv": {"total": 634, ...}},
    },
    "composer_totals": {"bach": {"total": 1500, "meloman": 800, "mosconsv": 700}},
    "composer_by_season": {"bach": {"2016/17": 120, ...}},        # только ненулевые
    "composer_by_season_by_hall": {"bach": {"2016/17": {"meloman": 60, "mosconsv": 60}}},
    "coverage_by_season": [{"season": "2016/17", "meloman": 600, "mosconsv": 634}, ...],
    "jubilees": [{"cid": "shostakovich", "season": "2025/26", "year": 2025,
                  "label": "50 лет со дня смерти"}],
}
```

Юбилеи: для каждого composer с известным born/died — годовщины 50/100/125/150/175/200/250; год Y относится к сезону `Y/(Y+1)%100` (юбилейное программирование в основном осенью); в список идут только сезоны из `seasons`. Label: `"{k} лет со дня рождения"` / `"{k} лет со дня смерти"`.

`with_text` = непустой `program_text` (после strip) или непустой `structured_composers`.

- [ ] **Step 1: Write failing tests**

```python
"""Tests for AGGREGATES precomputation."""

from concert_stats.aggregates import compute_aggregates


def _ds():
    return {
        "concerts": [
            {"source": "meloman", "date": "2016-10-01", "season": "2016/17", "hall": "h1",
             "title": "A", "program_text": "Бах", "structured_composers": [],
             "composers": ["bach"]},
            {"source": "mosconsv", "date": "2017-03-01", "season": "2016/17", "hall": "h2",
             "title": "B", "program_text": "", "structured_composers": [],
             "composers": []},
            {"source": "meloman", "date": "2016-11-01", "season": "2016/17", "hall": "h1",
             "title": "C", "program_text": "Бах, Моцарт", "structured_composers": [],
             "composers": ["bach", "mozart"]},
            {"source": "meloman", "date": "2026-10-01", "season": "2026/27", "hall": "h1",
             "title": "D", "program_text": "", "structured_composers": ["Шостакович"],
             "composers": ["shostakovich"]},
        ],
        "composers": {
            "bach": {"name": "Иоганн Себастьян Бах", "born": 1685, "died": 1750},
            "mozart": {"name": "Вольфганг Амадей Моцарт", "born": 1756, "died": 1791},
            "shostakovich": {"name": "Дмитрий Шостакович", "born": 1906, "died": 1975},
        },
        "coverage": {"by_year": []},
        "quality": {"total": 4, "without_composers_pct": 50.0},
    }


def test_season_totals_per_hall():
    agg = compute_aggregates(_ds())
    st = agg["season_totals"]["2016/17"]
    assert st["total"] == 3
    assert st["with_text"] == 2
    assert st["with_composers"] == 2
    assert st["meloman"]["total"] == 2
    assert st["mosconsv"]["with_text"] == 0


def test_composer_aggregates():
    agg = compute_aggregates(_ds())
    assert agg["composer_totals"]["bach"] == {"total": 2, "meloman": 2, "mosconsv": 0}
    assert agg["composer_by_season"]["bach"] == {"2016/17": 2}
    assert agg["composer_by_season_by_hall"]["bach"]["2016/17"] == {"meloman": 2, "mosconsv": 0}
    assert agg["composer_by_season"].get("mozart") == {"2016/17": 1}


def test_jubilees_mapped_to_season():
    agg = compute_aggregates(_ds())
    labels = [j["label"] for j in agg["jubilees"] if j["cid"] == "shostakovich"]
    assert "50 лет со дня смерти" in labels          # 1975 + 50 = 2025 → 2025/26
    jub = [j for j in agg["jubilees"] if j["cid"] == "shostakovich" and j["year"] == 2025]
    assert jub and jub[0]["season"] == "2025/26"
    # юбилей вне диапазона сезонов не попадает
    assert all(j["season"] in agg["seasons"] for j in agg["jubilees"])


def test_current_season_is_last():
    agg = compute_aggregates(_ds())
    assert agg["current_season"] == agg["seasons"][-1] == "2026/27"


def test_identified_coverage_semantics():
    # identified coverage = with_composers / with_text, не / total
    agg = compute_aggregates(_ds())
    st = agg["season_totals"]["2016/17"]
    assert st["with_text"] == 2 and st["with_composers"] == 2
```

- [ ] **Step 2: Run, verify fail**

`uv run pytest tests/test_aggregates.py -q` → FAIL (ModuleNotFoundError).

- [ ] **Step 3: Implement `aggregates.py`**

```python
"""Precompute AGGREGATES for the dashboard: season totals, composer stats, jubilees."""

from concert_stats.composers import by_cid

_JUBILEE_K = (50, 100, 125, 150, 175, 200, 250)


def _empty_hall() -> dict:
    return {"total": 0, "with_text": 0, "with_composers": 0}


def _season_of_year(year: int) -> str:
    return f"{year}/{(year + 1) % 100:02d}"


def compute_aggregates(ds: dict) -> dict:
    """Aggregate dataset concerts into dashboard-ready structures.

    season_totals carries per-hall total/with_text/with_composers so share
    denominators respect the hall filter without touching raw events.
    """
    seasons = sorted({c["season"] for c in ds["concerts"]})
    season_set = set(seasons)

    season_totals: dict[str, dict] = {
        s: {"total": 0, "with_text": 0, "with_composers": 0,
            "meloman": _empty_hall(), "mosconsv": _empty_hall()}
        for s in seasons
    }
    composer_totals: dict[str, dict] = {}
    composer_by_season: dict[str, dict[str, int]] = {}
    composer_by_season_by_hall: dict[str, dict[str, dict[str, int]]] = {}

    for c in ds["concerts"]:
        src = c["source"]
        has_text = bool(c["program_text"].strip() or c["structured_composers"])
        has_comp = bool(c["composers"])

        st = season_totals[c["season"]]
        st["total"] += 1
        st["meloman" if src == "meloman" else "mosconsv"]["total"] += 1
        if has_text:
            st["with_text"] += 1
            st["meloman" if src == "meloman" else "mosconsv"]["with_text"] += 1
        if has_comp:
            st["with_composers"] += 1
            st["meloman" if src == "meloman" else "mosconsv"]["with_composers"] += 1

        for cid in c["composers"]:
            ct = composer_totals.setdefault(cid, {"total": 0, "meloman": 0, "mosconsv": 0})
            ct["total"] += 1
            ct[src] += 1
            composer_by_season.setdefault(cid, {})
            composer_by_season[cid][c["season"]] = composer_by_season[cid].get(c["season"], 0) + 1
            by_hall = composer_by_season_by_hall.setdefault(cid, {}).setdefault(c["season"], {})
            by_hall[src] = by_hall.get(src, 0) + 1

    coverage_by_season = [
        {"season": s,
         "meloman": season_totals[s]["meloman"]["total"],
         "mosconsv": season_totals[s]["mosconsv"]["total"]}
        for s in seasons
    ]

    jubilees = []
    info = by_cid()
    for cid, comp in info.items():
        for kind, year_birth in (("рождения", comp.born), ("смерти", comp.died)):
            if year_birth is None:
                continue
            for k in _JUBILEE_K:
                year = year_birth + k
                season = _season_of_year(year)
                if season in season_set:
                    jubilees.append({"cid": cid, "season": season, "year": year,
                                     "label": f"{k} лет со дня {kind}"})
    jubilees.sort(key=lambda j: (j["season"], j["cid"]))

    return {
        "seasons": seasons,
        "current_season": seasons[-1] if seasons else None,
        "season_totals": season_totals,
        "composer_totals": composer_totals,
        "composer_by_season": composer_by_season,
        "composer_by_season_by_hall": composer_by_season_by_hall,
        "coverage_by_season": coverage_by_season,
        "jubilees": jubilees,
    }
```

- [ ] **Step 4: Run tests, verify pass**

`uv run pytest tests/test_aggregates.py -q` → 5 passed.

- [ ] **Step 5: Wire into build_dashboard.main()** (после чтения dataset):

```python
from concert_stats.aggregates import compute_aggregates
agg = compute_aggregates(ds)
```
и в рендере template добавить вторую строку данных `window.AGGREGATES = __AGGREGATES__;` (placeholder заменяется тем же `json.dumps(..., ensure_ascii=False)`). Полная сборка template — Task 4; здесь достаточно, чтобы `render()` принимал агрегаты и подставлял оба placeholder (см. Task 2 Step 3 для финальной сигнатуры).

- [ ] **Step 6: `uv run pytest -q` (все зелёные), ruff, commit**

```bash
git add src/concert_stats/aggregates.py src/concert_stats/build_dashboard.py tests/test_aggregates.py
git commit -m "feat: precompute dashboard aggregates in Python"
```

---

### Task 2: Build pipeline — app.js инклад, slim DATASET, script-safe JSON

**Files:**
- Create: `src/concert_stats/dashboard_app.js` (пока пустой каркас: UMD-guard + exports)
- Modify: `src/concert_stats/build_dashboard.py`, `src/concert_stats/dashboard_template.html`
- Test: `tests/test_dashboard.py` (расширить)

**Interfaces:**
- Consumes: `compute_aggregates` (Task 1).
- Produces:
  - `render(template_html: str, dataset: dict, aggregates: dict, app_js: str) -> str` — заменяет `__DATA__`, `__AGGREGATES__`, `__APP__`.
  - `slim_concerts(ds) -> list[dict]` — concerts только с `id, source, date, season, hall, title, composers`.
  - Встроенные JSON экранированы: `</` → `<\/` (regexp по сериализованной строке — валидный JSON это переживает, `json.loads` возвращает исходные строки).
  - `dashboard_app.js` структура: сверху pure-функции, внизу

```javascript
if (typeof module !== "undefined" && module.exports) {
  module.exports = { scopeTotals, getComposerRanking, getComposerTrend,
                     getHeatmapData, getHallComparison, getCoverage, jubileeMap };
}
if (typeof document !== "undefined" && typeof window !== "undefined") {
  window.DashApp = init;  // init определён в Task 5
}
```

- [ ] **Step 1: Failing tests** (добавить в `tests/test_dashboard.py`)

```python
def test_render_escapes_script_closing_tag():
    ds = {"concerts": [{"id": "x:1", "source": "meloman", "date": "2020-01-01",
                        "season": "2019/20", "hall": "h", "title": "a</script><b>",
                        "program_text": "", "structured_composers": [],
                        "composers": [], "parse_failed": False, "date_approximate": False}],
          "composers": {}, "coverage": {"by_year": []},
          "quality": {"total": 1, "without_composers_pct": 100.0}, "unknown_top": []}
    out = render("<script>window.DATASET = __DATA__;</script>", ds, {}, "")
    assert "</script><b>" not in out
    assert "<\\/script>" in out
    # и JSON после unescape валиден:
    import json as j
    raw = out.split("window.DATASET = ")[1].split(";</script>")[0].replace("<\\/", "</")
    assert j.loads(raw)["concerts"][0]["title"] == "a</script><b>"


def test_slim_concerts_drops_program_text():
    ds = _ds()  # существующий в файле хелпер или копия фикстуры выше
    slim = slim_concerts(ds)
    assert slim and set(slim[0]) == {"id", "source", "date", "season", "hall",
                                     "title", "composers"}


def test_render_inlines_app_js():
    out = render("__APP__", _ds(), {}, "console.log('app');")
    assert "console.log('app');" in out and "__APP__" not in out
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement.** `build_dashboard.py`:

```python
import json
import re
from importlib import resources

_HERE = resources.files("concert_stats")


def _embed(value) -> str:
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def slim_concerts(ds: dict) -> list[dict]:
    keep = ("id", "source", "date", "season", "hall", "title", "composers")
    return [{k: c[k] for k in keep} for c in ds["concerts"]]


def render(template_html: str, dataset: dict, aggregates: dict, app_js: str) -> str:
    html = template_html.replace("__APP__", app_js)
    html = html.replace("__AGGREGATES__", _embed(aggregates))
    return html.replace("__DATA__", _embed({**dataset, "concerts": slim_concerts(dataset)}))


def main() -> None:
    ds = json.loads((DATA_DIR / "dataset.json").read_text(encoding="utf-8"))
    agg = compute_aggregates(ds)
    template = (_HERE / "dashboard_template.html").read_text(encoding="utf-8")
    app_js = (_HERE / "dashboard_app.js").read_text(encoding="utf-8")
    out = DATA_DIR / "dashboard.html"
    out.write_text(render(template, ds, agg, app_js), encoding="utf-8")
    print(f"dashboard.html written ({out.stat().st_size // 1024} KB)")
```
(импорты `compute_aggregates` — из Task 1; `DATA_DIR` уже есть). В template добавить строку `<script>window.AGGREGATES = __AGGREGATES__;</script>` рядом с DATASET и `<script>__APP__</script>`. Создать `dashboard_app.js` с UMD-хвостом из Interfaces (селекторы добавит Task 3).

- [ ] **Step 4: `uv run pytest -q` → pass. Step 5: Commit**

```bash
git add src/concert_stats/build_dashboard.py src/concert_stats/dashboard_template.html src/concert_stats/dashboard_app.js tests/test_dashboard.py
git commit -m "feat: inline app.js, slim dataset, script-safe JSON embed"
```

---

### Task 3: Pure selectors в app.js + node-тесты

**Files:**
- Modify: `src/concert_stats/dashboard_app.js`
- Create: `tests/js/dashboard_app.test.js`, `tests/test_js.py`
- Test: сам `tests/js/dashboard_app.test.js`, запускаемый pytest-обёрткой

**Interfaces:**
- Consumes: `AGG` (schema Task 1), `state = {hall: "all"|"meloman"|"mosconsv", seasonFrom: str, seasonTo: str, metric: "share"|"count", selected: [cid], heatmapExtra: int}`.
- Produces (все чистые, без DOM/Plotly):

```javascript
seasonsInRange(AGG, state)                      // -> ["2016/17", ...] обрезанный диапазоном
scopeTotals(AGG, state)                         // -> {total, withText, withComposers} по hall+диапазону
getComposerRanking(AGG, state)                  // -> [{cid, name, share, count, deltaFirstSeason,
                                                //      sparkline: [num|null, ...]}] sorted by share desc
getComposerTrend(AGG, state, cids)              // -> [{cid, name, values: [share|count|null,...]}]
getHeatmapData(AGG, state, rowLimit)            // -> {rows: [{cid, name, values:[...]}], forced: [cid]}
getHallComparison(AGG, state, cid)              // -> {seasons, phil: [share|null], cons: [share|null],
                                                //     philTotal: n, consTotal: n,
                                                //     philShare: x, consShare: y}
getCoverage(AGG)                                // -> coverage_by_season как есть (для render)
jubileeMap(AGG)                                 // -> {"bach|2025/26": "100 лет со дня рождения", ...}
```

Правила: share = composer_concerts / season_total **в рамках state.hall** (делитель из `season_totals[s][hall]["total"]`), ×100, округление на рендере; отсутствующий сезон у композитора → `null` (разрыв линии), а не 0; `deltaFirstSeason` = share последнего **завершённого** сезона минус share первого в диапазоне (текущий сезон исключён), в п.п.; `sparkline` — share по всем сезонам диапазона (включая текущий). `getHeatmapData` включает `state.selected` в rows даже вне Top `rowLimit` (поле `forced`). Хелпер `_hallTotals(AGG, season, hall)` возвращает per-hall dict (hall="all" → сумма).

- [ ] **Step 1: Failing tests** (`tests/js/dashboard_app.test.js`, node:test)

```javascript
const { test } = require("node:test");
const assert = require("node:assert");
const S = require("../../src/concert_stats/dashboard_app.js");

const AGG = {
  seasons: ["2016/17", "2017/18", "2026/27"],
  current_season: "2026/27",
  season_totals: {
    "2016/17": { total: 10, with_text: 8, with_composers: 6,
      meloman: { total: 6, with_text: 5, with_composers: 4 },
      mosconsv: { total: 4, with_text: 3, with_composers: 2 } },
    "2017/18": { total: 20, with_text: 18, with_composers: 16,
      meloman: { total: 12, with_text: 11, with_composers: 10 },
      mosconsv: { total: 8, with_text: 7, with_composers: 6 } },
    "2026/27": { total: 5, with_text: 5, with_composers: 5,
      meloman: { total: 3, with_text: 3, with_composers: 3 },
      mosconsv: { total: 2, with_text: 2, with_composers: 2 } },
  },
  composer_totals: {
    bach: { total: 12, meloman: 7, mosconsv: 5 },
    mozart: { total: 6, meloman: 6, mosconsv: 0 },
  },
  composer_by_season: {
    bach: { "2016/17": 3, "2017/18": 8, "2026/27": 1 },
    mozart: { "2016/17": 6 },
  },
  composer_by_season_by_hall: {
    bach: { "2016/17": { meloman: 1, mosconsv: 2 },
            "2017/18": { meloman: 5, mosconsv: 3 },
            "2026/27": { meloman: 1, mosconsv: 0 } },
  },
  coverage_by_season: [],
  jubilees: [{ cid: "bach", season: "2017/18", year: 2017, label: "К юбилею" }],
};
const COMPOSERS = { bach: { name: "И. С. Бах", born: 1685, died: 1750 },
                    mozart: { name: "В. А. Моцарт", born: 1756, died: 1791 } };
const baseState = { hall: "all", seasonFrom: "2016/17", seasonTo: "2026/27",
                    metric: "share", selected: [], heatmapExtra: 0 };

test("share uses hall-specific denominator", () => {
  const t = S.getComposerTrend(AGG, { ...baseState, hall: "meloman" }, ["bach"]);
  // 2016/17: meloman bach=1, meloman total=6 → ~16.7%
  assert.ok(Math.abs(t[0].values[0] - 100 * 1 / 6) < 1e-9);
});

test("missing season yields null, not zero", () => {
  const t = S.getComposerTrend(AGG, baseState, ["mozart"]);
  assert.strictEqual(t[0].values[1], null);
  assert.strictEqual(t[0].values[0], 60);
});

test("delta excludes current season", () => {
  const r = S.getComposerRanking(AGG, baseState);
  const bach = r.find((x) => x.cid === "bach");
  // last completed = 2017/18 (40%), first = 2016/17 (30%) → +10
  assert.ok(Math.abs(bach.deltaFirstSeason - 10) < 1e-9);
});

test("heatmap forces selected composers into rows", () => {
  const h = S.getHeatmapData(AGG, { ...baseState, selected: ["mozart"] }, 1);
  const ids = h.rows.map((r) => r.cid);
  assert.ok(ids.includes("mozart"));
  assert.strictEqual(h.rows.length, 2); // top1 (bach) + forced mozart
});

test("season range clamps", () => {
  const s = S.seasonsInRange(AGG, { ...baseState, seasonFrom: "2017/18", seasonTo: "2017/18" });
  assert.deepStrictEqual(s, ["2017/18"]);
});

test("scopeTotals respects hall", () => {
  const t = S.scopeTotals(AGG, { ...baseState, hall: "mosconsv" });
  assert.strictEqual(t.total, 14);
});
```

pytest-обёртка `tests/test_js.py`:

```python
"""Run node:test suites for dashboard JS selectors."""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("suite", [Path("tests/js")])
def test_js_selectors(suite: Path) -> None:
    result = subprocess.run(
        ["node", "--test", str(suite)], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
    assert result.returncode == 0, result.stderr
```

- [ ] **Step 2: Run `uv run pytest tests/test_js.py -q` → FAIL** (node: cannot find module / функции undefined).

- [ ] **Step 3: Implement selectors в `dashboard_app.js`** — обычный ES2020 без сборщика, `const AGG`/`COMPOSERS` приходят из window в браузере и передаются аргументами в тестах. Имена/даты: `NAME(cid)` хелпер читает `window.DATASET.composers`; для node — вторая сигнатура не нужна: передавать `COMPOSERS` внутри AGG нельзя, поэтому selectors принимают третий опциональный аргумент `meta = {composers}` c дефолтом `typeof window !== "undefined" ? window.DATASET.composers : {}`. Следить за ≤100 строк/функцию — разбить хелперами (`_share(n, d)`, `_hallTotals`).

- [ ] **Step 4: `uv run pytest tests/test_js.py -q` → pass; `node --check src/concert_stats/dashboard_app.js` → OK.**

- [ ] **Step 5: Commit**

```bash
git add src/concert_stats/dashboard_app.js tests/js/dashboard_app.test.js tests/test_js.py
git commit -m "feat: pure dashboard selectors with node tests"
```

---

### Task 4: Template shell — дизайн-система, layout, header, controls, секции

**Files:**
- Modify: `src/concert_stats/dashboard_template.html` (полная замена body/CSS, JS-логика НЕ в этой задаче — только разметка)
- Test: `tests/test_dashboard.py` (структурные ассерты)

**Interfaces:**
- Produces: DOM-каркас, на который вешается Task 5–9. Обязательные id/классы:

```
header.site-head          h1 + .sub + .desc + кнопку #about-open
.controls (sticky)        #hall-seg (3 кнопки .seg-btn), #season-from, #season-to,
                          #composer-search + #search-ac (autocomplete list), #chips
section#kpi               #kpi-concerts #kpi-composers #kpi-coverage #kpi-unknown
section#trend             #metric-seg (Доля/Количество), #trend-plot, .method-note
section#ranking           #ranking-search, table#ranking-table thead th[data-sort]
section#heatmap           #heatmap-metric-seg, #heatmap-plot-wrap, #heatmap-more
section#halls             #hall-cid (select), #hall-plot, #hall-summary
section#coverage          #coverage-plot, .cov-note
#drawer (aside)           #drawer-body, [data-close], backdrop #drawer-bg
#about (dialog)           methodology text
```

CSS-токены (в `:root`): `--bg:#F7F5F0; --text:#22211F; --muted:#77736B; --grid:#DDD9D0; --phil:#8C2635; --cons:#536B63; --jub:#A77A2B`. Serif (`Georgia, 'Times New Roman', serif`) только для `h1`, заголовков секций; UI/данные — system sans (`-apple-system, 'Segoe UI', Roboto, sans-serif`). Layout: `.wrap{max-width:1440px;margin:0 auto;padding:32px 48px}`; `#trend .plot` высота ~560px, вторичные ~320–380px; секции разделены whitespace + тонкий `border-top:1px solid var(--grid)` c заголовком-надписью, НЕ карточки с рамками. Breakpoints 1200/900/600: одна колонка ниже 900, `.controls` sticky `top:0` c `background:var(--bg)`; `#heatmap-plot-wrap{overflow-x:auto}` всегда; focus-visible: `outline:2px solid var(--jub); outline-offset:2px`; touch targets `min-height:40px` у всех кнопок/опций.

Тексты: header по ТЗ §3; method-note и «О проекте» — текст из ТЗ §11 дословно.

- [ ] **Step 1: Failing structural test**

```python
def test_template_has_redesign_shell():
    html = (resources.files("concert_stats") / "dashboard_template.html").read_text("utf-8")
    for needle in (
        "Музыкальный репертуар Москвы",
        "сезоны 2016/17—2026/27",
        'id="hall-seg"', 'id="season-from"', 'id="season-to"',
        'id="composer-search"', 'id="chips"',
        'id="trend-plot"', 'id="ranking-table"', 'id="heatmap-plot-wrap"',
        'id="hall-plot"', 'id="coverage-plot"', 'id="drawer"', 'id="about"',
        "#8C2635", "#536B63", "#A77A2B", "#F7F5F0",
        "Для сравнения сезонов основной показатель — доля концертов",
        "Wayback Machine",
    ):
        assert needle in html, needle
```

- [ ] **Step 2: FAIL → Step 3: переписать template** (полный HTML+CSS, пустые контейнеры, `<noscript>`-заглушка «Для интерактивных графиков нужен JavaScript и интернет (Plotly CDN)»). Plotly tag уже пиненный — не трогать. `__APP__` после `<script>window.AGGREGATES...` блока.

- [ ] **Step 4: `uv run pytest -q` → pass. Step 5: Commit** `feat: redesign template shell, design tokens, layout`.

---

### Task 5: State, контролы, KPI, init

**Files:**
- Modify: `src/concert_stats/dashboard_app.js`
- Test: `tests/js/dashboard_app.test.js` (addSelected/cap logic), `tests/test_dashboard.py` (render smoke)

**Interfaces:**
- Produces: `init()` (bootstrap: читает `window.DATASET`, `window.AGGREGATES`, вешает события, зовёт `renderAll()`), `addSelected(cid)` / `removeSelected(cid)` с капом 6, `renderKPIs()`, `renderChips()`, autocomplete (фильтр по name, стрелки/Enter/Escape, `role="listbox"/"option"`, aria-selected), `renderAll()` — вызывает все render* из Tasks 5–9.

Кап 6: при попытке 7-го — короткий toast `#toast` «Максимум 6 композиторов» (aria-live=polite), выбор отклонён. Default selection при пустом selected: top-5 по share текущего фильтра (не мутация state.selected — вычисляется в getComposerTrend-view, чтобы «сбросить выбор» возвращал default). KPI: концерты (`scopeTotals.total`), композиторы (число cid с count>0 в scope), identified coverage (`withComposers/withText`, %, 1 знак), без композиторов (`(total-withComposers)/total`, %). Значения — тонкая строка из четырёх «число + подпись», без карточек.

- [ ] **Step 1: Failing node test**

```javascript
test("selection capped at 6 with flag", () => {
  const sel = [];
  const a1 = S.addSelected(sel, "a"); const a2 = S.addSelected(sel, "b");
  ["c","d","e","f"].forEach((c) => S.addSelected(sel, c));
  const a7 = S.addSelected(sel, "g");
  assert.strictEqual(sel.length, 6);
  assert.strictEqual(a7, false);          // отклонён
  assert.strictEqual(a1 && a2, true);
});

test("removeSelected toggles off", () => {
  const sel = ["a", "b"];
  S.removeSelected(sel, "a");
  assert.deepStrictEqual(sel, ["b"]);
});
```
(`addSelected(sel, cid) -> boolean` — чистая мутация переданного массива; рендер слушает изменения через `renderAll()`.)

- [ ] **Step 2: FAIL → Step 3: implement** — `addSelected`, `removeSelected`, `init`, `renderKPIs`, `renderChips`, autocomplete, `renderAll` (с safe-guard `typeof renderTrend === "function"` пока соседние рендеры не написаны — NO: этого guard не будет, Tasks 6–9 добавляют рендеры; чтобы каждая задача оставалась зелёной, `renderAll` вызывает массив `RENDERERS`, в который каждая задача добавляет свою функцию — `RENDERERS.push(renderTrend)` в Task 6 и т.д.).

- [ ] **Step 4: tests pass; smoke: `uv run python -m concert_stats.build_dashboard`, открыть dashboard.html — контролы отвечают, KPI заполнены, чарты пусты.**

- [ ] **Step 5: Commit** `feat: dashboard state, controls, KPI, autocomplete`.

---

### Task 6: renderTrend — доминирующий чарт

**Files:**
- Modify: `src/concert_stats/dashboard_app.js`
- Test: `tests/js/dashboard_app.test.js` (view-model: metric switch, hover data complete), ручная проверка конфига

**Interfaces:**
- Consumes: `getComposerTrend`, `jubileeMap`, `seasonsInRange`, `RENDERERS`.
- Produces: `renderTrend()` — Plotly в `#trend-plot`.

Правила рендера:
- Цвета линий — curated palette на базе ТЗ, не Plotly default: `["#8C2635","#536B63","#A77A2B","#3E5C76","#7A5C3E","#4F6228"]` (6 шт. под кап; контраст к #F7F5F0 ≥ 4.5:1 у первых трёх, остальные ≥ 3:1 — проверить).
- hovertemplate: `Сезон %{x}<br>%{fullData.name}<br>%{customdata[0]}<br>концертов: %{customdata[1]}<extra></extra>`; customdata per point: форматированное значение + count + (hall split `филармония X · консерватория Y` при hall=all) + юбилейная строка, склеенная через `<br>`.
- Jubilee: `annotations` на точке (arrowhead small, text=label, bgcolor rgba(167,122,43,0.15)) — НЕ shapes на всю высоту.
- COVID: `shapes: [{type:'rect', x0:'2019/20', x1:'2020/21', yref:'paper', y0:0, y1:1, fillcolor:'#77736B', opacity:0.06, line:{width:0}}]` + annotation «ковид» сверху muted.
- Current season: последняя категория x — `2026/27 *` (или `, text: '2026/27<br><tspan>текущий</tspan>'` — проще: ticktext с пометкой «(тек.)»), столбик grid-линии не выделяем; в hover для точек текущего сезона добавлять «Сезон продолжается; данные неполные».
- metric=count: `yaxis.title='концертов за сезон'`, integer ticks (`tickformat:',d'`); metric=share: `yaxis.title='% концертов сезона'`, `ticksuffix:'%'`.
- config: `{displayModeBar:false, responsive:true}`.
- a11y: `#trend-plot` получает `aria-label` «Линейный график доли концертов по сезонам для выбранных композиторов» + под чартом текстовый summary «N концертов, топ: X (Y%)…» (обновляется в renderTrend).

- [ ] **Step 1: Failing test** — view-model: `trendViewModel(AGG, state)` (добавить как чистую функцию) возвращает `{x, traces:[{cid,name,color,shares,counts}], annotations:[...], covidRange}`; тест: длина traces ≤ 6; в каждой точке `counts[i] !== undefined`; при metric=count значение = counts. Step 2: FAIL. Step 3: implement renderTrend + trendViewModel. Step 4: pass + build + `node --check`. Step 5: Commit `feat: main trend chart with jubilees, covid band, current season`.

---

### Task 7: renderRanking — таблица

**Files:**
- Modify: `src/concert_stats/dashboard_app.js`
- Test: `tests/js/dashboard_app.test.js` (сортировка view-model, delta формат)

**Interfaces:**
- Consumes: `getComposerRanking`, `RENDERERS`, `addSelected`.
- Produces: `renderRanking()` — DOM-таблица в `#ranking-table`.

- Колонки: Композитор (кнопка-строка), Доля (`12,4%`), Количество (int), Δ к первому сезону (`+3,1 п.п.` / `−2,0 п.п.` / `—` если нет пары завершённых сезонов; всегда с ▲/▼ — не только цвет), Sparkline (inline `<svg width="72" height="20">` polyline по `sparkline`, stroke `var(--phil)`).
- Sort: клик по `th[data-sort]` (share|count|delta|name) asc/desc, стрелка-индикатор в th, `aria-sort`.
- Row click → `addSelected` (с капом и toast из Task 5) → renderAll. Выбранные строки: `class="sel"` + слева полоска 3px цвета композитора из palette Task 6 (дублирует клик — цвет не единственный носитель: есть иконка ✓).
- `#ranking-search` фильтрует строки по подстроке имени (case-insensitive).
- Показ топ-50 строк + кнопка «Показать ещё 50» (state.rankingLimit).
- Sparkline и числа — из `getComposerRanking`; НИКАКОЙ агрегации в рендере.

- [ ] **Step 1: Failing test**: `rankingViewModel` — сортировка по count desc меняет порядок; delta null при одном завершённом сезоне. Step 2: FAIL. Step 3: implement. Step 4: pass + build. Step 5: Commit `feat: sortable composer ranking table with sparklines`.

---

### Task 8: renderHeatmap

**Files:**
- Modify: `src/concert_stats/dashboard_app.js`
- Test: `tests/js/dashboard_app.test.js` (rows limit + forced + metric), build smoke

**Interfaces:**
- Consumes: `getHeatmapData`, `RENDERERS`.
- Produces: `renderHeatmap()`.

- `Plotly.newPlot('#heatmap-plot', [{type:'heatmap', ...}])`: `colorscale` сдержанный sequential от `#F7F5F0` к `#8C2635` (например `[[0,'#F7F5F0'],[0.5,'#D9A69B'],[1,'#8C2635']]` — проверить контраст надписей hover), `colorbar` c title по metric (Доля / Количество), `x=seasons, y=names`, `hovertemplate` c сезон/композитор/значение и неполнотой текущего сезона.
- Selected rows: y-tickfont жирный/цветной по palette + тонкая полоска слева невозможна в Plotly → двойной якорь: жирный шрифт + `°` в label (проверить глазами).
- `#heatmap-more` кнопка: `state.heatmapExtra += 15`, перерендер (15 → 30 → 45…).
- Current season колонка: в ticktext последнего x добавить ` (тек.)`; поверх — annotation «неполный сезон» под углом, muted.
- Wrap `overflow-x:auto` (уже в CSS Task 4); Plotly `responsive:true`; ширина по числу сезонов.

- [ ] **Step 1: Failing test**: `getHeatmapData(AGG, state, 15)` при 20 композиторах и `selected=['rank18cid']` → 16 rows, forced содержит selected. Step 2: FAIL. Step 3: implement renderHeatmap. Step 4: pass + build. Step 5: Commit `feat: repertoire heatmap with top-15, show-more, forced selected rows`.

---

### Task 9: Hall comparison + composer drawer

**Files:**
- Modify: `src/concert_stats/dashboard_app.js`
- Test: `tests/js/dashboard_app.test.js` (getHallComparison числа), build smoke

**Interfaces:**
- Consumes: `getHallComparison`, `getComposerTrend`, `jubileeMap`, `window.DATASET.concerts` (slim — для списка концертов).
- Produces: `renderHallComparison()`, `openComposerDrawer(cid)`.

**Hall comparison:**
- `#hall-cid` select: список всех композиторов scope, отсортирован по share; default — первый выбранный в чипах, иначе top-1.
- Две линии: Филармония `#8C2635`, Консерватория `#536B63`; y — % концертов зала сезона (делитель — per-hall season total).
- Summary над чартом: `Филармония 12,3% · Консерватория 8,9%` по всему диапазону (композитор_концертов зала / total зала).

**Drawer:**
- Открытие: клик строки ranking (с `Shift`? — NO: обычный клик добавляет в selection; открытие drawer — отдельная кнопка-стрелка в конце строки «детали ↗», плюс клик по линии/точке trend и по heatmap ячейке (plotly_click), плюс выбор в `#hall-cid` не открывает).
- Содержимое: имя + годы жизни (`1840–1893`); KPI: всего концертов (total, per hall), доля; mini trend (Plotly, share, две линии залов); юбилейные отметки списком; таблица по сезонам (сезон, концертов, доля, залы); последние 20 концертов (дата, зал, название) из slim DATASET (`DATASET.concerts.filter(c=>c.composers.includes(cid)).slice(-20).reverse()`).
- `aside#drawer` fixed right 0, width 420px, transform translateX(100%) → 0, `role="dialog" aria-modal="true" aria-label="Карточка композитора"`, фокус в drawer, Esc/backdrop/`[data-close]` закрывают, фокус возвращается на триггер. Mobile (<600): width 100%.
- Никаких перезагрузок; на plotly_click по trend линии — `openComposerDrawer(cid)` (cid из trace meta).

- [ ] **Step 1: Failing test**: `getHallComparison` — philShare/consShare по фикстуре; phil values используют meloman делители. Step 2: FAIL. Step 3: implement оба рендера + drawer. Step 4: pass + build. Step 5: Commit `feat: hall comparison chart and composer detail drawer`.

---

### Task 10: Coverage, «О проекте», accessibility-проход, финальная сборка

**Files:**
- Modify: `src/concert_stats/dashboard_app.js`, `src/concert_stats/dashboard_template.html`
- Test: `uv run pytest -q` (все), ручной QA-чеклист

**Interfaces:**
- Produces: `renderCoverage()`; финальный `data/dashboard.html`.

- Coverage чарт: stacked bar по `coverage_by_season` (сезоны, не календарные годы — согласовано с остальным дашбордом), цвета залов из токенов; annotations: «частичный охват (Wayback)» над 2016/17–2018/19, «ковид» над 2019/20–2020/21, «текущий, неполный» над последним; `#cov-note` — текст из ТЗ §10–11.
- «О проекте»: `<dialog id="about">` + `#about-open`; методология дословно из ТЗ §11 + краткое описание источников и ограничение «один концерт — одна строка, доля считается по концертам».
- A11y проход: все интерактивные элементы `aria-label`/`aria-sort`/`role` на месте; focus-visible стили; проверка клавиатурой (Tab порядок: controls → ranking → heatmap → halls → about); contrast: muted #77736B на #F7F5F0 ≈ 4.6:1 — ок для текста, для мелких подписей чартов использовать #5d5952 если контраст ниже 4.5; touch targets ≥40px (padding у seg-btn, чипов, th, autocomplete options).
- Resize: `window.addEventListener('resize', debounce(150, renderAll))` — Plotly responsive уже пересоздаёт, но heatmap/tables width зависят от wrap.

- [ ] **Step 1: implement** (render-тесты не нужны — тонкий конфиг; структурный assert что `renderCoverage` в RENDERERS — тривиально, пропускаем по YAGNI, проверка ручная).
- [ ] **Step 2: Полная сборка**: `uv run pytest -q && uv run ruff check src tests && uv run ruff format --check src tests && uv run python -m concert_stats.build_dashboard`.
- [ ] **Step 3: Ручной QA-чеклист** (все пункты ТЗ §21):
  - загрузка: заголовок и доминирующий trend видны сразу, без layout shift;
  - смена зала/диапазона/метрики обновляет ВСЕ секции;
  - выбор композитора (ranking click, autocomplete, heatmap click) отражается в чипах+trend+heatmap+hall comparison;
  - кап 6 работает из всех точек входа;
  - % ↔ количество везде переключается;
  - drawer открывается из trend/heatmap/ranking, Esc закрывает, фокус возвращается;
  - heatmap: топ-15, «Показать ещё», выбранные вне топа присутствуют;
  - 2026/27 помечен везде, tooltip неполноты есть;
  - coverage-пояснения видны ДО просмотра абсолютных количеств;
  - Safari + Chrome desktop 1440px и 375px (mobile): без горизонтального скролла страницы (heatmap скроллится внутри), drawer full-screen, sticky controls;
  - file:// открытие работает (Plotly с CDN при интернете).
- [ ] **Step 4: Commit** `feat: coverage section, about dialog, accessibility pass, final build`.

```bash
git add -A
git commit -m "feat: complete dashboard redesign per spec"
```

---

## Notes для исполнителя

- `data/dashboard.html` регенерируется — большие диффы в git ожидаемы; коммитить только в Task 10 (иначе шум в истории).
- Никаких новых Python-зависимостей. Node 22 нужен только для тестов (уже в системе).
- Если Plotly annotation поверх COVID-rect мешает чтению — снизить opacity annotation, не rect.
- Числа форматируются по-русски: запятая как десятичный разделитель (`toLocaleString('ru-RU')`), `п.п.` для разниц долей.
