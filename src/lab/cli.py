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
                f"{d['name']:24s} {st['stories_found']:5.1f} {st['budget_found']:5.1f} {st['precision']:5.2f} {st['hours_per_story']:8.1f}"
                f" {st['wrong_texts_per_1000']:12.1f} {st['wrong_notes_per_100']:14.1f} {st['broken_published']:7.1f} {st['false_quarantines']:7.1f}"
            )
        for d in r["night"]:
            st = {k: v["value"] for k, v in d["stats"].items()}
            print(
                f"night {d['name']:18s} wrong calls {st['wrong_calls']:.2f}  median call minute {st['median_call_minute']}  wrong-figure minutes {st['wrong_figures_minutes']:.0f}"
            )
        for g in r["gates"]:
            print(f"  {'PASS' if g['pass'] else 'FAIL'}  {g['name']}: {g['rule']} {g['want']}, got {g['got']}")
        return 0
    if a.cmd == "readme":
        from .readme import readme

        readme(ROOT)
        return 0
    if a.cmd == "web-data":
        from .webdata import web_data

        print(web_data(ROOT))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
