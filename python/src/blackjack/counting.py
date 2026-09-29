"""Finite-shoe simulation with Hi-Lo counting.

Plays the real game (6-deck shoe, cut card) with a fixed basic strategy and
records, for every round, the true count *at the moment the bet is placed*
and the round's profit per unit bet. Grouping rounds by true count gives the
EV-vs-true-count curve; any betting ramp can then be evaluated from the
per-count moments without re-simulating (see `ramp_summary`).

The player uses basic strategy only (no count-based strategy deviations), so
the results understate what a counter using index plays would achieve.

This is the reference implementation; the C simulator in /C runs the same
algorithm ~100x faster for the headline numbers, and a test checks the two
agree.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Mapping

from .engine import HiLoCounter, Shoe, play_round
from .rules import Rules
from .strategy import BasicStrategy

TC_MIN, TC_MAX = -10, 10


def tc_bin(true_count: float) -> int:
    """Floor the true count (TC 2.7 -> +2), clipped to [-10, 10]."""
    return max(TC_MIN, min(TC_MAX, math.floor(true_count)))


@dataclass
class BinStats:
    n: int = 0
    sum: float = 0.0     # sum of profit per unit bet
    sumsq: float = 0.0   # sum of squared profit per unit bet

    def add(self, x: float) -> None:
        self.n += 1
        self.sum += x
        self.sumsq += x * x

    def merge(self, o: "BinStats") -> None:
        self.n += o.n
        self.sum += o.sum
        self.sumsq += o.sumsq

    @property
    def mean(self) -> float:
        return self.sum / self.n if self.n else float("nan")

    @property
    def var(self) -> float:
        return self.sumsq / self.n - self.mean ** 2 if self.n else float("nan")

    @property
    def se(self) -> float:
        return math.sqrt(self.var / self.n) if self.n > 1 else float("nan")


@dataclass
class CountingResult:
    rounds: int = 0
    shoes: int = 0
    bins: Dict[int, BinStats] = field(default_factory=dict)
    # Optional outcome histograms per bin (C simulator only): counts of the
    # round result -4.0, -3.5, ..., +4.0 units.
    hist: Dict[int, List[int]] = field(default_factory=dict)

    @property
    def overall(self) -> BinStats:
        total = BinStats()
        for b in self.bins.values():
            total.merge(b)
        return total


def simulate(rules: Rules, strategy: BasicStrategy, rounds: int, seed: int = 1) -> CountingResult:
    rng = random.Random(seed)
    shoe = Shoe(rules.decks, rules.penetration, rng)
    counter = HiLoCounter()
    out = CountingResult(shoes=1)
    for _ in range(rounds):
        if shoe.needs_shuffle:
            shoe.shuffle()
            counter.reset()
            out.shoes += 1
        b = tc_bin(counter.true_count(shoe))
        r = play_round(shoe, rules, strategy, 1.0, counter)
        out.bins.setdefault(b, BinStats()).add(r.net)
        out.rounds += 1
    return out


@dataclass
class RampSummary:
    ev_per_round: float     # expected profit per round, in units
    sd_per_round: float
    avg_bet: float
    edge: float             # ev_per_round / avg_bet


def ramp_summary(result: CountingResult, ramp: Mapping[int, float]) -> RampSummary:
    """Evaluate a betting ramp {tc_bin: units} from per-bin moments.

    Missing bins bet the ramp's smallest value.
    """
    n = sum(b.n for b in result.bins.values())
    lo = min(ramp.values())
    e = e2 = avg = 0.0
    for tc, b in result.bins.items():
        f = b.n / n
        bet = ramp.get(tc, lo if tc < min(ramp) else ramp[max(ramp)])
        e += f * bet * b.mean
        e2 += f * bet * bet * (b.sumsq / b.n)
        avg += f * bet
    return RampSummary(e, math.sqrt(e2 - e * e), avg, e / avg)


def risk_of_ruin(ev: float, sd: float, bankroll: float) -> float:
    """Diffusion approximation for the probability of ever losing `bankroll`
    units when each round has mean `ev` and standard deviation `sd`."""
    if ev <= 0:
        return 1.0
    return math.exp(-2 * ev * bankroll / (sd * sd))
