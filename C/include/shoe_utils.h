/**
 * @file shoe_utils.h
 * @brief Card shoe management - shuffling, dealing, penetration tracking
 *
 * PURPOSE:
 * Manages the multi-deck card shoe, which is the dealer's card
 * dispensing device. The shoe contains 4-8 shuffled decks and
 * uses a "cut card" to determine when to reshuffle.
 *
 * WHY THE SHOE MATTERS FOR CARD COUNTING:
 * The shoe was introduced specifically to combat card counting.
 * More decks = smaller true count fluctuations = harder to detect
 * favorable situations. The penetration (how deep they deal before
 * reshuffling) critically affects counting profitability.
 *
 * PENETRATION AND PROFIT:
 * - 75% penetration: ~4.5 decks dealt from 6-deck shoe
 *   Advantage: ~1.0-1.5% with 1-10 bet spread
 * - 50% penetration: ~3 decks dealt
 *   Advantage: ~0.3-0.5% (nearly unbeatable)
 *
 * Card counters always seek out games with deep penetration.
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#ifndef SHOE_UTILS_H
#define SHOE_UTILS_H

#include "blackjack_types.h"

/**
 * shoe_init: Creates and initializes a complete multi-deck shoe.
 *
 * Builds all cards for the specified number of decks (each deck
 * has 52 cards: 4 suits × 13 ranks). Cards are created in order
 * and immediately shuffled to randomize. The cut card position
 * is calculated as total_cards × penetration.
 *
 * Example: 6 decks, 75% penetration
 * - Total cards: 6 × 52 = 312
 * - Cut position: 312 × 0.75 = 234
 * - Cards dealt before reshuffle: ~234 (about 4.5 decks)
 *
 * @param shoe Pointer to Shoe structure to initialize
 * @param num_decks Number of 52-card decks (1-8)
 * @param penetration Fraction dealt before reshuffle (0.0-1.0)
 */
void shoe_init(Shoe* shoe, int num_decks, double penetration);

/**
 * shoe_shuffle: Randomizes card order using Fisher-Yates algorithm.
 *
 * FISHER-YATES SHUFFLE (Knuth Shuffle):
 * Produces a uniformly random permutation in O(n) time.
 * Iterates from the end of the array, swapping each element
 * with a randomly chosen earlier element.
 *
 * After shuffling:
 * - Deal position resets to 0 (top of shoe)
 * - Cut card position recalculated based on penetration
 *
 * @param shoe Pointer to Shoe to shuffle
 */
void shoe_shuffle(Shoe* shoe);

/**
 * shoe_deal_card: Deals one card from the shoe.
 *
 * Checks two conditions before dealing:
 * 1. Have we reached the cut card? (penetration limit)
 * 2. Have we exhausted all cards? (shoe empty)
 *
 * If either condition is true, returns NULL to signal that
 * a reshuffle is needed. The caller must check for NULL
 * and reshuffle when indicated.
 *
 * @param shoe Pointer to Shoe to deal from
 * @return Pointer to dealt Card, or NULL if reshuffle needed
 */
Card* shoe_deal_card(Shoe* shoe);

/**
 * shoe_needs_reshuffle: Checks if shoe requires reshuffling.
 *
 * Returns true when the cut card position has been reached
 * or all cards have been dealt. The game engine should check
 * this before each new round.
 *
 * @param shoe Pointer to Shoe to check
 * @return true if reshuffle needed, false otherwise
 */
bool shoe_needs_reshuffle(const Shoe* shoe);

/**
 * shoe_cards_remaining: Counts undealt cards in the shoe.
 *
 * Used for true count calculation:
 * True Count = Running Count / (Remaining Cards / 52)
 *
 * Example: 156 cards remain = 156/52 = 3.0 decks remaining
 *
 * @param shoe Pointer to Shoe to check
 * @return Number of undealt cards
 */
int shoe_cards_remaining(const Shoe* shoe);

#endif /* SHOE_UTILS_H */