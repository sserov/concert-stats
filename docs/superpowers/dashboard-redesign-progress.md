# Dashboard Redesign — Progress

Spec: `docs/superpowers/specs/2026-09-27-dashboard-redesign-design.md`
Plan: `docs/superpowers/plans/2026-09-27-dashboard-redesign.md`

Definition of done per CLAUDE.md: task finished only when the 1440×900
screenshot matches the spec (desktop only; mobile out of scope, 2026-09-27)
AND pytest/ruff/build pass AND aggregates match raw dataset numbers.

## Stage 1 — Design audit

- [x] Analyze current dashboard.html (structure, interactions, visual problems)
- [x] Analyze dataset: seasons, halls, top composers, coverage gaps
- [x] Screenshot current state at 1440×900 (desktop only) —
      `docs/screens/before/desktop-1440.png`
      (NOTE: снят с однострочным патчем — в текущем dashboard.html баг:
       `#top.on('plotly_click')` до первого redraw() валит весь JS, графики
       не рисуются вообще; в redesign заменяется целиком)
- [x] Write UX/UI redesign proposal → `docs/superpowers/dashboard-redesign-audit.md`
- [ ] User approves proposal

## Stage 2 — Implementation (plan Tasks 1–10)

- [x] Task 1: Aggregates in Python (`aggregates.py`)
- [x] Task 2: Build pipeline — app.js inline, slim DATASET, script-safe JSON
- [x] Task 3: Pure selectors + node tests
- [x] Task 4: Template shell — design tokens, layout, header, controls, sections
- [x] Task 5: State, controls, KPI, autocomplete
- [x] Task 6: renderTrend — main chart
- [x] Task 7: renderRanking — table
- [x] Task 8: renderHeatmap
- [x] Task 9: Hall comparison + composer drawer
- [ ] Task 10: Coverage, About, a11y pass, final build

## Stage 3 — Visual QA loop

- [ ] 1440×900: hierarchy, readability, spacing, chart density, interactions OK
- [ ] Screenshots verified against spec §21 checklist

## Stage 4 — Data QA

- [ ] `uv run pytest -q` green (incl. node selector tests)
- [ ] `uv run ruff check` / `ruff format --check` clean
- [ ] `uv run python -m concert_stats.build_dashboard` succeeds
- [ ] Aggregates cross-check: season_totals totals == len(concerts in range);
      composer_totals top-5 == direct recount from raw concerts;
      coverage_by_season sums == per-source counts
