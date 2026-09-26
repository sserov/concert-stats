from concert_stats.composers import COMPOSERS, match_composers, unknown_surnames


def test_full_name_match():
    assert match_composers("Исполняется Пётр Ильич Чайковский, симфония №5") == {"tchaikovsky"}


def test_surname_only_match():
    assert "shostakovich" in match_composers("В программе: Шостакович, Симфония №7")


def test_initials_variant_match():
    assert "mozart" in match_composers("В. А. Моцарт. Симфония №40")


def test_no_false_substring_match():
    # «Рахманинов» не должен матчиться внутри другой фамилии/слова
    assert match_composers("Рахманиновский хор") == set()


def test_transliterated_variant():
    assert "shchedrin" in match_composers("Rodion Shchedrin, Concerto No.3")


def test_ambiguous_surname_maps_to_generic():
    assert match_composers("Штраус, вальс «Голубой Дунай»") == {"strauss"}
    assert match_composers("И. Штраус, Голубой Дунай") == {"strauss_johann"}
    assert match_composers("Р. Штраус, Альпийская симфония") == {"strauss_richard"}


def test_multiple_composers():
    found = match_composers("Бетховен — Симфония №9; Малер — Симфония №1")
    assert found == {"beethoven", "mahler"}


def test_unknown_surnames_finds_initials_pattern_not_in_dict():
    text = "О. Хрящевский. Сюита для оркестра\nВ. А. Моцарт. Симфония №40"
    assert unknown_surnames(text) == {"Хрящевский"}


def test_every_composer_has_lifespan_years():
    for c in COMPOSERS:
        assert c.born is None or 1000 <= c.born <= 2030, c
        assert c.died is None or 1000 <= c.died <= 2030, c


def test_cids_unique():
    cids = [c.cid for c in COMPOSERS]
    assert len(cids) == len(set(cids))
