import math

import numpy as np
import pytest

from blackjack.exact import BUST, ExactSolver
from blackjack.rules import Rules
from blackjack.solver import solve
from blackjack.strategy import reference_chart

# Differences between the published 6-deck chart and the infinite-deck
# optimum that are genuine card-removal effects, not bugs.
KNOWN_INFINITE_DECK_DIFFS = {("soft", 13, 5)}


def chart_cells(s):
    for (t, u), c in s.hard.items():
        yield ("hard", t, u), c
    for (t, u), c in s.soft.items():
        yield ("soft", t, u), c
    for (v, u), c in s.pairs.items():
        yield ("pair", v, u), c


# ------------------------------------------------------------------- exact
@pytest.fixture(scope="module")
def exact():
    return ExactSolver()


def test_dealer_distribution_is_a_distribution(exact):
    for up in range(2, 12):
        assert math.isclose(sum(exact.dealer(up).values()), 1.0)


@pytest.mark.parametrize("up,bust", [(2, 0.3536), (6, 0.4232), (7, 0.2623), (11, 0.1665)])
def test_dealer_bust_rates_s17(up, bust):
    # Standard infinite-deck S17 bust probabilities (given no dealer blackjack).
    d = ExactSolver(Rules(dealer_hits_soft_17=False)).dealer(up)
    assert d[BUST] == pytest.approx(bust, abs=5e-5)


def test_exact_optimum_matches_published_chart(exact):
    ref = dict(chart_cells(reference_chart()))
    opt = dict(chart_cells(exact.optimal_strategy()))
    diffs = {k for k in ref if ref[k] != opt[k]}
    assert diffs == KNOWN_INFINITE_DECK_DIFFS


def test_house_edge_and_rule_effects(exact):
    h17 = exact.round_ev()
    s17 = ExactSolver(Rules(dealer_hits_soft_17=False)).round_ev()
    six_five = ExactSolver(Rules(blackjack_payout=1.2)).round_ev()
    assert -0.0085 < h17 < -0.0070
    assert 0.0015 < s17 - h17 < 0.0030          # H17 costs ~0.2%
    assert 0.012 < h17 - six_five < 0.015        # 6:5 costs ~1.4%


def test_following_a_chart_never_beats_the_optimum(exact):
    assert ExactSolver(policy=reference_chart()).round_ev() <= exact.round_ev() + 1e-12


# --------------------------------------------------------------- Monte Carlo
@pytest.fixture(scope="module")
def mc():
    return solve(n=60_000, seed=11, processes=1)


def exact_evs(exact, key):
    kind, t, up = key
    tb = exact.tables(up)
    return tb.pair_evs(t) if kind == "pair" else tb.action_evs(t, kind == "soft")


def test_mc_estimates_are_unbiased(exact, mc):
    z = []
    for key, st in mc.states.items():
        e = exact_evs(exact, key)
        for a, est in st.evs.items():
            if a in e and not math.isnan(e[a]) and est.se > 0:
                z.append((est.mean - e[a]) / est.se)
    z = np.array(z)
    assert abs(z.mean()) < 0.15
    assert np.mean(np.abs(z) > 3) < 0.01


def test_mc_chart_differs_only_on_statistical_ties(exact, mc):
    opt = dict(chart_cells(exact.optimal_strategy()))
    for key, code in chart_cells(mc.strategy()):
        if code != opt[key]:
            st = mc.states[key]
            assert st.margin < 3 * st.margin_se, (key, code, opt[key])


def test_mc_chart_loses_almost_nothing(exact, mc):
    assert ExactSolver(policy=mc.strategy()).round_ev() > exact.round_ev() - 2e-4
