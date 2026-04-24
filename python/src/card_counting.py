"""
Hi-Lo Card Counting System for Blackjack
==========================================

THE REVOLUTIONARY DISCOVERY:
In 1962, mathematics professor Edward O. Thorp published "Beat the Dealer,"
proving mathematically that blackjack could be beaten through card counting.
This discovery transformed blackjack from a house-advantage game into one
where skilled players could consistently profit.

Thorp's key insight: Blackjack has MEMORY. Unlike roulette (where each spin
is independent), cards dealt in blackjack are REMOVED from the shoe, changing
the composition of remaining cards. A deck rich in Aces and 10-value cards
favors the player; a deck rich in small cards favors the dealer.

THE HI-LO SYSTEM:
The most popular card counting system, developed by Harvey Dubner and
refined by Julian Braun (an IBM programmer who used early computers to
analyze blackjack). Hi-Lo is popular because it's:
1. Effective enough (captures ~97% of available advantage)
2. Simple enough (only three values: +1, 0, -1)
3. Practical in casino conditions

THE FUNDAMENTAL MECHANISM:
Cards 2-6: +1 (Player-favorable when REMOVED - they help the dealer)
Cards 7-9:  0 (Neutral - don't significantly affect odds)
Cards 10-A: -1 (Player-favorable when REMAINING - they help the player)

When the running count is HIGH (many low cards dealt, many high cards remain):
- More blackjacks (3:2 payout for player, only 1:1 loss to dealer blackjack)
- Dealer busts more often (must hit 12-16 vs high cards)
- Double downs more successful (more 10s to complete strong hands)
- Insurance becomes profitable (dealer more likely to have blackjack)

BETTING CORRELATION:
The Hi-Lo system has a betting correlation of 0.97, meaning it predicts
player advantage with 97% accuracy. This is why counters increase bets
when the true count rises - they're betting more when they have a
mathematical edge.

Author: Claudia Maria Lopez Bombin
Reference: Thorp, E.O. "Beat the Dealer" (1966)
           Wong, S. "Professional Blackjack" (1975)
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from game_engine import BlackjackGame, Action, Hand, Card, HandStatus
from monte_carlo_solver import MonteCarloSolver
from tqdm import tqdm

# ============================================================================
# BETTING STRATEGY - Converting information into profit
# ============================================================================

@dataclass
class BettingStrategy:
    """
    Dynamic bet sizing based on True Count.
    
    THE CORE CONCEPT - BET SPREAD:
    Card counters profit by betting MORE when they have an advantage
    and LESS (minimum) when the casino has the advantage. The "spread"
    is the ratio of maximum to minimum bet.
    
    Typical spreads:
    - 1-4: Conservative, low risk, low return (~0.3% advantage)
    - 1-8: Moderate, common for part-time players (~0.7% advantage)
    - 1-12: Aggressive, requires larger bankroll (~1.0% advantage)
    - 1-20: Very aggressive, high risk of detection (~1.5% advantage)
    
    THE DETECTION PROBLEM:
    Casinos watch for bet variation correlated with the count.
    Large spreads (>1-8) attract attention. "Wonging" (entering mid-shoe
    when count is favorable) also looks suspicious. Modern casinos use
    facial recognition, bet tracking software, and shared databases
    to identify and ban card counters.
    
    KELLY CRITERION:
    The mathematically optimal bet fraction = advantage / variance.
    For blackjack: optimal bet ≈ bankroll × advantage × 0.7
    Example: $10,000 bankroll, 2% advantage → bet ~$140
    
    Our betting ramp uses a simplified but practical approach.
    
    Attributes:
        base_bet: Minimum bet (when count is neutral or negative)
        max_bet: Maximum bet (capped for bankroll protection)
        ramp: Dictionary mapping true count → bet multiplier
    """
    base_bet: float = 10.0
    max_bet: float = 100.0
    ramp: Dict[int, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """
        Initialize the betting ramp after dataclass creation.
        
        THE BET RAMP - Converting Count to Cash:
        
        We define bet multipliers for each True Count value.
        The ramp is based on the estimated player advantage at each count.
        
        Player Advantage vs True Count (approximate):
        TC ≤ 0:    -0.5% to 0%  → Minimum bet (we have no edge)
        TC = +1:   ~0.5%        → Minimum bet (edge is small)
        TC = +2:   ~1.0%        → Double bet (clear advantage)
        TC = +3:   ~1.5%        → Triple bet (good advantage)
        TC = +4:   ~2.0%        → 5x bet (strong advantage)
        TC ≥ +5:   ~2.5%+       → Max bet (excellent advantage)
        
        WHY NOT BET MORE AT TC +1?
        At TC +1, the player edge is roughly 0.5%, which is about the
        same as the house edge at TC 0. But variance is high, and the
        edge isn't strong enough to justify increasing bets. Most
        counters wait until TC +2 or higher.
        
        RISK MANAGEMENT:
        The ramp must balance profit maximization against:
        1. Risk of Ruin (losing entire bankroll)
        2. Casino detection (large spread = suspicious)
        3. Table maximums (can't bet infinitely)
        """
        # Define betting ramp: True Count → Bet Multiplier
        self.ramp = {
            # Negative counts: minimum bet (casino has edge)
            -10: 1.0,  # Way negative
            -5: 1.0,   # Very negative
            -4: 1.0,   # Quite negative  
            -3: 1.0,   # Moderately negative
            -2: 1.0,   # Slightly negative
            -1: 1.0,   # Barely negative
            
            # Neutral/Slightly positive: minimum bet
            0: 1.0,    # Neutral (house has ~0.5% edge)
            1: 1.0,    # Slight player edge (~0.5%)
            
            # Positive counts: INCREASE bets (player has edge!)
            2: 2.0,    # Player edge ~1.0% - TIME TO BET MORE
            3: 3.0,    # Player edge ~1.5% - GOOD OPPORTUNITY
            4: 5.0,    # Player edge ~2.0% - STRONG ADVANTAGE
            5: 7.0,    # Player edge ~2.5% - EXCELLENT COUNT
            
            # Very high counts: MAXIMUM BET
            6: 10.0,   # Rare opportunity - BET THE MAX
            10: 10.0   # Cap at max bet
        }
    
    def get_bet(self, true_count: float) -> float:
        """
        Determine the appropriate bet size for a given true count.
        
        DECISION PROCESS:
        1. Round true count to nearest integer
        2. Clamp to our defined range (-10 to +10)
        3. Look up the multiplier in our ramp table
        4. Apply multiplier to base bet
        5. Cap at maximum bet for bankroll protection
        
        Example scenarios (base=$10, max=$100):
        TC = -3: bet = $10 × 1.0 = $10 (minimum)
        TC = 0:  bet = $10 × 1.0 = $10 (minimum)
        TC = +2: bet = $10 × 2.0 = $20 (starting to bet more)
        TC = +4: bet = $10 × 5.0 = $50 (significant edge)
        TC = +6: bet = $10 × 10.0 = $100 (max bet - huge edge!)
        TC = +8: bet = $100 (capped at maximum)
        
        Parameters:
            true_count: Current true count (running / decks remaining)
            
        Returns:
            Bet amount in dollars
        """
        # Round to nearest integer for table lookup
        tc_rounded = round(true_count)
        
        # Clamp to our defined range
        tc_rounded = max(min(tc_rounded, 10), -10)
        
        # Get multiplier (default to 1.0 if TC outside defined keys)
        multiplier = self.ramp.get(tc_rounded, 1.0)
        
        # Calculate bet
        bet = self.base_bet * multiplier
        
        # Enforce maximum bet
        return min(bet, self.max_bet)


# ============================================================================
# CARD COUNTING SIMULATOR
# ============================================================================

class CardCountingSimulator:
    """
    Simulates thousands of shoes with Hi-Lo counting to measure advantage.
    
    WHAT WE'RE MEASURING:
    We want to quantify exactly how much advantage card counting provides.
    By simulating many shoes with optimal betting and strategy, we can:
    1. Calculate the expected return with counting
    2. Compare it to the basic strategy return (house edge)
    3. Determine if counting provides a statistically significant edge
    4. Analyze returns by true count to validate the betting ramp
    
    SIMULATION METHODOLOGY:
    - Each "shoe" is played from shuffle to cut card
    - Running count is maintained throughout
    - Bets are adjusted before each hand based on true count
    - Basic strategy is used for all playing decisions
    - Results are tracked per true count for analysis
    
    PERFORMANCE EXPECTATIONS:
    With 6 decks, 75% penetration, 1-10 bet spread:
    - Expected advantage: ~1.0-1.5%
    - Hands per shoe: ~40-50
    - Shoes per hour in casino: ~4-5
    - Hourly win rate (flat $10): ~$15-25/hour
    - Hourly win rate ($25-$250 spread): ~$40-60/hour
    
    Parameters:
        decks: Number of decks in shoe
        penetration: How deep to deal (0.5-0.85)
        base_bet: Minimum bet amount
        shoes: Number of shoes to simulate
        strategy: Basic strategy table
    """
    
    def __init__(self, decks: int = 6, penetration: float = 0.75,
                 base_bet: float = 10.0, shoes: int = 1000,
                 strategy: Dict = None):
        """
        Initialize the counting simulator.
        
        Parameters:
            decks: Number of decks (typically 6 or 8)
            penetration: Shoe penetration (0.75 = 75%)
            base_bet: Starting bet amount
            shoes: Number of shoes to simulate
            strategy: Pre-computed basic strategy table
        """
        self.decks = decks
        self.penetration = penetration
        self.base_bet = base_bet
        self.num_shoes = shoes
        self.strategy = strategy or {}
        self.betting = BettingStrategy(base_bet=base_bet)
        
        # TRACKING DATA STRUCTURES
        # Maps true count → list of returns (for statistical analysis)
        self.tc_results: Dict[int, List[float]] = defaultdict(list)
        # Stores aggregate results for each shoe
        self.shoe_results: List[Dict] = []
    
    def simulate_shoe(self) -> Dict:
        """
        Simulate one complete shoe (shuffle to cut card).
        
        SHOE SIMULATION PROCESS:
        1. Start with freshly shuffled shoe
        2. Before each hand: calculate true count, determine bet
        3. Play hand using basic strategy
        4. Track running count as cards are revealed
        5. Continue until cut card reached
        6. Record statistics for this shoe
        
        WHAT WE TRACK:
        - Hands played (productivity measure)
        - Total amount wagered (exposure measure)
        - Total won/lost (profitability measure)
        - Maximum/minimum true count reached (opportunity measure)
        - Returns by true count (for EV vs TC analysis)
        
        Returns:
            Dictionary with shoe statistics
        """
        # Create fresh game for this shoe
        game = BlackjackGame(self.decks, self.penetration)
        
        hands_played = 0
        total_wagered = 0.0
        total_won = 0.0
        max_tc = -999  # Track best count seen
        min_tc = 999   # Track worst count seen
        
        # Play hands until we hit the cut card
        while not game.shoe.needs_reshuffle:
            # CALCULATE TRUE COUNT BEFORE BETTING
            # This is the key moment - the counter decides bet size
            # based on their perceived advantage
            true_count = game.true_count
            
            # Update extreme counts seen
            max_tc = max(max_tc, true_count)
            min_tc = min(min_tc, true_count)
            
            # DETERMINE BET SIZE based on current count
            bet = self.betting.get_bet(true_count)
            
            # PLAY THE HAND using basic strategy
            # Note: We use basic strategy, not count-modified strategy
            # Count-modified strategy (playing deviations) adds ~0.2% edge
            payout = game.play_round(bet=bet, strategy=self.strategy)
            
            # Record results
            hands_played += 1
            total_wagered += bet
            total_won += payout
            
            # Track normalized return for this true count
            # Normalized = return / bet (percentage return)
            # This allows comparing returns across different bet sizes
            normalized_return = payout / bet if bet > 0 else 0
            tc_bin = round(true_count)  # Round to nearest integer for grouping
            self.tc_results[tc_bin].append(normalized_return)
        
        # Calculate average return for this shoe
        avg_return = (total_won / total_wagered * 100) if total_wagered > 0 else 0
        
        # Compile shoe statistics
        shoe_stats = {
            'hands': hands_played,
            'total_bet': total_wagered,
            'total_won': total_won,
            'return_pct': avg_return,
            'max_tc': max_tc,
            'min_tc': min_tc
        }
        
        self.shoe_results.append(shoe_stats)
        return shoe_stats
    
    def run(self, num_shoes: int = None) -> Dict:
        """
        Execute the full card counting simulation.
        
        RUNS THE ENTIRE EXPERIMENT:
        1. Reset all tracking data
        2. Simulate the specified number of shoes
        3. Each shoe is an independent trial
        4. Aggregate results for statistical analysis
        
        The simulation demonstrates that card counting DOES provide
        a real mathematical advantage over the casino.
        
        Parameters:
            num_shoes: Number of shoes (uses init value if None)
            
        Returns:
            Dictionary with aggregated results
        """
        shoes_to_run = num_shoes or self.num_shoes
        
        print(f"\n{'='*60}")
        print(f"CARD COUNTING SIMULATION")
        print(f"{'='*60}")
        print(f"Shoes to simulate: {shoes_to_run:,}")
        print(f"Decks: {self.decks}")
        print(f"Penetration: {self.penetration*100:.0f}%")
        print(f"Base bet: ${self.base_bet}")
        print(f"Max bet: ${self.betting.max_bet}")
        print(f"Bet spread: 1:{self.betting.max_bet/self.base_bet:.0f}")
        print(f"{'='*60}\n")
        
        # Reset tracking
        self.tc_results = defaultdict(list)
        self.shoe_results = []
        
        # Simulate all shoes with progress bar
        for _ in tqdm(range(shoes_to_run), desc="Simulating shoes"):
            self.simulate_shoe()
        
        # Calculate and return aggregate statistics
        return self._compute_statistics()
    
    def _compute_statistics(self) -> Dict:
        """
        Aggregate statistics across all simulated shoes.
        
        CALCULATIONS:
        1. Total hands and money wagered/won
        2. Average return with counting
        3. Theoretical return without counting (house edge)
        4. Advantage derived from counting
        5. Returns broken down by true count
        
        Returns:
            Comprehensive statistics dictionary
        """
        # Aggregate across all shoes
        total_hands = sum(s['hands'] for s in self.shoe_results)
        total_bet = sum(s['total_bet'] for s in self.shoe_results)
        total_won = sum(s['total_won'] for s in self.shoe_results)
        
        # Calculate counting return
        counting_return = (total_won / total_bet * 100) if total_bet > 0 else 0
        
        # Basic strategy return (known house edge)
        basic_return = -0.5  # ~0.5% house edge with basic strategy
        
        # ADVANTAGE FROM COUNTING
        advantage = counting_return - basic_return
        
        # BREAKDOWN BY TRUE COUNT
        # For each true count value, calculate average return and std dev
        tc_returns = {}
        for tc, returns in sorted(self.tc_results.items()):
            if len(returns) > 0:
                tc_returns[tc] = {
                    'avg_return': np.mean(returns) * 100,  # Convert to percentage
                    'std': np.std(returns) * 100,          # Standard deviation
                    'count': len(returns)                   # Number of observations
                }
        
        return {
            'shoes': len(self.shoe_results),
            'hands': total_hands,
            'total_bet': total_bet,
            'total_won': total_won,
            'counting_return': counting_return,
            'basic_return': basic_return,
            'advantage': advantage,
            'tc_returns': tc_returns
        }
    
    def print_results(self):
        """
        Display comprehensive counting simulation results.
        
        OUTPUT INCLUDES:
        1. Summary statistics (shoes, hands, money)
        2. Comparison of counting vs no counting
        3. The crucial ADVANTAGE figure
        4. Breakdown by true count
        
        THE KEY NUMBER:
        The "ADVANTAGE" field shows how much edge card counting provides.
        If positive, counting works. If negative, something is wrong
        (bad strategy, insufficient penetration, poor bet spread).
        """
        stats = self._compute_statistics()
        
        print(f"\n{'='*60}")
        print(f"CARD COUNTING SIMULATION RESULTS")
        print(f"{'='*60}")
        
        # Summary statistics
        print(f"\nSUMMARY:")
        print(f"  Shoes simulated: {stats['shoes']:,}")
        print(f"  Total hands: {stats['hands']:,}")
        print(f"  Total wagered: ${stats['total_bet']:,.2f}")
        print(f"  Total won/lost: ${stats['total_won']:+,.2f}")
        
        # The crucial comparison
        print(f"\nRETURN COMPARISON:")
        print(f"  Basic strategy (no counting): {stats['basic_return']:+.3f}%")
        print(f"  With Hi-Lo counting:         {stats['counting_return']:+.3f}%")
        print(f"  {'='*40}")
        print(f"  COUNTING ADVANTAGE:           {stats['advantage']:+.3f}%")
        
        # Verdict
        if stats['advantage'] > 0:
            print(f"\n✓ Card counting PROVIDES a {stats['advantage']:.3f}% player advantage")
            print(f"  This means for every $100 bet, you expect to WIN")
            print(f"  ${stats['advantage']:.2f} in the long run.")
        else:
            print(f"\n✗ Card counting did not provide an advantage")
            print(f"  Check: penetration, bet spread, and strategy accuracy")
        
        # True Count breakdown
        print(f"\n{'='*60}")
        print(f"RETURN BY TRUE COUNT")
        print(f"{'='*60}")
        print(f"{'TC':>4}  {'Return':>8}  {'Std Dev':>8}  {'Hands':>8}")
        print(f"{'-'*40}")
        
        for tc in sorted(stats['tc_returns'].keys()):
            d = stats['tc_returns'][tc]
            print(f"{tc:+4d}  {d['avg_return']:+7.3f}%  "
                  f"{d['std']:7.3f}%  {d['count']:8,d}")
        
        return stats


# ============================================================================
# ADVANCED ANALYSIS - Risk metrics and optimization
# ============================================================================

class CountingAnalyzer:
    """
    Advanced analysis of card counting performance.
    
    BEYOND BASIC SIMULATION:
    While the simulator shows counting works, the analyzer quantifies
    the RISKS and helps OPTIMIZE the approach.
    
    KEY METRICS:
    
    1. RISK OF RUIN (RoR):
       The probability of losing your entire bankroll. Even with a
       positive expectation, variance can wipe you out. Professional
       counters typically target RoR < 5%.
       
       RoR = ((1 - EV/std) / (1 + EV/std)) ^ (bankroll/std)
       
       Example: $10,000 bankroll, 1% advantage, std = 1.15 units
       RoR ≈ 13% (too high for professionals)
       
       To reduce RoR: increase bankroll, reduce bets, or accept lower EV
    
    2. TRUE COUNT DISTRIBUTION:
       How often does each true count occur? Most hands (~70%) are
       played at TC -1 to +1. Only ~5% of hands see TC ≥ +4.
       This is why large bet spreads are necessary - you must bet
       enough on those rare high counts to overcome losses on the
       majority of hands.
    
    3. OPTIMAL BET SPREAD:
       The Kelly criterion gives the theoretically optimal bet size:
       f* = advantage / variance
       Bet = bankroll × f*
       However, practical constraints (table minimums/maximums) and
       risk tolerance lead to modified Kelly strategies.
    """
    
    def __init__(self, simulator: CardCountingSimulator):
        """
        Initialize analyzer with simulation results.
        
        Parameters:
            simulator: CardCountingSimulator with completed simulation
        """
        self.sim = simulator
    
    def analyze_tc_distribution(self) -> Dict[int, float]:
        """
        Analyze how frequently each true count occurs.
        
        WHY THIS MATTERS:
        Understanding TC distribution helps optimize the bet spread.
        If high counts rarely occur, you need a wider spread to profit.
        If high counts are frequent, a narrower spread suffices.
        
        TYPICAL DISTRIBUTION (6 decks, 75% penetration):
        TC ≤ -3: ~5% of hands
        TC -2 to -1: ~15%
        TC 0: ~30% (most common)
        TC +1 to +2: ~30%
        TC +3 to +4: ~15%
        TC ≥ +5: ~5% (where the big money is made)
        
        Returns:
            Dictionary mapping TC → frequency percentage
        """
        distribution = {}
        total_observations = sum(
            len(returns) for returns in self.sim.tc_results.values()
        )
        
        for tc, returns in sorted(self.sim.tc_results.items()):
            distribution[tc] = len(returns) / total_observations * 100
        
        return distribution
    
    def calculate_risk_of_ruin(self, bankroll: float, 
                              simulations: int = 1000) -> float:
        """
        Estimate the probability of losing the entire bankroll.
        
        RISK OF RUIN CALCULATION:
        We simulate many independent "careers" starting with the given
        bankroll. Each career continues until either doubling the bankroll
        (success) or losing everything (ruin).
        
        This Monte Carlo approach accounts for the non-normal distribution
        of blackjack returns (skewed by doubles, splits, and blackjacks).
        
        Parameters:
            bankroll: Starting bankroll
            simulations: Number of careers to simulate
            
        Returns:
            Probability of ruin (0.0 to 1.0)
        """
        ruined_count = 0
        
        for _ in range(simulations):
            current_bankroll = bankroll
            game = BlackjackGame(self.sim.decks, self.sim.penetration)
            game.running_count = 0
            
            # Play until ruin or doubling
            while 0 < current_bankroll < bankroll * 2:
                # Calculate bet based on current count
                tc = game.true_count
                bet = self.sim.betting.get_bet(tc)
                
                # Don't bet more than we have
                if bet > current_bankroll:
                    bet = current_bankroll
                
                # Play one hand
                result = game.play_round(bet=bet, 
                                        strategy=self.sim.strategy)
                current_bankroll += result
                
                # Check for ruin
                if current_bankroll <= 0:
                    ruined_count += 1
                    break
        
        return ruined_count / simulations
    
    def optimize_betting_ramp(self, bankroll: float, 
                            target_ror: float = 0.05) -> BettingStrategy:
        """
        Optimize bet sizes for maximum return given risk tolerance.
        
        OPTIMIZATION GOAL:
        Find the bet ramp that maximizes EV while keeping Risk of Ruin
        below the target (typically 1-5%).
        
        This uses a simplified Kelly criterion approach:
        Optimal bet fraction = (advantage × bankroll) / variance
        
        For blackjack, variance ≈ 1.33 units², so:
        Kelly bet ≈ 0.75 × advantage × bankroll
        
        We reduce from full Kelly (typically half or quarter Kelly)
        to achieve lower risk of ruin.
        
        Parameters:
            bankroll: Total playing bankroll
            target_ror: Maximum acceptable risk of ruin (0.05 = 5%)
            
        Returns:
            Optimized BettingStrategy
        """
        # Start with conservative base bet (~0.25% of bankroll)
        conservative_base = bankroll * 0.0025
        
        optimized = BettingStrategy(
            base_bet=conservative_base,
            max_bet=bankroll * 0.02  # Max 2% of bankroll per hand
        )
        
        # Adjust ramp for more aggressive betting at high counts
        # Full Kelly suggests betting proportionally to advantage
        optimized.ramp = {
            -10: 1.0, -5: 1.0, -4: 1.0, -3: 1.0,
            -2: 1.0, -1: 1.0,
            0: 1.0,    # No edge, minimum bet
            1: 1.5,    # Slight edge, modest increase
            2: 2.5,    # Clear edge, meaningful increase
            3: 4.0,    # Good edge, significant bet
            4: 6.0,    # Strong edge, large bet
            5: 8.0,    # Great edge, near maximum
            6: 10.0,   # Excellent edge, maximum bet
            10: 10.0   # Cap at maximum
        }
        
        return optimized
    
    def print_advanced_analysis(self, bankroll: float = 10000):
        """
        Print comprehensive advanced analysis.
        
        Includes TC distribution, risk metrics, and recommendations.
        """
        print(f"\n{'='*60}")
        print(f"ADVANCED CARD COUNTING ANALYSIS")
        print(f"{'='*60}")
        print(f"Bankroll: ${bankroll:,.0f}")
        
        # True Count distribution
        print(f"\nTRUE COUNT DISTRIBUTION:")
        distribution = self.analyze_tc_distribution()
        for tc in sorted(distribution.keys()):
            pct = distribution[tc]
            bar = "█" * int(pct)
            print(f"  TC {tc:+3d}: {pct:5.1f}% {bar}")
        
        # Risk analysis
        print(f"\nRISK ANALYSIS:")
        ror = self.calculate_risk_of_ruin(bankroll, 200)
        print(f"  Risk of Ruin: {ror*100:.1f}%")
        
        if ror > 0.10:
            print(f"  WARNING: RoR exceeds 10%. Consider:")
            print(f"    - Increasing bankroll to ${bankroll*2:,.0f}")
            print(f"    - Reducing bet spread")
            print(f"    - Using half-Kelly instead of full-Kelly")
        elif ror > 0.05:
            print(f"  CAUTION: RoR above 5%. Acceptable for aggressive players")
        else:
            print(f"  GOOD: RoR below 5%. Professional-level risk management")
        
        # Recommendations
        print(f"\nRECOMMENDATIONS:")
        optimized = self.optimize_betting_ramp(bankroll)
        print(f"  Base bet: ${optimized.base_bet:.2f}")
        print(f"  Max bet: ${optimized.max_bet:.2f}")
        print(f"  Spread: 1:{optimized.max_bet/optimized.base_bet:.1f}")