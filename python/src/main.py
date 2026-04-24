"""
Blackjack Monte Carlo Solver - Main Entry Point
=================================================

PROJECT OVERVIEW:
This program demonstrates the complete pipeline for computing and
validating blackjack strategy:

1. MONTE CARLO SIMULATION: Computes the mathematically optimal basic
   strategy by simulating millions of hands from each possible game state.

2. CARD COUNTING: Implements the Hi-Lo system to track deck composition
   and dynamically adjust betting to exploit favorable situations.

3. PERFORMANCE ANALYSIS: Quantifies the advantage gained through counting
   and provides risk metrics for bankroll management.

4. VISUALIZATION: Generates professional-quality charts that clearly
   demonstrate the effectiveness of card counting.

WHY THIS IMPRESSES JANE STREET:
- Demonstrates understanding of stochastic processes
- Shows ability to optimize decisions under uncertainty
- Reveals appreciation for game theory and strategy
- Provides clean, well-documented, production-quality code
- Includes professional visualizations suitable for presentation

INTERVIEW TALKING POINTS:
- "I implemented Monte Carlo simulation to derive the optimal strategy"
- "The EV vs True Count graph empirically proves counting works"
- "I optimized the simulation with parallel processing for speed"
- "The risk of ruin analysis shows proper bankroll management"

USAGE:
    python main.py              # Interactive menu
    python main.py --full       # Run complete analysis
    python main.py --quick      # Fast mode with fewer simulations
    python main.py --demo       # Basic gameplay demonstration
    python main.py --help       # Show all options

Author: Claudia Maria Lopez Bombin
License: MIT
"""

import argparse
import sys
import os
import time
from datetime import datetime
from game_engine import BlackjackGame, HandStatus, Card
from monte_carlo_solver import MonteCarloSolver, MCConfig
from card_counting import CardCountingSimulator, CountingAnalyzer
from visualization import Visualizer


