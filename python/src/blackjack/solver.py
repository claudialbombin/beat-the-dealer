"""Monte Carlo basic-strategy solver.

Idea
----
For every decision state (player total, soft/hard, dealer upcard) and every
legal action, estimate the action's expected value by simulating N hands and
averaging the profit. The best action is the one with the highest estimate.

Two details make this a correct solver rather than a heuristic:

1. **Backward induction.** After hitting, the hand must be played on
   *optimally*, not with a fixed rule such as "hit to 17". States are solved in
   an order where every state a hit can lead to has already been solved (hard
   21..11, then soft 21..12, then hard 10..4), and the continuation uses the
   policy estimated so far.

2. **Common random numbers.** Within one upcard every action is evaluated
   against the *same* simulated dealer hands, and the actions of one state use
   the same player cards. The comparison "hit vs stand" therefore measures the
   difference of the decisions, not the luck of two unrelated samples, which
   cuts the variance of the difference by an order of magnitude.

Draws come from an infinite deck (see exact.py for why and what it costs), so
the estimates can be compared one-to-one with the exact solver.

Everything is vectorised with NumPy: one state-action is a handful of array
operations over N simulated hands.
"""

from __future__ import annotations

import multiprocessing as mp
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .cards import ACE, CARD_PROBS, RANK_VALUES, TEN
from .rules import Rules
from .strategy import HARD_TOTALS, PAIR_VALUES, SOFT_TOTALS, UPCARDS, BasicStrategy

_VALUES = np.array(RANK_VALUES, dtype=np.int8)
_KIND = {"hard": 0, "soft": 1, "pair": 2}

StateKey = Tuple[str, int, int]  # (kind, total or pair value, upcard)


@dataclass
class ActionEstimate:
    mean: float
    se: float  # standard error of the mean


@dataclass
class StateResult:
    evs: Dict[str, ActionEstimate]
    best: str             # H, S, D or P
    code: str             # chart code (H, S, Dh, Ds, P, -)
    margin: float         # EV(best) - EV(runner-up)
    margin_se: float      # paired standard error of that difference


@dataclass
class SolveResult:
    rules: Rules
    n: int
    seed: int
    states: Dict[StateKey, StateResult] = field(default_factory=dict)

    def strategy(self) -> BasicStrategy:
        s = BasicStrategy()
        for (kind, total, up), r in self.states.items():
            if kind == "hard":
                s.hard[(total, up)] = r.code
            elif kind == "soft":
                s.soft[(total, up)] = r.code
            else:
                s.pairs[(total, up)] = r.code == "P"
        return s


# ---------------------------------------------------------------------------
# Vectorised hand mechanics
# ---------------------------------------------------------------------------

def _draw(rng: np.random.Generator, n: int) -> np.ndarray:
    return _VALUES[rng.integers(0, 13, n)]


def _add(total: np.ndarray, soft: np.ndarray, card: np.ndarray):
    hard = total - 10 * soft
    is_ace = card == ACE
    hard = hard + np.where(is_ace, 1, card)
    promote = (soft | is_ace) & (hard + 10 <= 21)
    return hard + 10 * promote, promote


def simulate_dealer(up: int, n: int, rules: Rules, rng: np.random.Generator) -> np.ndarray:
    """Final dealer totals (22 = bust), conditioned on no dealer blackjack."""
    values = np.array(sorted(CARD_PROBS), dtype=np.int16)
    probs = np.array([CARD_PROBS[v] for v in values])
    if up == ACE:
        probs[values == TEN] = 0
    elif up == TEN:
        probs[values == ACE] = 0
    hole = rng.choice(values, size=n, p=probs / probs.sum())

    total = np.full(n, 11 if up == ACE else up, dtype=np.int16)
    soft = np.full(n, up == ACE)
    total, soft = _add(total, soft, hole)
    while True:
        hit = (total < 17) | ((total == 17) & soft & rules.dealer_hits_soft_17)
        if not hit.any():
            break
        t2, s2 = _add(total, soft, _draw(rng, n).astype(np.int16))
        total = np.where(hit, t2, total)
        soft = np.where(hit, s2, soft)
    return np.minimum(total, 22)


def _payoff(total: np.ndarray, dealer: np.ndarray) -> np.ndarray:
    return np.where(
        total > 21, -1,
        np.where((dealer > 21) | (total > dealer), 1, np.where(total < dealer, -1, 0)),
    ).astype(np.int8)


def _play_out(total, soft, rng, hit_hard, hit_soft):
    """Hit/stand until the policy stands or the hand busts."""
    total = total.astype(np.int16)
    soft = soft.copy()
    while True:
        hit = np.where(soft, hit_soft[np.minimum(total, 22)], hit_hard[np.minimum(total, 22)]) & (total < 21)
        if not hit.any():
            return total
        t2, s2 = _add(total, soft, _draw(rng, total.size).astype(np.int16))
        total = np.where(hit, t2, total)
        soft = np.where(hit, s2, soft)


# ---------------------------------------------------------------------------
# Per-upcard solve
# ---------------------------------------------------------------------------

def _estimate(x: np.ndarray) -> ActionEstimate:
    return ActionEstimate(float(x.mean()), float(x.std(ddof=1) / np.sqrt(x.size)))


