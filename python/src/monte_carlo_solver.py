"""
Monte Carlo Solver for Basic Strategy
======================================

Computes the optimal basic strategy for blackjack through
massive Monte Carlo simulation. For each possible game state,
millions of hands are simulated to determine which action
maximizes expected value.

The result is a complete strategy table matching published
basic strategy charts.

Author: Claudia Maria Lopez Bombin
License: MIT
"""

import numpy as np
from typing import Dict, Tuple, List
from collections import defaultdict
import pickle
import os
from tqdm import tqdm
import multiprocessing as mp
from game_engine import BlackjackGame, Action, Hand, Card, HandStatus

class MCConfig:
    """Configuration for Monte Carlo simulation."""
    
    def __init__(self, simulations: int = 100000, decks: int = 6,
                 penetration: float = 0.75, processes: int = None):
        self.simulations = simulations
        self.decks = decks
        self.penetration = penetration
        self.processes = processes or mp.cpu_count()

class StateGenerator:
    """Generates all possible game states for strategy computation."""
    
    @staticmethod
    def player_values() -> List[Tuple[int, bool, bool]]:
        """
        Generate all player hand configurations.
        Returns list of (value, is_soft, is_pair) tuples.
        """
        states = []
        
        # Hard totals: 5-21
        states.extend((v, False, False) for v in range(5, 22))
        
        # Soft totals: A2-A9 → 13-20
        states.extend((v, True, False) for v in range(13, 21))
        
        # Pairs: 22,33,...,AA
        for rank in range(1, 14):
            if rank == 1:  # Ace pair
                states.append((112, False, True))
            elif rank <= 10:
                states.append((rank * 100, False, True))
        
        return states
    
    @staticmethod
    def dealer_upcards() -> List[int]:
        """Generate possible dealer upcards: 2-10, 11(Ace)."""
        return list(range(2, 12))
    
    @staticmethod
    def make_hand(value: int, soft: bool, pair: bool) -> Hand:
        """
        Create a hand matching the specified state.
        Used to initialize simulations from any state.
        """
        if pair:
            if value == 112:
                rank = 1
            else:
                rank = value // 100
            return Hand([Card(rank, "♥"), Card(rank, "♠")])
        
        if soft:
            second = value - 11
            if 2 <= second <= 10:
                return Hand([Card(1, "♥"), Card(second, "♠")])
            return None
        
        # Hard total: find two non-ace cards summing to value
        for r1 in range(2, 11):
            for r2 in range(2, 11):
                if r1 + r2 == value:
                    return Hand([Card(r1, "♥"), Card(r2, "♠")])
        return None

