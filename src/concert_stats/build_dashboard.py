"""Render dashboard.html from dataset.json."""

import json
from importlib import resources
from pathlib import Path


def render(dataset: dict) -> str:
    """Return dashboard HTML with the dataset embedded."""
    template = (
        resources.files("concert_stats")
        .joinpath("dashboard_template.html")
        .read_text(encoding="utf-8")
    )
    payload = json.dumps(dataset, ensure_ascii=False)
    return template.replace("__DATA__", payload, 1)


def main() -> None:
    dataset = json.loads((Path("data") / "dataset.json").read_text(encoding="utf-8"))
    Path("dashboard.html").write_text(render(dataset), encoding="utf-8")
    print("dashboard.html written")


if __name__ == "__main__":
    main()
