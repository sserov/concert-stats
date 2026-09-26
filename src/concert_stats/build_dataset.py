"""Merge scraped events into dataset.json with seasons, dedupe and coverage."""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from concert_stats.composers import by_cid, match_composers, unknown_surnames

DATA_DIR = Path("data")


def season(d: str) -> str:
    """Season label: Sep-Jun is 'YYYY/YY+1'; Jul-Aug belong to the previous season."""
    year, month = int(d[:4]), int(d[5:7])
    start = year if month >= 9 else year - 1
    return f"{start}/{(start + 1) % 100:02d}"


def _norm_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().lower())


def _dedupe_key(rec: dict) -> tuple:
    return (rec["source"], rec["date"], _norm_title(rec["title"]))


def build(concerts: list[dict]) -> dict:
    seen: set[tuple] = set()
    out: list[dict] = []
    unknown_counter: Counter[str] = Counter()
    for rec in concerts:
        key = _dedupe_key(rec)
        if key in seen:
            continue
        seen.add(key)
        if not rec["date"]:
            continue
        text = " ".join([rec["title"], rec["program_text"], *rec["structured_composers"]])
        cids = match_composers(text)
        enriched = {**rec, "composers": sorted(cids), "season": season(rec["date"])}
        out.append(enriched)
        unknown_counter.update(unknown_surnames(rec["program_text"]))

    by_year: dict[int, dict] = defaultdict(lambda: {"meloman": 0, "mosconsv": 0})
    for rec in out:
        by_year[int(rec["date"][:4])][rec["source"]] += 1
    coverage_rows = [
        {"year": y, "meloman": v["meloman"], "mosconsv": v["mosconsv"]}
        for y, v in sorted(by_year.items())
    ]

    without = sum(1 for r in out if not r["composers"])
    total = len(out)
    info = by_cid()
    return {
        "concerts": out,
        "composers": {
            cid: {"name": c.name, "born": c.born, "died": c.died} for cid, c in info.items()
        },
        "coverage": {"by_year": coverage_rows},
        "quality": {
            "total": total,
            "without_composers_pct": round(100.0 * without / total, 1) if total else 0.0,
        },
        "unknown_top": unknown_counter.most_common(50),
    }


def main() -> None:
    concerts: list[dict] = []
    for source in ("meloman", "mosconsv"):
        path = DATA_DIR / source / "events.jsonl"
        if not path.exists():
            print(f"skip {path} (missing)", flush=True)
            continue
        with path.open(encoding="utf-8") as fh:
            concerts.extend(json.loads(line) for line in fh)
    ds = build(concerts)
    out = DATA_DIR / "dataset.json"
    out.write_text(json.dumps(ds, ensure_ascii=False), encoding="utf-8")
    review = DATA_DIR / "review_unknown.txt"
    review.write_text(
        "\n".join(f"{n}\t{surname}" for surname, n in ds["unknown_top"]), encoding="utf-8"
    )
    print(f"dataset: {ds['quality']} -> {out}")


if __name__ == "__main__":
    main()
