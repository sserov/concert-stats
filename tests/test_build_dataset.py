from concert_stats.build_dataset import build, season


def test_season_september_starts_new():
    assert season("2025-09-01") == "2025/26"


def test_season_june_belongs_to_current():
    assert season("2025-06-30") == "2024/25"


def test_season_july_belongs_to_previous():
    assert season("2025-07-31") == "2024/25"
    assert season("2025-08-01") == "2024/25"


def _rec(**kw):
    base = {
        "id": "x:1",
        "source": "meloman",
        "date": "2025-05-01",
        "date_approximate": False,
        "hall": "КЗЧ",
        "title": "Концерт",
        "program_text": "Бетховен. Симфония №5",
        "structured_composers": [],
        "parse_failed": False,
    }
    base.update(kw)
    return base


def test_dedupe_same_concert_different_ids():
    concerts = [
        _rec(id="meloman:aaa", title="Большой концерт"),
        _rec(id="meloman:bbb", title="  Большой концерт  "),
    ]
    ds = build(concerts)
    assert len(ds["concerts"]) == 1


def test_composers_attached():
    ds = build([_rec()])
    assert ds["concerts"][0]["composers"] == ["beethoven"]
    assert ds["concerts"][0]["season"] == "2024/25"


def test_structured_composers_matched():
    ds = build([_rec(structured_composers=["В. А. Моцарт"], program_text="")])
    assert ds["concerts"][0]["composers"] == ["mozart"]


def test_coverage_counts_by_year_and_source():
    ds = build(
        [
            _rec(date="2020-05-01"),
            _rec(id="x:2", source="mosconsv", date="2020-06-01"),
            _rec(id="x:3", source="mosconsv", date="2021-06-01"),
        ]
    )
    by_year = {r["year"]: r for r in ds["coverage"]["by_year"]}
    assert by_year[2020] == {"year": 2020, "meloman": 1, "mosconsv": 1}
    assert by_year[2021]["mosconsv"] == 1


def test_quality_reported():
    ds = build(
        [
            _rec(title="Вечер первый", program_text="Совершенно неизвестный автор. Сюита"),
            _rec(id="x:2", title="Вечер второй", program_text="Малер. Симфония №1"),
        ]
    )
    assert ds["quality"]["total"] == 2
    assert ds["quality"]["without_composers_pct"] == 50.0
