"""The simulated world: municipalities, what really happened in them each quarter, and the files the offices publish.

The truth stays here. The desk sees only the published files (bytes in three layouts) and the official list of
boundary changes. The world has its own copy of the trade's conventions (signs, layouts, secrecy) and never reads the
desk's settings.

Planted in the world, each with its truth recorded:
- real stories: a municipality's rate shifts for one to three quarters (a new building area, a closed plant), or a
  whole district shifts (a district-wide programme);
- small numbers: villages where one permit more is +100%;
- mergers on 1 January 2026: a village absorbed by its neighbour, so the neighbour "jumps";
- withheld cells: the building-permit office keeps counts of 1 and 2 secret (".");
- file drift: a stale file re-published under a new quarter, counts above 999 written with English separators, an
  unknown unit, a known unit change to thousands, an extra column, a truncated file, a renamed JSON field.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np

from desk.domain import AgsChange, Municipality, Period
from desk.numbers import fmt_de

from .geo import SimMunicipality, build, load_kreise, neighbours

ROOT = Path(__file__).resolve().parents[2]


def keyed(*parts: object) -> np.random.Generator:
    """A generator fixed by its key, so every design meets the same luck."""
    h = 1469598103934665603
    for ch in "|".join(map(str, parts)).encode():
        h = ((h ^ ch) * 1099511628211) % (1 << 64)
    return np.random.default_rng(h)


@dataclass
class Story:
    indicator: str
    level: str  # gemeinde | kreis
    key: str
    start: Period
    quarters: int
    factor: float

    def active(self, p: Period) -> bool:
        return self.start <= p < self.start.shift(self.quarters)


@dataclass
class Release:
    source: str
    indicator: str
    period: Period
    format: str
    raw: bytes
    drift: str | None
    published: date
    # truth, for the lab only
    true_values: dict[str, float]  # what happened, on the boundaries the file uses
    printed: dict[str, float | None]  # what the file means to say, withheld cells as None (stale: last quarter)
    clean: dict[str, float | None]  # what a correct file for this quarter would say


@dataclass
class World:
    cfg: dict[str, Any]
    seed: int
    municipalities: list[SimMunicipality]
    neighbours: dict[str, list[str]]
    changes: list[AgsChange]
    changes_raw: bytes
    releases: list[Release]
    stories: list[Story]
    periods: list[Period]

    def reissue(self, rel: Release) -> bytes:
        """The office's corrected file after the desk's query: this quarter's numbers, no drift."""
        ic = self.cfg["indicators"][rel.indicator]
        return render(
            ic,
            self.cfg["phrases"],
            rel.period,
            rel.clean,
            self.municipalities,
            None,
            keyed(self.seed, "re", rel.indicator),
        )

    def as_desk_municipalities(self) -> dict[str, Municipality]:
        return {m.ags: Municipality(m.ags, m.name, m.population, m.lon, m.lat, m.kind) for m in self.municipalities}


def load_config(which: str) -> dict[str, Any]:
    name = "world.json" if which == "dev" else "heldout.json"
    cfg: dict[str, Any] = json.loads((ROOT / "config" / name).read_text(encoding="utf-8"))
    cfg["phrases"] = json.loads((ROOT / "config" / cfg["layouts"]).read_text(encoding="utf-8"))
    return cfg


_geo_cache: dict[tuple[int, int], tuple[list[SimMunicipality], dict[str, list[str]]]] = {}


def geography(cfg: dict[str, Any]) -> tuple[list[SimMunicipality], dict[str, list[str]]]:
    key = (int(cfg["geo_seed"]), int(cfg["municipalities"]))
    if key not in _geo_cache:
        ms = build(
            load_kreise(ROOT / "geo" / "bw_kreise.geojson"),
            cfg["municipalities"],
            cfg["land_population"],
            cfg["geo_seed"],
        )
        _geo_cache[key] = (ms, neighbours(ms))
    return _geo_cache[key]