def print_project_banner():
    """
    Display an informative project banner.
    
    The banner provides context about what the project demonstrates
    and why it's relevant for quantitative finance interviews.
    """
    banner = f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║     BLACKJACK MONTE CARLO SOLVER                             ║
    ║     with Hi-Lo Card Counting System                          ║
    ║                                                              ║
    ║     Demonstrates:                                            ║
    ║     • Monte Carlo simulation methods                         ║
    ║     • Decision optimization under uncertainty                ║
    ║     • Stochastic process modeling                            ║
    ║     • Card counting algorithms (Hi-Lo)                       ║
    ║     • Statistical analysis & risk metrics                    ║
    ║     • Professional data visualization                        ║
    ║                                                              ║
    ║     Ideal for interviews with:                               ║
    ║     Jane Street | HRT | Citadel | Two Sigma | Optiver        ║
    ║                                                              ║
    ║     Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                    ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def demonstrate_basic_gameplay():
    """
    Demonstrate the basic mechanics of blackjack.
    
    This function shows a few sample hands to verify that the game
    engine is working correctly. It uses a simple strategy (hit until
    17) rather than the optimal basic strategy, so it's just for
    demonstration purposes.
    
    Each hand shows:
    - Initial deal
    - Player decisions and resulting hand
    - Dealer's play
    - Final outcome and payout
    """
    print("\n" + "="*60)
    print("DEMONSTRATION: Basic Blackjack Gameplay")
    print("="*60)
    print("Playing 5 sample hands with simple strategy (hit to 17)")
    print("-"*60)
    
    # Create a game with 6 decks
    game = BlackjackGame(num_decks=6, penetration=0.75)
    
    for hand_num in range(1, 6):
        print(f"\n{'─'*40}")
        print(f"HAND #{hand_num}")
        print(f"{'─'*40}")
        
        # Deal initial cards
        player_hand, dealer_hand = game.deal_initial(bet=10)
        
        # Show the visible cards
        print(f"Player's hand: {[str(c) for c in player_hand.cards]} "
              f"(value: {player_hand.best_value})")
        print(f"Dealer shows: {dealer_hand.cards[0]} (value: {dealer_hand.cards[0].value})")
        
        # Check for natural blackjack
        if player_hand.is_blackjack:
            print("✦ BLACKJACK! ✦")
            # Reveal dealer's full hand
            print(f"Dealer's hand: {[str(c) for c in dealer_hand.cards]} "
                  f"(value: {dealer_hand.best_value})")
            if dealer_hand.is_blackjack:
                print("Dealer also has blackjack → PUSH (tie)")
            else:
                print("Player wins 3:2!")
            continue
        
        # Player's turn - simple strategy: hit until 17
        print("\nPlayer's turn:")
        while player_hand.best_value < 17 and player_hand.status == HandStatus.ACTIVE:
            card = game.shoe.deal()
            if card is None:
                break
            player_hand.add(card)
            print(f"  HIT → receives {card} → hand value: {player_hand.best_value}")
        
        # Check result of player's decisions
        if player_hand.best_value > 21:
            print(f"  BUST! (hand value: {player_hand.best_value})")
            print("Player loses automatically")
            continue
        
        if player_hand.status == HandStatus.ACTIVE:
            player_hand.status = HandStatus.STANDING
            print(f"  STAND at {player_hand.best_value}")
        
        # Dealer's turn
        print(f"\nDealer's turn:")
        print(f"  Reveals hole card: {dealer_hand.cards[1]}")
        print(f"  Full hand: {[str(c) for c in dealer_hand.cards]} "
              f"(value: {dealer_hand.best_value})")
        
        game.play_dealer(dealer_hand)
        print(f"  Dealer {'BUSTS' if dealer_hand.best_value > 21 else 'STANDS'}"
              f" at {dealer_hand.best_value}")
        
        # Determine outcome
        payout = game.calculate_payout(player_hand, dealer_hand)
        if payout > 0:
            result = "PLAYER WINS"
        elif payout < 0:
            result = "PLAYER LOSES"
        else:
            result = "PUSH (tie)"
        
        print(f"\nRESULT: {result} | Payout: ${payout:+.2f}")
    
    print(f"\n{'='*60}")
    print("Basic demonstration complete.")
    print("Note: The strategy used here (hit to 17) is NOT optimal.")
    print("The Monte Carlo solver will compute the TRUE optimal strategy.")
    print(f"{'='*60}")


def build_basic_strategy(simulations: int = 50000, 
                        use_cache: bool = True) -> tuple:
    """
    Build the optimal basic strategy using Monte Carlo simulation.
    
    This is the computationally intensive part of the project.
    For each of ~340 game states, we simulate many hands to determine
    which action (hit, stand, double, split) maximizes expected value.
    
    THE PROCESS:
    1. Configure the Monte Carlo solver with desired accuracy
    2. Generate all possible game states
    3. Distribute state evaluations across CPU cores
    4. For each state, simulate all legal actions
    5. Select the action with highest average return
    6. Cache results for future use
    
    Parameters:
        simulations: Number of trials per state-action pair
        use_cache: Whether to load cached results if available
        
    Returns:
        Tuple of (strategy_dictionary, solver_object)
    """
    print(f"\n{'='*60}")
    print(f"PHASE 1: BUILDING BASIC STRATEGY (Monte Carlo)")
    print(f"{'='*60}")
    
    # Configure the simulation
    config = MCConfig(
        simulations=simulations,
        decks=6,
        penetration=0.75,
        processes=None  # Auto-detect CPU cores
    )
    
    # Create and run the solver
    solver = MonteCarloSolver(config)
    
    start_time = time.time()
    strategy = solver.build_strategy_table(use_cache=use_cache)
    elapsed = time.time() - start_time
    
    # Display the computed strategy
    solver.print_strategy()
    
    # Calculate the expected value
    print(f"\n{'─'*40}")
    basic_ev = solver.calculate_basic_ev(num_hands=50000)
    
    print(f"\nSTRATEGY COMPUTATION SUMMARY:")
    print(f"  Time elapsed: {elapsed:.1f} seconds")
    print(f"  States evaluated: {len(strategy)}")
    print(f"  Simulations per state: {simulations:,}")
    print(f"  Basic Strategy EV: {basic_ev:+.4f}%")
    print(f"  House Edge: {abs(basic_ev):.4f}%")
    print(f"  Theoretical house edge: ~0.5% for these rules")
    
    return strategy, solver


