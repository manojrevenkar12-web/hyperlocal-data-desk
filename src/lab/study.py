"""The study: every design on the same worlds (same seeds, same files, same model mistakes), scored against the
truth, with 95% bootstrap intervals over seeds and the gates in config/gates.json. The held-out world runs once.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from world import generate, load_config

from .night import DESIGNS as NIGHT_DESIGNS
from .night import NightScore, night_for, play_night
from .play import Design, Played, load_designs, play
from .score import score

ROOT = Path(__file__).resolve().parents[2]


class LockedError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("reports/heldout.lock exists: the held-out study runs once. Its numbers are in reports/heldout.json")


def _seed_run(args: tuple[str, int]) -> dict[str, Any]:
    which, seed = args
    cfg = load_config(which)
    lab = json.loads((ROOT / "config" / "lab.json").read_text(encoding="utf-8"))
    desk_cfg = json.loads((ROOT / "config" / "desk.json").read_text(encoding="utf-8"))
    w = generate(cfg, seed)
    out: dict[str, Any] = {"seed": seed, "scores": {}, "night": {}, "stories": len(w.stories)}
    played: dict[str, Played] = {}
    for d in load_designs(ROOT):
        pl = play(ROOT, w, d, lab)
        played[d.name] = pl
        out["scores"][d.name] = asdict(score(w, pl, lab))
    ew = night_for(w, seed)
    nights: dict[str, NightScore] = {}
    for nd in NIGHT_DESIGNS:
        ns = play_night(w, ew, nd, desk_cfg["election"], keep_frames=nd in {"desk", "counted_half"})
        nights[nd] = ns
        out["night"][nd] = {
            "wrong_calls": ns.wrong_calls,
            "uncalled": ns.uncalled,
            "districts": ns.districts,
            "call_minutes": ns.call_minutes,
            "wrong_figures_minutes": ns.wrong_figures_minutes,
        }
    if seed == min(json.loads((ROOT / "config" / "seeds.json").read_text())[which]):
        out["showcase"] = showcase(w, played, nights, ew)
    return out


# ------------------------------------------------------------------------------------------------- metrics


def _sum(ss: list[dict[str, Any]], k: str) -> float:
    return float(sum(s[k] for s in ss))


Metric = Callable[[list[dict[str, Any]]], float]

QUARTER_METRICS: dict[str, Metric] = {
    "stories_found": lambda ss: _sum(ss, "stories_found") / len(ss),
    "budget_found": lambda ss: _sum(ss, "budget_found") / len(ss),
    "precision": lambda ss: _sum(ss, "true_leads") / max(1.0, _sum(ss, "leads")),
    "leads_per_release": lambda ss: _sum(ss, "leads") / max(1.0, _sum(ss, "releases")) * 4 / 4,
    "hours_per_story": lambda ss: _sum(ss, "hours") / max(1.0, _sum(ss, "stories_found")),
    "wrong_texts_per_1000": lambda ss: 1000 * _sum(ss, "texts_wrong") / max(1.0, _sum(ss, "texts")),
    "wrong_notes_per_100": lambda ss: 100 * _sum(ss, "wrong_notes") / max(1.0, _sum(ss, "leads")),
    "broken_published": lambda ss: _sum(ss, "broken_published") / len(ss),
    "false_quarantines": lambda ss: _sum(ss, "false_quarantines") / len(ss),
    "quarantines": lambda ss: _sum(ss, "quarantines") / len(ss),
}

NIGHT_METRICS: dict[str, Metric] = {
    "wrong_calls": lambda ns: float(sum(n["wrong_calls"] for n in ns)) / len(ns),
    "median_call_minute": lambda ns: (
        float(np.median([m for n in ns for m in n["call_minutes"]])) if any(n["call_minutes"] for n in ns) else float("nan")
    ),
    "wrong_figures_minutes": lambda ns: float(sum(n["wrong_figures_minutes"] for n in ns)) / len(ns),
    "uncalled": lambda ns: float(sum(n["uncalled"] for n in ns)) / len(ns),
}


def _rng(key: str) -> np.random.Generator:
    h = 0
    for ch in key.encode():
        h = (h * 131 + ch) % (1 << 63)
    return np.random.default_rng(h)


def bootstrap(items: list[Any], f: Metric, reps: int, key: str) -> dict[str, float]:
    v = f(items)
    if len(items) < 2 or reps == 0:
        return {"value": round(v, 4), "lo": round(v, 4), "hi": round(v, 4)}
    r = _rng(key)
    vals = [f([items[int(i)] for i in r.integers(0, len(items), len(items))]) for _ in range(reps)]
    vals = [x for x in vals if not math.isnan(x)]
    return {
        "value": round(v, 4),
        "lo": round(float(np.percentile(vals, 2.5)), 4),
        "hi": round(float(np.percentile(vals, 97.5)), 4),
    }


# ------------------------------------------------------------------------------------------------- gates


def _r3(x: float) -> float:
    return round(x, 3)


def gates(spec: dict[str, Any], designs: list[dict[str, Any]], night: list[dict[str, Any]]) -> list[dict[str, Any]]:
    v = {d["name"]: {k: s["value"] for k, s in d["stats"].items()} for d in designs}
    nv = {d["name"]: {k: s["value"] for k, s in d["stats"].items()} for d in night}
    desk = v["desk"]
    best_other = max(v["spreadsheet"]["budget_found"], v["model_alone"]["budget_found"])
    out = [
        ("Share of strong leads that are real stories", "at least", spec["precision_min"], _r3(desk["precision"])),
        (
            "Stories in the top 8 per release, against the better baseline",
            "at least",
            spec["budget_found_share_min"],
            _r3(desk["budget_found"] / max(best_other, 1e-9)),
        ),
        (
            "Reporter hours per story, against a model alone",
            "at most",
            spec["hours_per_story_share_max"],
            _r3(desk["hours_per_story"] / max(v["model_alone"]["hours_per_story"], 1e-9)),
        ),
        (
            "Automated texts with a wrong number, per 1,000",
            "at most",
            spec["wrong_texts_per_1000_max"],
            _r3(desk["wrong_texts_per_1000"]),
        ),
        (
            "Lead notes with a wrong number, per 100",
            "at most",
            spec["wrong_notes_per_100_max"],
            _r3(desk["wrong_notes_per_100"]),
        ),
        (
            "Broken files that reached readers, per season",
            "at most",
            spec["broken_published_max"],
            _r3(desk["broken_published"]),
        ),
        (
            "Clean files held in quarantine, per season",
            "at most",
            spec["false_quarantines_max"],
            _r3(desk["false_quarantines"]),
        ),
        (
            "Election night: districts called for the wrong party",
            "at most",
            spec["wrong_calls_max"],
            _r3(nv["desk"]["wrong_calls"]),
        ),
        (
            "Election night: minutes saved against waiting for every count",
            "at least",
            spec["call_minutes_saved_min"],
            _r3(nv["wait_for_all"]["median_call_minute"] - nv["desk"]["median_call_minute"]),
        ),
    ]
    return [
        {"name": n, "rule": rule, "want": want, "got": got, "pass": got >= want if rule == "at least" else got <= want}
        for n, rule, want, got in out
    ]


# ------------------------------------------------------------------------------------------------- showcase


def showcase(w: Any, played: dict[str, Played], nights: dict[str, NightScore], ew: Any) -> dict[str, Any]:
    desk = played["desk"]
    sc = dict(desk.showcase)
    # values per municipality for the map: the showcase release, the desk's reading and its expectation
    rel = next((r for r in desk.releases if r.indicator == sc.get("indicator") and str(r.period) == sc.get("period")), None)
    pops = {m.ags: m.population for m in w.municipalities}
    for c in w.changes:
        pops[c.new] = pops.get(c.new, 0) + pops.get(c.old, 0)
    sc["values"] = {a: (None if v is None else round(v / max(pops.get(a, 1), 1) * 1000, 2)) for a, v in (rel.values.items() if rel else [])}
    sc["log"] = [
        {
            "indicator": r.indicator,
            "period": str(r.period),
            "drift": r.drift,
            "quarantined": r.quarantined,
            "delay_days": r.delay_days,
        }
        for r in desk.releases
    ]
    sc["night"] = {k: n.frames for k, n in nights.items() if n.frames}
    sc["kreis_winner"] = ew.kreis_winner
    sc["spreadsheet_leads"] = [
        {"key": ld.key, "observed": ld.observed}
        for ld in played["spreadsheet"].leads
        if ld.indicator == sc.get("indicator") and str(ld.period) == sc.get("period")
    ]
    names = {m.ags: m.name for m in w.municipalities}
    sc["spreadsheet_leads"] = [{**x, "name": names.get(x["key"], x["key"])} for x in sc["spreadsheet_leads"]]
    return sc


# ------------------------------------------------------------------------------------------------- study


def study(root: Path, which: str, log: Any = print, workers: int = 6) -> dict[str, Any]:
    lock = root / "reports" / "heldout.lock"
    if which == "heldout" and lock.exists():
        raise LockedError()
    seeds = json.loads((root / "config" / "seeds.json").read_text())
    spec = json.loads((root / "config" / "gates.json").read_text())
    designs = load_designs(root)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        runs = list(ex.map(_seed_run, [(which, s) for s in seeds[which]]))
    for r in runs:
        log(f"{which} seed {r['seed']} done")
    reps = seeds["bootstrap"]
    rep_designs = []
    for d in designs:
        ss = [r["scores"][d.name] for r in runs]
        rep_designs.append(
            {
                "name": d.name,
                "label": d.label,
                "about": d.about,
                "ablation": d.ablation,
                "kind": d.kind,
                "stats": {k: bootstrap(ss, f, reps, f"{d.name}|{k}") for k, f in QUARTER_METRICS.items()},
                "totals": {k: sum(s[k] for s in ss) for k in ss[0]},
            }
        )
    rep_night = []
    for nd, label in NIGHT_DESIGNS.items():
        ns = [r["night"][nd] for r in runs]
        rep_night.append(
            {
                "name": nd,
                "label": label,
                "stats": {k: bootstrap(ns, f, reps, f"night|{nd}|{k}") for k, f in NIGHT_METRICS.items()},
            }
        )
    cfg = load_config(which)
    report = {
        "world": which,
        "seeds": seeds[which],
        "quarters": cfg["quarters"],
        "municipalities": cfg["municipalities"],
        "indicators": list(cfg["indicators"]),
        "stories_per_seed": sum(r["stories"] for r in runs) / len(runs),
        "designs": rep_designs,
        "night": rep_night,
        "gates": gates(spec, rep_designs, rep_night),
        "showcase": next(r["showcase"] for r in runs if "showcase" in r),
    }
    (root / "reports").mkdir(exist_ok=True)
    (root / "reports" / f"{which}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1, default=_json) + "\n", encoding="utf-8"
    )
    if which == "heldout":
        lock.write_text("The held-out study ran; it does not run again.\n")
    return report


def _json(x: Any) -> Any:
    if isinstance(x, float) and math.isnan(x):
        return None
    return str(x)


def as_design(d: dict[str, Any]) -> Design:
    return Design(**d)
