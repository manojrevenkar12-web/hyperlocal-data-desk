"""Story leads from a quarterly release: which municipalities and districts changed more than chance explains.

The trap this module exists for: in a village of 800 people, two building permits instead of one is "+100%".
Ranking by percentage change fills the reporters' list with villages and noise. Instead:

1. Every series is put on today's boundaries (Gebietsstand), so a merger is not a jump.
2. Each municipality's expected count comes from its own history, shrunk towards its district when the history is
   thin (gamma-Poisson), and moved with its district this quarter, so a district-wide change is one district story
   rather than forty village stories.
3. The surprise is the tail probability under a negative binomial that allows for the quarter-to-quarter wobble seen
   in the history. A release tests a thousand municipalities at once, so the cut-off controls the false discovery
   rate over the release (Benjamini-Hochberg), not one p-value at a time. Leads past the cut-off are strong; the
   rest of the desk's capacity is filled with the next best, marked as a watch list. A lead also needs a change a
   reader would care about.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

import numpy as np
from scipy import stats

from .domain import Gebietsstand, Observation, Period, kreis_of


@dataclass
class LeadSettings:
    history_quarters: int = 4
    prior_exposure: float = 6.0  # thousand inhabitant-quarters of district rate behind each municipal rate
    min_ratio: float = 1.35  # observed / expected, or its inverse
    min_abs: float = 5.0  # counts
    fdr: float = 0.05  # false discovery rate over all tests of a release (Benjamini-Hochberg)
    per_release: int = 8  # leads a desk can check per release
    kreis_min_ratio: float = 1.15
    overdispersion: bool = True  # off = plain Poisson, no shrinkage: the textbook test that ignores lumpy data


@dataclass
class Lead:
    indicator: str
    level: str  # gemeinde | kreis
    key: str
    period: Period
    observed: float
    expected: float
    p: float
    history: list[float]
    population: int
    strong: bool = True  # passes the release's false-discovery cut-off; False = watch list
    facts: dict[str, float | str] = field(default_factory=dict)

    @property
    def ratio(self) -> float:
        return (self.observed + 0.5) / (self.expected + 0.5)

    @property
    def score(self) -> float:
        return -math.log10(max(self.p, 1e-300))


Series = dict[Period, dict[str, Observation]]


def harmonise(series: Series, geb: Gebietsstand, day: date) -> dict[Period, dict[str, float | None]]:
    """Every quarter on the boundaries of `day`: parts merged since then are added to their successor.

    A withheld part makes the merged value unknown, never zero.
    """
    out: dict[Period, dict[str, float | None]] = {}
    for p, rows in series.items():
        acc: dict[str, float | None] = {}
        for ags, o in rows.items():
            to = geb.successor(ags, day)
            if to in acc and acc[to] is None:
                continue
            acc[to] = None if o.value is None else (acc.get(to) or 0.0) + o.value
        out[p] = acc
    return out


def _nb_two_sided(y: float, mu: float, shape: float) -> float:
    """Two-sided tail probability of y under a negative binomial with mean mu and shape (dispersion) `shape`."""
    mu = max(mu, 1e-6)
    n = max(shape, 1e-6)
    prob = n / (n + mu)
    lo = stats.nbinom.cdf(y, n, prob)
    hi = stats.nbinom.sf(y - 1, n, prob)
    return float(min(1.0, 2 * min(lo, hi)))


def find_leads(
    indicator: str,
    series: Series,
    period: Period,
    geb: Gebietsstand,
    s: LeadSettings,
) -> list[Lead]:
    day = period.end
    h = harmonise(series, geb, day)
    if period not in h:
        return []
    past = [period.shift(-k) for k in range(s.history_quarters, 0, -1)]
    if any(q not in h for q in past):
        return []
    keys = sorted(geb.valid_on(day))
    pop = {a: geb.population_on(a, day) / 1000 for a in keys}  # thousands

    def usable(a: str) -> bool:
        return h[period].get(a) is not None and all(h[q].get(a) is not None for q in past)

    ok = [a for a in keys if usable(a)]

    # district and Land rates, history and now
    k_hist: dict[str, float] = defaultdict(float)
    k_now: dict[str, float] = defaultdict(float)
    k_exp: dict[str, float] = defaultdict(float)
    for a in ok:
        k = kreis_of(a)
        k_hist[k] += sum(h[q][a] or 0 for q in past)
        k_now[k] += h[period][a] or 0
        k_exp[k] += pop[a]
    land_hist = sum(k_hist.values())
    land_now = sum(k_now.values())
    land_trend = (land_now + 1) / (land_hist / len(past) + 1)

    # wobble beyond Poisson, pooled over all municipalities (method of moments): Var = mu + phi * mu^2.
    # Pooling matters: four quarters per municipality are far too few to estimate it one by one.
    num = 0.0
    den = 0.0
    for a in ok:
        arr = np.array([h[q][a] or 0 for q in past], dtype=float)
        m = float(arr.mean())
        if m >= 3:
            num += float(arr.var(ddof=1)) - m
            den += m * m
    phi = max(0.0, num / den) if den and s.overdispersion else 0.0
    prior = s.prior_exposure if s.overdispersion else 0.0

    # district totals over every published cell, each quarter on its own: a district lead states what was published
    k_all_now: dict[str, float] = defaultdict(float)
    k_all_hist: dict[str, float] = defaultdict(float)
    withheld: dict[str, int] = defaultdict(int)
    for a in keys:
        k = kreis_of(a)
        v = h[period].get(a)
        if v is None:
            withheld[k] += 1
        else:
            k_all_now[k] += v
        k_all_hist[k] += sum(h[q].get(a) or 0 for q in past)

    leads: list[Lead] = []
    tests: list[float] = []  # every test made in this release, also those too small to be a lead
    for k in sorted(k_now):
        exp_k = k_all_hist[k] / len(past) * land_trend
        y = k_all_now[k]
        shape = 1 / phi if phi > 0 else 1e6
        p = _nb_two_sided(y, exp_k, shape)
        ratio = (y + 0.5) / (exp_k + 0.5)
        tests.append(p)
        if abs(y - exp_k) >= s.min_abs and max(ratio, 1 / ratio) >= s.kreis_min_ratio:
            ld = Lead(
                indicator,
                "kreis",
                k,
                period,
                y,
                exp_k,
                p,
                [sum(h[q].get(a) or 0 for a in keys if kreis_of(a) == k) for q in past],
                round(sum(pop[a] for a in keys if kreis_of(a) == k) * 1000),
            )
            ld.facts["withheld"] = withheld[k]
            leads.append(ld)

    for a in ok:
        k = kreis_of(a)
        ys = [h[q][a] or 0.0 for q in past]
        exposure = pop[a] * len(past)
        k_rate = k_hist[k] / max(k_exp[k] * len(past), 1e-9)
        alpha = k_rate * prior
        rate = (sum(ys) + alpha) / (exposure + prior)
        # the district's move this quarter, without this municipality: one big town must not move its neighbours
        rest_now = k_now[k] - (h[period][a] or 0.0)
        rest_hist = (k_hist[k] - sum(ys)) / len(past)
        k_trend = (rest_now + land_trend * 5) / (rest_hist + 5)  # shrunk to the Land's move when the rest is small
        mu = rate * pop[a] * k_trend
        # predictive: gamma posterior on the rate plus the quarter-to-quarter wobble
        post_shape = sum(ys) + alpha
        var = mu + (mu * mu / max(post_shape, 1e-6) if s.overdispersion else 0.0) + phi * mu * mu
        shape = mu * mu / max(var - mu, 1e-9)
        y = h[period][a] or 0.0
        p = _nb_two_sided(y, mu, shape)
        ratio = (y + 0.5) / (mu + 0.5)
        tests.append(p)
        if abs(y - mu) >= s.min_abs and max(ratio, 1 / ratio) >= s.min_ratio:
            leads.append(Lead(indicator, "gemeinde", a, period, y, mu, p, ys, round(pop[a] * 1000)))

    cut = bh_cutoff(tests, s.fdr)
    for ld in leads:
        ld.strong = ld.p <= cut
    # a municipality that is a whole district (Stuttgart) is reported once, as the district
    kreis_keys = {ld.key for ld in leads if ld.level == "kreis"}
    leads = [ld for ld in leads if not (ld.level == "gemeinde" and kreis_of(ld.key) in kreis_keys and _is_whole_district(ld.key, ok))]
    leads.sort(key=lambda ld: (-ld.score, -ld.population, ld.key))
    # strong leads first; the rest of the desk's capacity is a ranked watch list, marked as such
    return leads[: s.per_release]


def bh_cutoff(ps: list[float], q: float) -> float:
    """The largest p-value Benjamini-Hochberg accepts at false discovery rate q; -1 when none is accepted."""
    srt = sorted(ps)
    m = len(srt)
    cut = -1.0
    for i, p in enumerate(srt, start=1):
        if p <= q * i / m:
            cut = p
    return cut


def _is_whole_district(ags: str, keys: list[str]) -> bool:
    k = kreis_of(ags)
    return sum(1 for a in keys if kreis_of(a) == k) == 1


def naive_leads(
    indicator: str,
    series: Series,
    period: Period,
    per_release: int,
    min_base: float = 1.0,
    withheld_as_zero: bool = True,
) -> list[Lead]:
    """The spreadsheet way: rank municipalities by percentage change against the previous quarter.

    No boundary changes, withheld cells read as zero, no notion of chance. This is the status quo being measured.
    """
    prev = series.get(period.shift(-1), {})
    now = series.get(period, {})
    out: list[Lead] = []
    for a, o in now.items():
        b = prev.get(a)
        y = o.value if o.value is not None else (0.0 if withheld_as_zero else None)
        x = b.value if b and b.value is not None else (0.0 if withheld_as_zero and b else None)
        if y is None or x is None or x < min_base:
            continue
        pct = (y - x) / x
        out.append(Lead(indicator, "gemeinde", a, period, y, x, 1 / (1 + abs(pct) * 100), [x], 0))
    out.sort(key=lambda ld: (ld.p, ld.key))
    return out[:per_release]
