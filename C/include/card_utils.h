/**
 * @file card_utils.h
 * @brief Card utility functions - initialization, valuation, and display
 *
 * PURPOSE:
 * This module provides the fundamental card operations used throughout
 * the entire project. Every card in the simulation is created, valued,
 * and displayed through these functions. Centralizing card operations
 * ensures consistency across all modules and prevents subtle bugs
 * where different parts of the code might value cards differently.
 *
 * KEY CONCEPTS:
 * - Game Value: The card's contribution to a blackjack hand total
 * - Hi-Lo Value: The card's contribution to the running count
 * - Ace Detection: Quick identification of the special two-value card
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#ifndef CARD_UTILS_H
#define CARD_UTILS_H

#include "blackjack_types.h"

/**
 * card_init: Initializes all fields of a Card structure from raw data.
 *
 * This function takes fundamental card attributes (rank and suit) and
 * computes all derived properties: game value, Ace flag, and Hi-Lo
 * counting value. Computing these once at initialization and storing
 * them avoids repeated calculations during simulation inner loops,
 * providing a significant performance optimization when running
 * millions of hand simulations.
 *
 * @param card Pointer to Card structure to initialize
 * @param rank Numeric rank (1=Ace, 2-10, 11=J, 12=Q, 13=K)
 * @param suit Card suit (HEARTS, DIAMONDS, CLUBS, SPADES)
 */
void card_init(Card* card, int rank, CardSuit suit);

/**
 * card_get_value: Converts card rank to blackjack game value.
 *
 * Blackjack valuation rules:
 * - Ace (rank 1) = 11 initially (Hand logic may reduce to 1)
 * - Face cards (rank >= 10) = 10
 * - Number cards (rank 2-9) = their face value
 *
 * @param rank Numeric card rank (1-13)
 * @return Blackjack game value (1-11)
 */
int card_get_value(int rank);

/**
 * card_is_ace_val: Checks if a rank represents an Ace.
 *
 * Aces require special handling throughout the game because they
 * have TWO possible values (1 or 11). This function provides a
 * clear, semantic way to check for Aces rather than comparing
 * rank == 1 directly (which is less readable and maintainable).
 *
 * @param rank Numeric card rank
 * @return true if rank is 1 (Ace), false otherwise
 */
bool card_is_ace_val(int rank);

/**
 * card_hi_lo_value: Determines the Hi-Lo counting system value.
 *
 * THE HI-LO COUNTING SYSTEM (Harvey Dubner, 1963):
 * This is the most widely used card counting system because it
 * balances effectiveness with simplicity. The system assigns
 * point values to track deck composition:
 *
 * +1: Ranks 2, 3, 4, 5, 6 (low cards - favorable when REMOVED)
 *  0: Ranks 7, 8, 9      (neutral cards - no effect)
 * -1: Ranks 10, 11, 12, 13 AND Ace (high cards - favorable when REMAINING)
 *
 * When the running count is POSITIVE, more low cards have been dealt
 * than high cards, meaning the remaining deck is rich in Aces and
 * 10-value cards, which favors the player.
 *
 * @param rank Numeric card rank
 * @return +1, 0, or -1 based on Hi-Lo system
 */
int card_hi_lo_value(int rank);

/**
 * card_to_string: Creates human-readable string representation.
 *
 * Generates strings like "A♥", "7♣", "K♠", "10♦" for display
 * and logging purposes. Uses a static buffer (not thread-safe,
 * but acceptable for single-threaded simulation use).
 *
 * @param card Pointer to Card to convert
 * @return Pointer to static string buffer (do not free)
 */
const char* card_to_string(const Card* card);

#endif /* CARD_UTILS_H */