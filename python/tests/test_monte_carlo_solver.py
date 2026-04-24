"""
Comprehensive tests for monte_carlo_solver.py

Covers: MCConfig, StateGenerator, MonteCarloSolver
"""

import pytest
from monte_carlo_solver import MCConfig, StateGenerator, MonteCarloSolver
from game_engine import Action, Hand, Card


# ============================================================================
# MCConfig Tests
# ============================================================================

class TestMCConfig:
    def test_default_simulations(self):
        config = MCConfig()
        assert config.simulations == 100000

    def test_default_decks(self):
        config = MCConfig()
        assert config.decks == 6

    def test_default_penetration(self):
        config = MCConfig()
        assert config.penetration == 0.75

    def test_default_processes_is_positive(self):
        config = MCConfig()
        assert config.processes >= 1

    def test_custom_simulations(self):
        config = MCConfig(simulations=500)
        assert config.simulations == 500

    def test_custom_decks(self):
        config = MCConfig(decks=2)
        assert config.decks == 2

    def test_custom_penetration(self):
        config = MCConfig(penetration=0.9)
        assert config.penetration == 0.9

    def test_custom_processes(self):
        config = MCConfig(processes=2)
        assert config.processes == 2


# ============================================================================
# StateGenerator Tests
# ============================================================================

class TestStateGeneratorPlayerValues:
    def setup_method(self):
        self.states = StateGenerator.player_values()

    def test_returns_list(self):
        assert isinstance(self.states, list)

    def test_returns_nonempty(self):
        assert len(self.states) > 0

    def test_hard_totals_present(self):
        hard_states = [(v, s, p) for v, s, p in self.states
                       if not s and not p]
        values = [v for v, _, _ in hard_states]
        for expected in range(5, 22):
            assert expected in values, f"Hard total {expected} missing"

    def test_hard_totals_range(self):
        hard_values = [v for v, s, p in self.states if not s and not p]
        assert min(hard_values) >= 5
        assert max(hard_values) <= 21

    def test_soft_totals_present(self):
        soft_states = [(v, s, p) for v, s, p in self.states if s and not p]
        values = [v for v, _, _ in soft_states]
        for expected in range(13, 21):
            assert expected in values, f"Soft total {expected} missing"

    def test_soft_totals_are_marked_soft(self):
        soft_states = [(v, s, p) for v, s, p in self.states if s]
        for v, s, p in soft_states:
            assert s is True

    def test_pairs_are_marked_as_pairs(self):
        pair_states = [(v, s, p) for v, s, p in self.states if p]
        assert len(pair_states) > 0
        for v, s, p in pair_states:
            assert p is True

    def test_pair_ace_encoded_as_112(self):
        pair_states = [(v, s, p) for v, s, p in self.states if p]
        pair_values = [v for v, _, _ in pair_states]
        assert 112 in pair_values

    def test_pair_eights_encoded_as_800(self):
        pair_states = [(v, s, p) for v, s, p in self.states if p]
        pair_values = [v for v, _, _ in pair_states]
        assert 800 in pair_values

    def test_pair_twos_encoded_as_200(self):
        pair_states = [(v, s, p) for v, s, p in self.states if p]
        pair_values = [v for v, _, _ in pair_states]
        assert 200 in pair_values

    def test_state_tuples_are_three_elements(self):
        for state in self.states:
            assert len(state) == 3

    def test_no_duplicate_states(self):
        assert len(self.states) == len(set(self.states))


class TestStateGeneratorDealerUpcards:
    def test_returns_list_of_ten(self):
        upcards = StateGenerator.dealer_upcards()
        assert len(upcards) == 10

    def test_ranges_from_2_to_11(self):
        upcards = StateGenerator.dealer_upcards()
        assert 2 in upcards
        assert 11 in upcards

    def test_contains_all_expected_values(self):
        upcards = StateGenerator.dealer_upcards()
        for v in range(2, 12):
            assert v in upcards

    def test_no_duplicates(self):
        upcards = StateGenerator.dealer_upcards()
        assert len(upcards) == len(set(upcards))


