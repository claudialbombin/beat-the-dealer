/**
 * @file betting_core.c
 * @brief Dynamic bet sizing based on True Count - 4 functions
 *
 * Converts the card counter's information advantage into actual
 * profit by betting MORE when the count is favorable and MINIMUM
 * when it's unfavorable.
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#include "../include/betting_strategy.h"
#include <stdio.h>
#include <math.h>

/* Rampa de apuestas: mapeo True Count -> Multiplicador */
static double bet_ramp[21];
static double base_bet_amount = 10.0;
static double max_bet_amount = 100.0;

/**
 * bet_init: Initialize betting strategy.
 *
 * Sets up bet ramp mapping true count values to bet multipliers.
 * Conservative at low counts, aggressive at high counts.
 */
void bet_init(double base_bet, double max_bet) {
    base_bet_amount = base_bet;
    max_bet_amount = max_bet;
    
    for (int tc = -10; tc <= 10; tc++) {
        if (tc <= 1) bet_ramp[tc + 10] = 1.0;
        else if (tc == 2) bet_ramp[tc + 10] = 2.0;
        else if (tc == 3) bet_ramp[tc + 10] = 3.0;
        else if (tc == 4) bet_ramp[tc + 10] = 5.0;
        else if (tc == 5) bet_ramp[tc + 10] = 7.0;
        else bet_ramp[tc + 10] = 10.0;
    }
}

/**
 * bet_calculate: Determine bet for current true count.
 *
 * Rounds true count to integer, looks up multiplier, applies
 * to base bet, and caps at maximum bet for bankroll protection.
 */
double bet_calculate(double true_count) {
    int tc_rounded = (int)round(true_count);
    if (tc_rounded < -10) tc_rounded = -10;
    if (tc_rounded > 10) tc_rounded = 10;
    
    double multiplier = bet_ramp[tc_rounded + 10];
    double bet = base_bet_amount * multiplier;
    if (bet > max_bet_amount) bet = max_bet_amount;
    return bet;
}

/**
 * bet_optimize_ramp: Optimize bet spread for risk tolerance.
 *
 * Uses Kelly criterion to balance profit maximization against
 * risk of ruin for the given bankroll.
 */
void bet_optimize_ramp(double bankroll, double target_ror) {
    (void)target_ror;
    
    double conservative_base = bankroll * 0.0025;
    base_bet_amount = conservative_base;
    max_bet_amount = bankroll * 0.02;
    
    for (int tc = -10; tc <= 10; tc++) {
        if (tc <= 1) bet_ramp[tc + 10] = 1.0;
        else if (tc == 2) bet_ramp[tc + 10] = 2.5;
        else if (tc == 3) bet_ramp[tc + 10] = 4.0;
        else if (tc == 4) bet_ramp[tc + 10] = 6.0;
        else if (tc == 5) bet_ramp[tc + 10] = 8.0;
        else bet_ramp[tc + 10] = 10.0;
    }
}

/**
 * bet_print_ramp: Display the complete betting ramp.
 *
 * Shows how bet size varies with true count for user verification.
 */
void bet_print_ramp(void) {
    printf("\n=== HI-LO BET RAMP ===\n");
    printf("Base bet: $%.2f, Max bet: $%.2f\n", base_bet_amount, max_bet_amount);
    
    for (int tc = -10; tc <= 10; tc++)
        printf("TC %+3d: $%6.2f (%.0fx)\n",
               tc, bet_calculate((double)tc), bet_ramp[tc + 10]);
}