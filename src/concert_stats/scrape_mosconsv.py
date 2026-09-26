"""Scrape mosconsv.ru concert history via the forday API and concert pages."""

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from concert_stats.fetcher import USER_AGENT, fetch

BASE = "https://www.mosconsv.ru"
DATA_DIR = Path("data")


def _extract_hall(soup, h1) -> str:
    # Hall is the div directly preceding the h1 in the page header
    if h1 is not None:
        sib = h1.find_previous_sibling("div")
        if sib:
            return sib.get_text(" ", strip=True)
    hall_tag = soup.find(class_=re.compile("hall|place", re.I))
    return hall_tag.get_text(" ", strip=True) if hall_tag else ""


def parse_mosconsv_concert(html: str, date: str, event_id: int) -> dict:
    """Extract one concert record from a /ru/concert/<id> page."""
    soup = BeautifulSoup(html, "lxml")
    h1 = soup.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else ""

    program_text = ""
    structured: list[str] = []
    parse_failed = True
    for heading in soup.find_all(["h2", "h3"]):
        if heading.get_text(strip=True).lower() != "программа":
            continue
        # Real pages: the heading sits inside a section holding div.prose.
        # Degraded pages: fall back to the next div sibling of the heading.
        parent = heading.parent
        block = parent.find("div", class_="prose") if parent is not None else None
        if block is None:
            block = heading.find_next_sibling("div")
        if block is None:
            block = parent
        if block is None:
            continue
        program_text = block.get_text("\n", strip=True)
        structured = [s.get_text(" ", strip=True) for s in block.find_all("strong")]
        parse_failed = False
        break

    return {
        "id": f"mosconsv:{event_id}",
        "source": "mosconsv",
        "date": date,
        "date_approximate": False,
        "hall": _extract_hall(soup, h1),
        "title": title,
        "program_text": program_text,
        "structured_composers": structured,
        "parse_failed": parse_failed,
    }


def scrape(start: dt.date, end: dt.date, out_path: Path, cache_dir: Path) -> None:
    client = httpx.Client(timeout=30.0, follow_redirects=True, headers={"User-Agent": USER_AGENT})
    stats = {"days": 0, "events": 0, "failed": 0, "no_program": 0}
    day = start
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("a", encoding="utf-8") as out:
            while day <= end:
                stats["days"] += 1
                url = f"{BASE}/api/concert/forday?date={day.isoformat()}"
                body = fetch(url, cache_dir, client=client)
                if body is None:
                    stats["failed"] += 1
                else:
                    _scrape_day(body, day, cache_dir, client, out, stats)
                day += dt.timedelta(days=1)
                if stats["days"] % 200 == 0:
                    print(f"...{day} {stats}", file=sys.stderr)
    finally:
        client.close()
    print(f"done: {stats}")


def _scrape_day(body: str, day: dt.date, cache_dir, client, out, stats) -> None:
    try:
        events = json.loads(body)
    except json.JSONDecodeError:
        stats["failed"] += 1
        return
    for ev in events:
        page = fetch(f"{BASE}{ev['concertUrl']}", cache_dir, client=client)
        if page is None:
            stats["failed"] += 1
            continue
        rec = parse_mosconsv_concert(page, day.isoformat(), int(ev["id"]))
        rec["hall"] = rec["hall"] or ev.get("hall", "")
        rec["title"] = rec["title"] or ev.get("title", "")
        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
        stats["events"] += 1
        if rec["parse_failed"]:
            stats["no_program"] += 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()
    out = DATA_DIR / "mosconsv" / "events.jsonl"
    scrape(
        dt.date.fromisoformat(args.start),
        dt.date.fromisoformat(args.end),
        out,
        DATA_DIR / "raw" / "mosconsv",
    )


if __name__ == "__main__":
    main()