def generate(cfg: dict[str, Any], seed: int) -> World:
    ms, nb = geography(cfg)
    start = Period.parse(cfg["start"])
    periods = [start.shift(i) for i in range(cfg["quarters"])]
    merge_day = date.fromisoformat(cfg["merge_on"])

    # ---- mergers: a small municipality absorbed by its largest neighbour
    r = keyed(seed, "mergers")
    small = [m for m in ms if m.kind == "gemeinde" and m.population < 2500 and nb[m.ags]]
    picks = r.choice(len(small), size=cfg["mergers"], replace=False)
    changes: list[AgsChange] = []
    gone: set[str] = set()
    pop = {m.ags: m.population for m in ms}
    for i in sorted(picks):
        old = small[int(i)].ags
        cands = [a for a in nb[old] if a not in gone and a not in {c.old for c in changes}]
        if not cands or old in {c.new for c in changes}:
            continue
        new = max(cands, key=lambda a: pop[a])
        changes.append(AgsChange(old, new, merge_day))
        gone.add(old)
    succ = {c.old: c.new for c in changes}

    def on_boundaries(p: Period) -> list[str]:
        return [m.ags for m in ms if not (m.ags in succ and merge_day <= p.end)]

    # ---- latent rates
    ind_cfg: dict[str, dict[str, Any]] = cfg["indicators"]
    kreise = sorted({m.kreis for m in ms})
    rates: dict[str, dict[str, float]] = {}
    for ind, ic in ind_cfg.items():
        rr = keyed(seed, "rates", ind)
        keff = dict(zip(kreise, rr.normal(0, ic["kreis_sd"], len(kreise)), strict=True))
        rates[ind] = {m.ags: ic["rate"] * float(np.exp(keff[m.kreis] + rr.normal(0, ic["muni_sd"]))) for m in ms}

    # ---- stories
    stories: list[Story] = []
    sc = cfg["stories"]
    for ind, ic in ind_cfg.items():
        for qi, p in enumerate(periods):
            if qi < sc["from_quarter"]:
                continue
            rs = keyed(seed, "stories", ind, str(p))
            keys = on_boundaries(p)
            exp_now = {a: _expected(a, ind, ic, rates, pop, succ, merge_day, p, qi) for a in keys}
            cands = [a for a in keys if exp_now[a] >= sc["min_expected"] and not any(s.key == a and s.indicator == ind for s in stories)]
            for _ in range(int(rs.poisson(sc["municipal_per_release"]))):
                if not cands:
                    break
                a = cands[int(rs.integers(len(cands)))]
                cands.remove(a)
                f = float(np.exp(rs.uniform(np.log(sc["factor"][0]), np.log(sc["factor"][1]))))
                f = f if rs.random() < sc["share_up"] else 1 / f
                stories.append(Story(ind, "gemeinde", a, p, int(rs.integers(1, sc["max_quarters"] + 1)), f))
            for _ in range(int(rs.poisson(sc["kreis_per_release"]))):
                k = kreise[int(rs.integers(len(kreise)))]
                f = float(np.exp(rs.uniform(np.log(sc["kreis_factor"][0]), np.log(sc["kreis_factor"][1]))))
                f = f if rs.random() < sc["share_up"] else 1 / f
                stories.append(Story(ind, "kreis", k, p, 1, f))

    # ---- counts, files
    releases: list[Release] = []
    layouts = cfg["phrases"]
    for ind, ic in ind_cfg.items():
        prev_printed: dict[str, float | None] | None = None
        for qi, p in enumerate(periods):
            rc = keyed(seed, "counts", ind, str(p))
            raw_counts: dict[str, float] = {}
            for m in ms:
                mu = rates[ind][m.ags] * m.population / 1000 * (ic["trend"] ** (qi / 4))
                for s in stories:
                    if (
                        s.indicator == ind
                        and s.active(p)
                        and (
                            (s.level == "gemeinde" and (s.key == m.ags or s.key == succ.get(m.ags)))
                            or (s.level == "kreis" and s.key == m.kreis)
                        )
                    ):
                        mu *= s.factor
                shape = 1 / ic["overdispersion"]
                raw_counts[m.ags] = float(rc.poisson(rc.gamma(shape, mu / shape)))
            true_values: dict[str, float] = {}
            for a in on_boundaries(p):
                true_values[a] = raw_counts[a] + sum(raw_counts[o] for o, n in succ.items() if n == a and merge_day <= p.end)
            printed: dict[str, float | None] = {a: (None if 0 < v < ic.get("suppress_below", 0) else v) for a, v in true_values.items()}

            rd = keyed(seed, "drift", ind, str(p))
            drift = None
            if qi > 0 and rd.random() < cfg["drift"]["share"]:
                kinds = [k for k in cfg["drift"]["kinds"] if k in layouts["drift_kinds"][ic["format"]]]
                w = np.array([cfg["drift"]["kinds"][k] for k in kinds], dtype=float)
                drift = str(kinds[int(rd.choice(len(kinds), p=w / w.sum()))])
            if drift == "stale" and prev_printed is not None:
                # last quarter's file under this quarter's name; a merger in between would make keys differ, so the
                # office only does this when the boundaries are the same
                if set(prev_printed) == set(printed):
                    file_values = dict(prev_printed)
                else:
                    drift = None
                    file_values = printed
            else:
                file_values = printed
            meant = file_values
            truth_for_file = true_values
            raw = render(ic, layouts, p, file_values, ms, drift, rd)
            releases.append(Release(ic["source"], ind, p, ic["format"], raw, drift, _publish_day(p), truth_for_file, meant, printed))
            prev_printed = printed

    changes_raw = render_changes(changes, ms, layouts)
    return World(cfg, seed, ms, nb, changes, changes_raw, releases, stories, periods)


