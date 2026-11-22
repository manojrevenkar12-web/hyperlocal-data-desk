"""Scores what a design published against what the world knows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from world import World

from .play import Played, is_true_lead


@dataclass
class Score:
    releases: int
    budget_leads: int  # leads within the reporters' capacity, strong and watch list together
    budget_found: int  # stories among them
    leads: int
    true_leads: int
    stories_found: int
    stories: int
    wrong_notes: int
    refused_drafts: int
    texts: int
    texts_wrong: int
    broken_published: int
    drifts: int
    quarantines: int
    false_quarantines: int
    hand_fixes: int
    delay_days: int
    hours: float


def score(w: World, pl: Played, lab: dict[str, Any]) -> Score:
    from_q = w.periods[w.cfg["stories"]["from_quarter"]]
    found: set[int] = set()
    budget_found: set[int] = set()
    true = 0
    strong = [ld for ld in pl.leads if ld.strong]
    for ld in pl.leads:
        i = is_true_lead(w, ld)
        if i is not None:
            budget_found.add(i)
            if ld.strong:
                true += 1
                found.add(i)
    stories = sum(1 for s in w.stories if from_q <= s.start)
    truth = {(r.indicator, r.period): r for r in w.releases}
    broken = 0
    for pr in pl.releases:
        r = truth[(pr.indicator, pr.period)]
        if r.drift is None or pr.quarantined:
            continue
        diff = sum(
            1 for a, v in pr.values.items() if v is not None and r.clean.get(a) is not None and abs(v - (r.true_values.get(a) or 0)) > 0.5
        )
        if diff > 0.01 * max(1, len(pr.values)) or len(pr.values) < 0.95 * len(r.true_values):
            broken += 1
    wrong_notes = sum(1 for ld in strong if ld.note_wrong)
    hours = (
        len(strong) * lab["hours_per_lead"]
        + (pl.quarantines + pl.hand_fixes) * lab["hours_per_quarantine"]
        + (wrong_notes + broken) * lab["wrong_number_hours"]
    )
    return Score(
        releases=len(pl.releases),
        budget_leads=len(pl.leads),
        budget_found=len(budget_found),
        leads=len(strong),
        true_leads=true,
        stories_found=len(found),
        stories=stories,
        wrong_notes=wrong_notes,
        refused_drafts=sum(1 for ld in strong if ld.note_refused),
        texts=sum(pr.texts for pr in pl.releases),
        texts_wrong=sum(pr.texts_wrong for pr in pl.releases),
        broken_published=broken,
        drifts=sum(1 for r in w.releases if r.drift),
        quarantines=pl.quarantines,
        false_quarantines=pl.false_quarantines,
        hand_fixes=pl.hand_fixes,
        delay_days=sum(pr.delay_days for pr in pl.releases),
        hours=round(hours, 2),
    )
