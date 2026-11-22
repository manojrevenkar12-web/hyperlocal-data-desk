"""Simulated municipalities inside the real district outlines: positions, outlines, names and populations.

Names and outlines are invented. A Stadtkreis is one municipality covering its whole district, as in reality.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import MultiPolygon, Point, Polygon, shape
from shapely.ops import unary_union

CITIES = {  # Stadtkreise: (name, population)
    "08111": ("Stuttgart", 633_000),
    "08121": ("Heilbronn", 128_000),
    "08211": ("Baden-Baden", 57_000),
    "08212": ("Karlsruhe", 306_000),
    "08221": ("Heidelberg", 162_000),
    "08222": ("Mannheim", 316_000),
    "08231": ("Pforzheim", 127_000),
    "08311": ("Freiburg im Breisgau", 236_000),
    "08421": ("Ulm", 128_000),
}

_ROOT = [
    "Eber",
    "Wald",
    "Linden",
    "Rot",
    "Sulz",
    "Hirsch",
    "Mühl",
    "Kirch",
    "Stein",
    "Buch",
    "Eich",
    "Hasel",
    "Birken",
    "Erlen",
    "Fels",
    "Hagen",
    "Kalt",
    "Lauter",
    "Mos",
    "Neu",
    "Ried",
    "Schön",
    "Tann",
    "Weil",
    "Wolf",
    "Zell",
    "Bären",
    "Dorn",
    "Ehr",
    "Fisch",
    "Gold",
    "Holz",
    "Ilsen",
    "Kreuz",
    "Lang",
    "Matt",
    "Nuss",
    "Oster",
    "Pfaff",
    "Ross",
    "Salz",
    "Teck",
    "Ulmen",
    "Vogel",
    "Wiesen",
    "Bronn",
    "Hall",
    "Kling",
]
_END = [
    "bach",
    "heim",
    "ingen",
    "hausen",
    "weiler",
    "stetten",
    "dorf",
    "berg",
    "au",
    "feld",
    "hofen",
    "tal",
    "weil",
    "bronn",
    "statt",
    "wang",
    "ach",
    "loch",
]
_PRE = ["Ober", "Unter", "Groß", "Klein", "Alt", "Hohen", "Nieder", "Mittel"]


@dataclass
class SimMunicipality:
    ags: str
    name: str
    kreis: str
    population: int
    lon: float
    lat: float
    outline: Polygon | MultiPolygon
    kind: str


def load_kreise(path: Path) -> list[dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return [
        {
            "ags": f["properties"]["ags"],
            "name": f["properties"]["name"],
            "city": f["properties"]["city"],
            "shape": shape(f["geometry"]),
        }
        for f in doc["features"]
    ]


def _points_in(poly: Polygon | MultiPolygon, n: int, rng: np.random.Generator) -> np.ndarray:
    minx, miny, maxx, maxy = poly.bounds
    pts: list[tuple[float, float]] = []
    tries = 0
    while len(pts) < n and tries < n * 400:
        tries += 1
        x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
        if poly.contains(Point(x, y)):
            pts.append((x, y))
    arr = np.array(pts)
    for _ in range(3):  # Lloyd relaxation: evenly spread centres, cells of similar size
        cells = _cells(arr, poly)
        arr = np.array([[c.centroid.x, c.centroid.y] if not c.is_empty else p for c, p in zip(cells, arr, strict=True)])
    return arr


def _cells(pts: np.ndarray, poly: Polygon | MultiPolygon) -> list[Polygon | MultiPolygon]:
    if len(pts) == 1:
        return [poly]
    minx, miny, maxx, maxy = poly.bounds
    far = 10 * max(maxx - minx, maxy - miny)
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    ghosts = np.array([[cx - far, cy - far], [cx + far, cy - far], [cx - far, cy + far], [cx + far, cy + far]])
    vor = Voronoi(np.vstack([pts, ghosts]))
    out = []
    for i in range(len(pts)):
        region = vor.regions[vor.point_region[i]]
        if -1 in region or not region:
            out.append(Polygon())
            continue
        cell = Polygon([vor.vertices[j] for j in region]).intersection(poly)
        out.append(cell)
    return out


def _name(rng: np.random.Generator, taken: set[str], large: bool) -> str:
    for _ in range(200):
        stem = str(rng.choice(_ROOT)) + str(rng.choice(_END))
        name = stem if large or rng.random() < 0.7 else str(rng.choice(_PRE)) + stem.lower()
        if name not in taken:
            taken.add(name)
            return name
    raise RuntimeError("ran out of names")


def build(kreise: list[dict[str, Any]], total: int, land_population: int, seed: int) -> list[SimMunicipality]:
    rng = np.random.default_rng(seed)
    rural = [k for k in kreise if not k["city"]]
    n_rural = total - (len(kreise) - len(rural))
    areas = np.array([k["shape"].area for k in rural])
    counts = np.maximum(5, np.round(areas / areas.sum() * n_rural)).astype(int)
    while counts.sum() > n_rural:
        counts[int(np.argmax(counts))] -= 1
    while counts.sum() < n_rural:
        counts[int(np.argmin(counts))] += 1

    city_pop = sum(p for _, p in CITIES.values())
    rural_pop = land_population - city_pop
    taken = {n for n, _ in CITIES.values()}
    out: list[SimMunicipality] = []
    for k in kreise:
        ags_k = str(k["ags"])
        poly = k["shape"]
        if k["city"]:
            name, pop = CITIES[ags_k]
            c = poly.representative_point()
            out.append(SimMunicipality(ags_k + "000", name, ags_k, pop, c.x, c.y, poly, "stadtkreis"))
    raw_pops: list[float] = []
    staged: list[tuple[str, np.ndarray, Polygon | MultiPolygon]] = []
    for k, n in zip(rural, counts, strict=True):
        pts = _points_in(k["shape"], int(n), rng)
        cells = _cells(pts, k["shape"])
        for i, (p, cell) in enumerate(zip(pts, cells, strict=True)):
            staged.append((f"{k['ags']}{i + 1:03d}", p, cell))
            raw_pops.append(float(rng.lognormal(mean=8.6, sigma=0.95)))
    scale = rural_pop / sum(raw_pops)
    for (ags, p, cell), rp in zip(staged, raw_pops, strict=True):
        pop = max(250, int(round(rp * scale, -1)))
        out.append(
            SimMunicipality(
                ags,
                _name(rng, taken, pop > 20_000),
                ags[:5],
                pop,
                float(p[0]),
                float(p[1]),
                cell if not cell.is_empty else Point(p).buffer(0.01),
                "stadt" if pop >= 10_000 else "gemeinde",
            )
        )
    out.sort(key=lambda m: m.ags)
    return out


def neighbours(ms: list[SimMunicipality]) -> dict[str, list[str]]:
    """Municipalities whose outlines touch, within the same district."""
    by_k: dict[str, list[SimMunicipality]] = {}
    for m in ms:
        by_k.setdefault(m.kreis, []).append(m)
    out: dict[str, list[str]] = {m.ags: [] for m in ms}
    for group in by_k.values():
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                if a.outline.buffer(1e-6).intersects(b.outline):
                    out[a.ags].append(b.ags)
                    out[b.ags].append(a.ags)
    return out


def land_outline(ms: list[SimMunicipality]) -> Polygon | MultiPolygon:
    return unary_union([m.outline for m in ms])
