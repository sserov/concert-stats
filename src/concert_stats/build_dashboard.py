"""Render dashboard.html from dataset.json and precomputed aggregates."""

import json
from importlib import resources
from pathlib import Path

from concert_stats.aggregates import compute_aggregates


def _embed(value) -> str:
    """Serialize to JSON, escaping `</` so `</script>` cannot break the page."""
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def slim_concerts(ds: dict) -> list[dict]:
    """Keep only the fields the dashboard needs for drill-down."""
    keep = ("id", "source", "date", "season", "hall", "title", "composers")
    return [{k: c[k] for k in keep} for c in ds["concerts"]]


def render(template_html: str, dataset: dict, aggregates: dict, app_js: str) -> str:
    """Inline dataset, aggregates and app JS into the template."""
    html = template_html.replace("__APP__", app_js)
    html = html.replace("__AGGREGATES__", _embed(aggregates))
    return html.replace("__DATA__", _embed({**dataset, "concerts": slim_concerts(dataset)}))


def main() -> None:
    ds = json.loads((Path("data") / "dataset.json").read_text(encoding="utf-8"))
    agg = compute_aggregates(ds)
    pkg = resources.files("concert_stats")
    template = pkg.joinpath("dashboard_template.html").read_text(encoding="utf-8")
    app_js = pkg.joinpath("dashboard_app.js").read_text(encoding="utf-8")
    out = Path("dashboard.html")
    out.write_text(render(template, ds, agg, app_js), encoding="utf-8")
    print(f"dashboard.html written ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
