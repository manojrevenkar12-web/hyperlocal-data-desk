"""Plays one design through one simulated world: every release in publication order, the way it would reach the
newsroom, and records what each design published: leads, notes and municipal texts, with their numbers.

The designs:
- spreadsheet: the status quo. Column three is the value, a withheld cell is zero, the unit line is not read,
  rank municipalities by percentage change on last quarter.
- model_alone: a model reads each file and names the leads and writes the texts; nothing checks it.
- desk (and its ablations): the product in src/desk, run exactly as in production on an in-memory store.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from desk.domain import Observation, Period
from desk.leads import naive_leads
from desk.pipeline import Desk
from desk.store import MemoryStore
from world import Release, World
from world.standin import StandInWriter, model_reading


@dataclass
class Design:
    name: str
    label: str
    kind: str  # spreadsheet | model_alone | desk
    settings: dict[str, Any] = field(default_factory=dict)
    about: str = ""
    ablation: bool = False


def load_designs(root: Path) -> list[Design]:
    doc = json.loads((root / "config" / "designs.json").read_text(encoding="utf-8"))
    return [Design(**d) for d in doc["designs"]]


@dataclass
class PublishedLead:
    indicator: str
    period: Period
    level: str
    key: str
    observed: float
    note_wrong: bool
    note_refused: bool = False
    strong: bool = True  # False = on the desk's watch list, not sent to reporters


@dataclass
class PublishedRelease:
    indicator: str
    period: Period
    drift: str | None
    quarantined: bool
    delay_days: int
    values: dict[str, float | None]  # what the design believed the municipalities' numbers were
    texts_wrong: int
    texts: int


@dataclass
class Played:
    design: Design
    leads: list[PublishedLead] = field(default_factory=list)
    releases: list[PublishedRelease] = field(default_factory=list)
    quarantines: int = 0
    false_quarantines: int = 0
    hand_fixes: int = 0
    showcase: dict[str, Any] = field(default_factory=dict)


# ------------------------------------------------------------------------------------------- the status quo parser


def _lenient(cell: str) -> float:
    """How a quick script reads a cell: signs are zero, German separators, nothing refused."""
    t = cell.strip()
    if t in {".", "–", "-", "x", "/", "...", ""}:
        return 0.0
    try:
        return float(t.replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0


def positional_parse(rel: Release) -> dict[str, float | None] | None:
    raw = rel.raw.decode("utf-8")
    out: dict[str, float | None] = {}
    if rel.format == "csv":
        for ln in raw.splitlines():
            c = ln.split(";")
            if len(c) >= 3 and re.fullmatch(r"\d{8}", c[0].strip()):
                out[c[0].strip()] = _lenient(c[2])
        return out
    if rel.format == "json":
        doc = json.loads(raw)
        for row in doc.get("daten", []):
            if "wert" not in row:
                return None  # the script crashes; someone fixes it by hand
            v = row["wert"]
            out[row["ags"]] = 0.0 if v is None else (float(v) if isinstance(v, (int, float)) else _lenient(str(v)))
        return out
    soup = BeautifulSoup(raw, "lxml")
    for tr in soup.select("table.statistik tbody tr"):
        tds = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(tds) >= 3 and re.fullmatch(r"\d{8}", tds[0]):
            out[tds[0]] = _lenient(tds[2])
    return out


# ------------------------------------------------------------------------------------------- play


def _wrong(believed: float | None, truth: float | None) -> bool:
    if believed is None or (isinstance(believed, float) and math.isnan(believed)):
        return False  # nothing printed
    if truth is None:
        return True  # a number printed where the truth is withheld or absent
    return abs(believed - truth) > 0.5


def play(root: Path, w: World, d: Design, lab: dict[str, Any]) -> Played:
    model_cfg = w.cfg["model"]
    writer = StandInWriter(w.seed, model_cfg["note_error"])
    text_writer = StandInWriter(w.seed + 7919, model_cfg["text_error"])
    from_q = w.periods[w.cfg["stories"]["from_quarter"]]
    out = Played(d)
    rels = sorted(w.releases, key=lambda r: (r.published, r.indicator))
    changes_day = date.fromisoformat(w.cfg["merge_on"]) - timedelta(days=17)
    truth_by = {(r.indicator, r.period): r for r in rels}

    if d.kind == "desk":
        st = MemoryStore()
        st.put_municipalities(list(w.as_desk_municipalities().values()))
        desk = Desk.from_config(root, st, d.settings, writer=writer)
        loaded = False
        for r in rels:
            if not loaded and r.published >= changes_day and desk.s.gebietsstand:
                desk.ingest_changes(w.changes_raw)
                loaded = True
            o = desk.ingest(r.source, r.raw, r.published)
            delay = 0
            quarantined = o.status == "quarantined"
            if quarantined:
                out.quarantines += 1
                if r.drift is None:
                    out.false_quarantines += 1
                o = desk.ingest(r.source, w.reissue(r), r.published + timedelta(days=lab["reissue_days"]))
                delay = lab["reissue_days"]
            if o.status != "published":
                continue
            prev_truth = truth_by.get((r.indicator, r.period.shift(-1)))
            tw = 0
            for a, f in o.text_facts.items():
                truth_now = r.true_values.get(a) if r.clean.get(a) is not None else None
                believed = None if f.get("withheld") else float(f["observed"])
                prev_b = float(f["previous"]) if not f.get("withheld") else float("nan")
                prev_t = prev_truth.true_values.get(a) if prev_truth and prev_truth.clean.get(a) is not None else None
                if _wrong(believed, truth_now) or (prev_t is not None and _wrong(prev_b, prev_t)):
                    tw += 1
            series_now = o.text_facts
            out.releases.append(
                PublishedRelease(
                    r.indicator,
                    r.period,
                    r.drift,
                    quarantined,
                    delay,
                    {a: (None if f.get("withheld") else float(f["observed"])) for a, f in series_now.items()},
                    tw,
                    len(o.text_facts),
                )
            )
            if from_q <= r.period:
                for ld, f, n in zip(o.leads, o.lead_facts, o.notes, strict=True):
                    truth = _lead_truth(w, r, ld.level, ld.key)
                    note_wrong = (
                        (abs(float(f["observed"]) - truth) > 0.5)
                        or (n.source == "model" and not n.ok)
                        or (n.source == "model" and writer.wrong("lead", f) and not desk.s.number_check)
                    )
                    out.leads.append(
                        PublishedLead(
                            r.indicator,
                            r.period,
                            ld.level,
                            ld.key,
                            ld.observed,
                            note_wrong,
                            note_refused=any("verworfen" in p for p in n.problems),
                        )
                    )
                for ld in o.watch:
                    out.leads.append(PublishedLead(r.indicator, r.period, ld.level, ld.key, ld.observed, False, strong=False))
            # the showcase is the release with the most strong leads (the earliest of equals)
            if o.leads and from_q <= r.period and len(o.leads) > len(out.showcase.get("leads", [])):
                out.showcase = {
                    "indicator": r.indicator,
                    "period": str(r.period),
                    "leads": [
                        {
                            **{k: v for k, v in f.items() if not (isinstance(v, float) and math.isnan(v))},
                            "note": n.text,
                            "note_source": n.source,
                            "problems": n.problems,
                            "numbers": [[a, b, c] for a, b, c in n.numbers],
                            "p": ld.p,
                        }
                        for ld, f, n in zip(o.leads, o.lead_facts, o.notes, strict=True)
                    ],
                    "checks": [c.__dict__ for c in o.checks],
                }
        return out

    # spreadsheet and model_alone keep their own series
    series: dict[str, dict[Period, dict[str, Observation]]] = {}
    for r in rels:
        if d.kind == "spreadsheet":
            vals = positional_parse(r)
            delay = 0
            if vals is None:
                out.hand_fixes += 1
                vals = {a: (v if v is not None else 0.0) for a, v in r.clean.items()}
                delay = lab["reissue_days"]
        else:
            vals = model_reading(r)
            delay = 0
        s = series.setdefault(r.indicator, {})
        s[r.period] = {a: Observation(a, r.period, v, None) for a, v in vals.items()}
        prev = s.get(r.period.shift(-1), {})
        prev_truth = truth_by.get((r.indicator, r.period.shift(-1)))
        tw = 0
        for a, v in vals.items():
            truth_now = r.true_values.get(a) if r.clean.get(a) is not None else None
            pv = prev.get(a)
            prev_t = prev_truth.true_values.get(a) if prev_truth and prev_truth.clean.get(a) is not None else None
            wrong = _wrong(v, truth_now) or (pv is not None and prev_t is not None and _wrong(pv.value, prev_t))
            if d.kind == "model_alone" and v is not None and not wrong:
                wrong = text_writer.wrong("text", {"name": a, "indicator": r.indicator, "year": r.period.year, "quarter": r.period.quarter})
            tw += wrong
        out.releases.append(PublishedRelease(r.indicator, r.period, r.drift, False, delay, dict(vals), tw, len(vals)))
        if from_q <= r.period:
            lds = naive_leads(
                r.indicator,
                s,
                r.period,
                lab["per_release"],
                min_base=1.0 if d.kind == "spreadsheet" else float(w.cfg["model"]["min_base"]),
                withheld_as_zero=d.kind == "spreadsheet",
            )
            for ld in lds:
                truth = _lead_truth(w, r, ld.level, ld.key)
                facts: dict[str, float | str] = {
                    "name": ld.key,
                    "indicator": r.indicator,
                    "year": r.period.year,
                    "quarter": r.period.quarter,
                }
                wrong = abs(ld.observed - truth) > 0.5 or (d.kind == "model_alone" and writer.wrong("lead", facts))
                out.leads.append(PublishedLead(r.indicator, r.period, ld.level, ld.key, ld.observed, wrong))
    return out


def _lead_truth(w: World, r: Release, level: str, key: str) -> float:
    if level == "kreis":  # what could be known: withheld cells are not in a published total
        return sum(v for a, v in r.true_values.items() if a[:5] == key and r.clean.get(a) is not None)
    return r.true_values.get(key, float("nan"))


def is_true_lead(w: World, ld: PublishedLead) -> int | None:
    """The index of the story a lead points to, or None. A village lead inside a district-wide story counts: the
    reporter who follows it finds the district story."""
    for i, s in enumerate(w.stories):
        if s.indicator != ld.indicator or not s.active(ld.period):
            continue
        if s.key == ld.key or (s.level == "kreis" and ld.level == "gemeinde" and ld.key[:5] == s.key):
            return i
    return None
