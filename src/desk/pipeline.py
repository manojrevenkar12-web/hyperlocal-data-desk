"""The desk's pipeline for one release: parse, check, keep, find leads, write checked notes and municipal texts.

desk = Desk.from_config(root, store)
out = desk.ingest("statla-bau", raw_bytes, received=date(2026, 11, 14))
out.status            # "published" or "quarantined"
out.leads, out.notes  # ranked leads with checked notes
out.texts             # one checked text per municipality, the automated article
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .checks import Check, CheckSettings, blocking_failures, check_release
from .domain import AgsChange, Gebietsstand, Indicator, Observation, Period, kreis_of
from .leads import Lead, LeadSettings, find_leads, naive_leads
from .notes import CheckedText, Facts, Writer, check_numbers, lead_facts, template_municipal, write_checked
from .numbers import fmt_de
from .sources import ParseError, SourceSpec, parse
from .store import ReleaseRecord, Store


@dataclass
class DeskSettings:
    leads: LeadSettings = field(default_factory=LeadSettings)
    checks: CheckSettings = field(default_factory=CheckSettings)
    run_checks: bool = True  # off = publish whatever parses
    gebietsstand: bool = True  # off = ignore the official list of boundary changes
    ranking: str = "surprise"  # surprise | pct_change
    number_check: bool = True  # off = a model's draft goes out as written
    model: str = "claude-sonnet-5-5"


def load_settings(root: Path, overrides: dict[str, Any] | None = None) -> DeskSettings:
    cfg = json.loads((root / "config" / "desk.json").read_text(encoding="utf-8"))
    o = dict(overrides or {})
    lead_o = o.pop("leads", {})
    check_o = o.pop("checks", {})
    return DeskSettings(
        LeadSettings(**{**cfg["leads"], **lead_o}),
        CheckSettings(**{**cfg["checks"], **check_o}),
        model=cfg.get("model", "claude-sonnet-5-5"),
        **o,
    )


@dataclass
class Outcome:
    release_id: int | None
    source: str
    indicator: str
    period: Period | None
    status: str  # published | quarantined
    checks: list[Check]
    leads: list[Lead] = field(default_factory=list)  # strong leads, for reporters
    watch: list[Lead] = field(default_factory=list)  # the next best, marked as weaker
    notes: list[CheckedText] = field(default_factory=list)
    lead_facts: list[Facts] = field(default_factory=list)
    text_facts: dict[str, Facts] = field(default_factory=dict)
    problem: str | None = None


class Desk:
    def __init__(
        self,
        store: Store,
        specs: dict[str, SourceSpec],
        indicators: dict[str, Indicator],
        kreis_names: dict[str, str],
        settings: DeskSettings,
        writer: Writer | None = None,
    ) -> None:
        self.store = store
        self.specs = specs
        self.indicators = indicators
        self.kreis_names = kreis_names
        self.s = settings
        self.writer = writer

    @staticmethod
    def from_config(root: Path, store: Store, overrides: dict[str, Any] | None = None, writer: Writer | None = None) -> Desk:
        src = json.loads((root / "config" / "sources.json").read_text(encoding="utf-8"))
        specs = {d["id"]: SourceSpec.from_dict(d) for d in src["sources"]}
        inds = {k: Indicator(k, v["label"], v["unit"], 1000, v.get("suppress_below", 0)) for k, v in src["indicators"].items()}
        geo = json.loads((root / "geo" / "bw_kreise.geojson").read_text(encoding="utf-8"))
        names = {f["properties"]["ags"]: f["properties"]["name"] for f in geo["features"]}
        return Desk(store, specs, inds, names, load_settings(root, overrides), writer)

    # ------------------------------------------------------------------ boundary changes
    def ingest_changes(self, raw: bytes) -> list[AgsChange]:
        """The official list of boundary changes (Gebietsänderungen), CSV with a header row."""
        lines = [ln for ln in raw.decode("utf-8-sig").splitlines() if ";" in ln]
        header = [h.strip() for h in lines[0].split(";")]
        need = {"Alter Schlüssel", "Neuer Schlüssel", "Wirksam ab"}
        if not need <= set(header):
            raise ParseError(f"boundary-change list without {sorted(need - set(header))}")
        ix = {h: i for i, h in enumerate(header)}
        out = []
        for ln in lines[1:]:
            c = [x.strip() for x in ln.split(";")]
            out.append(
                AgsChange(
                    c[ix["Alter Schlüssel"]],
                    c[ix["Neuer Schlüssel"]],
                    datetime.strptime(c[ix["Wirksam ab"]], "%d.%m.%Y").date(),
                )
            )
        self.store.put_changes(out)
        return out

    def gebietsstand(self) -> Gebietsstand:
        return Gebietsstand(self.store.municipalities(), self.store.changes() if self.s.gebietsstand else [])

    # ------------------------------------------------------------------ one release
    def ingest(self, source: str, raw: bytes, received: date) -> Outcome:
        spec = self.specs[source]
        ind = self.indicators[spec.indicator]
        try:
            rel = parse(raw, spec)
        except ParseError as e:
            return Outcome(None, source, spec.indicator, None, "quarantined", [Check("parse", False, True, str(e))], problem=str(e))
        geb = self.gebietsstand()
        before = self.store.series(spec.indicator)
        prev = before.get(rel.period.shift(-1))
        checks = (
            check_release(rel, geb, {a: o.value for a, o in prev.items()} if prev else None, self.s.checks, integer=True)
            if self.s.run_checks
            else []
        )
        status = "quarantined" if blocking_failures(checks) else "published"
        rid = self.store.next_id()
        self.store.add_release(
            ReleaseRecord(
                rid,
                source,
                spec.indicator,
                rel.period,
                received,
                status,
                [asdict(c) for c in checks],
                rel.unit_label,
                rel.factor,
            ),
            rel.rows,
        )
        out = Outcome(rid, source, spec.indicator, rel.period, status, checks)
        if status != "published":
            out.problem = "; ".join(f"{c.name}: {c.detail}" for c in blocking_failures(checks))
            return out

        series = self.store.series(spec.indicator)
        if self.s.ranking == "surprise":
            leads = find_leads(spec.indicator, series, rel.period, geb, self.s.leads)
        else:
            leads = naive_leads(spec.indicator, series, rel.period, self.s.leads.per_release, min_base=5, withheld_as_zero=False)
        out.leads = [ld for ld in leads if ld.strong]
        out.watch = [ld for ld in leads if not ld.strong]
        leads = out.leads
        out.lead_facts = [self._lead_facts(ld, ind, series, geb) for ld in leads]
        out.notes = [self._note(f) for f in out.lead_facts]
        self.store.put_leads(
            rid,
            [
                {
                    **f,
                    "p": ld.p,
                    "level": ld.level,
                    "key": ld.key,
                    "note": n.text,
                    "note_source": n.source,
                    "strong": True,
                }
                for ld, f, n in zip(leads, out.lead_facts, out.notes, strict=True)
            ]
            + [
                {
                    "key": ld.key,
                    "level": ld.level,
                    "p": ld.p,
                    "observed": ld.observed,
                    "expected": ld.expected,
                    "strong": False,
                }
                for ld in out.watch
            ],
        )
        out.text_facts = self._municipal_facts(rel.period, series, geb, ind)
        return out

    def _note(self, f: Facts) -> CheckedText:
        if self.s.number_check:
            return write_checked("lead", f, self.writer)
        if self.writer is None:
            return write_checked("lead", f, None)
        t = check_numbers(self.writer.draft("lead", f), f)
        t.source = "model"
        return t

    def _lead_facts(self, ld: Lead, ind: Indicator, series: dict[Period, dict[str, Observation]], geb: Gebietsstand) -> Facts:
        ms = geb.municipalities
        now = series[ld.period]
        land_total = sum(o.value or 0 for o in now.values())
        land_pop = sum(m.population for m in ms.values())
        if ld.level == "kreis":
            name, kname, pop = self.kreis_names.get(ld.key, ld.key), self.kreis_names.get(ld.key, ld.key), ld.population
        else:
            name, kname = ms[ld.key].name if ld.key in ms else ld.key, self.kreis_names.get(kreis_of(ld.key), "")
            pop = geb.population_on(ld.key, ld.period.end) if self.s.gebietsstand else ms[ld.key].population if ld.key in ms else 1
        f = lead_facts(
            name=name,
            kreis_name=kname,
            level=ld.level,
            unit=ind.unit,
            year=ld.period.year,
            quarter=ld.period.quarter,
            observed=ld.observed,
            expected=ld.expected,
            population=max(pop, 1),
            land_rate=land_total / land_pop * 1000,
            history=ld.history,
        )
        f["key"] = ld.key
        f["indicator"] = ld.indicator
        f["withheld"] = int(ld.facts.get("withheld", 0))
        return f

    def _municipal_facts(
        self, p: Period, series: dict[Period, dict[str, Observation]], geb: Gebietsstand, ind: Indicator
    ) -> dict[str, Facts]:
        now = series[p]
        prev = series.get(p.shift(-1), {})
        k_sum: dict[str, float] = {}
        k_pop: dict[str, int] = {}
        for a, o in now.items():
            k = kreis_of(a)
            if o.value is not None:
                k_sum[k] = k_sum.get(k, 0) + o.value
                k_pop[k] = k_pop.get(k, 0) + geb.population_on(a, p.end)
        out: dict[str, Facts] = {}
        for a, o in now.items():
            m = geb.municipalities.get(a)
            if m is None:
                continue
            pv = prev.get(a)
            pop = geb.population_on(a, p.end)
            k = kreis_of(a)
            out[a] = {
                "name": m.name,
                "unit": ind.unit,
                "year": p.year,
                "quarter": p.quarter,
                "observed": o.value if o.value is not None else float("nan"),
                "previous": pv.value if pv and pv.value is not None else float("nan"),
                "change_prev": (o.value - pv.value) if (o.value is not None and pv and pv.value is not None) else 0.0,
                "rate": (o.value or 0) / max(pop, 1) * 1000,
                "kreis_rate": k_sum.get(k, 0) / max(k_pop.get(k, 1), 1) * 1000,
                "withheld": o.value is None,
            }
        return out

    @staticmethod
    def municipal_text(f: Facts) -> str:
        """The automated text; a withheld count is said to be withheld, never printed as zero."""
        if f.get("withheld"):
            return (
                f"Für {f['name']} hält das Amt die Zahl der {f['unit']} im {int(f['quarter'])}. Quartal "
                f"{int(f['year'])} geheim, weil sie sehr klein ist. Im Landkreis waren es "
                f"{fmt_de(float(f['kreis_rate']), 1)} je 1.000 Einwohner."
            )
        if f["previous"] != f["previous"]:  # no previous quarter
            f = {**f, "previous": f["observed"], "change_prev": 0.0}
        return template_municipal(f)
