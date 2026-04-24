/**
 * @file counting_core.c
 * @brief Hi-Lo card counting system implementation - 5 functions
 *
 * Implements the Hi-Lo counting system that tracks deck composition
 * and identifies favorable betting situations.
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#include "../include/counting_system.h"
#include "../include/shoe_utils.h"  /* NEEDED: for shoe_cards_remaining() */
#include <stdio.h>

/**
 * count_reset: Reset running count to zero.
 *
 * Called at start of each new shoe (after shuffle).
 */
void count_reset(int* running_count) {
    *running_count = 0;
}

/**
 * count_update: Update running count when card is revealed.
 *
 * Adds card's Hi-Lo value to running count.
 * Low cards (2-6): +1, Neutral (7-9): 0, High cards (10-A): -1
 */
void count_update(int* running_count, const Card* card) {
    *running_count += card->hi_lo_value;
}

/**
 * count_calculate_true: Compute true count from running count.
 *
 * True Count = Running Count / Decks Remaining
 * Normalizes count for different shoe depths.
 */
double count_calculate_true(int running_count, const Shoe* shoe) {
    int remaining = shoe_cards_remaining(shoe);
    if (remaining <= 0) return 0.0;
    
    double decks_remaining = (double)remaining / 52.0;
    return (double)running_count / decks_remaining;
}

/**
 * count_print_status: Display current counting status.
 *
 * Shows running count, true count, and remaining cards.
 */
void count_print_status(int running_count, const Shoe* shoe) {
    double true_count = count_calculate_true(running_count, shoe);
    printf("RC=%d, TC=%.2f, Cards=%d\n",
           running_count, true_count, shoe_cards_remaining(shoe));
}

/**
 * count_get_advantage_level: Qualitative assessment of true count.
 *
 * Translates numeric true count into human-readable advantage level.
 */
const char* count_get_advantage_level(double true_count) {
    if (true_count >= 5) return "Very favorable";
    if (true_count >= 3) return "Favorable";
    if (true_count >= 1) return "Slightly favorable";
    if (true_count >= -1) return "Neutral";
    if (true_count >= -3) return "Unfavorable";
    return "Very unfavorable";
}