import os
from datetime import date
from pathlib import Path

import pytest

from desk.pipeline import Desk
from desk.store import MemoryStore, SqlStore
from world import generate, load_config

ROOT = Path(__file__).resolve().parents[1]


def season(store):
    w = generate({**load_config("dev"), "quarters": 8}, 3)
    store.put_municipalities(list(w.as_desk_municipalities().values()), {m.ags: m.outline.wkt for m in w.municipalities})
    d = Desk.from_config(ROOT, store)
    out = []
    for r in sorted(w.releases, key=lambda r: (r.published, r.indicator)):
        o = d.ingest(r.source, r.raw, r.published)
        out.append((r.indicator, str(r.period), o.status, [(ld.key, round(ld.p, 12)) for ld in o.leads + o.watch]))
    return out


def test_the_store_never_changes_a_decision():
    mem = season(MemoryStore())
    assert mem == season(SqlStore.duckdb())
    url = os.environ.get("HDD_TEST_POSTGRES_URL")
    if url:
        pg = SqlStore.postgres(url)
        pg.reset()
        assert mem == season(pg)


@pytest.mark.skipif(not os.environ.get("HDD_TEST_POSTGRES_URL"), reason="needs Postgres with PostGIS")
def test_postgis_finds_neighbours_by_outline():
    pg = SqlStore.postgres(os.environ["HDD_TEST_POSTGRES_URL"])
    pg.reset()
    w = generate(load_config("dev"), 1)
    pg.put_municipalities(list(w.as_desk_municipalities().values()), {m.ags: m.outline.wkt for m in w.municipalities})
    a = w.municipalities[20].ags
    assert set(w.neighbours[a]) <= set(pg.touching(a))


def test_boundary_changes_are_read_from_the_official_list():
    st = MemoryStore()
    d = Desk.from_config(ROOT, st)
    raw = (
        "Amt\nAlter Schlüssel;Alte Gemeinde;Neuer Schlüssel;Neue Gemeinde;Wirksam ab;Art\n08115003;A;08115002;B;01.01.2026;Eingliederung\n"
    )
    cs = d.ingest_changes(raw.encode())
    assert cs[0].old == "08115003" and cs[0].valid_from == date(2026, 1, 1) and st.changes() == cs
