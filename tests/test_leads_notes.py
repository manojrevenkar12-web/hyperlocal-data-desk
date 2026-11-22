from datetime import date

from desk.domain import AgsChange, Gebietsstand, Municipality, Observation, Period
from desk.leads import LeadSettings, bh_cutoff, find_leads, harmonise, naive_leads
from desk.notes import check_numbers, lead_facts, template_lead, write_checked

P = [Period(2025, q) for q in (1, 2, 3, 4)] + [Period(2026, 1), Period(2026, 2), Period(2026, 3)]


def world(values: dict[str, list[float | None]], pops: dict[str, int]):
    ms = {a: Municipality(a, a, p, 0, 0) for a, p in pops.items()}
    series = {p: {a: Observation(a, p, v[i]) for a, v in values.items()} for i, p in enumerate(P)}
    return Gebietsstand(ms), series


def flat(n: int, base: float, last: float) -> list[float | None]:
    return [base] * (n - 1) + [last]


def test_a_village_going_from_one_to_four_is_not_a_lead_but_a_town_tripling_is():
    pops = {f"08115{i:03d}": 20_000 for i in range(1, 40)} | {"08115100": 600, "08116001": 20_000, "08116002": 20_000}
    vals = {a: [20.0 + (i % 3) for i in range(7)] for a in pops}
    vals["08115100"] = [1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 4.0]  # +300% on last quarter, three permits more
    vals["08116001"] = [20.0, 21.0, 19.0, 20.0, 22.0, 20.0, 62.0]
    geb, series = world(vals, pops)
    leads = find_leads("x", series, P[-1], geb, LeadSettings(history_quarters=6))
    keys = [ld.key for ld in leads if ld.strong]
    assert "08116001" in keys and "08115100" not in keys
    naive = naive_leads("x", series, P[-1], 3)
    assert naive[0].key == "08115100"  # the spreadsheet way puts the village first


def test_a_merger_is_not_a_jump():
    pops = {"08115001": 5000, "08115002": 4000} | {f"08116{i:03d}": 9000 for i in range(1, 30)}
    vals = {a: [30.0] * 7 for a in pops}
    vals["08115001"] = [15.0] * 4 + [30.0] * 3  # absorbed its neighbour on 1 January 2026
    vals["08115002"] = [15.0] * 4 + [None] * 3
    ms = {a: Municipality(a, a, p, 0, 0) for a, p in pops.items()}
    geb = Gebietsstand(ms, [AgsChange("08115002", "08115001", date(2026, 1, 1))])
    series = {p: {a: Observation(a, p, v[i]) for a, v in vals.items() if v[i] is not None} for i, p in enumerate(P)}
    h = harmonise(series, geb, P[-1].end)
    assert h[P[0]]["08115001"] == 30.0 and "08115002" not in h[P[0]]
    assert not [ld for ld in find_leads("x", series, P[-1], geb, LeadSettings(history_quarters=6)) if ld.key == "08115001"]


def test_benjamini_hochberg():
    assert bh_cutoff([0.001, 0.01, 0.02, 0.5], 0.05) == 0.02
    assert bh_cutoff([0.3, 0.6], 0.05) == -1.0


FACTS = lead_facts(
    name="Kirchtal",
    kreis_name="Böblingen",
    level="gemeinde",
    unit="genehmigte Wohnungen",
    year=2026,
    quarter=3,
    observed=62,
    expected=20.4,
    population=20_000,
    land_rate=1.1,
    history=[20, 21, 19, 20],
)


def test_the_template_passes_its_own_number_check():
    t = template_lead(FACTS)
    c = check_numbers(t, FACTS)
    assert c.ok, c.problems
    assert "62" in t and "Prozent mehr" in t


def test_a_number_with_no_fact_or_the_wrong_direction_is_refused():
    bad = template_lead(FACTS).replace("3,1 je", "31,0 je")
    assert not check_numbers(bad, FACTS).ok
    flipped = template_lead(FACTS).replace("mehr", "weniger")
    assert "schreibt „gesunken“, die Zahl ist gestiegen" in check_numbers(flipped, FACTS).problems


class Liar:
    def draft(self, kind, facts):
        return template_lead(facts).replace("62 genehmigte", "26 genehmigte")


def test_a_refused_model_draft_falls_back_to_the_template():
    out = write_checked("lead", FACTS, Liar())
    assert out.ok and out.source == "template" and "62 genehmigte" in out.text
    assert any("verworfen" in p for p in out.problems)
