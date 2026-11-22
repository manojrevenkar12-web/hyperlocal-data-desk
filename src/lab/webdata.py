"""Writes the files the web app reads: municipal outlines, district outlines and the lab reports.

The outlines are the dev world's simulated municipalities, so the map and the reports describe the same places.
data/register.json is the municipal register the `desk` command line loads into its database.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from shapely.geometry import mapping

from world import geography, load_config


def _round(obj: object) -> object:
    if isinstance(obj, float):
        return round(obj, 4)
    if isinstance(obj, (list, tuple)):
        return [_round(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _round(v) for k, v in obj.items()}
    return obj


def web_data(root: Path) -> str:
    out = root / "web" / "static" / "data"
    out.mkdir(parents=True, exist_ok=True)
    # each world has its own simulated municipalities; the app draws the ones its report describes
    for which in ("dev", "heldout"):
        wms, _ = geography(load_config(which))
        feats = [
            {
                "type": "Feature",
                "properties": {"ags": m.ags, "name": m.name, "kreis": m.kreis, "population": m.population},
                "geometry": _round(mapping(m.outline.simplify(0.0015, preserve_topology=True))),
            }
            for m in wms
        ]
        (out / f"gemeinden-{which}.geojson").write_text(
            json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )
    ms, _ = geography(load_config("dev"))
    shutil.copy(root / "geo" / "bw_kreise.geojson", out / "kreise.geojson")
    for which in ("dev", "heldout"):
        src = root / "reports" / f"{which}.json"
        if src.exists():
            shutil.copy(src, out / f"report-{which}.json")
    reg = [
        {"ags": m.ags, "name": m.name, "population": m.population, "kind": m.kind, "lon": round(m.lon, 5), "lat": round(m.lat, 5)}
        for m in ms
    ]
    (root / "data").mkdir(exist_ok=True)
    (root / "data" / "register.json").write_text(json.dumps(reg, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    return f"wrote the municipal outlines of both worlds and the reports to {out}"
