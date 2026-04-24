/**
 * @file shoe_utils.c
 * @brief Card shoe management implementation - 5 functions
 *
 * THE SHOE: THE DEALER'S TOOL AND THE COUNTER'S ENEMY
 *
 * In modern blackjack, cards are dealt from a "shoe" - a plastic box
 * containing multiple shuffled decks. The shoe was introduced in the
 * 1960s specifically to combat card counting, which had become
 * widespread after Edward Thorp published "Beat the Dealer."
 *
 * HOW THE SHOE AFFECTS COUNTING:
 * - More decks = smaller true count fluctuations
 * - Deeper penetration = more opportunities for high counts
 * - Cut card placement critically affects profitability
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#include "../include/shoe_utils.h"
#include <stdlib.h>

/**
 * shoe_init: Create and initialize a complete multi-deck shoe.
 *
 * For a 6-deck shoe: 6 × 52 = 312 cards total.
 * Cards are created in order and immediately shuffled.
 * Cut card position = total × penetration.
 */
void shoe_init(Shoe* shoe, int num_decks, double penetration) {
    shoe->num_decks = num_decks;
    shoe->penetration = penetration;
    shoe->total_cards = num_decks * 52;
    shoe->current_position = 0;
    
    int idx = 0;
    for (int d = 0; d < num_decks; d++) {
        for (int suit = 0; suit < 4; suit++) {
            for (int rank = 1; rank <= 13; rank++) {
                card_init(&shoe->cards[idx++], rank, (CardSuit)suit);
            }
        }
    }
    shoe_shuffle(shoe);
}

/**
 * shoe_shuffle: Randomize card order using Fisher-Yates algorithm.
 *
 * FISHER-YATES produces a uniformly random permutation in O(n) time.
 * Iterates from the end, swapping each element with a randomly
 * chosen earlier element. After shuffling, position resets to 0.
 */
void shoe_shuffle(Shoe* shoe) {
    for (int i = shoe->total_cards - 1; i > 0; i--) {
        int j = rand() % (i + 1);
        Card temp = shoe->cards[i];
        shoe->cards[i] = shoe->cards[j];
        shoe->cards[j] = temp;
    }
    shoe->current_position = 0;
    shoe->cut_card_position = (int)(shoe->total_cards * shoe->penetration);
}

/**
 * shoe_deal_card: Deal one card from the shoe.
 *
 * Checks if cut card reached or shoe empty before dealing.
 * Returns NULL to signal reshuffle needed.
 */
Card* shoe_deal_card(Shoe* shoe) {
    if (shoe->current_position >= shoe->cut_card_position) return NULL;
    if (shoe->current_position >= shoe->total_cards) return NULL;
    return &shoe->cards[shoe->current_position++];
}

/**
 * shoe_needs_reshuffle: Check if shoe requires reshuffling.
 *
 * Returns true when cut card reached or all cards dealt.
 * Game engine checks this before each round.
 */
bool shoe_needs_reshuffle(const Shoe* shoe) {
    return shoe->current_position >= shoe->cut_card_position ||
           shoe->current_position >= shoe->total_cards;
}

/**
 * shoe_cards_remaining: Count undealt cards in the shoe.
 *
 * Used for true count calculation.
 * True Count = Running Count / (Remaining Cards / 52)
 */
int shoe_cards_remaining(const Shoe* shoe) {
    return shoe->total_cards - shoe->current_position;
}