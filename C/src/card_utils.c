/**
 * @file card_utils.c
 * @brief Card utility functions implementation - 5 functions maximum
 *
 * Each function is strictly limited to 25 lines or fewer,
 * including the function signature and closing brace.
 * This constraint forces clear, focused functions that
 * each do exactly one thing well.
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#include "../include/card_utils.h"
#include <stdio.h>

/**
 * card_init: Initialize all fields of a Card structure.
 *
 * Rather than requiring callers to set each field individually
 * (which risks inconsistency between game value and Hi-Lo value),
 * this function computes all derived values from the fundamental
 * attributes (rank and suit).
 *
 * EXAMPLE: card_init(&c, 1, HEARTS) creates an Ace of Hearts with:
 *   value = 11, is_ace = true, hi_lo_value = -1
 */
void card_init(Card* card, int rank, CardSuit suit) {
    card->rank = rank;
    card->suit = suit;
    card->value = card_get_value(rank);
    card->is_ace = card_is_ace_val(rank);
    card->hi_lo_value = card_hi_lo_value(rank);
}

/**
 * card_get_value: Map card rank to blackjack game value.
 *
 * Three cases correspond to the three card categories:
 * Ace (11), face cards (10), and number cards (their rank).
 * The Ace starts at 11 and may be reduced to 1 by hand logic.
 */
int card_get_value(int rank) {
    if (rank == 1) return 11;
    if (rank >= 10) return 10;
    return rank;
}

/**
 * card_is_ace_val: Simple Ace detection predicate.
 *
 * While we could check rank == 1 everywhere, this function
 * provides semantic meaning. Reading card_is_ace_val(c->rank)
 * immediately communicates intent better than c->rank == 1.
 */
bool card_is_ace_val(int rank) {
    return rank == 1;
}

/**
 * card_hi_lo_value: Assign Hi-Lo counting value to a card rank.
 *
 * THE HI-LO SYSTEM:
 * +1: Ranks 2-6 (low cards - favorable when removed from deck)
 *  0: Ranks 7-9 (neutral cards - no effect on composition)
 * -1: Ranks 10-13 and Ace (high cards - unfavorable when removed)
 */
int card_hi_lo_value(int rank) {
    if (rank >= 2 && rank <= 6) return 1;
    if (rank >= 7 && rank <= 9) return 0;
    return -1;
}

/**
 * card_to_string: Generate human-readable card representation.
 *
 * Uses a static buffer for simplicity. The format combines
 * the rank symbol with the suit symbol.
 * EXAMPLE OUTPUT: "A♥", "10♠", "K♦", "7♣"
 */
const char* card_to_string(const Card* card) {
    static char buffer[8];
    const char* suits[] = {"H", "D", "C", "S"};
    const char* ranks[] = {"A","2","3","4","5","6","7","8","9","10","J","Q","K"};
    snprintf(buffer, sizeof(buffer), "%s%s", ranks[card->rank-1], suits[card->suit]);
    return buffer;
}