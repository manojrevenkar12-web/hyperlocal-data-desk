from desk.election import PARTIES, ElectionSettings, Night, Previous, Report


def votes(**kw):
    return {p: kw.get(p, 0) for p in PARTIES}


def setup():
    prev = {f"0811500{i}": Previous(1000, votes(CDU=400, GRÜNE=200, AfD=150, SPD=100, FDP=50, Sonstige=100)) for i in range(1, 6)}
    prev["08115009"] = Previous(50_000, votes(CDU=12_000, GRÜNE=20_000, AfD=3_000, SPD=6_000, FDP=2_000, Sonstige=2_000))
    return Night({"08115": sorted(prev)}, prev, ElectionSettings(z=1.96)), prev


def test_no_winner_is_named_while_the_city_has_not_counted():
    night, _prev = setup()
    for i in range(1, 6):
        night.receive(Report(f"0811500{i}", 30, 1000, votes(CDU=420, GRÜNE=190, AfD=160, SPD=90, FDP=40, Sonstige=100)), 30)
    night.update(30)
    c = night.calls["08115"]
    assert c.leader_now == "CDU" and c.winner is None
    assert "nach Auszählung von 5 der 6 Gemeinden vorn" in night.text("08115", "Böblingen")
    night.receive(
        Report("08115009", 200, 50_000, votes(CDU=12_500, GRÜNE=19_500, AfD=3_200, SPD=5_800, FDP=2_000, Sonstige=2_000)),
        200,
    )
    night.update(200)
    assert night.calls["08115"].winner == "GRÜNE"


def test_an_implausible_report_is_held_until_corrected():
    night, _prev = setup()
    swapped = Report("08115001", 30, 1000, votes(CDU=40, GRÜNE=190, AfD=160, SPD=90, FDP=420, Sonstige=100))
    assert night.receive(swapped, 30) == "held"
    assert "08115001" not in night.reports
    assert night.receive(Report("08115001", 50, 1000, votes(CDU=420, GRÜNE=190, AfD=160, SPD=90, FDP=40, Sonstige=100)), 50) == "used"
    assert night.receive(Report("08115002", 50, 1000, votes(CDU=2000)), 50) == "refused"  # more votes than voters
