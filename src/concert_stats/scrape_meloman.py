"""Scrape meloman.ru concerts: live pages first, Wayback snapshots as fallback."""

import hashlib
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup
from bs4.element import Comment

DATA_DIR = Path("data")

_SLUG_DATE_RE = re.compile(r"-(\d{4})-(\d{2})-(\d{2})/?$")
_RU_DATE_RE = re.compile(r"\b(\d{2})\.(\d{2})\.(\d{4})\b")

_HALLS = (
    "Концертный зал имени П. И. Чайковского",
    "Большой зал консерватории",
    "Рахманиновский зал",
    "Камерный зал филармонии",
    "Малый зал консерватории",
    "Малый зал филармонии",
    "Большой зал филармонии",
    "Концертный зал «Филармония-2»",
    "Филармония-2",
    "КЗЧ",
)


def _has_marker(block) -> bool:
    return any(isinstance(s, Comment) and "композиторы" in s for s in block.descendants)


def _extract_program(soup: BeautifulSoup) -> tuple[str, list[str], bool]:
    """(program_text, structured_composers, parse_failed) from the composer block."""
    blocks = soup.find_all("div", class_="editor--preview")
    for block in blocks:
        composer_blocks = block.find_all("b", class_="uppercase")
        if composer_blocks:
            text_all = block.get_text("\n", strip=True)
            structured = [b.get_text(" ", strip=True) for b in composer_blocks]
            return text_all, structured, False
    for block in blocks:
        if _has_marker(block):
            return block.get_text("\n", strip=True), [], False
    return "", [], True


def parse_meloman_concert(html: str, url: str, snapshot_ts: str | None) -> dict:
    """Extract one concert record from a meloman event page."""
    soup = BeautifulSoup(html, "lxml")
    h1 = soup.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else ""

    program_text, structured, parse_failed = _extract_program(soup)
    date, approximate = _extract_date(html, url, snapshot_ts)
    hall = next((h for h in _HALLS if h in html), "")

    return {
        "id": f"meloman:{hashlib.sha1(url.encode()).hexdigest()[:12]}",
        "source": "meloman",
        "date": date,
        "date_approximate": approximate,
        "hall": hall,
        "title": title,
        "program_text": program_text,
        "structured_composers": structured,
        "parse_failed": parse_failed,
    }


def _extract_date(html: str, url: str, snapshot_ts: str | None) -> tuple[str, bool]:
    m = _SLUG_DATE_RE.search(url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}", False
    m = _RU_DATE_RE.search(html)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}", False
    if snapshot_ts:
        return f"{snapshot_ts[:4]}-{snapshot_ts[4:6]}-{snapshot_ts[6:8]}", True
    return "", True


def scrape(urls_path: Path, out_path: Path, cache_dir: Path) -> None:
    from concert_stats.discover_meloman import wayback_url
    from concert_stats.fetcher import fetch

    stats = {"ok": 0, "failed": 0, "approx": 0, "no_program": 0}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as out, urls_path.open(encoding="utf-8") as urls:
        for line in urls:
            target = json.loads(line)
            page = fetch(target["url"], cache_dir)
            if page is None and target["snapshot_ts"]:
                page = fetch(wayback_url(target["snapshot_ts"], target["url"]), cache_dir)
            if page is None:
                stats["failed"] += 1
                continue
            rec = parse_meloman_concert(page, target["url"], target["snapshot_ts"])
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            stats["ok"] += 1
            stats["approx"] += rec["date_approximate"]
            stats["no_program"] += rec["parse_failed"]
            if stats["ok"] % 200 == 0:
                print(f"...{stats}", file=sys.stderr)
    print(f"done: {stats}")


def main() -> None:
    scrape(
        DATA_DIR / "meloman" / "urls.jsonl",
        DATA_DIR / "meloman" / "events.jsonl",
        DATA_DIR / "raw" / "meloman",
    )


if __name__ == "__main__":
    main()
