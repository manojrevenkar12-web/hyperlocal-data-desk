"""Source adapters. Every adapter meets one contract: raw bytes in, a ParsedRelease out, or a ParseError that says
what the file looked like. An adapter never guesses: an unknown column, unit or number format is an error, and the
release goes to quarantine instead of into a story.

Three layouts a newsroom meets every week are covered: a statistical office's CSV with preamble and footnotes, a JSON
open-data API, and an HTML table scraped from a press page.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from bs4 import BeautifulSoup

from .domain import AGS_RE, KREIS_RE, Observation, Period
from .numbers import NumberFormatError, parse_cell


class ParseError(ValueError):
    pass


@dataclass
class SourceSpec:
    """How the desk expects a source to look; from config/sources.json."""

    id: str
    indicator: str
    format: str  # csv | json | html
    unit: str  # the unit the desk expects, e.g. "Anzahl"
    decimal: str = ","
    columns: dict[str, list[str]] = field(default_factory=dict)  # role -> accepted header names
    units: dict[str, float] = field(default_factory=dict)  # unit label -> factor to the expected unit

    @staticmethod
    def from_dict(d: dict[str, Any]) -> SourceSpec:
        return SourceSpec(**d)


@dataclass
class ParsedRelease:
    source: str
    period: Period
    unit_label: str
    factor: float  # values were multiplied by this to reach the expected unit
    rows: list[Observation]  # municipalities (8-digit keys)
    kreis_totals: dict[str, float | None]  # district subtotal rows the file also carried
    land_total: float | None
    header: list[str]
    footnotes: list[str] = field(default_factory=list)
    duplicate_keys: list[str] = field(default_factory=list)


class Adapter(Protocol):
    def parse(self, raw: bytes, spec: SourceSpec) -> ParsedRelease: ...


def _role_index(header: list[str], spec: SourceSpec) -> dict[str, int]:
    norm = [h.strip().lower() for h in header]
    out: dict[str, int] = {}
    for role, names in spec.columns.items():
        hits = [i for i, h in enumerate(norm) if h in {n.lower() for n in names}]
        if len(hits) != 1:
            raise ParseError(f"column for {role!r}: expected one of {names}, found header {header}")
        out[role] = hits[0]
    return out


def _unit_factor(label: str, spec: SourceSpec) -> float:
    key = label.strip()
    if key == spec.unit:
        return 1.0
    if key in spec.units:
        return spec.units[key]
    raise ParseError(f"unit {key!r} is neither {spec.unit!r} nor a known conversion {sorted(spec.units)}")


def _rows(
    cells: list[tuple[str, str]], spec: SourceSpec, factor: float, period: Period
) -> tuple[list[Observation], dict[str, float | None], float | None, list[str]]:
    rows: list[Observation] = []
    kreise: dict[str, float | None] = {}
    land: float | None = None
    seen: set[str] = set()
    dup: list[str] = []
    for key, cell in cells:
        k = key.strip()
        try:
            v, flag = parse_cell(cell, decimal=spec.decimal)
        except NumberFormatError as e:
            raise ParseError(f"row {k}: {e}") from e
        v = None if v is None else v * factor
        if AGS_RE.match(k):
            if k in seen:
                dup.append(k)
                continue
            seen.add(k)
            rows.append(Observation(k, period, v, flag))
        elif KREIS_RE.match(k):
            kreise[k] = v
        elif k == "08":
            land = v
        else:
            raise ParseError(f"row key {k!r} is not a municipality, district or Land key")
    return rows, kreise, land, dup


class CsvAdapter:
    """A statistical office's CSV: 'Key: value' preamble lines, a ';' header, data rows, then source and footnotes."""

    def parse(self, raw: bytes, spec: SourceSpec) -> ParsedRelease:
        text = raw.decode("utf-8-sig")
        lines = [ln for ln in text.splitlines() if ln.strip()]
        meta: dict[str, str] = {}
        i = 0
        while i < len(lines) and ";" not in lines[i]:
            if ":" in lines[i]:
                k, v = lines[i].split(":", 1)
                meta[k.strip().lower()] = v.strip()
            i += 1
        if i == len(lines):
            raise ParseError("no header row with ';' found")
        header = [h.strip() for h in lines[i].split(";")]
        idx = _role_index(header, spec)
        period_text = meta.get("berichtszeitraum") or meta.get("zeitraum")
        if not period_text:
            raise ParseError(f"no period in the preamble {sorted(meta)}")
        period = Period.parse(period_text)
        unit = meta.get("einheit", "")
        factor = _unit_factor(unit, spec)
        cells: list[tuple[str, str]] = []
        notes: list[str] = []
        for ln in lines[i + 1 :]:
            parts = [p.strip() for p in ln.split(";")]
            if not re.fullmatch(r"\d{2,8}", parts[0]):
                notes.append(ln.strip())  # source line and footnotes; they may contain ';' themselves
                continue
            if len(parts) != len(header):
                raise ParseError(f"row has {len(parts)} cells, header has {len(header)}: {ln!r}")
            cells.append((parts[idx["ags"]], parts[idx["value"]]))
        rows, kreise, land, dup = _rows(cells, spec, factor, period)
        return ParsedRelease(spec.id, period, unit, factor, rows, kreise, land, header, notes, dup)