def _summarise(samples: Dict[str, np.ndarray]) -> Tuple[Dict[str, ActionEstimate], str, str, float, float]:
    evs = {a: _estimate(x) for a, x in samples.items()}
    ranked = sorted(evs, key=lambda a: evs[a].mean, reverse=True)
    best = ranked[0]
    if len(ranked) == 1:
        return evs, best, best, float("inf"), 0.0
    second = ranked[1]
    diff = samples[best].astype(np.int16) - samples[second]
    margin = evs[best].mean - evs[second].mean
    margin_se = float(diff.std(ddof=1) / np.sqrt(diff.size))
    return evs, best, second, margin, margin_se


def _solve_upcard(args) -> Dict[StateKey, StateResult]:
    up, rules, n, seed = args

    def rng_for(*key) -> np.random.Generator:
        return np.random.default_rng([seed, up, *key])

    dealer = simulate_dealer(up, n, rules, rng_for(99))
    hit_hard = np.zeros(23, dtype=bool)
    hit_soft = np.zeros(23, dtype=bool)
    stand = {t: _payoff(np.full(n, t, dtype=np.int16), dealer) for t in range(4, 22)}
    hs: Dict[Tuple[str, int], Dict[str, np.ndarray]] = {}

    def solve_hs(kind: str, t: int) -> None:
        soft = kind == "soft"
        samples = {"S": stand[t]}
        if t < 21:
            total, s = _add(
                np.full(n, t, dtype=np.int16), np.full(n, soft),
                _draw(rng_for(_KIND[kind], t, 0), n).astype(np.int16),
            )
            final = _play_out(total, s, rng_for(_KIND[kind], t, 1), hit_hard, hit_soft)
            samples["H"] = _payoff(final, dealer)
        (hit_soft if soft else hit_hard)[t] = "H" in samples and samples["H"].mean() > samples["S"].mean()
        hs[(kind, t)] = samples

    for t in range(21, 10, -1):
        solve_hs("hard", t)
    for t in range(21, 11, -1):
        solve_hs("soft", t)
    for t in range(10, 3, -1):
        solve_hs("hard", t)

    # Doubling: one card (the same first card as the hit), then stand, 2 units.
    results: Dict[StateKey, StateResult] = {}
    code_arrays = {"hard": np.zeros(23, dtype=np.int8), "soft": np.zeros(23, dtype=np.int8)}  # 0 H, 1 S, 2 D
    for (kind, t), samples in hs.items():
        if t < 21:
            total, _ = _add(
                np.full(n, t, dtype=np.int16), np.full(n, kind == "soft"),
                _draw(rng_for(_KIND[kind], t, 0), n).astype(np.int16),
            )
            samples["D"] = (2 * _payoff(total, dealer)).astype(np.int8)
        evs, best, second, margin, margin_se = _summarise(samples)
        if best == "D":
            code = "Dh" if evs["H"].mean >= evs["S"].mean else "Ds"
        else:
            code = best
        code_arrays[kind][t] = {"H": 0, "S": 1, "D": 2}[best]
        results[(kind, t, up)] = StateResult(evs, best, code, margin, margin_se)

    # Splitting: both hands face the same dealer hand.
    for v in PAIR_VALUES:
        pair_total = 12 if v == ACE else 2 * v
        pair_kind = "soft" if v == ACE else "hard"
        split = np.zeros(n, dtype=np.int8)
        for hand in (0, 1):
            rng = rng_for(_KIND["pair"], v, hand)
            start_t = np.full(n, 11 if v == ACE else v, dtype=np.int16)
            total, soft = _add(start_t, np.full(n, v == ACE), _draw(rng, n).astype(np.int16))
            if v == ACE:
                split += _payoff(total, dealer)
                continue
            codes = np.where(soft, code_arrays["soft"][total], code_arrays["hard"][total])
            if not rules.double_after_split:
                codes = np.where(codes == 2, np.where(
                    np.where(soft, hit_soft[total], hit_hard[total]), 0, 1), codes)
            codes = np.where(total >= 21, 1, codes)
            dbl_total, _ = _add(total, soft, _draw(rng, n).astype(np.int16))
            hit_final = _play_out(total, soft, rng, hit_hard, hit_soft)
            final = np.where(codes == 1, total, np.where(codes == 2, dbl_total, hit_final))
            bet = np.where(codes == 2, 2, 1).astype(np.int8)
            split += bet * _payoff(final, dealer)
        base = hs[(pair_kind, pair_total)]
        samples = {a: x for a, x in base.items()}
        samples["P"] = split
        evs, best, second, margin, margin_se = _summarise(samples)
        # Report the margin between splitting and the best non-split play.
        non_split = max((a for a in evs if a != "P"), key=lambda a: evs[a].mean)
        diff = split.astype(np.int16) - samples[non_split]
        results[("pair", v, up)] = StateResult(
            evs, best, "P" if best == "P" else "-",
            abs(evs["P"].mean - evs[non_split].mean),
            float(diff.std(ddof=1) / np.sqrt(n)),
        )
    return results


def solve(rules: Rules = Rules(), n: int = 400_000, seed: int = 2026,
          processes: Optional[int] = None) -> SolveResult:
    """Solve every upcard in parallel (upcards are independent)."""
    jobs = [(up, rules, n, seed) for up in UPCARDS]
    if processes == 1:
        parts: List = [_solve_upcard(j) for j in jobs]
    else:
        with mp.get_context("spawn").Pool(processes) as pool:
            parts = pool.map(_solve_upcard, jobs)
    out = SolveResult(rules, n, seed)
    for p in parts:
        out.states.update(p)
    return out
