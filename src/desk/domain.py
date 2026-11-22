"""The vocabulary of municipal statistics: keys, municipalities, boundary changes, periods and indicators.

These are facts of the trade, not settings. Thresholds, capacities and source layouts live in config/.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

AGS_RE = re.compile(r"^08\d{6}$")  # Amtlicher Gemeindeschlüssel, Baden-Württemberg: 08 + district (3) + municipality (3)
KREIS_RE = re.compile(r"^08\d{3}$")


def kreis_of(ags: str) -> str:
    """The district key of a municipality key: 08111000 -> 08111."""
    if not AGS_RE.match(ags):
        raise ValueError(f"not a municipality key: {ags!r}")
    return ags[:5]


@dataclass(frozen=True)
class Municipality:
    ags: str
    name: str
    population: int
    lon: float
    lat: float
    kind: str = "gemeinde"  # gemeinde | stadt | stadtkreis

    @property
    def kreis(self) -> str:
        return kreis_of(self.ags)


@dataclass(frozen=True)
class AgsChange:
    """A boundary change from the official list (Gebietsänderungen): `old` is absorbed into `new` from `valid_from`."""

    old: str
    new: str
    valid_from: date
    kind: str = "merger"


@dataclass(frozen=True)
class Period:
    """A quarter, the release rhythm of the indicators here."""

    year: int
    quarter: int

    @staticmethod
    def parse(text: str) -> Period:
        m = re.fullmatch(r"\s*(\d{4})\s*[-/ ]?\s*Q([1-4])\s*", text, re.I) or re.fullmatch(
            r"\s*([1-4])\.\s*Quartal\s+(\d{4})\s*", text, re.I
        )
        if not m:
            raise ValueError(f"not a quarter: {text!r}")
        a, b = m.group(1), m.group(2)
        return Period(int(a), int(b)) if len(a) == 4 else Period(int(b), int(a))

    def __str__(self) -> str:
        return f"{self.year}Q{self.quarter}"

    def german(self) -> str:
        return f"{self.quarter}. Quartal {self.year}"

    @property
    def end(self) -> date:
        month = self.quarter * 3
        return date(self.year, month, 30 if month in (6, 9) else 31)

    @property
    def start(self) -> date:
        return date(self.year, self.quarter * 3 - 2, 1)

    def shift(self, quarters: int) -> Period:
        i = self.year * 4 + (self.quarter - 1) + quarters
        return Period(i // 4, i % 4 + 1)

    def __lt__(self, other: Period) -> bool:
        return (self.year, self.quarter) < (other.year, other.quarter)

    def __le__(self, other: Period) -> bool:
        return (self.year, self.quarter) <= (other.year, other.quarter)


@dataclass(frozen=True)
class Indicator:
    id: str
    label: str  # German, as used in notes
    unit: str  # what one count is, German: "Wohnungen", "Geburten"
    per: int = 1000  # rates per this many inhabitants
    suppress_below: int = 0  # cells below this count are kept secret by the source ("."), 0 = none


@dataclass
class Observation:
    ags: str
    period: Period
    value: float | None  # None when the source withholds or has no value
    flag: str | None = None  # the source's sign: "geheim", "nichts", "unbekannt", "gesperrt", "später", "unsicher"


@dataclass
class Gebietsstand:
    """Municipalities and boundary changes, so that numbers from different years compare like with like."""

    municipalities: dict[str, Municipality]
    changes: list[AgsChange] = field(default_factory=list)

    _cache: dict[date, tuple[dict[str, str], dict[str, int], set[str]]] = field(default_factory=dict, repr=False)

    def _on(self, day: date) -> tuple[dict[str, str], dict[str, int], set[str]]:
        """Successor of every key, population of every key and the keys that exist, all on `day`; computed once."""
        if day not in self._cache:
            step = {c.old: c.new for c in self.changes if c.valid_from <= day}
            succ: dict[str, str] = {}
            for a in self.municipalities:
                cur, seen = a, set()
                while cur in step and cur not in seen:
                    seen.add(cur)
                    cur = step[cur]
                succ[a] = cur
            pop: dict[str, int] = {}
            for a, m in self.municipalities.items():
                pop[succ[a]] = pop.get(succ[a], 0) + m.population
            self._cache[day] = (succ, pop, {a for a in self.municipalities if a not in step})
        return self._cache[day]

    def valid_on(self, day: date) -> set[str]:
        """Keys that exist on `day`: every key, minus those already absorbed by then."""
        return set(self._on(day)[2])

    def successor(self, ags: str, day: date) -> str:
        """The key that `ags` belongs to on `day`, following chains of mergers."""
        return self._on(day)[0].get(ags, ags)

    def population_on(self, ags: str, day: date) -> int:
        """Population of `ags` within its boundaries on `day`, including everything merged into it by then."""
        return self._on(day)[1].get(ags, 0)
