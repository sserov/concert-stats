# Dashboard redesign

This project is a cultural data-journalism project, not a generic BI dashboard.

Primary goal:
Help users explore how the repertoire of the Moscow Philharmonic
and Moscow Conservatory changed across seasons.

Design direction:
Editorial / cultural data visualization / restrained / sophisticated.

Avoid:
- generic SaaS dashboard aesthetics
- excessive cards
- excessive rounded corners
- default Plotly styling
- rainbow palettes
- giant KPI cards
- dense unreadable heatmaps
- generic Inter/Roboto dashboard typography

Important:
- share (%) is the default historical metric
- absolute counts are secondary
- 2026/27 is an incomplete current season
- Philharmonic coverage before 2019 is partial
- COVID period must be visibly contextualized

Do not change the data pipeline unless necessary.
Do not replace the project architecture with React unless explicitly required.

## Redesign workflow (binding order)

1. **Design audit** before code: analyze current dashboard, dataset, screenshots;
   produce UX/UI proposal. No code changes in this stage.
2. **Implementation** per `docs/superpowers/plans/2026-09-27-dashboard-redesign.md`.
3. **Visual QA**: open dashboard in browser at 1440×900 (desktop only; mobile
   version out of scope, decision 2026-09-27), screenshot, inspect
   hierarchy/readability/spacing/chart density/interactions, fix, repeat until
   the layout is coherent. A task is NOT done until the screenshot matches the
   spec (`docs/superpowers/specs/2026-09-27-dashboard-redesign-design.md`).
4. **Data QA**: pytest, ruff, rebuild; verify new aggregates reproduce the same
   base numbers as the raw dataset.

Progress tracked in `docs/superpowers/dashboard-redesign-progress.md`.
