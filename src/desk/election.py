"""Election night: municipal results arrive one by one, and texts for every municipality and district go out live.

The trap: villages count first and cities last. At 19:30 the counted votes lean rural, so the party that is strong
in villages "leads" almost everywhere, and a text that says so is wrong by 22:00. The desk projects each district
from the swing seen in the municipalities that have reported, applied to last election's result in those that have
not, with an interval from the spread of those swings. It names a winner only when the interval clears, and its
texts say "liegt nach Auszählung von 12 der 40 Gemeinden vorn" until then.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import cast

import numpy as np

PARTIES = ["CDU", "GRÜNE", "AfD", "SPD", "FDP", "Sonstige"]


@dataclass
class Report:
    ags: str
    minute: int  # minutes after 18:00
    eligible: int
    votes: dict[str, int]  # valid votes per party

    @property
    def valid(self) -> int:
        return sum(self.votes.values())


@dataclass
class Previous:
    eligible: int
    votes: dict[str, int]

    def shares(self) -> np.ndarray:
        v = np.array([self.votes[p] for p in PARTIES], dtype=float)
        return cast(np.ndarray, v / max(float(v.sum()), 1.0))


@dataclass
class Call:
    kreis: str
    minute: int | None  # when a winner was named, None while open
    winner: str | None
    leader_now: str  # leader in counted votes
    projected: dict[str, float] = field(default_factory=dict)
    margin_low: float = 0.0  # lower bound of the projected lead over the runner-up, share points
    reported: int = 0
    municipalities: int = 0


@dataclass
class ElectionSettings:
    z: float = 2.58  # interval width for calling a district
    min_reported: int = 3  # municipalities that must have reported before any projection
    min_share_counted: float = 0.15  # share of the district's expected votes counted before a call
    hold_swing: float = 0.20  # a party moving more than this share since last time: hold the report and ask
    hold_minutes: int = 30  # a held report nobody corrected is taken after this long
    hold: bool = True


def project(
    kreis_munis: list[str],
    reports: dict[str, Report],
    prev: dict[str, Previous],
    land_reports: dict[str, Report],
    s: ElectionSettings,
) -> tuple[dict[str, float], float, str | None]:
    """Projected district shares, the lower bound of the leader's margin, and the projected leader."""
    reported = [a for a in kreis_munis if a in reports]
    if len(reported) < min(s.min_reported, len(kreis_munis)):
        return {}, -1.0, None

    # swings of reported municipalities in this district; the Land's swings fill in when the district has few
    def swing(a: str, r: Report) -> np.ndarray:
        v = np.array([r.votes[p] for p in PARTIES], dtype=float)
        return cast(np.ndarray, v / max(float(v.sum()), 1.0) - prev[a].shares())

    own = np.array([swing(a, reports[a]) for a in reported])
    w_own = np.array([prev[a].eligible for a in reported], dtype=float)
    land = np.array([swing(a, r) for a, r in land_reports.items()]) if land_reports else own
    k = len(reported)
    blend = k / (k + 5)  # shrink the district's swing towards the Land's when few have reported
    mean_swing = blend * np.average(own, axis=0, weights=w_own) + (1 - blend) * land.mean(axis=0)
    spread = np.vstack([own, land]).std(axis=0)

    counted = np.zeros(len(PARTIES))
    projected = np.zeros(len(PARTIES))
    var = np.zeros(len(PARTIES))
    total_expected = 0.0
    for a in kreis_munis:
        p = prev[a]
        expected_valid = sum(p.votes.values()) * (p.eligible and 1.0)
        total_expected += expected_valid
        if a in reports:
            v = np.array([reports[a].votes[q] for q in PARTIES], dtype=float)
            counted += v
            projected += v
        else:
            sh = np.clip(p.shares() + mean_swing, 0, 1)
            projected += sh * expected_valid
            var += (spread**2) * expected_valid**2
    tot = projected.sum()
    shares = projected / tot
    sd = np.sqrt(var) / tot + np.sqrt(np.maximum(shares * (1 - shares), 0) / max(len(reported), 1)) * (
        1 - counted.sum() / max(total_expected, 1)
    )
    order = np.argsort(-shares)
    lead, second = order[0], order[1]
    margin = shares[lead] - shares[second]
    margin_sd = float(np.sqrt(sd[lead] ** 2 + sd[second] ** 2))
    share_counted = counted.sum() / max(total_expected, 1)
    low = margin - s.z * margin_sd if share_counted >= s.min_share_counted else -1.0
    if len(reported) == len(kreis_munis):
        low = margin  # everything counted: the margin is the result
    return {PARTIES[i]: float(shares[i]) for i in range(len(PARTIES))}, float(low), PARTIES[int(lead)]


