/**
 * @file hand_utils.c
 * @brief Hand valuation and manipulation - 5 functions
 *
 * HAND VALUATION: THE HARDEST PART OF BLACKJACK PROGRAMMING
 *
 * The difficulty comes from the dual nature of Aces. An Ace can
 * be worth either 1 or 11, and a hand can contain multiple Aces.
 * This means a hand doesn't have a single value - it has MULTIPLE
 * possible values depending on how many Aces we count as 11.
 *
 * EXAMPLE: Hand containing A, A, A, A
 * Possible values: 4, 14, 24, 34, 44
 * (0 Aces as 11 = 4, 1 Ace as 11 = 14, etc.)
 *
 * The "best value" is the highest total not exceeding 21.
 * If all totals exceed 21, the hand is "bust."
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#include "../include/hand_utils.h"
#include <string.h>

/**
 * hand_init: Initialize a Hand structure to starting state.
 *
 * Sets all fields to their initial values for a new hand.
 * Uses memset for a clean zeroed starting point, then sets
 * non-zero fields appropriately.
 */
void hand_init(Hand* hand, double bet) {
    memset(hand, 0, sizeof(Hand));
    hand->bet = bet;
    hand->status = HAND_ACTIVE;
}

/**
 * hand_add_card: Add a card to the hand and check for bust.
 *
 * After adding the card, immediately checks if the hand has
 * exceeded 21. If so, marks the hand as BUST, which prevents
 * any further actions and guarantees a loss.
 */
void hand_add_card(Hand* hand, const Card* card) {
    if (hand->num_cards < MAX_CARDS_PER_HAND) {
        hand->cards[hand->num_cards++] = *card;
        if (hand_best_value(hand) > BLACKJACK_VALUE) {
            hand->status = HAND_BUST;
        }
    }
}

/**
 * hand_calculate_values: Compute all possible hand totals.
 *
 * ALGORITHM: Start with [0], then for each card:
 * - If NOT an Ace: Add value to all existing totals
 * - If IS an Ace: Branch each total into two (Ace=1 and Ace=11)
 *
 * This handles the combinatorial explosion from multiple Aces.
 * With max 4 Aces, we can have up to 2^4 = 16 possible values.
 */
int hand_calculate_values(const Hand* hand, int* values, int max_values) {
    int num_values = 1;
    values[0] = 0;
    
    for (int i = 0; i < hand->num_cards; i++) {
        if (hand->cards[i].is_ace) {
            int current_count = num_values;
            for (int j = 0; j < current_count && num_values < max_values; j++) {
                values[num_values] = values[j] + 11;
                values[j] += 1;
                num_values++;
            }
        } else {
            for (int j = 0; j < num_values; j++) {
                values[j] += hand->cards[i].value;
            }
        }
    }
    return num_values;
}

/**
 * hand_best_value: Find the optimal playable value for a hand.
 *
 * Strategy: Among all possible values, find the highest one
 * not exceeding 21. If all values bust, return the lowest
 * bust value for comparison purposes.
 */
int hand_best_value(const Hand* hand) {
    int values[32];
    int num_values = hand_calculate_values(hand, values, 32);
    int best = 0;
    
    for (int i = 0; i < num_values; i++) {
        if (values[i] <= BLACKJACK_VALUE && values[i] > best) {
            best = values[i];
        }
    }
    if (best == 0) {
        best = values[0];
        for (int i = 1; i < num_values; i++) {
            if (values[i] < best) best = values[i];
        }
    }
    return best;
}

/**
 * hand_is_soft: Determine if hand is "soft" (contains usable Ace).
 *
 * A hand is soft if there are multiple possible values (indicating
 * an Ace exists) AND at least one value is ≤ 21 (the Ace can be
 * used as 11 without busting).
 */
bool hand_is_soft(const Hand* hand) {
    int values[32];
    int num_values = hand_calculate_values(hand, values, 32);
    
    for (int i = 0; i < num_values; i++) {
        if (values[i] <= BLACKJACK_VALUE) {
            for (int j = i + 1; j < num_values; j++) {
                if (values[j] <= BLACKJACK_VALUE && values[i] != values[j]) {
                    return true;
                }
            }
        }
    }
    return false;
}