from concert_stats.discover_meloman import extract_event_links, parse_cdx

CDX = """20200713020341 https://meloman.ru/concert/1585-let-rodion-shedrin-158551019346/ 200
20210309204616 http://meloman.ru/concert/ 301
20220101120000 https://meloman.ru/concert/vsh-2022-01-12/ 200
20240505000000 https://meloman.ru/news/article/ 200
"""


def test_parse_cdx_filters_status_and_pattern():
    out = parse_cdx(CDX)
    urls = [orig for _, orig in out]
    assert urls == [
        "https://meloman.ru/concert/1585-let-rodion-shedrin-158551019346/",
        "https://meloman.ru/concert/vsh-2022-01-12/",
    ]


def test_parse_cdx_empty_input():
    assert parse_cdx("") == []


def test_extract_event_links_from_listing():
    html = """
    <html><body>
    <a href="/concert/kzch-2026-09-27/">Концерт</a>
    <a href="https://meloman.ru/concert/mzf-2020-11-05/">Другой</a>
    <a href="/subscription/">Абонемент</a>
    </body></html>
    """
    links = extract_event_links(html)
    assert links == {
        "https://meloman.ru/concert/kzch-2026-09-27/",
        "https://meloman.ru/concert/mzf-2020-11-05/",
    }


def test_url_in_range_filters_by_slug_year():
    from concert_stats.discover_meloman import url_in_range

    assert url_in_range("https://meloman.ru/concert/kzch-2026-09-27/", 2016, 2026)
    assert not url_in_range("https://meloman.ru/concert/kzch-2026-09-27/", 2016, 2023)
    # no slug date -> keep, date resolved later from page content
    assert url_in_range(
        "https://meloman.ru/concert/1585-let-rodion-shedrin-158551019346/", 2016, 2026
    )