class JsonAdapter:
    """An open-data API: {"meta": {"zeitraum", "einheit"}, "daten": [{"ags", "name", "wert", "kennzeichen"}]}."""

    def parse(self, raw: bytes, spec: SourceSpec) -> ParsedRelease:
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ParseError(f"not JSON: {e}") from e
        meta = doc.get("meta")
        data = doc.get("daten")
        if not isinstance(meta, dict) or not isinstance(data, list):
            raise ParseError(f"expected 'meta' and 'daten', found {sorted(doc) if isinstance(doc, dict) else type(doc)}")
        period = Period.parse(str(meta.get("zeitraum", "")))
        unit = str(meta.get("einheit", ""))
        factor = _unit_factor(unit, spec)
        header = sorted({k for row in data for k in row})
        idx_names = {role: names for role, names in spec.columns.items()}
        cells: list[tuple[str, str]] = []
        for row in data:
            key = _pick(row, idx_names["ags"])
            val = _pick(row, idx_names["value"])
            sign = row.get("kennzeichen")
            if val is None and isinstance(sign, str):
                val = sign
            if isinstance(val, (int, float)):
                # a JSON number has no separator to misread; render it the way the source declares
                val = f"{val}".replace(".", ",") if spec.decimal == "," else f"{val}"
            cells.append((str(key), str(val)))
        rows, kreise, land, dup = _rows(cells, spec, factor, period)
        return ParsedRelease(spec.id, period, unit, factor, rows, kreise, land, header, [], dup)


def _pick(row: dict[str, Any], names: list[str]) -> Any:
    hits = [n for n in names if n in row]
    if len(hits) != 1:
        raise ParseError(f"field: expected one of {names}, found {sorted(row)}")
    return row[hits[0]]


class HtmlAdapter:
    """A table scraped from a press page: <caption>Title, 3. Quartal 2026 (Einheit)</caption> and one row each."""

    def parse(self, raw: bytes, spec: SourceSpec) -> ParsedRelease:
        soup = BeautifulSoup(raw, "lxml")
        tables = soup.select("table.statistik")
        if len(tables) != 1:
            raise ParseError(f"expected one table.statistik, found {len(tables)}")
        t = tables[0]
        cap = t.caption.get_text(" ", strip=True) if t.caption else ""
        m = re.search(r"(\d\.\s*Quartal\s+\d{4}).*\(([^)]*)\)\s*$", cap)
        if not m:
            raise ParseError(f"caption without period and unit: {cap!r}")
        period = Period.parse(m.group(1))
        unit = m.group(2)
        factor = _unit_factor(unit, spec)
        header = [th.get_text(strip=True) for th in t.select("thead th")]
        idx = _role_index(header, spec)
        cells: list[tuple[str, str]] = []
        for tr in t.select("tbody tr"):
            tds = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if len(tds) != len(header):
                raise ParseError(f"row has {len(tds)} cells, header has {len(header)}")
            cells.append((tds[idx["ags"]], tds[idx["value"]]))
        notes = [p.get_text(" ", strip=True) for p in soup.select("p.fussnote")]
        rows, kreise, land, dup = _rows(cells, spec, factor, period)
        return ParsedRelease(spec.id, period, unit, factor, rows, kreise, land, header, notes, dup)


ADAPTERS: dict[str, Adapter] = {"csv": CsvAdapter(), "json": JsonAdapter(), "html": HtmlAdapter()}


def parse(raw: bytes, spec: SourceSpec) -> ParsedRelease:
    return ADAPTERS[spec.format].parse(raw, spec)