def simulate_card_counting(strategy: dict, 
                          shoes: int = 500,
                          base_bet: float = 10.0) -> tuple:
    """
    Simulate Hi-Lo card counting to measure player advantage.
    
    This function plays through many shoes using the computed basic
    strategy while dynamically adjusting bets based on the true count.
    It quantifies exactly how much edge card counting provides.
    
    THE EXPERIMENT:
    1. For each shoe, start with a fresh shuffle
    2. Before each hand, calculate the true count
    3. Adjust bet size based on the count
    4. Play the hand using basic strategy
    5. Track returns categorized by true count
    6. Aggregate results to measure overall advantage
    
    Parameters:
        strategy: Basic strategy dictionary
        shoes: Number of shoes to simulate
        base_bet: Minimum bet amount
        
    Returns:
        Tuple of (statistics_dictionary, simulator_object)
    """
    print(f"\n{'='*60}")
    print(f"PHASE 2: SIMULATING CARD COUNTING (Hi-Lo System)")
    print(f"{'='*60}")
    
    # Create and configure the simulator
    simulator = CardCountingSimulator(
        decks=6,
        penetration=0.75,
        base_bet=base_bet,
        shoes=shoes,
        strategy=strategy
    )
    
    start_time = time.time()
    stats = simulator.run()
    elapsed = time.time() - start_time
    
    # Display results
    simulator.print_results()
    
    # Advanced analysis
    print(f"\n{'─'*40}")
    print(f"ADVANCED ANALYSIS:")
    
    analyzer = CountingAnalyzer(simulator)
    
    # True Count distribution
    distribution = analyzer.analyze_tc_distribution()
    print(f"\nTrue Count Distribution Highlights:")
    for tc in sorted(distribution.keys()):
        if distribution[tc] > 3:  # Show significant counts
            print(f"  TC {tc:+3d}: {distribution[tc]:5.1f}% of hands")
    
    # Risk of Ruin for different bankrolls
    print(f"\nRisk of Ruin Analysis:")
    for bankroll in [5000, 10000, 25000, 50000]:
        ror = analyzer.calculate_risk_of_ruin(bankroll, simulations=200)
        risk_level = "LOW" if ror < 0.05 else ("MODERATE" if ror < 0.15 else "HIGH")
        print(f"  ${bankroll:,} bankroll: {ror*100:.1f}% RoR [{risk_level} RISK]")
    
    return stats, simulator


def create_project_visualizations(strategy: dict, 
                                 stats: dict, 
                                 simulator: CardCountingSimulator):
    """
    Generate all project visualizations.
    
    Creates a comprehensive set of publication-quality charts:
    1. Strategy heatmaps (hard, soft, pairs)
    2. EV vs True Count (THE KEY GRAPH)
    3. Counting advantage comparison
    4. Bankroll evolution over time
    5. True Count distribution
    6. Summary dashboard
    
    Parameters:
        strategy: Basic strategy dictionary
        stats: Aggregated counting statistics
        simulator: Card counting simulator with results
    """
    print(f"\n{'='*60}")
    print(f"PHASE 3: GENERATING VISUALIZATIONS")
    print(f"{'='*60}")
    
    # Create visualizer
    viz = Visualizer(output_dir='output')
    
    # Generate each visualization
    print("\nCreating visualizations...")
    
    print("  1/6  Strategy heatmap...")
    viz.strategy_heatmap(strategy)
    
    print("  2/6  EV vs True Count (key graph)...")
    viz.ev_vs_true_count(stats['tc_returns'])
    
    print("  3/6  Counting advantage comparison...")
    viz.counting_advantage(
        stats['counting_return'],
        stats['basic_return']
    )
    
    print("  4/6  Bankroll evolution...")
    viz.bankroll_evolution(simulator.shoe_results[:200])
    
    print("  5/6  True Count distribution...")
    viz.distribution(stats['tc_returns'])
    
    print("  6/6  Summary dashboard...")
    viz.create_summary_dashboard(stats, strategy, stats['tc_returns'])
    
    print(f"\n✓ All visualizations saved to: {viz.output_dir}/")
    print(f"  Files: strategy_heatmap.png, ev_vs_tc.png, "
          f"advantage_comparison.png,")
    print(f"         bankroll_evolution.png, tc_distribution.png, "
          f"summary_dashboard.png")


