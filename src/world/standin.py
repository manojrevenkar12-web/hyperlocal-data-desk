"""Stand-ins for the people and models the designs rely on, with stated error rates. Lab only.

- model_reading: what a language model reads from a file. It understands units and separators the way the file
  means them, but it has no history: a stale file looks fine to it.
- StandInWriter: a model drafting German notes and texts. With probability `error` one number goes wrong the way
  model drafts go wrong: a decimal slips, the comparison base changes, two numbers swap, a percentage is made up.
"""

from __future__ import annotations

from desk.notes import Facts, template_lead, template_municipal
from desk.numbers import fmt_de

from . import Release, keyed


def model_reading(rel: Release) -> dict[str, float | None]:
    return dict(rel.printed)


class StandInWriter:
    def __init__(self, seed: int, error: float) -> None:
        self.seed = seed
        self.error = error

    def wrong(self, kind: str, f: Facts) -> bool:
        r = keyed(self.seed, "draft", kind, f.get("name"), f.get("indicator"), f.get("year"), f.get("quarter"))
        return bool(r.random() < self.error)

    def draft(self, kind: str, f: Facts) -> str:
        text = template_lead(f) if kind == "lead" else template_municipal(f)
        # paraphrase, as a model would
        text = text.replace("wurden", "registrierte das Amt", 1).replace(" gezählt", "", 1)
        if not self.wrong(kind, f):
            return text
        r = keyed(self.seed, "how", kind, f.get("name"), f.get("indicator"), f.get("year"), f.get("quarter"))
        how = int(r.integers(4))
        if kind == "lead":
            rate = fmt_de(float(f["rate"]), 1)
            if how == 0:
                return text.replace(f"Das sind {rate}", f"Das sind {fmt_de(float(f['rate']) * 10, 1)}", 1)
            if how == 1:
                pct = fmt_de(abs(float(f["change_pct"])))
                return text.replace(f"{pct} Prozent", f"{fmt_de(abs(float(f['change_pct'])) + int(r.integers(7, 40)))} Prozent", 1)
            if how == 2:
                return text.replace(fmt_de(float(f["observed"])), fmt_de(float(f["expected"]) + 1), 1)
            return text.replace("mehr", "weniger", 1) if float(f["change"]) > 0 else text.replace("weniger", "mehr", 1)
        return text.replace(fmt_de(float(f["observed"])), fmt_de(float(f["observed"]) + int(r.integers(1, 9))), 1)
