"""German statistical number formats and the official signs (Zeichenerklärung) of the statistical offices.

"1.234,5" is one thousand two hundred and thirty-four point five. A cell may hold a sign instead of a number:
  –    nichts vorhanden (zero)
  0    weniger als die Hälfte von 1 in der letzten besetzten Stelle, jedoch mehr als nichts
  .    Zahlenwert unbekannt oder geheim zu halten
  ...  Angabe fällt später an
  x    Tabellenfach gesperrt, weil Aussage nicht sinnvoll
  /    keine Angaben, da Zahlenwert nicht sicher genug
  ( )  Aussagewert eingeschränkt, da der Zahlenwert statistisch relativ unsicher ist
"""

from __future__ import annotations

import re

SIGNS: dict[str, tuple[float | None, str]] = {
    "–": (0.0, "nichts"),
    "-": (0.0, "nichts"),
    ".": (None, "geheim"),
    "...": (None, "später"),
    "…": (None, "später"),
    "x": (None, "gesperrt"),
    "X": (None, "gesperrt"),
    "/": (None, "unsicher"),
}

_DE = re.compile(r"^[+-]?\d{1,3}(\.\d{3})*(,\d+)?$|^[+-]?\d+(,\d+)?$")
_EN = re.compile(r"^[+-]?\d{1,3}(,\d{3})+(\.\d+)?$|^[+-]?\d+\.\d+$")


class NumberFormatError(ValueError):
    pass


def parse_cell(text: str, *, decimal: str = ",") -> tuple[float | None, str | None]:
    """A cell as (value, flag). Raises NumberFormatError for anything that is neither a number nor a known sign.

    `decimal` is the separator the source declares; a cell written the other way round is refused rather than
    guessed, because "1.234" means 1234 in German and 1.234 in English.
    """
    t = text.strip().replace(" ", "").replace(" ", "")
    if t in SIGNS:
        return SIGNS[t]
    flag = None
    if t.startswith("(") and t.endswith(")"):
        t, flag = t[1:-1], "eingeschränkt"
    if t.endswith("*") or re.search(r"\)\s*$", t):
        t = re.sub(r"\*+$", "", t)
    if decimal == ",":
        if not _DE.match(t):
            raise NumberFormatError(f"not a German number: {text!r}")
        return float(t.replace(".", "").replace(",", ".")), flag
    if not (_EN.match(t) or re.fullmatch(r"[+-]?\d+", t)):
        raise NumberFormatError(f"not an English number: {text!r}")
    return float(t.replace(",", "")), flag


def fmt_de(x: float, digits: int = 0) -> str:
    """12345.6 -> '12.345,6'."""
    s = f"{abs(x):,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return ("−" if x < 0 else "") + s


NUMBER_IN_TEXT = re.compile(r"(?<![\w,.])[−-]?\d{1,3}(?:\.\d{3})+(?:,\d+)?(?![\w])|(?<![\w,.])[−-]?\d+(?:,\d+)?(?![\w])")


def numbers_in(text: str) -> list[tuple[float, int, int, int]]:
    """Every number written in German in `text`: (value, decimals shown, start, end)."""
    out = []
    for m in NUMBER_IN_TEXT.finditer(text):
        raw = m.group(0).replace("−", "-")
        decimals = len(raw.split(",")[1]) if "," in raw else 0
        out.append((float(raw.replace(".", "").replace(",", ".")), decimals, m.start(), m.end()))
    return out
