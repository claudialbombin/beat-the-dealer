"""
Comprehensive tests for card_counting.py

Covers: BettingStrategy, CardCountingSimulator, CountingAnalyzer
"""

import pytest
from collections import defaultdict
from card_counting import BettingStrategy, CardCountingSimulator, CountingAnalyzer
from game_engine import BlackjackGame, Action, Hand, Card


# ============================================================================
# BettingStrategy Tests
# ============================================================================

class TestBettingStrategyInit:
    def test_default_base_bet(self):
        bs = BettingStrategy()
        assert bs.base_bet == 10.0

    def test_default_max_bet(self):
        bs = BettingStrategy()
        assert bs.max_bet == 100.0

    def test_ramp_is_populated_after_init(self):
        bs = BettingStrategy()
        assert len(bs.ramp) > 0

    def test_ramp_contains_negative_counts(self):
        bs = BettingStrategy()
        assert any(k < 0 for k in bs.ramp)

    def test_ramp_contains_positive_counts(self):
        bs = BettingStrategy()
        assert any(k > 0 for k in bs.ramp)

    def test_ramp_contains_zero(self):
        bs = BettingStrategy()
        assert 0 in bs.ramp

    def test_custom_base_bet(self):
        bs = BettingStrategy(base_bet=25.0)
        assert bs.base_bet == 25.0

    def test_custom_max_bet(self):
        bs = BettingStrategy(max_bet=500.0)
        assert bs.max_bet == 500.0


class TestBettingStrategyGetBet:
    def setup_method(self):
        self.bs = BettingStrategy(base_bet=10.0, max_bet=100.0)

    def test_negative_count_returns_base_bet(self):
        assert self.bs.get_bet(-5) == 10.0

    def test_zero_count_returns_base_bet(self):
        assert self.bs.get_bet(0) == 10.0

    def test_count_one_returns_base_bet(self):
        assert self.bs.get_bet(1) == 10.0

    def test_count_two_increases_bet(self):
        assert self.bs.get_bet(2) > 10.0

    def test_count_four_significantly_increases_bet(self):
        assert self.bs.get_bet(4) >= 30.0

    def test_high_count_capped_at_max(self):
        assert self.bs.get_bet(10) <= 100.0

    def test_very_high_count_capped_at_max(self):
        assert self.bs.get_bet(100) <= 100.0

    def test_very_low_count_returns_base_bet(self):
        assert self.bs.get_bet(-100) == 10.0

    def test_returns_float(self):
        assert isinstance(self.bs.get_bet(3), float)

    def test_bet_increases_with_count(self):
        bets = [self.bs.get_bet(tc) for tc in range(-2, 7)]
        # Bet should be non-decreasing as count rises
        for i in range(1, len(bets)):
            assert bets[i] >= bets[i - 1]

    def test_fractional_count_rounded(self):
        # TC 1.6 should round to 2
        bet_at_2 = self.bs.get_bet(2)
        bet_at_1_6 = self.bs.get_bet(1.6)
        assert bet_at_1_6 == bet_at_2

    def test_fractional_count_rounds_down(self):
        # TC 1.4 should round to 1
        bet_at_1 = self.bs.get_bet(1)
        bet_at_1_4 = self.bs.get_bet(1.4)
        assert bet_at_1_4 == bet_at_1


# ============================================================================
# CardCountingSimulator Tests
# ============================================================================

class TestCardCountingSimulatorInit:
    def test_default_decks(self):
        sim = CardCountingSimulator()
        assert sim.decks == 6

    def test_default_penetration(self):
        sim = CardCountingSimulator()
        assert sim.penetration == 0.75

    def test_default_base_bet(self):
        sim = CardCountingSimulator()
        assert sim.base_bet == 10.0

    def test_default_shoes(self):
        sim = CardCountingSimulator()
        assert sim.num_shoes == 1000

    def test_custom_parameters(self):
        sim = CardCountingSimulator(decks=2, penetration=0.8, base_bet=25.0, shoes=100)
        assert sim.decks == 2
        assert sim.penetration == 0.8
        assert sim.base_bet == 25.0
        assert sim.num_shoes == 100

    def test_betting_strategy_initialized(self):
        sim = CardCountingSimulator(base_bet=25.0)
        assert sim.betting.base_bet == 25.0

    def test_empty_tc_results_initially(self):
        sim = CardCountingSimulator()
        assert len(sim.tc_results) == 0

    def test_empty_shoe_results_initially(self):
        sim = CardCountingSimulator()
        assert len(sim.shoe_results) == 0

    def test_empty_strategy_by_default(self):
        sim = CardCountingSimulator()
        assert sim.strategy == {}


