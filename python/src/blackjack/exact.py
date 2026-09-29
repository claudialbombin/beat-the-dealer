"""Exact expected values under the infinite-deck approximation.

With an infinite deck every draw is independent (P(ten) = 4/13, every other
value 1/13), so the value of a hand depends only on (total, soft, upcard) and
the whole game can be solved by recursion over a few hundred states.

This is the *reference* the Monte Carlo solver is checked against: MC
estimates must converge to these numbers, and the MC-derived chart must
agree with the one derived here except where two actions are statistically
indistinguishable.

Infinite deck vs. a real 6-deck shoe: card removal shifts EVs by hundredths
of a percent. For these rules it moves exactly one chart cell, soft 13 vs 5
(double in a 6-deck shoe, hit with an infinite deck; the two actions are
0.6% apart). The finite-shoe simulations (engine.py and the C simulator)
measure the real game.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, Optional, Tuple

from .cards import ACE, CARD_PROBS, TEN, add_card
from .rules import Rules
from .strategy import (
    HARD_TOTALS,
    PAIR_VALUES,
    SOFT_TOTALS,
    UPCARDS,
    BasicStrategy,
    resolve,
    Action,
)

BUST = 22
Dist = Dict[int, float]  # dealer final total (17..21, 22 = bust) -> probability


class ExactSolver:
    def __init__(self, rules: Rules = Rules(), policy: Optional[BasicStrategy] = None):
        """With `policy=None` every decision is optimal; otherwise the given
        chart is followed and the solver evaluates it exactly."""
        self.rules = rules
        self.policy = policy
        self._dealer_cache: Dict[int, Dist] = {}
        self._tables: Dict[int, "_UpcardTables"] = {}

    # ---- dealer ----------------------------------------------------------
    def dealer(self, up: int) -> Dist:
        """Dealer's final-total distribution given `up`, conditioned on the
        dealer not having blackjack (the dealer peeks)."""
        if up in self._dealer_cache:
            return self._dealer_cache[up]
        h17 = self.rules.dealer_hits_soft_17

        @lru_cache(maxsize=None)
        def finish(total: int, soft: bool) -> Tuple[Tuple[int, float], ...]:
            if total > 21:
                return ((BUST, 1.0),)
            if total > 17 or (total == 17 and not (soft and h17)):
                return ((total, 1.0),)
            out: Dist = {}
            for c, p in CARD_PROBS.items():
                for k, q in finish(*add_card(total, soft, c)):
                    out[k] = out.get(k, 0.0) + p * q
            return tuple(out.items())

        hole_probs = dict(CARD_PROBS)
        if up == ACE:
            hole_probs.pop(TEN)
        elif up == TEN:
            hole_probs.pop(ACE)
        norm = sum(hole_probs.values())
        start = (11, True) if up == ACE else (up, False)
        dist: Dist = {}
        for c, p in hole_probs.items():
            for k, q in finish(*add_card(*start, c)):
                dist[k] = dist.get(k, 0.0) + p / norm * q
        self._dealer_cache[up] = dist
        return dist

    @staticmethod
    def p_dealer_blackjack(up: int) -> float:
        return CARD_PROBS[TEN] if up == ACE else CARD_PROBS[ACE] if up == TEN else 0.0

    # ---- player ----------------------------------------------------------
    def tables(self, up: int) -> "_UpcardTables":
        if up not in self._tables:
            self._tables[up] = _UpcardTables(self, up)
        return self._tables[up]

    def optimal_strategy(self) -> BasicStrategy:
        s = BasicStrategy()
        for up in UPCARDS:
            t = self.tables(up)
            for total in HARD_TOTALS:
                s.hard[(total, up)] = t.chart_code(total, False)
            for total in SOFT_TOTALS:
                s.soft[(total, up)] = t.chart_code(total, True)
            for v in PAIR_VALUES:
                evs = t.pair_evs(v)
                s.pairs[(v, up)] = evs["P"] > max(evs[a] for a in evs if a != "P")
        return s

    def round_ev(self) -> float:
        """Expected profit per initial unit bet for a whole round."""
        ev = 0.0
        payout = self.rules.blackjack_payout
        for up, pu in CARD_PROBS.items():
            p_dbj = self.p_dealer_blackjack(up)
            t = self.tables(up)
            for c1, p1 in CARD_PROBS.items():
                for c2, p2 in CARD_PROBS.items():
                    p = pu * p1 * p2
                    player_bj = {c1, c2} == {ACE, TEN}
                    if player_bj:
                        ev += p * (1 - p_dbj) * payout
                        continue
                    if c1 == c2:
                        play = t.pair_value(c1)
                    else:
                        total, soft = add_card(*add_card(0, False, c1), c2)
                        play = t.two_card_value(total, soft, can_double=True)
                    ev += p * ((1 - p_dbj) * play - p_dbj)
        return ev


class _UpcardTables:
    """All player EVs for one dealer upcard."""

    def __init__(self, solver: ExactSolver, up: int):
        self.solver = solver
        self.up = up
        self.rules = solver.rules
        self.policy = solver.policy
        d = solver.dealer(up)
        self.p_bust = d.get(BUST, 0.0)
        self.dist = d
        self._multi: Dict[Tuple[int, bool], float] = {}

    # -- elementary values
    def stand(self, total: int) -> float:
        if total > 21:
            return -1.0
        win = self.p_bust + sum(p for k, p in self.dist.items() if k < total)
        lose = sum(p for k, p in self.dist.items() if k != BUST and k > total)
        return win - lose

    def _after_draw(self, total: int, soft: bool, f) -> float:
        ev = 0.0
        for c, p in CARD_PROBS.items():
            nt, ns = add_card(total, soft, c)
            ev += p * (-1.0 if nt > 21 else f(nt, ns))
        return ev

    def hit(self, total: int, soft: bool) -> float:
        return self._after_draw(total, soft, self.multi_card_value)

    def double(self, total: int, soft: bool) -> float:
        return 2 * self._after_draw(total, soft, lambda t, s: self.stand(t))

    def multi_card_value(self, total: int, soft: bool) -> float:
        """Value of a hand that may only hit or stand."""
        key = (total, soft)
        if key not in self._multi:
            if total >= 21:
                v = self.stand(total)
            else:
                s, h = self.stand(total), self.hit(total, soft)
                if self.policy is None:
                    v = max(s, h)
                else:
                    a = resolve(self._code(total, soft), can_double=False)
                    v = h if a == Action.HIT else s
            self._multi[key] = v
        return self._multi[key]

    def two_card_value(self, total: int, soft: bool, can_double: bool) -> float:
        if total >= 21:
            return self.stand(total)
        evs = {"S": self.stand(total), "H": self.hit(total, soft)}
        if can_double:
            evs["D"] = self.double(total, soft)
        if self.policy is None:
            return max(evs.values())
        a = resolve(self._code(total, soft), can_double)
        return evs[{"H": "H", "S": "S", "D": "D"}[a.value]]

    def _code(self, total: int, soft: bool) -> str:
        table = self.policy.soft if soft else self.policy.hard
        return table.get((total, self.up), "S" if total >= 17 else "H")

    # -- splitting
    def split(self, v: int) -> float:
        start = (11, True) if v == ACE else (v, False)
        if v == ACE:  # one card each, no further action
            one = self._after_draw(*start, lambda t, s: self.stand(t))
        else:
            das = self.rules.double_after_split
            one = self._after_draw(*start, lambda t, s: self.two_card_value(t, s, das))
        return 2 * one

    def pair_evs(self, v: int) -> Dict[str, float]:
        total, soft = add_card(*add_card(0, False, v), v)
        evs = self.action_evs(total, soft, can_double=True)
        evs["P"] = self.split(v)
        return evs

    def pair_value(self, v: int) -> float:
        evs = self.pair_evs(v)
        split_ev = evs.pop("P")
        total, soft = add_card(*add_card(0, False, v), v)
        play = self.two_card_value(total, soft, can_double=True)
        if self.policy is None:
            return max(play, split_ev)
        return split_ev if self.policy.pairs.get((v, self.up)) else play

    # -- reporting
    def action_evs(self, total: int, soft: bool, can_double: bool = True) -> Dict[str, float]:
        evs = {"H": self.hit(total, soft) if total < 21 else float("nan"), "S": self.stand(total)}
        if can_double and total < 21:
            evs["D"] = self.double(total, soft)
        return evs

    def chart_code(self, total: int, soft: bool) -> str:
        if total >= 21:
            return "S"
        s, h, d = self.stand(total), self.hit(total, soft), self.double(total, soft)
        if d > max(s, h):
            return "Dh" if h >= s else "Ds"
        return "H" if h > s else "S"
