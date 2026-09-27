import json
from importlib import resources

from concert_stats.build_dashboard import render, slim_concerts


def _ds():
    return {
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


def test_render_embeds_dataset():
    html = render("<script>window.DATASET = __DATA__;</script>", _ds(), {}, "")
    assert "window.DATASET" in html
    payload = html.split("window.DATASET = ", 1)[1].split(";</script>", 1)[0]
    assert json.loads(payload.replace("<\\/", "</"))["quality"]["total"] == 1


def test_render_escapes_script_closing_tag():
    ds = {
        "concerts": [
            {
                "id": "x:1",
                "source": "meloman",
                "date": "2020-01-01",
                "season": "2019/20",
                "hall": "h",
                "title": "a</script><b>",
                "program_text": "",
                "structured_composers": [],
                "composers": [],
                "parse_failed": False,
                "date_approximate": False,
            }
        ],
        "composers": {},
        "coverage": {"by_year": []},
        "quality": {"total": 1, "without_composers_pct": 100.0},
        "unknown_top": [],
    }
    out = render("<script>window.DATASET = __DATA__;</script>", ds, {}, "")
    assert "</script><b>" not in out
    assert "<\\/script>" in out
    # и JSON после unescape валиден:
    raw = out.split("window.DATASET = ")[1].split(";</script>")[0].replace("<\\/", "</")
    assert json.loads(raw)["concerts"][0]["title"] == "a</script><b>"


def test_slim_concerts_drops_program_text():
    slim = slim_concerts(_ds())
    assert slim and set(slim[0]) == {"id", "source", "date", "season", "hall", "title", "composers"}


def test_render_inlines_app_js():
    out = render("__APP__", _ds(), {}, "console.log('app');")
    assert "console.log('app');" in out and "__APP__" not in out


def test_render_inlines_aggregates():
    agg = {"seasons": ["2024/25"], "current_season": "2024/25"}
    out = render("window.AGGREGATES = __AGGREGATES__;", _ds(), agg, "")
    assert '"current_season"' in out and "__AGGREGATES__" not in out


def test_template_has_redesign_shell():
    html = (resources.files("concert_stats") / "dashboard_template.html").read_text("utf-8")
    for needle in (
        "Музыкальный репертуар Москвы",
        "сезоны 2016/17—2026/27",
        'id="hall-seg"',
        'id="season-from"',
        'id="season-to"',
        'id="composer-search"',
        'id="chips"',
        'id="trend-plot"',
        'id="ranking-table"',
        'id="heatmap-plot-wrap"',
        'id="hall-plot"',
        'id="coverage-plot"',
        'id="drawer"',
        'id="about"',
        "#8C2635",
        "#536B63",
        "#A77A2B",
        "#F7F5F0",
        "Для сравнения сезонов основной показатель — доля концертов",
        "Wayback Machine",
    ):
        assert needle in html, needle
