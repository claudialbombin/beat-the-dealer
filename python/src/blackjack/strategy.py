"""Strategy tables and the player's decision interface.

A chart cell holds one of:

    H   hit                S   stand
    Dh  double, else hit   Ds  double, else stand
    P   split (pair table only; a pair that is not split is played as a total)

"Double, else ..." matters because doubling is only allowed on two cards: a
soft 18 vs 3 that becomes three cards should stand, while a hard 11 of three
cards should hit.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Tuple

from .cards import ACE

UPCARDS = tuple(range(2, 12))  # 11 = Ace
HARD_TOTALS = tuple(range(4, 22))
SOFT_TOTALS = tuple(range(12, 22))
PAIR_VALUES = tuple(range(2, 12))


class Action(str, Enum):
    HIT = "H"
    STAND = "S"
    DOUBLE = "D"
    SPLIT = "P"


@dataclass(frozen=True)
class Decision:
    """Everything a policy may look at when acting on a hand."""

    total: int
    soft: bool
    upcard: int
    can_double: bool
    can_split: bool
    pair_value: int | None = None  # set when the hand is a splittable pair


Table = Dict[Tuple[int, int], str]


@dataclass
class BasicStrategy:
    hard: Table = field(default_factory=dict)
    soft: Table = field(default_factory=dict)
    pairs: Dict[Tuple[int, int], bool] = field(default_factory=dict)

    def decide(self, d: Decision) -> Action:
        if d.can_split and d.pair_value is not None and self.pairs.get((d.pair_value, d.upcard)):
            return Action.SPLIT
        table = self.soft if d.soft else self.hard
        code = table.get((d.total, d.upcard), "S" if d.total >= 17 else "H")
        return resolve(code, d.can_double)

    # ---- serialisation -------------------------------------------------
    def to_rows(self):
        for (t, u), code in sorted(self.hard.items()):
            yield ("hard", t, u, code)
        for (t, u), code in sorted(self.soft.items()):
            yield ("soft", t, u, code)
        for (v, u), split in sorted(self.pairs.items()):
            yield ("pair", v, u, "P" if split else "-")

    def save_csv(self, path) -> None:
        with open(path, "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["kind", "total", "upcard", "action"])
            w.writerows(self.to_rows())

    @classmethod
    def load_csv(cls, path) -> "BasicStrategy":
        s = cls()
        with open(path) as f:
            for row in csv.DictReader(f):
                key = (int(row["total"]), int(row["upcard"]))
                if row["kind"] == "hard":
                    s.hard[key] = row["action"]
                elif row["kind"] == "soft":
                    s.soft[key] = row["action"]
                else:
                    s.pairs[key] = row["action"] == "P"
        return s


def resolve(code: str, can_double: bool) -> Action:
    if code.startswith("D"):
        if can_double:
            return Action.DOUBLE
        return Action.HIT if code == "Dh" else Action.STAND
    return Action(code)


# ---------------------------------------------------------------------------
# Published reference chart: 4-8 decks, dealer hits soft 17, double after
# split, no surrender (as printed by e.g. Wizard of Odds' strategy engine).
# Used only by the tests, as an independent check on the solvers.
# ---------------------------------------------------------------------------

def _row(spec: str) -> Dict[int, str]:
    """'H H Dh Dh ...' for upcards 2..A -> {upcard: code}."""
    codes = spec.split()
    assert len(codes) == 10, spec
    return dict(zip(UPCARDS, codes))


_REF_HARD = {
    8: "H H H H H H H H H H",
    9: "H Dh Dh Dh Dh H H H H H",
    10: "Dh Dh Dh Dh Dh Dh Dh Dh H H",
    11: "Dh Dh Dh Dh Dh Dh Dh Dh Dh Dh",
    12: "H H S S S H H H H H",
    13: "S S S S S H H H H H",
    14: "S S S S S H H H H H",
    15: "S S S S S H H H H H",
    16: "S S S S S H H H H H",
    17: "S S S S S S S S S S",
}
_REF_SOFT = {
    13: "H H H Dh Dh H H H H H",
    14: "H H H Dh Dh H H H H H",
    15: "H H Dh Dh Dh H H H H H",
    16: "H H Dh Dh Dh H H H H H",
    17: "H Dh Dh Dh Dh H H H H H",
    18: "Ds Ds Ds Ds Ds S S H H H",
    19: "S S S S Ds S S S S S",
    20: "S S S S S S S S S S",
}
_REF_PAIRS = {
    2: "P P P P P P - - - -",
    3: "P P P P P P - - - -",
    4: "- - - P P - - - - -",
    5: "- - - - - - - - - -",
    6: "P P P P P - - - - -",
    7: "P P P P P P - - - -",
    8: "P P P P P P P P P P",
    9: "P P P P P - P P - -",
    10: "- - - - - - - - - -",
    ACE: "P P P P P P P P P P",
}


def reference_chart() -> BasicStrategy:
    s = BasicStrategy()
    for t, spec in _REF_HARD.items():
        for u, c in _row(spec).items():
            s.hard[(t, u)] = c
    for t, spec in _REF_SOFT.items():
        for u, c in _row(spec).items():
            s.soft[(t, u)] = c
    for v, spec in _REF_PAIRS.items():
        for u, c in _row(spec).items():
            s.pairs[(v, u)] = c == "P"
    return s
