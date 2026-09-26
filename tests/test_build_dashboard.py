import json

from concert_stats.build_dashboard import render


def test_render_embeds_dataset():
    ds = {
        "concerts": [
            {
                "id": "x:1",
                "source": "meloman",
                "date": "2025-05-01",
                "date_approximate": False,
                "hall": "КЗЧ",
                "title": "T",
                "program_text": "Бетховен",
                "structured_composers": [],
                "parse_failed": False,
                "composers": ["beethoven"],
                "season": "2024/25",
            }
        ],
        "composers": {"beethoven": {"name": "Людвиг ван Бетховен", "born": 1770, "died": 1827}},
        "coverage": {"by_year": [{"year": 2025, "meloman": 1, "mosconsv": 0}]},
        "quality": {"total": 1, "without_composers_pct": 0.0},
        "unknown_top": [],
    }
    html = render(ds)
    assert "window.DATASET" in html
    payload = html.split("window.DATASET = ", 1)[1].split(";</script>", 1)[0]
    assert json.loads(payload)["quality"]["total"] == 1
    assert "plotly" in html.lower()
    assert "Бетховен" in html or "beethoven" in html
