import numpy as np
import pytest

from blackjack.counting import BinStats, CountingResult, ramp_summary, risk_of_ruin, simulate, tc_bin
from blackjack.rules import Rules
from blackjack.strategy import reference_chart


@pytest.fixture(scope="module")
def sim():
    return simulate(Rules(), reference_chart(), rounds=150_000, seed=5)


def test_tc_binning():
    assert tc_bin(2.7) == 2 and tc_bin(-0.2) == -1 and tc_bin(40) == 10


def test_house_edge_in_expected_range(sim):
    o = sim.overall
    # Exact infinite-deck value is -0.79%; the finite shoe is slightly better.
    assert abs(o.mean - (-0.0075)) < 4 * o.se


def test_ev_rises_with_true_count(sim):
    tcs = [tc for tc, b in sim.bins.items() if b.n > 2000]
    means = [sim.bins[tc].mean for tc in tcs]
    weights = [sim.bins[tc].n for tc in tcs]
    slope = np.polyfit(tcs, means, 1, w=np.sqrt(weights))[0]
    assert 0.002 < slope < 0.009   # roughly +0.5% per true count


def test_flat_ramp_reproduces_overall_edge(sim):
    flat = ramp_summary(sim, {tc: 1.0 for tc in range(-10, 11)})
    assert flat.edge == pytest.approx(sim.overall.mean)
    assert flat.avg_bet == pytest.approx(1.0)


def test_ramp_summary_on_synthetic_data():
    r = CountingResult(bins={0: BinStats(), 2: BinStats()})
    for x in (-1, 1, -1, 1):
        r.bins[0].add(x)
    for x in (1, 1, -1, 1):
        r.bins[2].add(x)
    s = ramp_summary(r, {0: 1, 2: 4})
    assert s.ev_per_round == pytest.approx(0.5 * 0 + 0.5 * 4 * 0.5)
    assert s.avg_bet == pytest.approx(2.5)


def test_risk_of_ruin():
    assert risk_of_ruin(-0.01, 1, 100) == 1.0
    assert risk_of_ruin(0.01, 1.15, 1000) < risk_of_ruin(0.01, 1.15, 100) < 1
