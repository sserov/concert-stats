from pathlib import Path

from concert_stats.scrape_mosconsv import parse_mosconsv_concert

FIXTURE = Path(__file__).parent / "fixtures" / "mosconsv_concert.html"


def test_parse_real_page():
    html = FIXTURE.read_text(encoding="utf-8")
    rec = parse_mosconsv_concert(html, date="2022-03-15", event_id=175432)
    assert rec["id"] == "mosconsv:175432"
    assert rec["source"] == "mosconsv"
    assert rec["date"] == "2022-03-15"
    assert "Большой зал" in rec["hall"]
    assert "Симфония № 40" in rec["program_text"]
    assert "Моцарт" in " ".join(rec["structured_composers"])
    assert rec["parse_failed"] is False


def test_parse_page_without_program_block():
    rec = parse_mosconsv_concert("<html><body><h1>Кафедра</h1></body></html>", "2022-03-15", 1)
    assert rec["parse_failed"] is True
    assert rec["program_text"] == ""


def test_parse_garbage_page_with_invalid_bytes():
    html = (
        "<html><body><h2>Программа</h2>"
        "<div><p>\x98<strong>В. А. Моцарт</strong></p></div></body></html>"
    )
    rec = parse_mosconsv_concert(html, "2022-03-15", 2)
    assert rec["parse_failed"] is False
    assert "Моцарт" in " ".join(rec["structured_composers"])