def _publish_day(p: Period) -> date:
    """Offices publish about six weeks after the quarter ends."""
    nxt = p.shift(1).start
    return date(nxt.year, nxt.month, 15) if nxt.month > 1 else date(nxt.year, 2, 15)


def _expected(
    a: str,
    ind: str,
    ic: dict[str, Any],
    rates: dict[str, dict[str, float]],
    pop: dict[str, int],
    succ: dict[str, str],
    merge_day: date,
    p: Period,
    qi: int,
) -> float:
    parts = [a] + [o for o, n in succ.items() if n == a and merge_day <= p.end]
    return float(sum(rates[ind][x] * pop[x] / 1000 for x in parts) * (ic["trend"] ** (qi / 4)))


# ------------------------------------------------------------------------------------------------- file layouts


def _cell(v: float | None, thousands_en: bool = False) -> str:
    if v is None:
        return "."
    if v == 0:
        return "–"
    if thousands_en and v >= 1000:
        return f"{v:,.0f}"
    return fmt_de(v)


def render(
    ic: dict[str, Any],
    layouts: dict[str, Any],
    p: Period,
    values: dict[str, float | None],
    ms: list[SimMunicipality],
    drift: str | None,
    r: np.random.Generator,
) -> bytes:
    L = layouts[ic["format"]]
    names = {m.ags: m.name for m in ms}
    kname = layouts["kreis_names"]
    keys = sorted(values)
    if drift == "truncated":
        cut = int(len(keys) * 0.7)
        keys = keys[:cut]
    unit = L["unit"]
    scale = 1.0
    if drift == "unknown_unit":
        unit, scale = L["unknown_unit"], 1000.0
    if drift == "known_unit_thousands":
        unit, scale = L["thousands_unit"], 1000.0
    en = drift == "english_thousands"

    def show(v: float | None) -> str:
        if v is None or scale == 1.0:
            return _cell(v, en)
        return fmt_de(v / scale, 3) if v else "–"

    title = ic["title"]
    if ic["format"] == "csv":
        value_col = ic["column"]
        header = ["Gemeindeschlüssel", "Gemeinde", value_col]
        extra = drift == "extra_column"
        swapped = drift == "swapped_columns"
        sep = "," if drift == "comma_separator" else ";"
        if extra:
            header = ["Gemeindeschlüssel", "Gemeinde", L["extra_column"], value_col]
        if swapped:
            header = ["Gemeindeschlüssel", value_col, "Gemeinde"]
        lines = [
            L["publisher"],
            f"Tabelle: {title} nach Gemeinden",
            f"Berichtszeitraum: {p.german()}",
            f"Einheit: {unit}",
            f"Gebietsstand: {p.end.strftime('%d.%m.%Y')}",
            sep.join(header),
        ]

        def put(cells: list[str]) -> None:
            if swapped:
                cells = [cells[0], cells[-1], *cells[1:-1]]
            if sep == ",":
                cells = [f'"{c}"' if "," in c or " " in c else c for c in cells]
            lines.append(sep.join(cells))

        by_k: dict[str, list[str]] = {}
        for a in keys:
            by_k.setdefault(a[:5], []).append(a)
        for k in sorted(by_k):
            for a in by_k[k]:
                row = [a, names[a], show(values[a])]
                if extra:
                    row.insert(2, fmt_de(float(r.integers(0, 50))))
                put(row)
            if ic.get("kreis_rows"):
                tot = None if any(values[a] is None for a in by_k[k]) else sum(values[a] or 0 for a in by_k[k])
                row = [k, f"{kname.get(k, k)} insgesamt", show(tot)]
                if extra:
                    row.insert(2, "–")
                put(row)
        lines += [f"Quelle: {L['publisher']}", L["footnote"]]
        return ("\n".join(lines) + "\n").encode("utf-8")

    if ic["format"] == "json":
        field = "wert" if drift != "renamed_field" else L["renamed_field"]
        data = []
        for a in keys:
            v = values[a]
            item: dict[str, Any] = {"ags": a, "name": names[a]}
            if v is None:
                item[field], item["kennzeichen"] = None, "."
            elif scale != 1.0:
                item[field] = round(v / scale, 3)
            elif en and v >= 1000:
                item[field] = f"{v:,.0f}"
            else:
                item[field] = int(v)
            data.append(item)
        doc = {
            "meta": {"titel": title, "zeitraum": str(p), "einheit": unit, "herausgeber": L["publisher"]},
            "daten": data,
        }
        return json.dumps(doc, ensure_ascii=False).encode("utf-8")

    # html
    cols = ["Schlüssel", "Gemeinde", ic["column"]]
    extra = drift == "extra_column"
    swapped = drift == "swapped_columns"
    if extra:
        cols = ["Schlüssel", "Gemeinde", L["extra_column"], ic["column"]]
    if swapped:
        cols = ["Schlüssel", ic["column"], "Gemeinde"]
    rows = []
    for a in keys:
        cells = [a, names[a], show(values[a])]
        if extra:
            cells.insert(2, fmt_de(float(r.integers(0, 40))))
        if swapped:
            cells = [a, show(values[a]), names[a]]
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    html = (
        f"<html><head><title>{title}</title></head><body><h1>{L['publisher']}</h1>"
        f'<table class="statistik"><caption>{title} nach Gemeinden, {p.german()} ({unit})</caption>'
        f"<thead><tr>{''.join(f'<th>{c}</th>' for c in cols)}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
        f'<p class="fussnote">{L["footnote"]}</p></body></html>'
    )
    return html.encode("utf-8")


def render_changes(changes: list[AgsChange], ms: list[SimMunicipality], layouts: dict[str, Any]) -> bytes:
    names = {m.ags: m.name for m in ms}
    lines = [
        layouts["csv"]["publisher"],
        "Tabelle: Gebietsänderungen",
        "Alter Schlüssel;Alte Gemeinde;Neuer Schlüssel;Neue Gemeinde;Wirksam ab;Art",
    ]
    for c in changes:
        lines.append(f"{c.old};{names[c.old]};{c.new};{names[c.new]};{c.valid_from.strftime('%d.%m.%Y')};Eingliederung")
    return ("\n".join(lines) + "\n").encode("utf-8")
