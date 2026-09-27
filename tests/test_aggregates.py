"""Tests for AGGREGATES precomputation."""

from concert_stats.aggregates import compute_aggregates


def _ds():
    return {
        "concerts": [
            {
                "source": "meloman",
                "date": "2016-10-01",
                "season": "2016/17",
                "hall": "h1",
                "title": "A",
                "program_text": "Бах",
                "structured_composers": [],
                "composers": ["bach"],
            },
            {
                "source": "mosconsv",
                "date": "2017-03-01",
                "season": "2016/17",
                "hall": "h2",
                "title": "B",
                "program_text": "",
                "structured_composers": [],
                "composers": [],
            },
            {
                "source": "meloman",
                "date": "2016-11-01",
                "season": "2016/17",
                "hall": "h1",
                "title": "C",
                "program_text": "Бах, Моцарт",
                "structured_composers": [],
                "composers": ["bach", "mozart"],
            },
            {
                "source": "meloman",
                "date": "2026-10-01",
                "season": "2026/27",
                "hall": "h1",
                "title": "D",
                "program_text": "",
                "structured_composers": ["Шостакович"],
                "composers": ["shostakovich"],
            },
            {
                "source": "mosconsv",
                "date": "2025-10-01",
                "season": "2025/26",
                "hall": "h2",
                "title": "E",
                "program_text": "",
                "structured_composers": [],
                "composers": [],
            },
        ],
        "composers": {
            "bach": {"name": "Иоганн Себастьян Бах", "born": 1685, "died": 1750},
            "mozart": {"name": "Вольфганг Амадей Моцарт", "born": 1756, "died": 1791},
            "shostakovich": {"name": "Дмитрий Шостакович", "born": 1906, "died": 1975},
        },
        "coverage": {"by_year": []},
        "quality": {"total": 4, "without_composers_pct": 50.0},
    }


def test_season_totals_per_hall():
    agg = compute_aggregates(_ds())
    st = agg["season_totals"]["2016/17"]
    assert st["total"] == 3
    assert st["with_text"] == 2
    assert st["with_composers"] == 2
    assert st["meloman"]["total"] == 2
    assert st["mosconsv"]["with_text"] == 0


def test_composer_aggregates():
    agg = compute_aggregates(_ds())
    assert agg["composer_totals"]["bach"] == {"total": 2, "meloman": 2, "mosconsv": 0}
    assert agg["composer_by_season"]["bach"] == {"2016/17": 2}
    assert agg["composer_by_season_by_hall"]["bach"]["2016/17"] == {"meloman": 2, "mosconsv": 0}
    assert agg["composer_by_season"].get("mozart") == {"2016/17": 1}


def test_jubilees_mapped_to_season():
    agg = compute_aggregates(_ds())
    labels = [j["label"] for j in agg["jubilees"] if j["cid"] == "shostakovich"]
    assert "50 лет со дня смерти" in labels  # 1975 + 50 = 2025 → 2025/26
    jub = [j for j in agg["jubilees"] if j["cid"] == "shostakovich" and j["year"] == 2025]
    assert jub and jub[0]["season"] == "2025/26"
    # юбилей вне диапазона сезонов не попадает
    assert all(j["season"] in agg["seasons"] for j in agg["jubilees"])


def test_current_season_is_last():
    agg = compute_aggregates(_ds())
    assert agg["current_season"] == agg["seasons"][-1] == "2026/27"


def test_identified_coverage_semantics():
    # identified coverage = with_composers / with_text, не / total
    agg = compute_aggregates(_ds())
    st = agg["season_totals"]["2016/17"]
    assert st["with_text"] == 2 and st["with_composers"] == 2
