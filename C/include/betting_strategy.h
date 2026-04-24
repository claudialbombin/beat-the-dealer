/**
 * @file betting_strategy.h
 * @brief Dynamic bet sizing based on True Count
 *
 * PURPOSE:
 * Converts the card counter's information advantage into actual
 * profit by betting MORE when the true count is favorable and
 * MINIMUM when it's unfavorable. This is the mechanism that
 * transforms card counting from a theoretical exercise into
 * a practical money-making strategy.
 *
 * THE BET SPREAD:
 * The ratio of maximum to minimum bet. Typical spreads:
 * - 1-4: Conservative, low risk, ~0.3% advantage
 * - 1-8: Moderate, common, ~0.7% advantage
 * - 1-12: Aggressive, requires larger bankroll, ~1.0% advantage
 * - 1-20: Very aggressive, high detection risk, ~1.5% advantage
 *
 * KELLY CRITERION:
 * Optimal bet fraction = advantage / variance
 * For blackjack: bet ≈ bankroll × advantage × 0.7
 * Example: $10,000 bankroll, 2% advantage → optimal bet ~$140
 *
 * CASINO COUNTERMEASURES:
 * Large bet spreads attract attention. Casinos use:
 * - Bet tracking software
 * - Facial recognition
 * - Shared databases of known counters
 * - "Flat betting" rules (no bet variation allowed)
 * - Continuous shuffle machines (no counting possible)
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#ifndef BETTING_STRATEGY_H
#define BETTING_STRATEGY_H

#include "blackjack_types.h"

/**
 * bet_init: Initializes betting strategy with base and maximum bets.
 *
 * Sets up the bet ramp that maps true count values to bet multipliers.
 * The ramp is conservative at low counts (minimum bet) and increases
 * aggressively at high counts where the player has a proven edge.
 *
 * @param base_bet Minimum bet (used when count is neutral or negative)
 * @param max_bet Maximum bet (cap for bankroll protection)
 */
void bet_init(double base_bet, double max_bet);

/**
 * bet_calculate: Determines appropriate bet for current true count.
 *
 * BETS BY TRUE COUNT (typical ramp):
 * TC ≤ +1: Minimum bet (no proven edge yet)
 * TC +2: 2× base (emerging edge, ~0.5% advantage)
 * TC +3: 3× base (clear edge, ~1.0% advantage)
 * TC +4: 5× base (strong edge, ~1.5% advantage)
 * TC +5: 7× base (excellent edge, ~2.5% advantage)
 * TC ≥ +6: Maximum bet (rare, exceptional opportunity)
 *
 * @param true_count Current true count
 * @return Bet amount in dollars
 */
double bet_calculate(double true_count);

/**
 * bet_optimize_ramp: Optimizes bet spread for given risk tolerance.
 *
 * Uses Kelly criterion to determine optimal bet sizes that
 * maximize expected growth while keeping risk of ruin below
 * the target threshold.
 *
 * @param bankroll Total playing bankroll
 * @param target_ror Maximum acceptable risk of ruin (e.g., 0.05 = 5%)
 */
void bet_optimize_ramp(double bankroll, double target_ror);

/**
 * bet_print_ramp: Displays the complete betting ramp.
 *
 * Shows the correlation between true count and bet size,
 * helping the user understand the betting strategy and
 * verify that it's configured correctly.
 */
void bet_print_ramp(void);

#endif /* BETTING_STRATEGY_H */