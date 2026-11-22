from world import generate, load_config
from world.election import generate_election


def test_the_simulated_land():
    w = generate(load_config("dev"), 1)
    assert len(w.municipalities) == 1101 and len({m.kreis for m in w.municipalities}) == 44
    assert abs(sum(m.population for m in w.municipalities) - 11_280_000) < 50_000
    assert all(len(m.ags) == 8 and m.ags.startswith("08") for m in w.municipalities)
    assert len(w.changes) >= 4 and all(c.new in w.neighbours[c.old] for c in w.changes)


def test_traps_are_planted_and_recorded():
    w = generate(load_config("dev"), 1)
    assert {r.drift for r in w.releases if r.drift}
    assert any(s.level == "kreis" for s in w.stories) and any(s.level == "gemeinde" for s in w.stories)
    stale = [r for r in w.releases if r.drift == "stale"]
    for r in stale:
        assert r.printed != r.clean  # a stale file says last quarter's numbers


def test_the_election_night():
    w = generate(load_config("dev"), 1)
    ew = generate_election(w, w.cfg["election"], 1)
    big = max(ew.final.values(), key=lambda r: r.eligible)
    small = min(ew.final.values(), key=lambda r: r.eligible)
    assert big.minute > small.minute  # cities count last
    assert len(set(ew.kreis_winner.values())) >= 2
