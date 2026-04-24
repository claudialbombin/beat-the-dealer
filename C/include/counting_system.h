/**
 * @file counting_system.h
 * @brief Hi-Lo card counting system for advantage play
 *
 * PURPOSE:
 * Implements the Hi-Lo card counting method, the most widely used
 * system for tracking deck composition and identifying favorable
 * betting situations. This is what transformed blackjack from a
 * house-advantage game into one beatable by skilled players.
 *
 * THE HI-LO SYSTEM (Harvey Dubner, 1963; refined by Julian Braun):
 *
 * Running Count (RC): Cumulative sum of card values
 *   Low cards (2-6): +1 when dealt
 *   Neutral (7-9): 0 when dealt
 *   High cards (10-A): -1 when dealt
 *
 * True Count (TC): Running Count ÷ Decks Remaining
 *   Normalizes the count for different shoe depths
 *   TC = +6 with 3 decks left → moderate advantage
 *   TC = +6 with 1 deck left → very strong advantage
 *
 * PLAYER ADVANTAGE vs TRUE COUNT:
 *   TC 0: -0.5% (house edge with basic strategy)
 *   TC +1: ~0.0% (approximately break-even)
 *   TC +2: ~0.5% (player gains edge)
 *   TC +3: ~1.0% (clear player advantage)
 *   TC +4: ~1.5% (strong player advantage)
 *   TC +5: ~2.5% (excellent conditions)
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#ifndef COUNTING_SYSTEM_H
#define COUNTING_SYSTEM_H

#include "blackjack_types.h"

/**
 * count_reset: Resets running count to zero.
 *
 * Called at the start of each new shoe (after shuffle).
 * The running count always begins at 0 with a fresh shoe.
 *
 * @param running_count Pointer to running count variable
 */
void count_reset(int* running_count);

/**
 * count_update: Updates running count when a card is revealed.
 *
 * Adds the card's Hi-Lo value to the running count.
 * Called for every card that becomes visible during play.
 *
 * @param running_count Pointer to running count variable
 * @param card Pointer to the revealed Card
 */
void count_update(int* running_count, const Card* card);

/**
 * count_calculate_true: Computes true count from running count.
 *
 * FORMULA: True Count = Running Count / Decks Remaining
 * Decks Remaining = Cards Remaining in Shoe / 52
 *
 * The true count normalizes the running count for shoe depth.
 * A running count of +8 means very different things with
 * 4 decks remaining (TC = +2, moderate edge) versus
 * 1 deck remaining (TC = +8, exceptional edge).
 *
 * @param running_count Current running count
 * @param shoe Pointer to Shoe for remaining card count
 * @return True count (floating point for accuracy)
 */
double count_calculate_true(int running_count, const Shoe* shoe);

/**
 * count_simulate_shoe: Simulates one complete shoe with counting.
 *
 * Plays through an entire shoe (from shuffle to cut card),
 * adjusting bets based on true count and recording results
 * for later analysis.
 *
 * @param config Simulation parameters
 * @param strategy_table Basic strategy table
 * @param strategy_entries Number of strategy entries
 * @param results Pointer to CountResults to populate
 */
void count_simulate_shoe(const SimConfig* config,
                        const StrategyEntry* strategy_table,
                        int strategy_entries,
                        CountingResults* results);

/**
 * count_run_full_simulation: Execute complete counting simulation.
 *
 * Runs multiple shoes and aggregates results for statistical analysis.
 */
void count_run_full_simulation(const SimConfig* config,
                              const StrategyEntry* strategy_table,
                              int strategy_entries,
                              int num_shoes,
                              CountingResults* results);

/**
 * count_print_results: Displays counting simulation results.
 *
 * Shows key metrics: total hands, return with/without counting,
 * and the calculated advantage. If advantage is positive,
 * confirms that counting provides a real edge.
 *
 * @param results Pointer to CountingResults to display
 */
void count_print_results(const CountingResults* results);

/**
 * count_get_advantage_level: Human-readable description of true count.
 *
 * @param true_count Current true count
 * @return String like "Favorable", "Neutral", etc.
 */
const char* count_get_advantage_level(double true_count);

#endif /* COUNTING_SYSTEM_H */