class MonteCarloSolver:
    """
    Main Monte Carlo solver for blackjack basic strategy.
    
    Computes expected value for each (state, action) pair
    through simulation and selects the optimal action.
    """
    
    def __init__(self, config: MCConfig = None):
        self.config = config or MCConfig()
        self.strategy: Dict[Tuple, Action] = {}
        self.ev_table: Dict[Tuple, Dict[Action, float]] = {}
    
    def simulate_action(self, state_key: Tuple, 
                       action: Action) -> float:
        """
        Simulate a specific action from a game state.
        Returns expected value through Monte Carlo estimation.
        """
        pv, du, soft, pair = state_key
        total_return = 0.0
        successes = 0
        
        for _ in range(self.config.simulations):
            game = BlackjackGame(self.config.decks, 1.0)
            
            # Create player hand for this state
            player_hand = StateGenerator.make_hand(pv, soft, pair)
            if player_hand is None:
                continue
            
            # Create dealer upcard
            dealer_up = Card(du if du <= 10 else 1, "♣")
            dealer_hand = Hand([dealer_up])
            player_hand.bet = 1.0
            
            try:
                # Execute the action
                result_hands = game.execute_action(
                    player_hand, action, dealer_up
                )
                
                # Complete remaining hands with simple strategy
                for hand in result_hands:
                    if hand.status == HandStatus.ACTIVE:
                        while hand.best_value < 17:
                            card = game.shoe.deal()
                            if card is None:
                                break
                            hand.add(card)
                        if hand.status == HandStatus.ACTIVE:
                            hand.status = HandStatus.STANDING
                
                # Complete dealer hand
                second = game.shoe.deal()
                if second:
                    dealer_hand.add(second)
                game.play_dealer(dealer_hand)
                
                # Calculate payout
                for hand in result_hands:
                    total_return += game.calculate_payout(
                        hand, dealer_hand
                    )
                successes += 1
                
            except Exception:
                continue
        
        return total_return / successes if successes else 0.0
    
    def solve_state(self, state_key: Tuple) -> Tuple[Action, Dict]:
        """Find best action for a specific game state."""
        pv, du, soft, pair = state_key
        
        # Determine applicable actions
        if pair:
            actions = [Action.HIT, Action.STAND, 
                      Action.DOUBLE_DOWN, Action.SPLIT]
        elif soft:
            actions = [Action.HIT, Action.STAND, Action.DOUBLE_DOWN]
        elif pv >= 12:
            actions = [Action.HIT, Action.STAND]
        else:
            actions = [Action.HIT, Action.STAND, Action.DOUBLE_DOWN]
        
        # Evaluate each action
        evs = {}
        for action in actions:
            evs[action] = self.simulate_action(state_key, action)
        
        # Select best
        best = max(evs, key=evs.get)
        return best, evs
    
    def build_strategy_table(self, use_cache: bool = True) -> Dict:
        """Build complete basic strategy table."""
        
        cache_file = f'data/strategy_{self.config.simulations}.pkl'
        
        if use_cache and os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
                self.strategy = data['strategy']
                self.ev_table = data['evs']
                return self.strategy
        
        print(f"Building strategy table: {self.config.simulations:,} "
              f"simulations per state")
        
        # Generate all states
        states = []
        for pv, soft, pair in StateGenerator.player_values():
            for du in StateGenerator.dealer_upcards():
                states.append((pv, du, soft, pair))
        
        print(f"Total states: {len(states)}")
        
        # Solve in parallel
        with mp.Pool(self.config.processes) as pool:
            results = list(tqdm(
                pool.imap(self.solve_state, states),
                total=len(states),
                desc="Evaluating states"
            ))
        
        # Build tables
        for state_key, (best_action, action_evs) in zip(states, results):
            self.strategy[state_key] = best_action
            self.ev_table[state_key] = action_evs
        
        # Cache results
        os.makedirs('data', exist_ok=True)
        with open(cache_file, 'wb') as f:
            pickle.dump({
                'strategy': self.strategy,
                'evs': self.ev_table
            }, f)
        
        return self.strategy
    
    def print_strategy(self):
        """Display the complete strategy table."""
        if not self.strategy:
            print("No strategy computed yet.")
            return
        
        dealer_vals = list(range(2, 12))
        
        # Hard totals
        print("\n" + "="*60)
        print("BASIC STRATEGY - HARD TOTALS")
        print("="*60)
        header = "Player".ljust(8)
        for dv in dealer_vals:
            header += f"{dv if dv <= 10 else 'A'}".rjust(6)
        print(header)
        print("-"*60)
        
        for pv in range(5, 22):
            row = str(pv).ljust(8)
            for dv in dealer_vals:
                action = self.strategy.get((pv, dv, False, False), 
                                          Action.STAND)
                row += f"{action.value}".rjust(6)
            print(row)
        
        # Soft totals
        print("\n" + "="*60)
        print("BASIC STRATEGY - SOFT TOTALS")
        print("="*60)
        print(header)
        print("-"*60)
        
        for pv in range(13, 21):
            row = f"A{pv-11}".ljust(8)
            for dv in dealer_vals:
                action = self.strategy.get((pv, dv, True, False),
                                          Action.STAND)
                row += f"{action.value}".rjust(6)
            print(row)
        
        # Pairs
        print("\n" + "="*60)
        print("BASIC STRATEGY - PAIRS")
        print("="*60)
        print(header)
        print("-"*60)
        
        pairs = [(1, 'A')] + [(i, str(i)) for i in range(2, 11)]
        for rank, label in pairs:
            state_base = 112 if rank == 1 else rank * 100
            row = f"{label},{label}".ljust(8)
            for dv in dealer_vals:
                action = self.strategy.get((state_base, dv, False, True),
                                          Action.STAND)
                row += f"{action.value}".rjust(6)
            print(row)
    
    def calculate_basic_ev(self, num_hands: int = 100000) -> float:
        """Calculate expected value of basic strategy."""
        total = 0.0
        
        for _ in tqdm(range(num_hands), desc="Computing basic EV"):
            game = BlackjackGame(self.config.decks)
            result = game.play_round(1.0, self.strategy)
            total += result
        
        return (total / num_hands) * 100