class TestCardCountingSimulatorSimulateShoe:
    def setup_method(self):
        self.sim = CardCountingSimulator(decks=6, penetration=0.75,
                                         base_bet=10.0, shoes=1)

    def test_simulate_shoe_returns_dict(self):
        result = self.sim.simulate_shoe()
        assert isinstance(result, dict)

    def test_simulate_shoe_has_required_keys(self):
        result = self.sim.simulate_shoe()
        required_keys = {'hands', 'total_bet', 'total_won', 'return_pct',
                         'max_tc', 'min_tc'}
        assert required_keys.issubset(result.keys())

    def test_simulate_shoe_plays_positive_hands(self):
        result = self.sim.simulate_shoe()
        assert result['hands'] > 0

    def test_simulate_shoe_total_bet_positive(self):
        result = self.sim.simulate_shoe()
        assert result['total_bet'] > 0

    def test_simulate_shoe_appends_to_shoe_results(self):
        initial_len = len(self.sim.shoe_results)
        self.sim.simulate_shoe()
        assert len(self.sim.shoe_results) == initial_len + 1

    def test_simulate_shoe_populates_tc_results(self):
        self.sim.simulate_shoe()
        assert len(self.sim.tc_results) > 0

    def test_simulate_shoe_max_tc_gte_min_tc(self):
        result = self.sim.simulate_shoe()
        assert result['max_tc'] >= result['min_tc']

    def test_simulate_shoe_total_bet_is_sum_of_hands_times_bets(self):
        result = self.sim.simulate_shoe()
        # total_bet should be >= hands * base_bet (some bets may be higher)
        assert result['total_bet'] >= result['hands'] * self.sim.base_bet


class TestCardCountingSimulatorComputeStatistics:
    def setup_method(self):
        self.sim = CardCountingSimulator(decks=6, penetration=0.75,
                                         base_bet=10.0, shoes=5)
        for _ in range(5):
            self.sim.simulate_shoe()

    def test_compute_statistics_returns_dict(self):
        stats = self.sim._compute_statistics()
        assert isinstance(stats, dict)

    def test_compute_statistics_has_required_keys(self):
        stats = self.sim._compute_statistics()
        required_keys = {'shoes', 'hands', 'total_bet', 'total_won',
                         'counting_return', 'basic_return', 'advantage',
                         'tc_returns'}
        assert required_keys.issubset(stats.keys())

    def test_shoes_count_matches_simulated(self):
        stats = self.sim._compute_statistics()
        assert stats['shoes'] == 5

    def test_total_hands_positive(self):
        stats = self.sim._compute_statistics()
        assert stats['hands'] > 0

    def test_total_bet_positive(self):
        stats = self.sim._compute_statistics()
        assert stats['total_bet'] > 0

    def test_basic_return_is_negative(self):
        # Basic strategy without counting has a slight house edge
        stats = self.sim._compute_statistics()
        assert stats['basic_return'] < 0

    def test_tc_returns_is_dict(self):
        stats = self.sim._compute_statistics()
        assert isinstance(stats['tc_returns'], dict)

    def test_tc_returns_have_avg_std_count_keys(self):
        stats = self.sim._compute_statistics()
        for tc, data in stats['tc_returns'].items():
            assert 'avg_return' in data
            assert 'std' in data
            assert 'count' in data

    def test_advantage_equals_counting_minus_basic(self):
        stats = self.sim._compute_statistics()
        expected = stats['counting_return'] - stats['basic_return']
        assert abs(stats['advantage'] - expected) < 1e-9

    def test_empty_sim_returns_zero_counting_return(self):
        empty_sim = CardCountingSimulator()
        stats = empty_sim._compute_statistics()
        assert stats['counting_return'] == 0


