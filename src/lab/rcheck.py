"""Writes reports/r-check.csv: every lead and watch-list entry of one dev season with the numbers behind its test,
so r/check_leads.R can reproduce the probabilities in R."""

from __future__ import annotations

import csv
from pathlib import Path

from desk.pipeline import Desk
from desk.store import MemoryStore
from world import generate, load_config


def r_check(root: Path) -> str:
    w = generate(load_config("dev"), 1)
    st = MemoryStore()
    st.put_municipalities(list(w.as_desk_municipalities().values()))
    desk = Desk.from_config(root, st)
    rows = []
    for r in sorted(w.releases, key=lambda r: (r.published, r.indicator)):
        o = desk.ingest(r.source, w.reissue(r) if r.drift else r.raw, r.published)
        for ld in o.leads + o.watch:
            rows.append([ld.indicator, str(ld.period), ld.level, ld.key, ld.observed, repr(ld.expected), repr(ld.shape), repr(ld.p)])
    out = root / "reports" / "r-check.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["indicator", "period", "level", "key", "observed", "expected", "shape", "p"])
        wr.writerows(rows)
    return f"wrote {len(rows)} leads to {out}"
