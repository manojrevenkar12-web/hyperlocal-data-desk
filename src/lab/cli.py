"""desk study --world dev|heldout | desk readme | desk web-data"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .study import LockedError, study

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="desk")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("study")
    s.add_argument("--world", default="dev", choices=["dev", "heldout"])
    s.add_argument("--workers", type=int, default=6)
    sub.add_parser("readme")
    sub.add_parser("web-data")
    i = sub.add_parser("ingest", help="run one published file through the desk, as n8n does")
    i.add_argument("--source", required=True)
    i.add_argument("--file", required=True)
    i.add_argument("--db", default="data/desk.duckdb")
    i.add_argument("--received", default=None)
    c = sub.add_parser("changes", help="load the official list of boundary changes")
    c.add_argument("--file", required=True)
    c.add_argument("--db", default="data/desk.duckdb")
    a = ap.parse_args(argv)
    if a.cmd == "study":
        try:
            r = study(ROOT, a.world, workers=a.workers)
        except LockedError as e:
            print(e, file=sys.stderr)
            return 3
        print(f"{r['world']} world: {len(r['seeds'])} seeds, {r['municipalities']} municipalities, {r['quarters']} quarters")
        print(f"{'design':24s} found  top8  prec  h/story  wrongtxt/1k  wrongnote/100  broken  falseQ")
        for d in r["designs"]:
            st = {k: v["value"] for k, v in d["stats"].items()}
            print(
                f"{d['name']:24s} {st['stories_found']:5.1f} {st['budget_found']:5.1f} {st['precision']:5.2f}"
                f" {st['hours_per_story']:8.1f} {st['wrong_texts_per_1000']:12.1f} {st['wrong_notes_per_100']:14.1f}"
                f" {st['broken_published']:7.1f} {st['false_quarantines']:7.1f}"
            )
        for d in r["night"]:
            st = {k: v["value"] for k, v in d["stats"].items()}
            print(
                f"night {d['name']:18s} wrong calls {st['wrong_calls']:.2f}  median call minute {st['median_call_minute']}"
                f"  wrong-figure minutes {st['wrong_figures_minutes']:.0f}"
            )
        for g in r["gates"]:
            print(f"  {'PASS' if g['pass'] else 'FAIL'}  {g['name']}: {g['rule']} {g['want']}, got {g['got']}")
        return 0
    if a.cmd == "readme":
        from .readme import readme

        readme(ROOT)
        return 0
    if a.cmd in ("ingest", "changes"):
        return _ingest(a)
    if a.cmd == "web-data":
        from .webdata import web_data

        print(web_data(ROOT))
        return 0
    return 2


def _ingest(a: argparse.Namespace) -> int:
    import json
    import os
    from datetime import date

    from desk.claude import ClaudeWriter
    from desk.domain import Municipality
    from desk.pipeline import Desk
    from desk.store import SqlStore

    url = os.environ.get("DESK_DATABASE_URL")
    store = SqlStore.postgres(url) if url else SqlStore.duckdb(str(ROOT / a.db))
    if not store.municipalities():
        reg = json.loads((ROOT / "data" / "register.json").read_text(encoding="utf-8"))
        store.put_municipalities([Municipality(r["ags"], r["name"], r["population"], r["lon"], r["lat"], r["kind"]) for r in reg])
    key = os.environ.get("ANTHROPIC_API_KEY")
    desk = Desk.from_config(ROOT, store)
    if key:
        desk.writer = ClaudeWriter(key, desk.s.model)
    raw = Path(a.file).read_bytes()
    if a.cmd == "changes":
        print(json.dumps({"changes": len(desk.ingest_changes(raw))}))
        return 0
    o = desk.ingest(a.source, raw, date.fromisoformat(a.received) if a.received else date.today())
    print(
        json.dumps(
            {
                "status": o.status,
                "indicator": o.indicator,
                "period": str(o.period) if o.period else None,
                "problem": o.problem,
                "leads": [
                    {"key": ld.key, "level": ld.level, "observed": ld.observed, "expected": round(ld.expected, 1), "note": n.text}
                    for ld, n in zip(o.leads, o.notes, strict=True)
                ],
                "watch": [{"key": ld.key, "observed": ld.observed, "expected": round(ld.expected, 1)} for ld in o.watch],
            },
            ensure_ascii=False,
        )
    )
    return 0 if o.status == "published" else 4


if __name__ == "__main__":
    raise SystemExit(main())
