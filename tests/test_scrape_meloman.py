from pathlib import Path

from concert_stats.scrape_meloman import parse_meloman_concert

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_current_page_slug_date():
    html = (FIXTURES / "meloman_current.html").read_text(encoding="utf-8", errors="replace")
    rec = parse_meloman_concert(html, "https://meloman.ru/concert/kzch-2026-09-27/", None)
    assert rec["source"] == "meloman"
    assert rec["date"] == "2026-09-27"
    assert rec["date_approximate"] is False
    assert rec["parse_failed"] is False
    assert any("Рахманинов" in c for c in rec["structured_composers"])
    assert "Концерт № 3" in rec["program_text"]


def test_parse_2020_page_inline_date():
    html = (FIXTURES / "meloman_2020.html").read_text(encoding="utf-8", errors="replace")
    rec = parse_meloman_concert(
        html, "https://meloman.ru/concert/1585-let-rodion-shedrin-158551019346/", None
    )
    assert rec["date"] == "2020-04-11"
    assert rec["date_approximate"] is False
    assert any("Щедрин" in c for c in rec["structured_composers"])


def test_inline_date_beats_snapshot_ts():
    html = (FIXTURES / "meloman_2020.html").read_text(encoding="utf-8", errors="replace")
    rec = parse_meloman_concert(
        html, "https://meloman.ru/concert/1585-let-rodion-shedrin-158551019346/", "20200609161921"
    )
    assert rec["date"] == "2020-04-11"
    assert rec["date_approximate"] is False


def test_parse_fallback_snapshot_date():
    rec = parse_meloman_concert(
        "<html><body><h1>X</h1></body></html>",
        "https://meloman.ru/concert/1585-let-rodion-shedrin-158551019346/",
        "20200609161921",
    )
    assert rec["date"] == "2020-06-09"
    assert rec["date_approximate"] is True


def test_parse_no_date_at_all():
    rec = parse_meloman_concert(
        "<html><body><h1>X</h1></body></html>", "https://meloman.ru/concert/a/", None
    )
    assert rec["date"] == ""
    assert rec["date_approximate"] is True


def test_parse_page_without_program():
    rec = parse_meloman_concert(
        "<html><body><h1>X</h1></body></html>", "https://meloman.ru/concert/a-2020-01-01/", None
    )
    assert rec["parse_failed"] is True
    assert rec["structured_composers"] == []


def test_parse_invalid_bytes():
    html = (
        '<html><body><div class="editor editor--preview">'
        '<p>\x98<b class="uppercase">Щедрин </b> Концерт</p></div></body></html>'
    )
    rec = parse_meloman_concert(html, "https://meloman.ru/concert/x-2020-01-01/", None)
    assert rec["parse_failed"] is False
    assert rec["structured_composers"] == ["Щедрин"]
