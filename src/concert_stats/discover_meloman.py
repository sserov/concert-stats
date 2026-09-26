"""Discover meloman.ru concert URLs via Wayback CDX and archived listing pages."""

import argparse
import json
import re
import sys
from pathlib import Path

from concert_stats.fetcher import fetch

CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
DATA_DIR = Path("data")

_EVENT_URL_RE = re.compile(r"meloman\.ru/(?:concert|afisha)/[a-z0-9-]+/?", re.I)
_HREF_RE = re.compile(r'href="([^"]+)"')
_SLUG_YEAR_RE = re.compile(r"-(\d{4})-\d{2}-\d{2}/?$")


def url_in_range(url: str, year_from: int, year_to: int) -> bool:
    """Slug-dated URLs must fall in the range; undated URLs are kept."""
    m = _SLUG_YEAR_RE.search(url)
    return m is None or year_from <= int(m.group(1)) <= year_to


def _is_event_url(url: str) -> bool:
    return bool(_EVENT_URL_RE.search(url) and not url.rstrip("/").endswith(("/concert", "/afisha")))


def parse_cdx(text: str) -> list[tuple[str, str]]:
    """[(timestamp, original)] for status-200 rows matching the event URL pattern."""
    rows: list[tuple[str, str]] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3 or parts[2] != "200":
            continue
        ts, original = parts[0], parts[1]
        if original.startswith("http://"):
            original = "https://" + original[len("http://") :]
        if _is_event_url(original):
            rows.append((ts, original))
    return rows


def extract_event_links(html: str) -> set[str]:
    """Absolute event URLs found in an archived afisha listing page."""
    links: set[str] = set()
    for href in _HREF_RE.findall(html):
        if href.startswith("/"):
            href = "https://meloman.ru" + href
        if _is_event_url(href):
            links.add(href.split("?")[0].rstrip("/") + "/")
    return links


def wayback_url(timestamp: str, original: str) -> str:
    return f"https://web.archive.org/web/{timestamp}id_/{original}"


def _cdx_query(params: str) -> str:
    return f"{CDX_ENDPOINT}?{params}&output=text&fl=timestamp,original,statuscode"


def discover(year_from: int, year_to: int, out_path: Path, cache_dir: Path) -> None:
    found: dict[str, str | None] = {}  # url -> snapshot ts (None = try live)
    for listing in ("concert/", "afisha/"):
        cdx = fetch(
            _cdx_query(
                f"url=meloman.ru/{listing}&from={year_from}&to={year_to}&collapse=timestamp:6"
            ),
            cache_dir,
        )
        if cdx is None:
            print(f"CDX failed for {listing}", file=sys.stderr)
            continue
        for ts, original in parse_cdx(cdx):
            page = fetch(wayback_url(ts, original), cache_dir)
            if page:
                for link in extract_event_links(page):
                    if url_in_range(link, year_from, year_to):
                        found.setdefault(link, None)

    cdx = fetch(
        _cdx_query(f"url=meloman.ru/concert/*&from={year_from}&to={year_to}&collapse=urlkey"),
        cache_dir,
    )
    if cdx:
        for ts, original in parse_cdx(cdx):
            if url_in_range(original, year_from, year_to):
                found.setdefault(original, ts)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as out:
        for url, ts in sorted(found.items()):
            out.write(json.dumps({"url": url, "snapshot_ts": ts}) + "\n")
    print(f"discovered {len(found)} urls -> {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="year_from", type=int, required=True)
    parser.add_argument("--to", dest="year_to", type=int, required=True)
    args = parser.parse_args()
    discover(
        args.year_from,
        args.year_to,
        DATA_DIR / "meloman" / "urls.jsonl",
        DATA_DIR / "raw" / "meloman_cdx",
    )


if __name__ == "__main__":
    main()