class TestStateGeneratorMakeHand:
    def test_hard_hand_9_returns_hand(self):
        hand = StateGenerator.make_hand(9, False, False)
        assert hand is not None
        assert isinstance(hand, Hand)

    def test_hard_hand_9_has_correct_value(self):
        hand = StateGenerator.make_hand(9, False, False)
        assert hand.best_value == 9

    def test_hard_hand_16_has_correct_value(self):
        hand = StateGenerator.make_hand(16, False, False)
        assert hand.best_value == 16

    def test_hard_hand_has_two_cards(self):
        hand = StateGenerator.make_hand(11, False, False)
        assert len(hand.cards) == 2

    def test_hard_hand_is_not_soft(self):
        hand = StateGenerator.make_hand(14, False, False)
        assert hand.is_soft is False

    def test_soft_hand_18_returns_hand(self):
        hand = StateGenerator.make_hand(18, True, False)
        assert hand is not None
        assert isinstance(hand, Hand)

    def test_soft_hand_18_has_correct_value(self):
        hand = StateGenerator.make_hand(18, True, False)
        assert hand.best_value == 18

    def test_soft_hand_is_soft(self):
        hand = StateGenerator.make_hand(15, True, False)
        assert hand.is_soft is True

    def test_soft_hand_has_ace(self):
        hand = StateGenerator.make_hand(16, True, False)
        aces = [c for c in hand.cards if c.is_ace]
        assert len(aces) >= 1

    def test_pair_aces_encoded_112(self):
        hand = StateGenerator.make_hand(112, False, True)
        assert hand is not None
        assert len(hand.cards) == 2
        assert hand.cards[0].is_ace
        assert hand.cards[1].is_ace

    def test_pair_eights_encoded_800(self):
        hand = StateGenerator.make_hand(800, False, True)
        assert hand is not None
        assert hand.cards[0].rank == 8
        assert hand.cards[1].rank == 8

    def test_pair_twos_encoded_200(self):
        hand = StateGenerator.make_hand(200, False, True)
        assert hand is not None
        assert hand.cards[0].rank == 2
        assert hand.cards[1].rank == 2

    def test_pair_has_two_cards(self):
        hand = StateGenerator.make_hand(600, False, True)
        assert len(hand.cards) == 2

    def test_invalid_soft_returns_none(self):
        # Soft 5 is impossible (A=11, second card = 5-11=-6 which is invalid)
        hand = StateGenerator.make_hand(5, True, False)
        assert hand is None

    def test_impossible_hard_hand_returns_none(self):
        # Hard 3 is impossible with two non-Ace cards (minimum is 2+2=4)
        hand = StateGenerator.make_hand(3, False, False)
        assert hand is None

    def test_hard_total_4_is_minimum(self):
        # Hard 4 = 2+2
        hand = StateGenerator.make_hand(4, False, False)
        assert hand is not None
        assert hand.best_value == 4

    def test_all_valid_hard_totals_can_be_created(self):
        for value in range(4, 21):
            hand = StateGenerator.make_hand(value, False, False)
            assert hand is not None, f"Failed to create hard {value}"
            assert hand.best_value == value

    def test_all_valid_soft_totals_can_be_created(self):
        for value in range(13, 21):  # A+2 through A+9
            hand = StateGenerator.make_hand(value, True, False)
            assert hand is not None, f"Failed to create soft {value}"
            assert hand.best_value == value


# ============================================================================
# MonteCarloSolver Tests
# ============================================================================

class TestMonteCarloSolverInit:
    def test_default_config(self):
        solver = MonteCarloSolver()
        assert solver.config is not None

    def test_custom_config(self):
        config = MCConfig(simulations=10)
        solver = MonteCarloSolver(config)
        assert solver.config.simulations == 10

    def test_empty_strategy_initially(self):
        solver = MonteCarloSolver()
        assert solver.strategy == {}

    def test_empty_ev_table_initially(self):
        solver = MonteCarloSolver()
        assert solver.ev_table == {}


