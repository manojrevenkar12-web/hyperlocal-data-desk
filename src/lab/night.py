"""Plays election night for each design: reports arrive in the world's order, every five minutes the designs update
their district texts, and the lab records when each district was called, for whom, and what the texts showed.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from desk.election import PARTIES, ElectionSettings, Night, Report, counted_leader
from world import World
from world.election import ElectionWorld, generate_election


@dataclass
class NightScore:
    districts: int = 0
    wrong_calls: int = 0
    call_minutes: list[int] = field(default_factory=list)  # minute of each correct call
    uncalled: int = 0
    wrong_figures_minutes: int = 0  # municipality-minutes a wrong (later corrected) result was shown
    frames: list[dict[str, Any]] = field(default_factory=list)  # for the dashboard's replay


DESIGNS = {
    "counted_half": "Call the leader once half the municipalities have counted",
    "wait_for_all": "Call only when every municipality has counted",
    "desk": "Project from the swing and call when the interval clears; hold implausible reports",
    "desk_no_hold": "The desk without holding implausible reports",
}


def play_night(w: World, ew: ElectionWorld, design: str, settings: dict[str, Any], step: int = 5, keep_frames: bool = False) -> NightScore:
    cfg = w.cfg["election"]
    by_kreis: dict[str, list[str]] = defaultdict(list)
    for a in ew.final:
        by_kreis[a[:5]].append(a)
    events: list[tuple[int, Report]] = []
    wrong_first = {r.ags for r in ew.corrections}
    for r in ew.corrections:
        events.append((r.minute, r))
    for a, r in ew.final.items():
        events.append((r.minute + (cfg["correction_delay"] if a in wrong_first else 0), r))
    events.sort(key=lambda e: (e[0], e[1].ags))
    s = ElectionSettings(**{**settings, "hold": design != "desk_no_hold"})
    night = Night(dict(by_kreis), ew.previous, s)
    shown: dict[str, Report] = {}
    calls: dict[str, tuple[int, str]] = {}
    out = NightScore(districts=len(by_kreis))
    i = 0
    for minute in range(0, 361, step):
        while i < len(events) and events[i][0] <= minute:
            night.receive(events[i][1], events[i][0])
            shown[events[i][1].ags] = events[i][1]
            i += 1
        if design.startswith("desk"):
            night.update(minute)
            visible = night.reports
            for k, c in night.calls.items():
                if c.winner and k not in calls:
                    calls[k] = (minute, c.winner)
        else:
            visible = shown
            for k, ms in by_kreis.items():
                done = sum(1 for a in ms if a in shown)
                need = len(ms) if design == "wait_for_all" else (len(ms) + 1) // 2
                if k not in calls and done >= need:
                    calls[k] = (minute, counted_leader(ms, shown) or "")
        out.wrong_figures_minutes += step * sum(1 for a, r in visible.items() if r.votes != ew.final[a].votes)
        if keep_frames and minute % 15 == 0:
            out.frames.append(
                {
                    "minute": minute,
                    "reported": len(visible),
                    "calls": {k: v[1] for k, v in calls.items()},
                    "leaders": {k: (counted_leader(ms, visible) or "") for k, ms in by_kreis.items()},
                }
            )
    for k in by_kreis:
        if k not in calls:
            out.uncalled += 1
        elif calls[k][1] != ew.kreis_winner[k]:
            out.wrong_calls += 1
        else:
            out.call_minutes.append(calls[k][0])
    return out


def night_for(w: World, seed: int) -> ElectionWorld:
    return generate_election(w, w.cfg["election"], seed)


__all__ = ["DESIGNS", "PARTIES", "NightScore", "night_for", "play_night"]
