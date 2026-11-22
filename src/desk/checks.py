"""Checks a parsed release must pass before its numbers reach a lead, a chart or an automated text.

A blocking check that fails sends the release to quarantine: the data desk sees why, the newsroom sees nothing.
Non-blocking checks are notes on the release (a revision, a withheld cell, a district that does not add up by one).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .domain import Gebietsstand, kreis_of
from .sources import ParsedRelease


@dataclass
class Check:
    name: str
    ok: bool
    blocking: bool
    detail: str


@dataclass
class CheckSettings:
    reconcile_tolerance: float = 0.02  # district total vs sum of its municipalities, share of the total
    stale_share: float = 0.95  # this share of values identical to the previous quarter = a re-published old file
    min_coverage: float = 1.0  # share of municipalities valid on the period end that must be present


def check_release(
    rel: ParsedRelease,
    geb: Gebietsstand,
    previous: dict[str, float | None] | None,
    s: CheckSettings,
    integer: bool = True,
) -> list[Check]:
    out: list[Check] = []
    valid = geb.valid_on(rel.period.end)
    present = {o.ags for o in rel.rows}

    # coverage: every municipality that exists at the end of the period, once, and nothing that does not exist
    missing = sorted(valid - present)
    unknown = sorted(present - valid)
    cov = 1 - len(missing) / max(1, len(valid))
    out.append(
        Check(
            "coverage",
            cov >= s.min_coverage and not unknown,
            True,
            f"{len(present)} of {len(valid)} municipalities; missing {missing[:5]}{'…' if len(missing) > 5 else ''}"
            + (f"; keys that do not exist on {rel.period.end}: {unknown[:5]}" if unknown else ""),
        )
    )
    out.append(
        Check(
            "duplicates",
            not rel.duplicate_keys,
            True,
            f"keys more than once: {rel.duplicate_keys[:5]}" if rel.duplicate_keys else "every key once",
        )
    )

    # reconciliation: district subtotal rows must match the municipalities they cover
    if rel.kreis_totals:
        sums: dict[str, float] = defaultdict(float)
        withheld: dict[str, int] = defaultdict(int)
        for o in rel.rows:
            if o.value is None:
                withheld[kreis_of(o.ags)] += 1
            else:
                sums[kreis_of(o.ags)] += o.value
        bad = []
        for k, total in rel.kreis_totals.items():
            if total is None or withheld[k]:
                continue  # a district with withheld cells cannot be reconciled from the cells
            if abs(sums[k] - total) > max(1.0, s.reconcile_tolerance * abs(total)):
                bad.append(f"{k}: rows {sums[k]:.0f}, total {total:.0f}")
        out.append(Check("reconciliation", not bad, True, "; ".join(bad[:4]) or f"{len(rel.kreis_totals)} districts add up"))

    # staleness: a file re-published under a new period carries last quarter's numbers
    if previous:
        same = sum(1 for o in rel.rows if o.ags in previous and o.value is not None and previous[o.ags] == o.value)
        comparable = sum(1 for o in rel.rows if o.ags in previous and o.value is not None)
        share = same / max(1, comparable)
        out.append(
            Check(
                "fresh",
                share < s.stale_share or comparable < 50,
                True,
                f"{share:.0%} of values identical to the previous quarter",
            )
        )

    # counts are whole numbers: "1,234" read the German way is 1.234, a count no office publishes
    if integer:
        frac = [o.ags for o in rel.rows if o.value is not None and abs(o.value - round(o.value)) > 1e-6]
        out.append(
            Check(
                "whole numbers",
                not frac,
                True,
                f"{len(frac)} counts with a fraction, e.g. {frac[:3]}" if frac else "all counts are whole",
            )
        )

    # unit: a converted unit is accepted but stated, so a reader of the log knows the file changed
    out.append(Check("unit", True, False, f"unit {rel.unit_label!r}, factor {rel.factor:g}"))
    withheld_n = sum(1 for o in rel.rows if o.value is None)
    out.append(Check("withheld", True, False, f"{withheld_n} cells withheld or unknown"))
    return out


def blocking_failures(checks: list[Check]) -> list[Check]:
    return [c for c in checks if c.blocking and not c.ok]
