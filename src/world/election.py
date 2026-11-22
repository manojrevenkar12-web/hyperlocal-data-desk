"""A simulated Landtag election night on the simulated municipalities: last election's results, tonight's true
results, and the order and minute in which municipalities report. Small places report first, cities last.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from desk.election import PARTIES, Previous, Report

from . import World, keyed


@dataclass
class ElectionWorld:
    previous: dict[str, Previous]
    final: dict[str, Report]  # every municipality's final result, with its reporting minute
    corrections: list[Report]  # some municipalities report wrong first, then correct it
    kreis_winner: dict[str, str]


def generate_election(w: World, cfg: dict[str, Any], seed: int) -> ElectionWorld:
    r = keyed(seed, "election")
    ms = [m for m in w.municipalities if m.ags not in {c.old for c in w.changes}]
    pops = {m.ags: m.population for m in w.municipalities}
    for c in w.changes:
        pops[c.new] += pops[c.old]
    kreise = sorted({m.kreis for m in ms})
    k_eff = {k: r.normal(0, cfg["kreis_sd"], len(PARTIES)) for k in kreise}
    k_swing = {k: r.normal(0, cfg["kreis_swing_sd"], len(PARTIES)) for k in kreise}
    land_swing = np.array(cfg["land_swing"])
    base_rural = np.array(cfg["rural"])
    base_urban = np.array(cfg["urban"])
    prev: dict[str, Previous] = {}
    final: dict[str, Report] = {}
    corrections: list[Report] = []
    for m in ms:
        pop = pops[m.ags]
        urban = min(1.0, np.log10(max(pop, 500)) / 5.8) ** 3  # 0 for a hamlet, ~1 for Stuttgart
        logit = np.log(base_rural * (1 - urban) + base_urban * urban) + k_eff[m.kreis] + r.normal(0, cfg["muni_sd"], len(PARTIES))
        sh0 = np.exp(logit) / np.exp(logit).sum()
        eligible = int(pop * 0.76)
        turnout0 = float(np.clip(r.normal(0.66, 0.05), 0.4, 0.9))
        v0 = r.multinomial(int(eligible * turnout0), sh0)
        prev[m.ags] = Previous(eligible, dict(zip(PARTIES, map(int, v0), strict=True)))
        sh1 = np.clip(sh0 + land_swing + k_swing[m.kreis] + r.normal(0, cfg["muni_swing_sd"], len(PARTIES)), 0.002, 1)
        sh1 = sh1 / sh1.sum()
        turnout1 = float(np.clip(turnout0 + r.normal(cfg["turnout_change"], 0.03), 0.4, 0.92))
        v1 = r.multinomial(int(eligible * turnout1), sh1)
        # small places count fast: minutes after 18:00 grow with size, plus noise
        minute = int(np.clip(25 + 38 * np.log10(max(pop, 300) / 300) ** 1.6 + r.exponential(18), 20, 330))
        rep = Report(m.ags, minute, eligible, dict(zip(PARTIES, map(int, v1), strict=True)))
        final[m.ags] = rep
        if r.random() < cfg["correction_share"]:
            wrong = dict(rep.votes)
            a, b = r.choice(len(PARTIES), 2, replace=False)
            wrong[PARTIES[a]], wrong[PARTIES[b]] = wrong[PARTIES[b]], wrong[PARTIES[a]]  # two columns swapped
            corrections.append(Report(m.ags, minute, eligible, wrong))
    winners = {}
    for k in kreise:
        tot = np.zeros(len(PARTIES))
        for m in ms:
            if m.kreis == k:
                tot += np.array([final[m.ags].votes[p] for p in PARTIES])
        winners[k] = PARTIES[int(np.argmax(tot))]
    return ElectionWorld(prev, final, corrections, winners)
