from datetime import date

import pytest

from desk.domain import AgsChange, Gebietsstand, Municipality, Period, kreis_of
from desk.numbers import NumberFormatError, fmt_de, numbers_in, parse_cell


def test_german_numbers_and_official_signs():
    assert parse_cell("1.234") == (1234.0, None)
    assert parse_cell("1.234,5") == (1234.5, None)
    assert parse_cell("–") == (0.0, "nichts")
    assert parse_cell(".") == (None, "geheim")
    assert parse_cell("x") == (None, "gesperrt")
    assert parse_cell("(12)") == (12.0, "eingeschränkt")


def test_an_english_thousands_separator_is_not_silently_read():
    # "1,266" read the German way is 1.266: accepted by the parser, refused later by the whole-number check
    assert parse_cell("1,266") == (1.266, None)
    with pytest.raises(NumberFormatError):
        parse_cell("1,234.5")


def test_formatting_and_finding_numbers_in_text():
    assert fmt_de(12345.6, 1) == "12.345,6"
    found = [(v, d) for v, d, _, _ in numbers_in("Im 3. Quartal 2026 wurden 1.234 Wohnungen genehmigt, 12,5 je 1.000.")]
    assert (1234.0, 0) in found and (12.5, 1) in found and (2026.0, 0) in found


def test_periods():
    p = Period.parse("3. Quartal 2026")
    assert p == Period.parse("2026Q3") and str(p.shift(2)) == "2027Q1" and p.end == date(2026, 9, 30)


def test_gebietsstand_follows_mergers_on_their_date():
    ms = {a: Municipality(a, a, pop, 0, 0) for a, pop in [("08111001", 1000), ("08111002", 500), ("08111003", 200)]}
    g = Gebietsstand(ms, [AgsChange("08111003", "08111002", date(2026, 1, 1)), AgsChange("08111002", "08111001", date(2027, 1, 1))])
    assert g.successor("08111003", date(2025, 12, 31)) == "08111003"
    assert g.successor("08111003", date(2026, 6, 30)) == "08111002"
    assert g.successor("08111003", date(2027, 6, 30)) == "08111001"  # a chain of mergers
    assert g.population_on("08111001", date(2027, 6, 30)) == 1700
    assert g.valid_on(date(2026, 6, 30)) == {"08111001", "08111002"}
    assert kreis_of("08111003") == "08111"
