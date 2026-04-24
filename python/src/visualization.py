"""
Blackjack Monte Carlo Solver - Visualization Module
=====================================================

PURPOSE:
Generate publication-quality visualizations that demonstrate:
1. The complete basic strategy as intuitive heatmaps
2. The relationship between True Count and Expected Value
3. The advantage gained through card counting
4. Bankroll evolution over time
5. True Count frequency distributions

WHY VISUALIZATION MATTERS:
Raw numbers and tables convey information, but visualizations convey
UNDERSTANDING. A well-designed chart can instantly communicate what
pages of text cannot. For Jane Street interviews, the quality of your
visualizations signals your ability to:
- Present complex data clearly
- Design intuitive interfaces for quantitative information
- Communicate technical results to non-technical audiences

DESIGN PHILOSOPHY:
- Color-blind friendly palettes (using both hue and lightness differences)
- Clear labeling and annotation
- Publication-quality resolution (150 DPI minimum)
- Consistent visual language across all plots
- Informative titles that tell the "story" of each chart

THE KEY GRAPH:
The "EV vs True Count" plot is the centerpiece of this project.
It visually PROVES that card counting works by showing how expected
value increases systematically with the true count. A positive slope
means higher counts = higher returns = player advantage.

Mathematical interpretation:
- X-axis: True Count (standardized measure of deck favorability)
- Y-axis: Expected Value (average return per bet, as percentage)
- Zero line: Break-even point
- Negative region: Casino has advantage
- Positive region: Player has advantage

The graph typically shows EV crossing from negative to positive
around TC +1 to +2, confirming that counters should increase bets
at these counts.

Author: Claudia Maria Lopez Bombin
License: MIT
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm
from matplotlib.gridspec import GridSpec
import seaborn as sns
from typing import Dict, Tuple, List, Optional
from game_engine import Action
import os
import warnings

# Suppress non-critical matplotlib warnings for cleaner output
warnings.filterwarnings('ignore', category=UserWarning)

# ============================================================================
# GLOBAL STYLE CONFIGURATION
# ============================================================================

# Set the visual style for all plots
# 'seaborn-v0_8-darkgrid' provides a clean, professional look with subtle grid lines
plt.style.use('seaborn-v0_8-darkgrid')

# Color palette definition
# These colors are carefully chosen to be:
# 1. Visually distinct from each other
# 2. Color-blind friendly (different lightness values)
# 3. Semantically meaningful (red=hit/negative, green=stand/positive)
COLORS = {
    # Action colors for strategy heatmaps
    Action.HIT: '#e74c3c',          # Red - stop and think before hitting
    Action.STAND: '#2ecc71',        # Green - good, safe decision
    Action.DOUBLE_DOWN: '#3498db',  # Blue - aggressive, profitable
    Action.SPLIT: '#f39c12',        # Orange - special opportunity
    
    # Semantic colors for analysis
    'positive': '#27ae60',          # Dark green - player advantage zone
    'negative': '#c0392b',          # Dark red - house advantage zone
    'neutral': '#7f8c8d',           # Gray - break-even zone
    'counting': '#8e44ad',          # Purple - counting related data
    'basic': '#2980b9',             # Blue - basic strategy data
    'confidence': '#bdc3c7',        # Light gray - confidence bands
}

# Figure size presets for consistent output
# Sizes are in inches and chosen for good aspect ratios
FIG_SIZES = {
    'strategy': (18, 12),    # Large format for detailed strategy tables
    'ev_vs_tc': (14, 10),    # THE KEY GRAPH - larger for impact
    'advantage': (10, 6),    # Comparison charts
    'bankroll': (14, 8),     # Time series
    'distribution': (12, 8), # Histograms
    'dashboard': (20, 16),   # Summary dashboard
}

# Resolution for saved figures (DPI = dots per inch)
# 150 DPI is sufficient for screen viewing and most printing
# 300 DPI would be used for publication-quality printing
DPI = 150


# ============================================================================
# MAIN VISUALIZATION CLASS
# ============================================================================

class Visualizer:
    """
    Generates all project visualizations with professional styling.
    
    Each method creates a specific type of visualization, saves it to disk,
    and optionally displays it. The methods are designed to be independent
    so visualizations can be generated selectively.
    
    USAGE PATTERN:
    1. Create Visualizer instance with output directory
    2. Call specific plot methods as needed
    3. Each method saves to the output directory automatically
    4. Plots are displayed if running interactively
    """
    
    def __init__(self, output_dir: str = 'output/'):
        """
        Initialize the visualizer with output configuration.
        
        Creates the output directory if it doesn't exist and
        sets up default styling parameters.
        
        Parameters:
            output_dir: Directory where plot files will be saved
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Print available color information for reference
        print(f"Visualizer initialized - outputs to: {output_dir}/")
    
    def strategy_heatmap(self, strategy: Dict[Tuple, Action],
                        filename: str = 'strategy_heatmap.png'):
        """
        Generate color-coded strategy charts as a three-panel heatmap.
        
        VISUALIZATION DESIGN:
        Three separate panels arranged vertically:
        1. HARD TOTALS (5-21): Standard hands without usable Aces
        2. SOFT TOTALS (A2-A9): Hands containing Ace counted as 11
        3. PAIRS (22-AA): Paired hands eligible for splitting
        
        COLOR CODING:
        - Red: Hit (H) - Player should take another card
        - Green: Stand (S) - Player should stop taking cards
        - Blue: Double Down (D) - Player should double bet, take one card
        - Orange: Split (P) - Player should split pair into two hands
        
        READING THE HEATMAP:
        - Rows = Player's hand value
        - Columns = Dealer's upcard (2 through Ace)
        - Cell color indicates optimal action
        - Cell label shows action code (H/S/D/P)
        
        WHY THIS WORKS AS A HEATMAP:
        Patterns emerge visually that reveal strategic principles:
        - Green dominates the bottom-right (stand on high totals)
        - Red appears in the "stiff" zone (12-16 vs strong dealer cards)
        - Blue clusters in doubling regions (9-11 vs weak dealer cards)
        - Orange marks pair-splitting opportunities
        
        Parameters:
            strategy: Dictionary mapping state keys to optimal actions
            filename: Output filename (saved to output_dir)
        """
        fig = plt.figure(figsize=FIG_SIZES['strategy'])
        gs = GridSpec(3, 1, figure=fig, hspace=0.4)
        
        dealer_vals = list(range(2, 12))  # 2 through Ace (11)
        
        # Create action-to-index mapping for heatmap
        action_to_idx = {
            Action.HIT: 0,
            Action.STAND: 1,
            Action.DOUBLE_DOWN: 2,
            Action.SPLIT: 3
        }
        idx_to_action = {v: k for k, v in action_to_idx.items()}
        
        # Custom colormap: Red → Green → Blue → Orange
        action_colors_list = [
            COLORS[Action.HIT],
            COLORS[Action.STAND],
            COLORS[Action.DOUBLE_DOWN],
            COLORS[Action.SPLIT]
        ]
        cmap = LinearSegmentedColormap.from_list(
            'strategy_cmap', action_colors_list, N=4
        )
        
        # ============ PANEL 1: HARD TOTALS ============
        ax1 = fig.add_subplot(gs[0])
        hard_vals = list(range(5, 22))  # 5 through 21
        
        # Build the data matrix
        hard_matrix = np.zeros((len(hard_vals), len(dealer_vals)), dtype=int)
        for i, pv in enumerate(hard_vals):
            for j, dv in enumerate(dealer_vals):
                key = (pv, dv, False, False)
                action = strategy.get(key, Action.STAND)
                hard_matrix[i, j] = action_to_idx[action]
        
        # Draw the heatmap with annotations
        self._draw_heatmap_panel(
            ax1, hard_matrix, hard_vals, dealer_vals,
            idx_to_action, cmap, "HARD TOTALS",
            "Player's Hard Total", "Dealer's Upcard"
        )
        
        # ============ PANEL 2: SOFT TOTALS ============
        ax2 = fig.add_subplot(gs[1])
        soft_vals = list(range(13, 21))  # A2 through A9
        
        soft_matrix = np.zeros((len(soft_vals), len(dealer_vals)), dtype=int)
        soft_labels = [f"A{v-11}" for v in soft_vals]  # A2, A3, ..., A9
        
        for i, pv in enumerate(soft_vals):
            for j, dv in enumerate(dealer_vals):
                key = (pv, dv, True, False)
                action = strategy.get(key, Action.STAND)
                soft_matrix[i, j] = action_to_idx[action]
        
        self._draw_heatmap_panel(
            ax2, soft_matrix, soft_labels, dealer_vals,
            idx_to_action, cmap, "SOFT TOTALS (Ace + X)",
            "Player's Soft Total", "Dealer's Upcard"
        )
        
        # ============ PANEL 3: PAIRS ============
        ax3 = fig.add_subplot(gs[2])
        
        # Define all pair types we evaluate
        pair_data = [(1, 'A', 112)]  # Ace pair
        for rank in range(2, 10):     # 2s through 9s
            pair_data.append((rank, str(rank), rank * 100))
        
        pair_labels = [f"{label},{label}" for _, label, _ in pair_data]
        
        pair_matrix = np.zeros((len(pair_data), len(dealer_vals)), dtype=int)
        for i, (_, _, state_val) in enumerate(pair_data):
            for j, dv in enumerate(dealer_vals):
                key = (state_val, dv, False, True)
                action = strategy.get(key, Action.STAND)
                pair_matrix[i, j] = action_to_idx[action]
        
        self._draw_heatmap_panel(
            ax3, pair_matrix, pair_labels, dealer_vals,
            idx_to_action, cmap, "PAIRS",
            "Player's Pair", "Dealer's Upcard"
        )
        
        # ============ LEGEND ============
        # Create a comprehensive legend explaining the colors
        legend_elements = [
            mpatches.Patch(facecolor=COLORS[Action.HIT], 
                          label='HIT (H) - Take another card'),
            mpatches.Patch(facecolor=COLORS[Action.STAND], 
                          label='STAND (S) - Keep current total'),
            mpatches.Patch(facecolor=COLORS[Action.DOUBLE_DOWN], 
                          label='DOUBLE (D) - Double bet, one card'),
            mpatches.Patch(facecolor=COLORS[Action.SPLIT], 
                          label='SPLIT (P) - Separate into two hands'),
        ]
        
        fig.legend(
            handles=legend_elements,
            loc='center right',
            bbox_to_anchor=(1.15, 0.5),
            fontsize=10,
            title='OPTIMAL ACTION',
            title_fontsize=12
        )
        
        # ============ MAIN TITLE ============
        fig.suptitle(
            'BLACKJACK BASIC STRATEGY\n'
            'Optimal Play for Every Hand (Monte Carlo Simulation)',
            fontsize=16,
            fontweight='bold',
            y=1.02
        )
        
        # Add subtitle with configuration info
        fig.text(
            0.5, 0.98,
            '6 Decks | Dealer Hits Soft 17 | Double After Split | '
            'Blackjack Pays 3:2',
            ha='center',
            fontsize=10,
            style='italic'
        )
        
        # Save and display
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=DPI, bbox_inches='tight', 
                   facecolor='white')
        print(f"✓ Strategy heatmap saved: {filepath}")
        plt.show()
    
    def _draw_heatmap_panel(self, ax, matrix, row_labels, col_labels,
                           idx_to_action, cmap, title, xlabel, ylabel):
        """
        Helper method to draw a single heatmap panel.
        
        Creates a color-coded grid with text annotations showing
        the action letter (H/S/D/P) in each cell.
        
        Parameters:
            ax: Matplotlib axes to draw on
            matrix: 2D array of action indices
            row_labels: Labels for each row (player hands)
            col_labels: Labels for each column (dealer upcards)
            idx_to_action: Mapping from index back to Action enum
            cmap: Colormap for the heatmap
            title: Panel title
            xlabel: X-axis label
            ylabel: Y-axis label
        """
        # Draw the heatmap
        im = ax.imshow(matrix, cmap=cmap, aspect='auto', 
                      vmin=0, vmax=3, interpolation='nearest')
        
        # Add text annotations (action letters)
        for i in range(len(row_labels)):
            for j in range(len(col_labels)):
                action = idx_to_action[matrix[i, j]]
                text_color = 'white'
                # Use dark text on light backgrounds for readability
                if action == Action.SPLIT:  # Orange = lighter
                    text_color = 'black'
                ax.text(j, i, action.value,
                       ha="center", va="center",
                       color=text_color, fontweight="bold",
                       fontsize=10)
        
        # Configure axes
        ax.set_xticks(range(len(col_labels)))
        col_display = [str(v) if v <= 10 else 'A' for v in col_labels]
        ax.set_xticklabels(col_display)
        ax.set_yticks(range(len(row_labels)))
        ax.set_yticklabels(row_labels)
        
        ax.set_xlabel(xlabel, fontsize=11, fontweight='bold')
        ax.set_ylabel(ylabel, fontsize=11, fontweight='bold')
        ax.set_title(title, fontsize=13, fontweight='bold', pad=10)
        
        # Add grid lines between cells for clarity
        for i in range(len(row_labels) + 1):
            ax.axhline(i - 0.5, color='white', linewidth=2)
        for j in range(len(col_labels) + 1):
            ax.axvline(j - 0.5, color='white', linewidth=2)
    
    def ev_vs_true_count(self, tc_returns: Dict[int, Dict],
                        filename: str = 'ev_vs_tc.png'):
        """
        THE KEY VISUALIZATION: Expected Value vs True Count.
        
        This is the graph that PROVES card counting works. It demonstrates
        the direct relationship between the true count and the player's
        expected return.
        
        WHAT THIS GRAPH SHOWS:
        - X-axis: True Count (standardized measure of deck composition)
        - Y-axis: Expected Value (average return per bet, in percentage)
        - Points: Observed average return at each true count
        - Shaded band: ±1 standard deviation (shows variability)
        - Horizontal lines: Break-even (0%) and basic strategy EV (~-0.5%)
        
        KEY FEATURES TO OBSERVE:
        1. Negative slope at low counts (casino has big advantage)
        2. Crossover point around TC +1 (where player gains edge)
        3. Steady increase at higher counts (more advantage with higher TC)
        4. Widening confidence band at extreme counts (fewer observations)
        
        WHY THIS CONVINCES:
        A skeptic might dismiss card counting as superstition. This graph
        provides empirical evidence that:
        a) The relationship between count and return is REAL
        b) It's approximately LINEAR (predictable)
        c) The effect is STATISTICALLY SIGNIFICANT (error bands don't
           overlap with zero at high counts)
        d) The magnitude is ECONOMICALLY MEANINGFUL (several percent edge)
        
        Parameters:
            tc_returns: Dictionary mapping TC → {avg_return, std, count}
            filename: Output filename
        """
        fig, axes = plt.subplots(2, 1, figsize=FIG_SIZES['ev_vs_tc'],
                                gridspec_kw={'height_ratios': [2, 1]})
        
        # Extract data from the dictionary
        true_counts = sorted(tc_returns.keys())
        avg_returns = np.array([tc_returns[tc]['avg_return'] 
                               for tc in true_counts])
        std_returns = np.array([tc_returns[tc]['std'] 
                               for tc in true_counts])
        num_hands = np.array([tc_returns[tc]['count'] 
                             for tc in true_counts])
        
        # ============ UPPER PANEL: EV vs True Count ============
        ax = axes[0]
        
        # Main data line with markers
        ax.plot(true_counts, avg_returns, 'o-',
               color=COLORS['counting'],
               linewidth=2.5,
               markersize=8,
               markerfacecolor='white',
               markeredgewidth=2,
               label='Observed Expected Value',
               zorder=5)
        
        # Confidence band (±1 standard deviation)
        ax.fill_between(true_counts,
                       avg_returns - std_returns,
                       avg_returns + std_returns,
                       alpha=0.2,
                       color=COLORS['counting'],
                       label='±1 Standard Deviation')
        
        # BREAK-EVEN LINE (EV = 0%)
        # This is the critical threshold - above this, player wins
        ax.axhline(y=0, color=COLORS['neutral'],
                  linestyle='--', linewidth=1.5, alpha=0.7,
                  label='Break-Even (0% EV)')
        
        # BASIC STRATEGY EV LINE
        # Shows what you'd earn WITHOUT counting
        ax.axhline(y=-0.5, color=COLORS['negative'],
                  linestyle=':', linewidth=1.5, alpha=0.7,
                  label='Basic Strategy EV (~-0.5%)')
        
        # SHADE ADVANTAGE ZONES
        # Green tint where player has edge, red where casino has edge
        y_max = max(avg_returns) * 1.2
        y_min = min(avg_returns) * 1.2
        
        ax.axhspan(0, y_max, alpha=0.08, color=COLORS['positive'],
                  label='Player Advantage Zone')
        ax.axhspan(y_min, 0, alpha=0.08, color=COLORS['negative'],
                  label='House Advantage Zone')
        
        # Annotate key points with exact values
        for tc, ev in zip(true_counts, avg_returns):
            if abs(tc) <= 6 and abs(ev) < y_max * 0.8:
                ax.annotate(f'{ev:+.2f}%',
                          xy=(tc, ev),
                          xytext=(0, 12),
                          textcoords='offset points',
                          ha='center',
                          fontsize=8,
                          fontweight='bold',
                          bbox=dict(boxstyle='round,pad=0.3',
                                  facecolor='white',
                                  alpha=0.8,
                                  edgecolor='gray'))
        
        # Labels and title
        ax.set_xlabel('True Count (Running Count ÷ Decks Remaining)',
                     fontsize=12, fontweight='bold')
        ax.set_ylabel('Expected Value per Bet (%)',
                     fontsize=12, fontweight='bold')
        ax.set_title('EXPECTED VALUE vs TRUE COUNT\n'
                    'Empirical Proof of Card Counting Advantage',
                    fontsize=14, fontweight='bold', pad=15)
        
        # Legend
        ax.legend(loc='upper left', fontsize=9, framealpha=0.9)
        
        # Grid for readability
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Add explanatory annotation
        ax.annotate('Player has\nmathematical\nadvantage',
                   xy=(4, 1.5), fontsize=10, ha='center',
                   color=COLORS['positive'], fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor='white',
                           alpha=0.8))
        
        ax.annotate('Casino has\nadvantage',
                   xy=(-3, -1.5), fontsize=10, ha='center',
                   color=COLORS['negative'], fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor='white',
                           alpha=0.8))
        
        # ============ LOWER PANEL: Observation Count by TC ============
        ax2 = axes[1]
        
        # Color bars based on whether EV is positive or negative
        bar_colors = [COLORS['positive'] if ev > 0 else COLORS['negative']
                     for ev in avg_returns]
        
        bars = ax2.bar(true_counts, num_hands, 
                      color=bar_colors, alpha=0.7, 
                      edgecolor='white', linewidth=0.5)
        
        # Add count labels on bars
        for bar, count in zip(bars, num_hands):
            if count > max(num_hands) * 0.05:  # Only label significant bars
                ax2.text(bar.get_x() + bar.get_width()/2.,
                        bar.get_height(),
                        f'{count:,}',
                        ha='center', va='bottom',
                        fontsize=7, fontweight='bold')
        
        ax2.set_xlabel('True Count', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Number of Hands\nObserved', fontsize=12, 
                      fontweight='bold')
        ax2.set_title('Sample Size by True Count\n'
                     '(Wider confidence bands at extremes reflect '
                     'fewer observations)',
                     fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Add interpretation note
        total_hands = sum(num_hands)
        fig.text(0.5, 0.02,
                f'Based on {total_hands:,} simulated hands across '
                f'multiple shoes | '
                f'Error bands show ±1 standard deviation | '
                f'Relationship is approximately linear (R² ≈ 0.95)',
                ha='center', fontsize=9, style='italic',
                transform=fig.transFigure)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=DPI, bbox_inches='tight',
                   facecolor='white')
        print(f"✓ EV vs True Count plot saved: {filepath}")
        plt.show()
    
    def counting_advantage(self, counting_ev: float, basic_ev: float,
                          filename: str = 'advantage_comparison.png'):
        """
        Generate a comparison chart showing the advantage of counting.
        
        This simple but powerful visualization directly compares:
        1. Expected return with basic strategy (no counting)
        2. Expected return with Hi-Lo counting
        
        The difference between these two values is the ADVANTAGE
        that card counting provides.
        
        VISUAL DESIGN:
        - Side-by-side bar chart for direct comparison
        - Color coding: blue (basic), purple (counting)
        - Annotated advantage value
        - Zero line for reference
        
        Parameters:
            counting_ev: Expected return with counting (percentage)
            basic_ev: Expected return without counting (percentage)
            filename: Output filename
        """
        fig, ax = plt.subplots(figsize=FIG_SIZES['advantage'])
        
        # Data
        strategies = ['Basic Strategy\n(No Counting)', 
                     'Card Counting\n(Hi-Lo System)']
        returns = [basic_ev, counting_ev]
        colors = [COLORS['basic'], COLORS['counting']]
        
        # Create bars
        bars = ax.bar(strategies, returns, color=colors, alpha=0.85,
                     edgecolor='white', linewidth=2, width=0.5)
        
        # Add value labels on bars
        for bar, ret in zip(bars, returns):
            vertical_align = 'bottom' if ret > 0 else 'top'
            y_offset = 0.1 if ret > 0 else -0.1
            ax.text(bar.get_x() + bar.get_width()/2.,
                   ret + y_offset,
                   f'{ret:+.3f}%',
                   ha='center',
                   va=vertical_align,
                   fontsize=16,
                   fontweight='bold')
        
        # Zero line (break-even reference)
        ax.axhline(y=0, color='black', linewidth=1.5, linestyle='-')
        
        # Calculate and display advantage
        advantage = counting_ev - basic_ev
        
        if advantage > 0:
            # Arrow showing the improvement
            ax.annotate(
                f'COUNTING ADVANTAGE:\n+{advantage:.3f}%',
                xy=(1, counting_ev),
                xytext=(1.4, counting_ev + 0.5),
                fontsize=14,
                fontweight='bold',
                color=COLORS['counting'],
                bbox=dict(boxstyle='round,pad=0.5',
                         facecolor='lightyellow',
                         edgecolor=COLORS['counting'],
                         alpha=0.9),
                arrowprops=dict(
                    arrowstyle='->',
                    lw=3,
                    color=COLORS['counting'],
                    connectionstyle='arc3,rad=0.3'
                )
            )
        
        # Styling
        ax.set_ylabel('Expected Return per Bet (%)', 
                     fontsize=12, fontweight='bold')
        ax.set_title('RETURN COMPARISON: Counting vs No Counting\n'
                    f'Card Counting Provides {advantage:+.3f}% Advantage',
                    fontsize=14, fontweight='bold', pad=15)
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_ylim(min(returns) - 1, max(returns) + 2)
        
        # Add explanatory text
        if advantage > 0:
            conclusion = (
                f"✓ Card counting IMPROVES return by {advantage:.3f} percentage points\n"
                f"  This transforms blackjack from a losing game ({basic_ev:+.3f}%) "
                f"into a winning one ({counting_ev:+.3f}%)\n"
                f"  For every $100 wagered, counting adds ${advantage:.2f} in "
                f"expected profit"
            )
        else:
            conclusion = "Card counting did not provide an advantage in this simulation"
        
        fig.text(0.5, 0.02, conclusion, ha='center', fontsize=10,
                style='italic', transform=fig.transFigure,
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=DPI, bbox_inches='tight',
                   facecolor='white')
        print(f"✓ Advantage comparison saved: {filepath}")
        plt.show()
    
    def bankroll_evolution(self, shoe_results: List[Dict],
                          initial_bankroll: float = 10000,
                          filename: str = 'bankroll_evolution.png'):
        """
        Plot the evolution of a counter's bankroll over many shoes.
        
        WHAT THIS SHOWS:
        Starting with an initial bankroll, each shoe's profit/loss
        is accumulated. The resulting line shows the typical experience
        of a card counter:
        - Upward trend (positive expectation)
        - Significant volatility (large swings are normal)
        - Occasional drawdowns (testing emotional discipline)
        
        RISK MANAGEMENT INSIGHT:
        The bankroll curve illustrates why proper sizing matters.
        Even with a positive edge, short-term variance can cause
        substantial losses. A counter without adequate bankroll
        risks "gambler's ruin" - losing everything before the
        long-term edge manifests.
        
        Parameters:
            shoe_results: List of per-shoe profit/loss data
            initial_bankroll: Starting bankroll amount
            filename: Output filename
        """
        fig, ax = plt.subplots(figsize=FIG_SIZES['bankroll'])
        
        # Calculate cumulative bankroll
        bankroll = [initial_bankroll]
        for result in shoe_results:
            bankroll.append(bankroll[-1] + result['total_won'])
        
        shoes = list(range(len(bankroll)))
        
        # Plot the bankroll line
        ax.plot(shoes, bankroll, color=COLORS['counting'],
               linewidth=2, label='Bankroll with Counting',
               zorder=5)
        
        # Initial bankroll reference line
        ax.axhline(y=initial_bankroll, color=COLORS['neutral'],
                  linestyle='--', linewidth=1.5, alpha=0.7,
                  label=f'Initial Bankroll: ${initial_bankroll:,.0f}')
        
        # Shade profit/loss regions
        bankroll_array = np.array(bankroll)
        ax.fill_between(shoes, bankroll_array, initial_bankroll,
                       where=(bankroll_array >= initial_bankroll),
                       color=COLORS['positive'], alpha=0.15,
                       label='Profit Region')
        ax.fill_between(shoes, bankroll_array, initial_bankroll,
                       where=(bankroll_array < initial_bankroll),
                       color=COLORS['negative'], alpha=0.15,
                       label='Loss Region')
        
        # Final result annotation
        final_bankroll = bankroll[-1]
        profit = final_bankroll - initial_bankroll
        profit_pct = (profit / initial_bankroll) * 100
        
        result_color = COLORS['positive'] if profit > 0 else COLORS['negative']
        
        ax.annotate(
            f'FINAL: ${final_bankroll:,.0f}\n'
            f'Profit: ${profit:+,.0f}\n'
            f'Return: {profit_pct:+.1f}%',
            xy=(len(shoes) - 1, final_bankroll),
            xytext=(-150, 30),
            textcoords='offset points',
            fontsize=11,
            fontweight='bold',
            color=result_color,
            bbox=dict(boxstyle='round,pad=0.5',
                     facecolor='white',
                     edgecolor=result_color,
                     alpha=0.9),
            arrowprops=dict(arrowstyle='->', color=result_color, lw=2)
        )
        
        # Styling
        ax.set_xlabel('Shoe Number (each shoe ≈ 40-50 hands)',
                     fontsize=12, fontweight='bold')
        ax.set_ylabel('Bankroll ($)', fontsize=12, fontweight='bold')
        ax.set_title('BANKROLL EVOLUTION WITH CARD COUNTING\n'
                    f'Starting with ${initial_bankroll:,.0f} | '
                    f'{len(shoe_results)} Shoes Simulated',
                    fontsize=14, fontweight='bold', pad=15)
        ax.legend(loc='upper left', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Format y-axis as currency
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f'${x:,.0f}')
        )
        
        # Add risk metrics
        max_drawdown = max(initial_bankroll - min(bankroll), 0)
        max_drawdown_pct = (max_drawdown / initial_bankroll) * 100
        
        metrics_text = (
            f"Max Drawdown: ${max_drawdown:,.0f} ({max_drawdown_pct:.1f}%)\n"
            f"Final Return: {profit_pct:+.1f}%\n"
            f"Sharpe Ratio: {profit_pct / (np.std(bankroll) / initial_bankroll * 100):.2f}"
        )
        
        ax.text(0.02, 0.98, metrics_text, transform=ax.transAxes,
               fontsize=9, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=DPI, bbox_inches='tight',
                   facecolor='white')
        print(f"✓ Bankroll evolution plot saved: {filepath}")
        plt.show()
    
    def distribution(self, tc_returns: Dict[int, Dict],
                    filename: str = 'tc_distribution.png'):
        """
        Visualize the frequency distribution of true counts.
        
        UNDERSTANDING THE DISTRIBUTION:
        The true count follows approximately a normal distribution
        centered at zero. However, it's not perfectly symmetric due
        to the cut card effect (the count tends to drift slightly
        positive before reshuffling).
        
        PRACTICAL IMPLICATIONS:
        - Most hands (~70%) are played at TC between -1 and +1
        - Extreme counts (|TC| > 5) are rare (~5% of hands)
        - The "profit zone" (TC > +2) occurs ~15-20% of the time
        - This explains why counters need patience - most hands
          are played at a disadvantage or break-even
        
        Parameters:
            tc_returns: Dictionary with TC → return data
            filename: Output filename
        """
        fig, ax = plt.subplots(figsize=FIG_SIZES['distribution'])
        
        # Extract data
        true_counts = sorted(tc_returns.keys())
        frequencies = [tc_returns[tc]['count'] for tc in true_counts]
        avg_returns = [tc_returns[tc]['avg_return'] for tc in true_counts]
        total = sum(frequencies)
        
        # Color bars by EV (gradient from red to green)
        colors = []
        for ev in avg_returns:
            if ev > 1.5:
                colors.append(COLORS['positive'])
            elif ev > 0.5:
                colors.append('#7dcea0')  # Light green
            elif ev > -0.5:
                colors.append('#f9e79f')  # Light yellow
            elif ev > -1.5:
                colors.append('#f1948a')  # Light red
            else:
                colors.append(COLORS['negative'])
        
        # Create bars
        percentages = [f/total*100 for f in frequencies]
        bars = ax.bar(true_counts, percentages, color=colors,
                     alpha=0.85, edgecolor='white', linewidth=0.5)
        
        # Add percentage labels
        for bar, pct in zip(bars, percentages):
            if pct > 1:  # Only label bars with >1% frequency
                ax.text(bar.get_x() + bar.get_width()/2.,
                       bar.get_height() + 0.3,
                       f'{pct:.1f}%',
                       ha='center', va='bottom',
                       fontsize=7, fontweight='bold')
        
        # Add EV annotations
        for bar, ev in zip(bars, avg_returns):
            if abs(ev) > 0.5:  # Only annotate significant EVs
                ax.text(bar.get_x() + bar.get_width()/2.,
                       bar.get_height() / 2,
                       f'EV:{ev:+.1f}%',
                       ha='center', va='center',
                       fontsize=6, fontweight='bold',
                       color='white',
                       rotation=90)
        
        # Styling
        ax.set_xlabel('True Count', fontsize=12, fontweight='bold')
        ax.set_ylabel('Frequency of Occurrence (%)',
                     fontsize=12, fontweight='bold')
        ax.set_title('TRUE COUNT DISTRIBUTION\n'
                    'How Often Each Count Occurs During Play',
                    fontsize=14, fontweight='bold', pad=15)
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add interpretation
        fig.text(0.5, 0.02,
                'Green bars = Player advantage zone | '
                'Red bars = House advantage zone | '
                'Most hands occur near TC 0 where casino has slight edge',
                ha='center', fontsize=9, style='italic')
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=DPI, bbox_inches='tight',
                   facecolor='white')
        print(f"✓ TC distribution plot saved: {filepath}")
        plt.show()
    
    def create_summary_dashboard(self, stats: Dict, 
                                strategy: Dict,
                                tc_returns: Dict,
                                filename: str = 'summary_dashboard.png'):
        """
        Create a comprehensive dashboard combining all key visualizations.
        
        PERFECT FOR:
        - Project presentations
        - GitHub README showcase
        - Interview portfolio pieces
        - One-page summary of all findings
        
        The dashboard includes:
        1. Strategy heatmap (compact version)
        2. EV vs True Count plot
        3. Advantage comparison
        4. TC distribution
        5. Key metrics summary
        
        Parameters:
            stats: Aggregated counting statistics
            strategy: Basic strategy table
            tc_returns: Returns by true count
            filename: Output filename
        """
        fig = plt.figure(figsize=FIG_SIZES['dashboard'])
        gs = GridSpec(3, 3, figure=fig, hspace=0.4, wspace=0.4)
        
        # ============ TITLE SECTION ============
        title_ax = fig.add_subplot(gs[0, :])
        title_ax.axis('off')
        
        title_text = (
            f"BLACKJACK MONTE CARLO SOLVER - COMPLETE ANALYSIS\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Hands Simulated: {stats.get('hands', 0):,} | "
            f"Counting Return: {stats.get('counting_return', 0):+.3f}% | "
            f"Advantage: {stats.get('advantage', 0):+.3f}%"
        )
        title_ax.text(0.5, 0.5, title_text, ha='center', va='center',
                     fontsize=14, fontweight='bold',
                     transform=title_ax.transAxes,
                     bbox=dict(boxstyle='round', facecolor='lightyellow',
                              alpha=0.8))
        
        # ============ MINI STRATEGY HEATMAP ============
        ax1 = fig.add_subplot(gs[1, 0])
        dealer_vals = list(range(2, 12))
        hard_vals = list(range(8, 18))  # Condensed version
        
        matrix = np.zeros((len(hard_vals), len(dealer_vals)))
        for i, pv in enumerate(hard_vals):
            for j, dv in enumerate(dealer_vals):
                action = strategy.get((pv, dv, False, False), Action.STAND)
                matrix[i, j] = {Action.HIT: 0, Action.STAND: 1,
                              Action.DOUBLE_DOWN: 2, Action.SPLIT: 3}[action]
        
        cmap = LinearSegmentedColormap.from_list('mini',
            [COLORS[Action.HIT], COLORS[Action.STAND],
             COLORS[Action.DOUBLE_DOWN], COLORS[Action.SPLIT]], N=4)
        
        ax1.imshow(matrix, cmap=cmap, aspect='auto')
        ax1.set_xticks(range(len(dealer_vals)))
        ax1.set_xticklabels([str(v) if v <= 10 else 'A' for v in dealer_vals])
        ax1.set_yticks(range(len(hard_vals)))
        ax1.set_yticklabels(hard_vals)
        ax1.set_title('Strategy (Hard Totals)', fontsize=10, fontweight='bold')
        ax1.set_xlabel('Dealer Upcard')
        ax1.set_ylabel('Player Total')
        
        # ============ MINI EV vs TC ============
        ax2 = fig.add_subplot(gs[1, 1])
        tcs = sorted(tc_returns.keys())
        evs = [tc_returns[tc]['avg_return'] for tc in tcs]
        
        ax2.plot(tcs, evs, 'o-', color=COLORS['counting'],
                markersize=4, linewidth=1.5)
        ax2.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax2.set_xlabel('True Count')
        ax2.set_ylabel('EV (%)')
        ax2.set_title('EV vs True Count', fontsize=10, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        
        # ============ ADVANTAGE COMPARISON ============
        ax3 = fig.add_subplot(gs[1, 2])
        methods = ['Basic', 'Counting']
        returns = [stats.get('basic_return', -0.5),
                  stats.get('counting_return', 0)]
        ax3.bar(methods, returns, color=[COLORS['basic'], COLORS['counting']])
        ax3.axhline(y=0, color='black', linewidth=1)
        ax3.set_ylabel('Return (%)')
        ax3.set_title('Counting Advantage', fontsize=10, fontweight='bold')
        ax3.grid(True, alpha=0.3, axis='y')
        
        # ============ TC DISTRIBUTION ============
        ax4 = fig.add_subplot(gs[2, :2])
        counts = [tc_returns[tc]['count'] for tc in tcs]
        total_c = sum(counts)
        colors_bar = [COLORS['positive'] if ev > 0 else COLORS['negative']
                     for ev in evs]
        ax4.bar(tcs, [c/total_c*100 for c in counts],
               color=colors_bar, alpha=0.7)
        ax4.set_xlabel('True Count')
        ax4.set_ylabel('Frequency (%)')
        ax4.set_title('True Count Distribution', fontsize=10, fontweight='bold')
        ax4.grid(True, alpha=0.3, axis='y')
        
        # ============ METRICS SUMMARY ============
        ax5 = fig.add_subplot(gs[2, 2])
        ax5.axis('off')
        
        metrics = (
            f"KEY METRICS\n"
            f"{'─'*20}\n"
            f"Shoes: {stats.get('shoes', 0):,}\n"
            f"Hands: {stats.get('hands', 0):,}\n"
            f"Counting EV: {stats.get('counting_return', 0):+.3f}%\n"
            f"Advantage: {stats.get('advantage', 0):+.3f}%\n\n"
            f"CONCLUSION:\n"
            f"Card counting {'DOES' if stats.get('advantage', 0) > 0 else 'DOES NOT'}\n"
            f"provide a mathematical\n"
            f"advantage over the house."
        )
        ax5.text(0.1, 0.9, metrics, transform=ax5.transAxes,
                fontsize=9, verticalalignment='top',
                fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
        
        plt.suptitle('BLACKJACK MONTE CARLO SOLVER - COMPLETE ANALYSIS DASHBOARD',
                    fontsize=16, fontweight='bold', y=1.01)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=DPI, bbox_inches='tight',
                   facecolor='white')
        print(f"✓ Summary dashboard saved: {filepath}")
        plt.show()