"""Curated composer dictionary and matching heuristics."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Composer:
    cid: str
    name: str
    variants: tuple[str, ...]
    born: int | None
    died: int | None


def _c(cid, name, born, died, *variants):
    all_variants = (name, *variants)
    return Composer(cid=cid, name=name, variants=all_variants, born=born, died=died)


COMPOSERS: tuple[Composer, ...] = (
    _c("bach", "Иоганн Себастьян Бах", 1685, 1750, "Бах", "Johann Sebastian Bach"),
    _c("handel", "Георг Фридрих Гендель", 1685, 1759, "Гендель", "Handel"),
    _c("vivaldi", "Антонио Вивальди", 1678, 1741, "Вивальди", "Vivaldi"),
    _c("haydn", "Йозеф Гайдн", 1732, 1809, "Гайдн", "Haydn"),
    _c("mozart", "Вольфганг Амадей Моцарт", 1756, 1791, "Моцарт", "Mozart"),
    _c("beethoven", "Людвиг ван Бетховен", 1770, 1827, "Бетховен", "Beethoven"),
    _c("schubert", "Франц Шуберт", 1797, 1828, "Шуберт", "Schubert"),
    _c("mendelssohn", "Феликс Мендельсон", 1809, 1847, "Мендельсон", "Mendelssohn"),
    _c("schumann", "Роберт Шуман", 1810, 1856, "Шуман", "Schumann"),
    _c("schumann_clara", "Клара Шуман", 1819, 1896, "К. Шуман", "Клара Шуман"),
    _c("chopin", "Фредерик Шопен", 1810, 1849, "Шопен", "Chopin"),
    _c("liszt", "Ференц Лист", 1811, 1886, "Лист", "Liszt"),
    _c("wagner", "Рихард Вагнер", 1813, 1883, "Вагнер", "Wagner"),
    _c("verdi", "Джузеппе Верди", 1813, 1901, "Верди", "Verdi"),
    _c("brahms", "Иоганнес Брамс", 1833, 1897, "Брамс", "Brahms"),
    _c("bruckner", "Антон Брукнер", 1824, 1896, "Брукнер", "Bruckner"),
    _c("tchaikovsky", "Пётр Ильич Чайковский", 1840, 1893, "Чайковский", "Tchaikovsky"),
    _c("dvorak", "Антонин Дворжак", 1841, 1904, "Дворжак", "Дворжák", "Dvorak"),
    _c("grieg", "Эдвард Григ", 1843, 1907, "Григ", "Grieg"),
    _c("rimsky", "Николай Римский-Корсаков", 1844, 1908, "Римский-Корсаков", "Римский Корсаков"),
    _c("bizet", "Жорж Бизе", 1838, 1875, "Бизе", "Bizet"),
    _c("saint_saens", "Камиль Сен-Санс", 1835, 1921, "Сен-Санс", "Saint-Saens"),
    _c("faure", "Габриэль Форе", 1845, 1924, "Форе", "Fauré", "Faure"),
    _c("franck", "Сезар Франк", 1822, 1890, "Франк", "Franck"),
    _c("massenet", "Жюль Массне", 1842, 1912, "Массне", "Massenet"),
    _c("offenbach", "Жак Оффенбах", 1819, 1880, "Оффенбах", "Offenbach"),
    _c("delibes", "Лео Делиб", 1836, 1891, "Делиб", "Delibes"),
    _c("puccini", "Джакомо Пуччини", 1858, 1924, "Пуччини", "Puccini"),
    _c("rossini", "Джоаккино Россини", 1792, 1868, "Россини", "Rossini"),
    _c("donizetti", "Гаэтано Доницетти", 1797, 1848, "Доницетти", "Donizetti"),
    _c("bellini", "Винченцо Беллини", 1801, 1835, "Беллини", "Bellini"),
    _c("mahler", "Густав Малер", 1860, 1911, "Малер", "Mahler"),
    _c(
        "strauss_richard",
        "Рихард Штраус",
        1864,
        1949,
        "Р. Штраус",
        "Рихард Штраус",
        "Richard Strauss",
    ),
    _c(
        "strauss_johann",
        "Иоганн Штраус",
        1825,
        1899,
        "И. Штраус",
        "Иоганн Штраус",
        "Johann Strauss",
    ),
    _c("strauss", "Штраус (не уточнён)", None, None, "Штраус", "Strauss"),
    _c("debussy", "Клод Дебюсси", 1862, 1918, "Дебюсси", "Debussy"),
    _c("ravel", "Морис Равель", 1875, 1937, "Равель", "Ravel"),
    _c("satie", "Эрик Сати", 1866, 1925, "Сати", "Satie"),
    _c("sibelius", "Жан Сибелиус", 1865, 1957, "Сибелиус", "Sibelius"),
    _c("elgar", "Эдвард Элгар", 1857, 1934, "Элгар", "Elgar"),
    _c("glazunov", "Александр Глазунов", 1865, 1936, "Глазунов", "Glazunov"),
    _c("scriabin", "Александр Скрябин", 1872, 1915, "Скрябин", "Scriabin"),
    _c("rachmaninoff", "Сергей Рахманинов", 1873, 1943, "Рахманинов", "Rachmaninoff"),
    _c("schoenberg", "Арнольд Шёнберг", 1874, 1951, "Шёнберг", "Шенберг", "Schoenberg"),
    _c("berg", "Альбан Берг", 1885, 1935, "Берг", "Alban Berg"),
    _c("webern", "Антон Веберн", 1883, 1945, "Веберн", "Webern"),
    _c("bartok", "Бела Барток", 1881, 1945, "Барток", "Бартók", "Bartok"),
    _c("stravinsky", "Игорь Стравинский", 1882, 1971, "Стравинский", "Stravinsky"),
    _c(
        "prokofiev",
        "Сергей Прокофьев",
        1891,
        1953,
        "Прокофьев",
        "Prokofiev",
        "С. С. Прокофьев",
        "Sergei Prokofiev",
    ),
    _c("shostakovich", "Дмитрий Шостакович", 1906, 1975, "Шостакович", "Shostakovich"),
    _c("britten", "Бенджамин Бриттен", 1913, 1976, "Бриттен", "Britten"),
    _c("shchedrin", "Родион Щедрин", 1932, 2022, "Щедрин", "Shchedrin"),
    _c("schnittke", "Альфред Шнитке", 1934, 1998, "Шнитке", "Schnittke"),
    _c("denisov", "Эдисон Денисов", 1929, 1996, "Денисов", "Denisov"),
    _c("gubaidulina", "София Губайдулина", 1931, 2025, "Губайдулина", "Gubaidulina"),
    _c("part", "Арво Пярт", 1935, None, "Пярт", "Pärt"),
    _c("kancheli", "Гия Канчели", 1935, 2019, "Канчели", "Kancheli"),
    _c("silvestrov", "Валентин Сильвестров", 1937, None, "Сильвестров", "Silvestrov"),
    _c("weinberg", "Мечислав Вайнберг", 1919, 1996, "Вайнберг", "Вейнберг", "Weinberg"),
    _c("hindemith", "Пауль Хиндемит", 1895, 1963, "Хиндемит", "Hindemith"),
    _c("messiaen", "Оливье Мессиан", 1908, 1992, "Мессиан", "Messiaen"),
    _c("dutilleux", "Анри Дютийё", 1916, 2013, "Дютийё", "Дютильё", "Dutilleux"),
    _c("poulenc", "Франсис Пуленк", 1899, 1963, "Пуленк", "Poulenc"),
    _c("honegger", "Артюр Онеггер", 1892, 1955, "Онеггер", "Honegger"),
    _c("milhaud", "Дариюс Мийо", 1892, 1974, "Мийо", "Milhaud"),
    _c("ligeti", "Дьёрдь Лигети", 1923, 2006, "Лигети", "Ligeti"),
    _c("lutoslawski", "Витольд Лютославский", 1913, 1994, "Лютославский", "Lutoslawski"),
    _c("penderecki", "Кшиштоф Пендерецкий", 1933, 2020, "Пендерецкий", "Penderecki"),
    _c("gorecki", "Генрик Гурецкий", 1933, 2010, "Гурецкий", "Górecki", "Gorecki"),
    _c("adams", "Джон Адамс", 1947, None, "Джон Адамс", "John Adams"),
    _c("glass", "Филип Гласс", 1937, None, "Гласс", "Glass"),
    _c("reich", "Стив Райх", 1936, None, "Райх", "Reich"),
    _c("glinka", "Михаил Глинка", 1804, 1857, "Глинка", "Glinka"),
    _c("mussorgsky", "Модест Мусоргский", 1839, 1881, "Мусоргский", "Мусоргскій", "Mussorgsky"),
    _c("borodin", "Александр Бородин", 1833, 1887, "Бородин", "Borodin"),
    _c("balakirev", "Милий Балакирев", 1837, 1910, "Балакирев", "Balakirev"),
    _c("cui", "Цезарь Кюи", 1835, 1918, "Кюи", "Cui"),
    _c("lyadov", "Анатолий Лядов", 1855, 1914, "Лядов", "Lyadov"),
    _c("arensky", "Антон Аренский", 1861, 1906, "Аренский", "Arensky"),
    _c("taneyev", "Сергей Танеев", 1856, 1915, "Танеев", "Taneyev"),
    _c("medtner", "Николай Метнер", 1880, 1951, "Метнер", "Medtner"),
    _c("miaskovsky", "Николай Мясковский", 1881, 1950, "Мясковский", "Miaskovsky"),
    _c("khachaturian", "Арам Хачатурян", 1903, 1978, "Хачатурян", "Khachaturian"),
    _c("kabalevsky", "Дмитрий Кабалевский", 1904, 1987, "Кабалевский", "Kabalevsky"),
    _c("sviridov", "Георгий Свиридов", 1915, 1998, "Свиридов", "Sviridov"),
    _c("shebalin", "Виссарион Шебалин", 1902, 1963, "Шебалин", "Shebalin"),
    _c("ustvolskaya", "Галина Уствольская", 1919, 2006, "Уствольская", "Ustvolskaya"),
    _c("tishchenko", "Борис Тищенко", 1939, 2010, "Тищенко", "Tishchenko"),
    _c("slonimsky", "Сергей Слонимский", 1932, 2020, "Слонимский", "Slonimsky"),
    _c("karamanov", "Алемдар Караманов", 1934, 2007, "Караманов", "Karamanov"),
    _c("vaughan_williams", "Ралф Воан-Уильямс", 1872, 1958, "Воан-Уильямс", "Воан Уильямс"),
    _c("walton", "Уильям Уолтон", 1902, 1983, "Уолтон", "Walton"),
    _c("nielsen", "Карл Нильсен", 1865, 1931, "Нильсен", "Nielsen"),
    _c("berlioz", "Гектор Берлиоз", 1803, 1869, "Берлиоз", "Berlioz"),
    _c("gershwin", "Джордж Гершвин", 1898, 1937, "Гершвин", "Gershwin"),
    _c("paganini", "Никколо Паганини", 1782, 1840, "Паганини", "Paganini"),
    _c("piazzolla", "Астор Пьяццолла", 1921, 1992, "Пьяццолла", "Piazzolla"),
    _c("ysaye", "Эжен Изаи", 1858, 1931, "Изаи", "Ysaÿe", "Ysaye"),
    _c("scarlatti", "Доменико Скарлатти", 1685, 1757, "Скарлатти", "Scarlatti"),
    _c("kreisler", "Фриц Крейслер", 1875, 1962, "Крейслер", "Kreisler"),
    _c("gounod", "Шарль Гуно", 1818, 1893, "Гуно", "Gounod"),
    _c("wieniawski", "Генрик Венявский", 1835, 1880, "Венявский", "Wieniawski"),
    _c("lehar", "Ференц Легар", 1870, 1948, "Легар", "Lehár", "Lehar"),
    _c("telemann", "Георг Филипп Телеман", 1681, 1767, "Телеман", "Telemann"),
    _c("dunaevsky", "Исаак Дунаевский", 1900, 1955, "Дунаевский", "Isaak Dunaevsky"),
    _c("couperin", "Франсуа Куперен", 1668, 1733, "Куперен", "Couperin"),
    _c("szymanowski", "Кароль Шимановский", 1882, 1937, "Шимановский", "Szymanowski"),
    _c("martinu", "Богуслав Мартину", 1890, 1959, "Мартину", "Martinů", "Martinu"),
    _c("chausson", "Эрнест Шоссон", 1855, 1899, "Шоссон", "Chausson"),
    _c("reger", "Макс Регер", 1873, 1916, "Регер", "Reger"),
    _c("glier", "Рейнгольд Глиэр", 1875, 1956, "Глиэр", "Glière", "Gliere"),
    _c("podgaits", "Валерий Подгайц", 1947, None, "Подгайц", "Podgaits"),
    _c("purcell", "Генри Пёрселл", 1659, 1695, "Пёрселл", "Перселл", "Purcell"),
    _c("barber", "Сэмюэл Барбер", 1910, 1981, "Барбер", "Barber"),
    _c("albeniz", "Исаак Альбенис", 1860, 1909, "Альбенис", "Albéniz", "Albeniz"),
    _c("sarasate", "Пабло де Сарасате", 1844, 1908, "Сарасате", "Sarasate"),
    _c("rubinstein", "Антон Рубинштейн", 1829, 1894, "Рубинштейн", "Anton Rubinstein"),
    _c("respighi", "Отторино Респиги", 1879, 1936, "Респиги", "Respighi"),
    _c("rota", "Нино Рота", 1911, 1979, "Рота", "Nino Rota"),
    _c("buxtehude", "Дитрих Букстехуде", 1637, 1707, "Букстехуде", "Buxtehude"),
    _c("janacek", "Леош Яначек", 1854, 1928, "Яначек", "Janáček", "Janacek"),
    _c("gavrilin", "Валерий Гаврилин", 1939, 1999, "Гаврилин", "Gavrilin"),
    _c("granados", "Энрике Гранадос", 1867, 1916, "Гранадос", "Granados"),
    _c("bruch", "Макс Брух", 1838, 1920, "Брух", "Bruch"),
    _c("babadzhanyan", "Арно Бабаджанян", 1921, 1983, "Бабаджанян", "Babadzhanyan"),
    _c("kalman", "Имре Кальман", 1882, 1953, "Кальман", "Kálmán", "Kalman"),
    _c("tariverdiev", "Микаэл Таривердиев", 1931, 1996, "Таривердиев", "Tariverdiev"),
    _c("ginastera", "Альберто Хинастера", 1916, 1983, "Хинастера", "Ginastera"),
    _c("eshpai", "Андрей Эшпай", 1925, 2015, "Эшпай", "Eshpai"),
    _c("desyatnikov", "Леонид Десятников", 1955, None, "Десятников", "Desyatnikov"),
    _c("boccherini", "Луиджи Боккерини", 1743, 1805, "Боккерини", "Boccherini"),
    _c("kikta", "Валерий Кикта", 1941, None, "Кикта", "Kikta"),
    _c("gluck", "Кристоф Виллибальд Глюк", 1714, 1787, "Глюк", "Gluck"),
    _c("gretchaninov", "Александр Гречанинов", 1864, 1956, "Гречанинов", "Gretchaninov"),
    _c("alyabyev", "Александр Алябьев", 1787, 1851, "Алябьев", "Alyabyev"),
    _c("orff", "Карл Орф", 1895, 1982, "Орф", "Orff"),
    _c("berio", "Лучано Берио", 1925, 2003, "Берио", "Berio"),
    _c("vierne", "Луи Вьерн", 1870, 1937, "Вьерн", "Vierne"),
    _c("hummel", "Иоганн Непомук Гуммель", 1778, 1837, "Гуммель", "Hummel"),
    _c("clementi", "Муцио Клементи", 1752, 1832, "Клементи", "Clementi"),
    _c("albinoni", "Томазо Альбинони", 1671, 1751, "Альбинони", "Albinoni"),
    _c("bernstein", "Леонард Бернстайн", 1918, 1990, "Бернстайн", "Bernstein"),
    _c("tsfasman", "Александр Цфасман", 1906, 1971, "Цфасман", "Tsfasman"),
    _c("smetana", "Бедржих Сметана", 1824, 1884, "Сметана", "Smetana"),
    _c("kapustin", "Николай Капустин", 1937, 2020, "Капустин", "Kapustin"),
    _c("ellington", "Дюк Эллингтон", 1899, 1974, "Эллингтон", "Duke Ellington"),
    _c("corelli", "Арканджело Корелли", 1653, 1713, "Корелли", "Corelli"),
    _c("weber", "Карл Мария фон Вебер", 1786, 1826, "Вебер", "Weber"),
    _c("jolivet", "Андре Жоливе", 1905, 1974, "Жоливе", "Jolivet"),
    _c("artemiev", "Эдуард Артемьев", 1937, 2022, "Артемьев", "Artemiev"),
    _c("guilmant", "Александр Гильман", 1837, 1911, "Гильман", "Guilmant"),
    _c("pakhmutova", "Александра Пахмутова", 1929, None, "Пахмутова", "Pakhmutova"),
    _c("leoncavallo", "Руджеро Леонкавалло", 1857, 1919, "Леонкавалло", "Leoncavallo"),
    _c("mascagni", "Пьетро Масканьи", 1863, 1945, "Масканьи", "Mascagni"),
    _c("popper", "Давид Поппер", 1843, 1913, "Поппер", "David Popper"),
    _c("marcello", "Алессандро Марчелло", 1669, 1747, "Марчелло", "Marcello"),
    _c("kalinnikov", "Василий Калинников", 1866, 1901, "Калинников", "Kalinnikov"),
    _c("bortniansky", "Дмитрий Бортнянский", 1751, 1825, "Бортнянский", "Bortniansky"),
    _c("khrennikov", "Тихон Хренников", 1913, 2007, "Хренников", "Khrennikov"),
    _c("dargomyzhsky", "Александр Даргомыжский", 1813, 1869, "Даргомыжский", "Dargomyzhsky"),
    _c("rameau", "Жан-Филипп Рамо", 1683, 1764, "Рамо", "Rameau"),
    _c("cherepnin_alexander", "Александр Черепнин", 1899, 1977, "Александр Черепнин", "Черепнин"),
    _c("cherepnin_nikolai", "Николай Черепнин", 1863, 1945, "Н. Черепнин", "Николай Черепнин"),
    _c("kodaly", "Золтан Кодай", 1882, 1967, "Кодай", "Kodály", "Kodaly"),
    _c("clarke_jeremiah", "Джеремайя Кларк", 1674, 1707, "Джеремайя Кларк", "Jeremiah Clarke"),
    _c("byrd", "Уильям Бёрд", 1540, 1623, "Бёрд", "Byrd"),
    _c("cassado", "Гаспар Кассадо", 1897, 1966, "Кассадо", "Cassadó", "Cassado"),
    _c("petrov", "Андрей Петров", 1930, 2006, "Андрей Петров", "Petrov"),
    _c("gedike", "Александр Гедике", 1877, 1957, "Гедике", "Gedike"),
    _c("butsko", "Юрий Буцко", 1938, 2015, "Буцко", "Butsko"),
    _c("waxman", "Франц Ваксман", 1906, 1967, "Ваксман", "Franz Waxman"),
    _c("molchanov", "Кирилл Молчанов", 1922, 1982, "Молчанов", "Kirill Molchanov"),
    _c("pospelov", "Пётр Поспелов", 1963, None, "Пётр Поспелов", "Pospelov"),
    _c("alexandrov", "Александр Александров", 1883, 1946, "Александров", "Alexander Alexandrov"),
)


def _build_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for comp in COMPOSERS:
        for variant in comp.variants:
            key = re.sub(r"\s+", " ", variant.strip().lower())
            index.setdefault(key, comp.cid)
    return index


_INDEX = _build_index()


def by_cid() -> dict[str, Composer]:
    return {c.cid: c for c in COMPOSERS}


def match_composers(text: str) -> set[str]:
    """Find all composer ids mentioned in `text` (case-insensitive, word-boundary)."""
    if not text:
        return set()
    found: set[str] = set()
    lowered = text.lower()
    for variant, cid in _INDEX.items():
        pattern = r"(?<![а-яёa-z0-9éáíóúý])" + re.escape(variant) + r"(?![а-яёa-z0-9éáíóúý])"
        if re.search(pattern, lowered):
            found.add(cid)
    return _resolve_ambiguous(found)


_AMBIGUOUS = {"strauss": {"strauss_richard", "strauss_johann"}}


def _resolve_ambiguous(found: set[str]) -> set[str]:
    """Drop a generic entry («Штраус») when a specific homonym matched («Р. Штраус»)."""
    for generic, specifics in _AMBIGUOUS.items():
        if generic in found and found & specifics:
            found.discard(generic)
    return found


_INITIALS_RE = re.compile(
    r"(?:^|\n)\s*[А-ЯЁ]\.\s?(?:[А-ЯЁ]\.\s?)?([А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?)"
)
_KNOWN_SURNAMES = {v.split()[-1].lower() for c in COMPOSERS for v in c.variants}


def unknown_surnames(text: str) -> set[str]:
    """Surnames from «И. О. Фамилия» line-start patterns absent from the dictionary."""
    hits = {m.group(1) for m in _INITIALS_RE.finditer(text or "")}
    return {s for s in hits if s.lower() not in _KNOWN_SURNAMES}
