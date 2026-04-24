/**
 * @file hand_utils.h
 * @brief Hand management functions - valuation, soft/hard detection, card addition
 *
 * PURPOSE:
 * This module handles the most algorithmically interesting part of
 * blackjack programming: hand valuation with multiple Aces. A hand
 * containing Aces doesn't have a single value - it has MULTIPLE
 * possible values depending on how many Aces are counted as 11.
 *
 * THE ACE PROBLEM:
 * An Ace can be worth 1 or 11. With N Aces in a hand, there are
 * 2^N possible valuations. For example, A+A+A+A can be:
 * - All as 1: 1+1+1+1 = 4
 * - One as 11: 11+1+1+1 = 14
 * - Two as 11: 11+11+1+1 = 24
 * - Three as 11: 11+11+11+1 = 34
 * - All as 11: 11+11+11+11 = 44
 *
 * The "best value" is the highest total not exceeding 21.
 * If all totals exceed 21, the hand is "bust" and the best
 * value is the lowest bust total.
 *
 * SOFT vs HARD:
 * A "soft" hand contains at least one Ace counted as 11 AND
 * a total not exceeding 21. Soft hands cannot bust from one hit
 * because the Ace can switch from 11 to 1 if needed.
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#ifndef HAND_UTILS_H
#define HAND_UTILS_H

#include "blackjack_types.h"

/**
 * hand_init: Initializes a Hand structure to starting state.
 *
 * Sets all fields to their initial values for a new hand.
 * Uses memset for a clean zeroed starting point, then sets
 * non-zero fields. The bet parameter allows flexible wagering.
 *
 * @param hand Pointer to Hand structure to initialize
 * @param bet Initial wager amount
 */
void hand_init(Hand* hand, double bet);

/**
 * hand_add_card: Adds a card to the hand and checks for bust.
 *
 * After adding the card, immediately checks if the hand has
 * exceeded 21. If so, marks the hand as BUST, preventing any
 * further actions and guaranteeing a loss regardless of the
 * dealer's eventual result.
 *
 * @param hand Pointer to Hand structure
 * @param card Pointer to Card to add
 */
void hand_add_card(Hand* hand, const Card* card);

/**
 * hand_calculate_values: Computes all possible hand totals.
 *
 * ALGORITHM (Iterative with Ace branching):
 * Start with [0] as the only possible total.
 * For each card:
 *   - If NOT an Ace: Add its value to every existing total
 *   - If IS an Ace: For each existing total, create TWO new
 *     totals: one with Ace=1 and one with Ace=11
 *
 * This handles the combinatorial explosion from multiple Aces.
 * With 4 Aces maximum in a hand, we can have up to 2^4 = 16
 * possible values.
 *
 * @param hand Pointer to Hand to evaluate
 * @param values Pre-allocated array for storing possible totals
 * @param max_values Maximum number of values to compute
 * @return Number of distinct values computed
 */
int hand_calculate_values(const Hand* hand, int* values, int max_values);

/**
 * hand_best_value: Finds the optimal playable value for a hand.
 *
 * Strategy: Among all possible values, find the highest one
 * not exceeding 21. If all values bust, return the lowest
 * bust value for comparison purposes.
 *
 * Examples:
 * - A+7 → values [8, 18] → best = 18 (soft 18)
 * - K+7 → values [17] → best = 17 (hard 17)
 * - 10+6+7 → values [23] → best = 23 (bust)
 *
 * @param hand Pointer to Hand to evaluate
 * @return Best value (highest ≤ 21, or lowest bust value)
 */
int hand_best_value(const Hand* hand);

/**
 * hand_is_soft: Determines if hand is "soft" (contains usable Ace).
 *
 * A hand is soft if there are multiple possible values (indicating
 * an Ace exists) AND at least one value is ≤ 21 (the Ace can be
 * used as 11 without busting).
 *
 * Why this matters: Soft hands cannot bust from one hit, which
 * fundamentally changes optimal strategy. Soft 18 vs dealer 10
 * should HIT (can't bust, might improve), while hard 18 vs
 * dealer 10 should STAND.
 *
 * @param hand Pointer to Hand to evaluate
 * @return true if hand is soft, false otherwise
 */
bool hand_is_soft(const Hand* hand);

#endif /* HAND_UTILS_H */