def counted_leader(kreis_munis: list[str], reports: dict[str, Report]) -> str | None:
    tot: dict[str, int] = defaultdict(int)
    for a in kreis_munis:
        if a in reports:
            for p, v in reports[a].votes.items():
                tot[p] += v
    return max(tot, key=lambda p: tot[p]) if tot else None


class Night:
    """The desk's state on election night: the latest report per municipality and the calls made so far."""

    def __init__(self, munis_by_kreis: dict[str, list[str]], prev: dict[str, Previous], s: ElectionSettings) -> None:
        self.by_kreis = munis_by_kreis
        self.prev = prev
        self.s = s
        self.reports: dict[str, Report] = {}
        self.held: dict[str, Report] = {}  # implausible reports waiting for a correction
        self.calls: dict[str, Call] = {k: Call(k, None, None, "", municipalities=len(v)) for k, v in munis_by_kreis.items()}

    def receive(self, r: Report, minute: int) -> str:
        """A report, or a correction of an earlier one: the newest wins.

        Votes that cannot be (more valid votes than voters) are refused. A party moving more than `hold_swing` since
        the last election is held: a swapped column in a municipal office's entry looks exactly like that.
        """
        if r.valid > r.eligible or any(v < 0 for v in r.votes.values()):
            return "refused"
        if self.s.hold and r.ags in self.prev:
            prev = self.prev[r.ags].shares()
            now = np.array([r.votes[p] for p in PARTIES], dtype=float) / max(r.valid, 1)
            if float(np.max(np.abs(now - prev))) > self.s.hold_swing:
                self.held[r.ags] = Report(r.ags, minute, r.eligible, r.votes)
                self.reports.pop(r.ags, None)
                return "held"
        self.held.pop(r.ags, None)
        self.reports[r.ags] = r
        return "used"

    def release_held(self, minute: int) -> None:
        for a, r in list(self.held.items()):
            if minute - r.minute >= self.s.hold_minutes:
                self.reports[a] = r
                del self.held[a]

    def update(self, minute: int) -> list[Call]:
        self.release_held(minute)
        changed = []
        for k, ms in self.by_kreis.items():
            c = self.calls[k]
            shares, low, lead = project(ms, self.reports, self.prev, self.reports, self.s)
            c.projected, c.margin_low = shares, low
            c.reported = sum(1 for a in ms if a in self.reports)
            c.leader_now = counted_leader(ms, self.reports) or ""
            if c.winner is None and lead is not None and low > 0:
                c.winner, c.minute = lead, minute
                changed.append(c)
        return changed

    def text(self, k: str, name: str) -> str:
        """The live district text: a winner only once called, otherwise who leads in what has been counted."""
        c = self.calls[k]
        if c.winner:
            return f"Im Landkreis {name} hat die {c.winner} nach unserer Hochrechnung die meisten Stimmen."
        if not c.reported:
            return f"Aus dem Landkreis {name} liegen noch keine Ergebnisse vor."
        return (
            f"Im Landkreis {name} liegt die {c.leader_now} nach Auszählung von {c.reported} der "
            f"{c.municipalities} Gemeinden vorn. Ein Sieger steht noch nicht fest."
        )