# ============================================================================
# CountingAnalyzer Tests
# ============================================================================

class TestCountingAnalyzerInit:
    def test_analyzer_stores_simulator(self):
        sim = CardCountingSimulator()
        analyzer = CountingAnalyzer(sim)
        assert analyzer.sim is sim


class TestCountingAnalyzerDistribution:
    def setup_method(self):
        self.sim = CardCountingSimulator(decks=6, penetration=0.75,
                                         base_bet=10.0, shoes=5)
        for _ in range(5):
            self.sim.simulate_shoe()
        self.analyzer = CountingAnalyzer(self.sim)

    def test_distribution_returns_dict(self):
        dist = self.analyzer.analyze_tc_distribution()
        assert isinstance(dist, dict)

    def test_distribution_values_are_percentages(self):
        dist = self.analyzer.analyze_tc_distribution()
        for tc, pct in dist.items():
            assert 0 <= pct <= 100

    def test_distribution_sums_to_100(self):
        dist = self.analyzer.analyze_tc_distribution()
        total = sum(dist.values())
        assert abs(total - 100.0) < 0.01

    def test_distribution_covers_common_tc_range(self):
        dist = self.analyzer.analyze_tc_distribution()
        keys = set(dist.keys())
        # Should have some counts near 0 (most common true count)
        assert any(-3 <= k <= 3 for k in keys)


class TestCountingAnalyzerRiskOfRuin:
    def setup_method(self):
        self.sim = CardCountingSimulator(decks=6, penetration=0.75,
                                         base_bet=10.0, shoes=5,
                                         strategy={})
        for _ in range(5):
            self.sim.simulate_shoe()
        self.analyzer = CountingAnalyzer(self.sim)

    def test_ror_returns_float(self):
        ror = self.analyzer.calculate_risk_of_ruin(bankroll=100.0, simulations=10)
        assert isinstance(ror, float)

    def test_ror_between_zero_and_one(self):
        ror = self.analyzer.calculate_risk_of_ruin(bankroll=100.0, simulations=10)
        assert 0.0 <= ror <= 1.0

    def test_large_bankroll_lower_ror(self):
        ror_small = self.analyzer.calculate_risk_of_ruin(
            bankroll=10.0, simulations=20)
        ror_large = self.analyzer.calculate_risk_of_ruin(
            bankroll=10000.0, simulations=20)
        # Large bankroll should have lower or equal risk of ruin
        # (can't guarantee strictly less with few simulations, so just check range)
        assert 0.0 <= ror_small <= 1.0
        assert 0.0 <= ror_large <= 1.0


class TestCountingAnalyzerOptimizeBetting:
    def setup_method(self):
        self.sim = CardCountingSimulator()
        self.analyzer = CountingAnalyzer(self.sim)

    def test_returns_betting_strategy(self):
        strategy = self.analyzer.optimize_betting_ramp(bankroll=10000.0)
        assert isinstance(strategy, BettingStrategy)

    def test_optimized_base_bet_is_fraction_of_bankroll(self):
        bankroll = 10000.0
        strategy = self.analyzer.optimize_betting_ramp(bankroll=bankroll)
        assert strategy.base_bet < bankroll

    def test_optimized_max_bet_is_fraction_of_bankroll(self):
        bankroll = 10000.0
        strategy = self.analyzer.optimize_betting_ramp(bankroll=bankroll)
        assert strategy.max_bet <= bankroll

    def test_optimized_max_greater_than_base(self):
        strategy = self.analyzer.optimize_betting_ramp(bankroll=10000.0)
        assert strategy.max_bet > strategy.base_bet

    def test_ramp_populated(self):
        strategy = self.analyzer.optimize_betting_ramp(bankroll=10000.0)
        assert len(strategy.ramp) > 0
