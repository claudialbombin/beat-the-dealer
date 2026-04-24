/**
 * @file interactive_mode.h
 * @brief Interactive blackjack game with strategy advisor
 *
 * Exposes two entry points:
 *  - play_interactive_round(): one round, returns profit/loss
 *  - run_interactive_game():   full session loop until player quits
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#ifndef INTERACTIVE_MODE_H
#define INTERACTIVE_MODE_H

#include "blackjack_types.h"
#include "shoe_utils.h"

/**
 * play_interactive_round: Play one round with the advisor active.
 *
 * Deals cards, shows the advisor hint before each player decision,
 * runs the dealer, and returns net profit/loss.
 *
 * @param shoe           Active shoe (updated in place)
 * @param bet            Wager for this round
 * @param table          Strategy table from Monte Carlo solver
 * @param num_entries    Number of entries in the table
 * @param running_count  Hi-Lo running count (updated in place)
 * @return               Net result in euros (positive = win)
 */
double play_interactive_round(Shoe* shoe, double bet,
                              const StrategyEntry* table, int num_entries,
                              int* running_count);

/**
 * run_interactive_game: Full interactive session.
 *
 * Loops round after round, asking for bet each time, reshuffling
 * when needed, and printing a summary at the end.
 *
 * @param table       Pre-built strategy table
 * @param num_entries Number of entries in the table
 */
void run_interactive_game(const StrategyEntry* table, int num_entries);

#endif /* INTERACTIVE_MODE_H */