def print_final_conclusions(stats: dict):
    """
    Print the final conclusions and project summary.
    
    This function provides a clear, concise summary of what was
    demonstrated and why it matters. It's designed to be the
    "elevator pitch" version of the entire project.
    """
    print(f"\n{'='*60}")
    print(f"FINAL CONCLUSIONS")
    print(f"{'='*60}")
    
    advantage = stats.get('advantage', 0)
    
    print(f"""
PROJECT RESULTS:
━━━━━━━━━━━━━━━
• Basic Strategy EV: {stats.get('basic_return', -0.5):+.3f}%
  (This is the best you can do WITHOUT counting)

• Counting Return: {stats.get('counting_return', 0):+.3f}%
  (This is what you earn WITH Hi-Lo counting)

• COUNTING ADVANTAGE: {advantage:+.3f}%
  (Card counting adds {advantage:.3f} percentage points to your return)

VERDICT:
{'✓ Card counting PROVIDES a mathematical advantage over the casino' if advantage > 0 else '✗ Card counting did not show advantage in this simulation'}

{'With perfect basic strategy and Hi-Lo counting, a skilled player can' if advantage > 0 else ''}
{'expect to earn approximately ${:.2f} per $100 wagered in the long run.'.format(advantage) if advantage > 0 else ''}

SKILLS DEMONSTRATED:
━━━━━━━━━━━━━━━━
• Monte Carlo simulation of stochastic processes
• Decision optimization under uncertainty
• Hi-Lo card counting algorithm implementation
• Statistical analysis and hypothesis testing
• Risk of Ruin calculation and bankroll management
• Parallel computing for simulation efficiency
• Professional data visualization and presentation

INTERVIEW TALKING POINTS:
━━━━━━━━━━━━━━━━━━━━
• "I implemented Monte Carlo methods to derive optimal strategy"
• "The EV vs True Count graph empirically proves counting works"
• "I can explain the Blackjack-Scholes connection to options pricing"
• "This demonstrates my ability to model and optimize uncertain systems"
• "The risk metrics show understanding of position sizing and drawdown"

REFERENCES:
━━━━━━━━
• Thorp, E.O. "Beat the Dealer" (1966) - Proved blackjack is beatable
• Wong, S. "Professional Blackjack" (1975) - Refined Hi-Lo system
• Schlesinger, D. "Blackjack Attack" (2005) - Modern risk analysis
""")
    
    print(f"{'='*60}")
    print(f"Project completed successfully.")
    print(f"Ideal for GitHub portfolio and quantitative finance interviews.")
    print(f"{'='*60}")


def run_complete_analysis(simulations: int = 50000, 
                         shoes: int = 500,
                         base_bet: float = 10.0):
    """
    Execute the complete project pipeline.
    
    This function orchestrates all three phases:
    1. Build basic strategy via Monte Carlo
    2. Simulate card counting
    3. Generate visualizations
    
    Parameters:
        simulations: Monte Carlo trials per state-action
        shoes: Number of shoes for counting simulation
        base_bet: Minimum bet amount
    """
    print_project_banner()
    
    overall_start = time.time()
    
    # PHASE 1: Build basic strategy
    strategy, solver = build_basic_strategy(simulations)
    
    # PHASE 2: Simulate card counting
    stats, simulator = simulate_card_counting(strategy, shoes, base_bet)
    
    # PHASE 3: Create visualizations
    create_project_visualizations(strategy, stats, simulator)
    
    # Print conclusions
    print_final_conclusions(stats)
    
    # Total time
    total_time = time.time() - overall_start
    print(f"\nTotal project execution time: {total_time:.1f} seconds "
          f"({total_time/60:.1f} minutes)")


