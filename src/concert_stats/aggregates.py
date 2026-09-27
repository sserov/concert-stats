"""Precompute AGGREGATES for the dashboard: season totals, composer stats, jubilees."""

from concert_stats.composers import by_cid

_JUBILEE_K = (50, 100, 125, 150, 175, 200, 250)


def _empty_hall() -> dict:
    return {"total": 0, "with_text": 0, "with_composers": 0}


def _season_of_year(year: int) -> str:
    return f"{year}/{(year + 1) % 100:02d}"


def compute_aggregates(ds: dict) -> dict:
    """Aggregate dataset concerts into dashboard-ready structures.

    season_totals carries per-hall total/with_text/with_composers so share
    denominators respect the hall filter without touching raw events.
    """
    seasons = sorted({c["season"] for c in ds["concerts"]})
    season_set = set(seasons)

    season_totals: dict[str, dict] = {
        s: {
            "total": 0,
            "with_text": 0,
            "with_composers": 0,
            "meloman": _empty_hall(),
            "mosconsv": _empty_hall(),
        }
        for s in seasons
    }
    composer_totals: dict[str, dict] = {}
    composer_by_season: dict[str, dict[str, int]] = {}
    composer_by_season_by_hall: dict[str, dict[str, dict[str, int]]] = {}

    for c in ds["concerts"]:
        src = c["source"]
        hall = season_totals[c["season"]]["meloman" if src == "meloman" else "mosconsv"]
        st = season_totals[c["season"]]
        has_text = bool(c["program_text"].strip() or c["structured_composers"])
        has_comp = bool(c["composers"])

        st["total"] += 1
        hall["total"] += 1
        if has_text:
            st["with_text"] += 1
            hall["with_text"] += 1
        if has_comp:
            st["with_composers"] += 1
            hall["with_composers"] += 1

        for cid in c["composers"]:
            ct = composer_totals.setdefault(cid, {"total": 0, "meloman": 0, "mosconsv": 0})
            ct["total"] += 1
            ct[src] += 1
            per_season = composer_by_season.setdefault(cid, {})
            per_season[c["season"]] = per_season.get(c["season"], 0) + 1
            by_hall = composer_by_season_by_hall.setdefault(cid, {}).setdefault(
                c["season"], {"meloman": 0, "mosconsv": 0}
            )
            by_hall[src] += 1

    coverage_by_season = [
        {
            "season": s,
            "meloman": season_totals[s]["meloman"]["total"],
            "mosconsv": season_totals[s]["mosconsv"]["total"],
        }
        for s in seasons
    ]

    jubilees = []
    for cid, comp in by_cid().items():
        for kind, year_birth in (("рождения", comp.born), ("смерти", comp.died)):
            if year_birth is None:
                continue
            for k in _JUBILEE_K:
                year = year_birth + k
                season = _season_of_year(year)
                if season in season_set:
                    jubilees.append(
                        {
                            "cid": cid,
                            "season": season,
                            "year": year,
                            "label": f"{k} лет со дня {kind}",
                        }
                    )
    jubilees.sort(key=lambda j: (j["season"], j["cid"]))

    return {
        "seasons": seasons,
        "current_season": seasons[-1] if seasons else None,
        "season_totals": season_totals,
        "composer_totals": composer_totals,
        "composer_by_season": composer_by_season,
        "composer_by_season_by_hall": composer_by_season_by_hall,
        "coverage_by_season": coverage_by_season,
        "jubilees": jubilees,
    }