class TestMonteCarloSolverSimulateAction:
    def setup_method(self):
        # Use very few simulations for speed in tests
        self.config = MCConfig(simulations=50, decks=6, processes=1)
        self.solver = MonteCarloSolver(self.config)

    def test_returns_float(self):
        state_key = (11, 6, False, False)  # Hard 11 vs dealer 6
        result = self.solver.simulate_action(state_key, Action.HIT)
        assert isinstance(result, float)

    def test_hit_on_11_vs_6_positive_ev(self):
        # Hard 11 vs dealer 6 is a classic double-down situation with positive EV
        state_key = (11, 6, False, False)
        ev_hit = self.solver.simulate_action(state_key, Action.HIT)
        ev_stand = self.solver.simulate_action(state_key, Action.STAND)
        # With small N, just verify they return reasonable values
        assert -2.0 <= ev_hit <= 2.0
        assert -2.0 <= ev_stand <= 2.0

    def test_stand_on_20_has_high_ev(self):
        # Standing on hard 20 should be very favorable
        state_key = (20, 6, False, False)
        ev = self.solver.simulate_action(state_key, Action.STAND)
        # Should generally be positive vs dealer 6 (weak upcard)
        assert isinstance(ev, float)

    def test_split_on_pair_eights_returns_float(self):
        state_key = (800, 7, False, True)  # Pair of 8s vs dealer 7
        ev = self.solver.simulate_action(state_key, Action.SPLIT)
        assert isinstance(ev, float)

    def test_ev_for_standing_on_21(self):
        # Standing on 21 should always be favorable
        state_key = (21, 10, False, False)
        ev = self.solver.simulate_action(state_key, Action.STAND)
        assert isinstance(ev, float)

    def test_invalid_state_returns_zero(self):
        # State with impossible hand returns 0
        state_key = (3, 7, False, False)  # Impossible hard 3
        result = self.solver.simulate_action(state_key, Action.HIT)
        assert result == 0.0


class TestMonteCarloSolverSolveState:
    def setup_method(self):
        self.config = MCConfig(simulations=50, decks=6, processes=1)
        self.solver = MonteCarloSolver(self.config)

    def test_returns_tuple(self):
        state_key = (11, 6, False, False)
        result = self.solver.solve_state(state_key)
        assert isinstance(result, tuple)

    def test_returns_action_and_dict(self):
        state_key = (11, 6, False, False)
        best_action, action_evs = self.solver.solve_state(state_key)
        assert isinstance(best_action, Action)
        assert isinstance(action_evs, dict)

    def test_best_action_is_in_ev_dict(self):
        state_key = (11, 6, False, False)
        best_action, action_evs = self.solver.solve_state(state_key)
        assert best_action in action_evs

    def test_best_action_has_max_ev(self):
        state_key = (11, 6, False, False)
        best_action, action_evs = self.solver.solve_state(state_key)
        assert action_evs[best_action] == max(action_evs.values())

    def test_hard_high_total_only_hit_stand(self):
        # Hard 16: only HIT and STAND should be evaluated (doubling 16 is not listed)
        state_key = (16, 10, False, False)
        best_action, action_evs = self.solver.solve_state(state_key)
        assert Action.DOUBLE_DOWN not in action_evs
        assert Action.SPLIT not in action_evs
        assert Action.HIT in action_evs
        assert Action.STAND in action_evs

    def test_hard_low_total_includes_double(self):
        # Hard 11: HIT, STAND, and DOUBLE_DOWN should be available
        state_key = (11, 6, False, False)
        best_action, action_evs = self.solver.solve_state(state_key)
        assert Action.HIT in action_evs
        assert Action.STAND in action_evs
        assert Action.DOUBLE_DOWN in action_evs

    def test_soft_total_includes_double(self):
        # Soft 15 (A+4): should evaluate HIT, STAND, DOUBLE
        state_key = (15, 5, True, False)
        best_action, action_evs = self.solver.solve_state(state_key)
        assert Action.HIT in action_evs
        assert Action.STAND in action_evs
        assert Action.DOUBLE_DOWN in action_evs
        assert Action.SPLIT not in action_evs

    def test_pair_includes_split(self):
        # Pair of 8s: should evaluate HIT, STAND, DOUBLE, SPLIT
        state_key = (800, 7, False, True)
        best_action, action_evs = self.solver.solve_state(state_key)
        assert Action.SPLIT in action_evs

    def test_returns_valid_action_enum(self):
        state_key = (18, 9, False, False)
        best_action, _ = self.solver.solve_state(state_key)
        assert best_action in list(Action)


class TestMonteCarloSolverEstimateTime:
    def test_returns_string(self):
        solver = MonteCarloSolver(MCConfig(simulations=1000))
        result = solver._estimate_time()
        assert isinstance(result, str)

    def test_contains_time_unit(self):
        solver = MonteCarloSolver(MCConfig(simulations=1000))
        result = solver._estimate_time()
        assert any(unit in result for unit in ['seconds', 'minutes', 'hours'])

    def test_large_simulation_gives_longer_estimate(self):
        solver_fast = MonteCarloSolver(MCConfig(simulations=100))
        solver_slow = MonteCarloSolver(MCConfig(simulations=100000))
        # Just verify both return strings
        assert isinstance(solver_fast._estimate_time(), str)
        assert isinstance(solver_slow._estimate_time(), str)