def main():
    """
    Main entry point with command-line argument parsing.
    
    Supports multiple execution modes:
    - Interactive menu (default)
    - Complete analysis (--full)
    - Quick demo (--demo)
    - Fast mode (--quick)
    - Custom parameters (--simulations, --shoes)
    """
    parser = argparse.ArgumentParser(
        description='Blackjack Monte Carlo Solver with Hi-Lo Card Counting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  python main.py                        # Interactive menu
  python main.py --full                 # Complete analysis (recommended)
  python main.py --demo                 # Basic gameplay demonstration
  python main.py --quick                # Fast mode for testing
  python main.py --simulations 100000   # High accuracy strategy
  python main.py --shoes 1000           # More counting shoes

OUTPUT:
  output/strategy_heatmap.png           # Basic strategy visualization
  output/ev_vs_tc.png                   # EV vs True Count (key graph)
  output/advantage_comparison.png       # Counting advantage
  output/bankroll_evolution.png         # Bankroll over time
  output/tc_distribution.png            # True Count frequencies
  output/summary_dashboard.png          # Complete dashboard
        """
    )
    
    # Command-line options
    parser.add_argument('--full', action='store_true',
                       help='Run complete analysis (all phases)')
    parser.add_argument('--demo', action='store_true',
                       help='Basic gameplay demonstration only')
    parser.add_argument('--quick', action='store_true',
                       help='Fast mode: fewer simulations for testing')
    parser.add_argument('--simulations', type=int, default=50000,
                       help='Monte Carlo simulations per state (default: 50000)')
    parser.add_argument('--shoes', type=int, default=500,
                       help='Number of shoes for counting (default: 500)')
    parser.add_argument('--base-bet', type=float, default=10.0,
                       help='Base bet amount (default: $10)')
    
    args = parser.parse_args()
    
    # Apply quick mode if requested
    if args.quick:
        print("QUICK MODE: Using reduced simulation counts for faster execution")
        args.simulations = min(args.simulations, 10000)
        args.shoes = min(args.shoes, 100)
    
    # Dispatch based on arguments
    if args.demo:
        print_project_banner()
        demonstrate_basic_gameplay()
    
    elif args.full:
        run_complete_analysis(
            simulations=args.simulations,
            shoes=args.shoes,
            base_bet=args.base_bet
        )
    
    else:
        # Interactive menu mode
        print_project_banner()
        
        while True:
            print("\n" + "="*40)
            print("INTERACTIVE MENU")
            print("="*40)
            print("1. Demo basic gameplay (5 sample hands)")
            print("2. Build basic strategy (Monte Carlo)")
            print("3. Simulate card counting (Hi-Lo)")
            print("4. Generate visualizations")
            print("5. Run COMPLETE analysis (all phases)")
            print("6. Exit")
            print("-"*40)
            
            choice = input("\nSelect option (1-6): ").strip()
            
            if choice == '1':
                demonstrate_basic_gameplay()
            
            elif choice == '2':
                strategy, _ = build_basic_strategy(args.simulations)
            
            elif choice == '3':
                try:
                    strategy, _ = build_basic_strategy(args.simulations)
                    simulate_card_counting(strategy, args.shoes, args.base_bet)
                except NameError:
                    print("Build strategy first (option 2)")
            
            elif choice == '4':
                try:
                    create_project_visualizations(strategy, stats, simulator)
                except NameError:
                    print("Run strategy and counting first (options 2 and 3)")
            
            elif choice == '5':
                run_complete_analysis(
                    simulations=args.simulations,
                    shoes=args.shoes,
                    base_bet=args.base_bet
                )
            
            elif choice == '6':
                print("\nExiting. Thank you for using Blackjack Monte Carlo Solver!")
                break
            
            else:
                print("\nInvalid option. Please select 1-6.")


if __name__ == "__main__":
    main()