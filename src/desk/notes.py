"""Lead notes and automated municipal texts, in German, with every number checked against the facts.

A model may draft the wording. Before a note reaches a reporter or a text reaches readers, code finds every number in
it and looks for a fact it could have come from, at the precision shown. A number with no fact behind it, or a word
that points the wrong way ("gestiegen" for a fall), and the draft is refused; the plain template text goes out.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Protocol

from .numbers import fmt_de, numbers_in

Facts = dict[str, float | str]


@dataclass
class CheckedText:
    text: str
    ok: bool
    problems: list[str] = field(default_factory=list)
    # for each number in the text: (start, end, fact name or None)
    numbers: list[tuple[int, int, str | None]] = field(default_factory=list)
    source: str = "template"  # template | model


ALWAYS_ALLOWED = {1000.0}  # "je 1.000 Einwohner"

UP = re.compile(r"\b(gestiegen|mehr|höher|zugenommen|Anstieg|Plus|verdoppelt|wächst|stieg)\b", re.I)
DOWN = re.compile(r"\b(gesunken|weniger|niedriger|abgenommen|Rückgang|Minus|halbiert|sank|fiel|eingebrochen)\b", re.I)


def check_numbers(text: str, facts: Facts) -> CheckedText:
    nums = [(k, float(v)) for k, v in facts.items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    problems: list[str] = []
    found: list[tuple[int, int, str | None]] = []
    for value, decimals, start, end in numbers_in(text):
        tol = 0.5 * 10 ** (-decimals) + 1e-9
        # a text writes magnitudes ("12 Prozent weniger"), so a fact matches by its absolute value at the shown precision
        hit = next((k for k, v in nums if abs(round(abs(v), decimals) - abs(value)) <= tol), None)
        if hit is None and (value in ALWAYS_ALLOWED or _is_period_number(value, facts)):
            hit = "period" if value not in ALWAYS_ALLOWED else "per"
        if hit is None:
            problems.append(f"„{text[start:end]}“ steht in keinem Datensatz")
        found.append((start, end, hit))
    change = facts.get("change")
    if isinstance(change, (int, float)) and abs(change) > 0:
        if change > 0 and DOWN.search(text) and not UP.search(text):
            problems.append("schreibt „gesunken“, die Zahl ist gestiegen")
        if change < 0 and UP.search(text) and not DOWN.search(text):
            problems.append("schreibt „gestiegen“, die Zahl ist gesunken")
    return CheckedText(text, not problems, problems, found)


def _is_period_number(value: float, facts: Facts) -> bool:
    return value in {facts.get("year"), facts.get("quarter")}


class Writer(Protocol):
    def draft(self, kind: str, facts: Facts) -> str: ...


def template_lead(f: Facts) -> str:
    """The plain note a reporter gets when no model is used or its draft was refused."""
    d = "mehr" if float(f["change"]) > 0 else "weniger"
    place = f"{f['name']} ({f['kreis_name']})" if f.get("level") == "gemeinde" else str(f["name"])
    at_least = "mindestens " if f.get("withheld") else ""  # withheld village cells are not in a district total
    return (
        f"{place}: Im {int(f['quarter'])}. Quartal {int(f['year'])} wurden {at_least}{fmt_de(float(f['observed']))} {f['unit']} "
        f"gezählt, {fmt_de(abs(float(f['change_pct'])))} Prozent {d} als erwartet ({fmt_de(float(f['expected']))}). "
        f"Das sind {fmt_de(float(f['rate']), 1)} je 1.000 Einwohner, landesweit {fmt_de(float(f['land_rate']), 1)}. "
        f"Im Schnitt der Vorquartale waren es {fmt_de(float(f['history_mean']), 1)}."
    )


def template_municipal(f: Facts) -> str:
    """The automated text for every municipality and release."""
    d = "mehr" if float(f["change_prev"]) > 0 else ("weniger" if float(f["change_prev"]) < 0 else "genauso viele")
    tail = (
        f" wie im Vorquartal ({fmt_de(float(f['previous']))})"
        if d == "genauso viele"
        else f" als im Vorquartal ({fmt_de(float(f['previous']))})"
    )
    return (
        f"In {f['name']} wurden im {int(f['quarter'])}. Quartal {int(f['year'])} {fmt_de(float(f['observed']))} "
        f"{f['unit']} gezählt, {d}{tail}. Je 1.000 Einwohner sind das {fmt_de(float(f['rate']), 1)}, "
        f"im Landkreis {fmt_de(float(f['kreis_rate']), 1)}."
    )


def write_checked(kind: str, facts: Facts, writer: Writer | None) -> CheckedText:
    plain = template_lead(facts) if kind == "lead" else template_municipal(facts)
    if writer is not None:
        draft = writer.draft(kind, facts)
        checked = check_numbers(draft, facts)
        checked.source = "model"
        if checked.ok:
            return checked
        fallback = check_numbers(plain, facts)
        fallback.problems = [f"Modellentwurf verworfen: {p}" for p in checked.problems]
        fallback.ok = True
        return fallback
    return check_numbers(plain, facts)


def lead_facts(
    *,
    name: str,
    kreis_name: str,
    level: str,
    unit: str,
    year: int,
    quarter: int,
    observed: float,
    expected: float,
    population: int,
    land_rate: float,
    history: list[float],
    per: int = 1000,
) -> Facts:
    change = observed - expected
    rate = observed / max(population, 1) * per
    return {
        "name": name,
        "kreis_name": kreis_name,
        "level": level,
        "unit": unit,
        "year": year,
        "quarter": quarter,
        "observed": observed,
        "expected": round(expected),
        "change": change,
        "change_pct": round(100 * change / max(expected, 1e-9)),
        "rate": rate,
        "land_rate": land_rate,
        "history_mean": sum(history) / max(1, len(history)),
    }


def is_finite(x: float) -> bool:
    return not (math.isnan(x) or math.isinf(x))
