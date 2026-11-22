"""Hand-offs to the newsroom's tools: a Datawrapper chart for a release, and the interactive's data files on S3.

Nothing here decides anything; it ships what the pipeline published. Both talk to their APIs through clients that can
be swapped in tests (httpx MockTransport, moto for S3).
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

import httpx

from .numbers import fmt_de


def datawrapper_chart(title: str, indicator_label: str, period: str, rows: list[dict[str, Any]], source: str) -> dict[str, Any]:
    """A choropleth of a release, by municipality key, with the desk's note on withheld cells."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=",")
    w.writerow(["AGS", "Gemeinde", "Wert je 1.000 Einwohner", "Hinweis"])
    for r in rows:
        w.writerow(
            [
                r["ags"],
                r["name"],
                "" if r.get("rate") is None else round(r["rate"], 2),
                "Wert geheim" if r.get("rate") is None else ("Recherchehinweis" if r.get("lead") else ""),
            ]
        )
    withheld = sum(1 for r in rows if r.get("rate") is None)
    return {
        "chart": {
            "title": title,
            "type": "d3-maps-choropleth",
            "metadata": {
                "describe": {"source-name": source, "intro": f"{indicator_label}, {period}, je 1.000 Einwohner", "byline": "Datenteam"},
                "annotate": {"notes": f"In {fmt_de(withheld)} Gemeinden hält das Amt den Wert geheim (weniger als 3)." if withheld else ""},
                "visualize": {"basemap": "germany-baden-wuerttemberg-gemeinden", "map-key-attr": "AGS"},
            },
        },
        "csv": buf.getvalue(),
    }


def publish_datawrapper(
    payload: dict[str, Any], token: str, client: httpx.Client | None = None, base_url: str = "https://api.datawrapper.de/v3"
) -> str:
    """Create the chart, upload its data, publish it; returns the chart id."""
    c = client or httpx.Client(timeout=30)
    h = {"Authorization": f"Bearer {token}"}
    created = c.post(f"{base_url}/charts", headers=h, json=payload["chart"])
    created.raise_for_status()
    cid = str(created.json()["id"])
    c.put(f"{base_url}/charts/{cid}/data", headers={**h, "content-type": "text/csv"}, content=payload["csv"].encode()).raise_for_status()
    c.post(f"{base_url}/charts/{cid}/publish", headers=h).raise_for_status()
    return cid


def publish_s3(files: dict[str, Any], bucket: str, prefix: str, s3: Any) -> list[str]:
    """Upload the interactive's data files. JSON is cached briefly so a corrected release reaches readers quickly."""
    keys = []
    for name, content in sorted(files.items()):
        body = content if isinstance(content, bytes) else json.dumps(content, ensure_ascii=False).encode()
        ctype = "application/geo+json" if name.endswith(".geojson") else "application/json" if name.endswith(".json") else "text/csv"
        key = f"{prefix.rstrip('/')}/{name}"
        s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType=ctype, CacheControl="public, max-age=300")
        keys.append(key)
    return keys
