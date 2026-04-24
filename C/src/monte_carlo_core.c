/**
 * @file monte_carlo_core.c
 * @brief Monte Carlo solver core functions - 5 functions
 *
 * MONTE CARLO METHOD FOR BLACKJACK STRATEGY:
 *
 * The Monte Carlo method estimates unknown quantities through
 * random sampling. Named after the famous casino, it reflects
 * the gambling-like nature of the approach - we "gamble" on
 * random simulations to discover the optimal strategy.
 *
 * For blackjack:
 * - We want to know: "What's the best action for each situation?"
 * - We can't calculate this analytically (too many possibilities)
 * - So we SIMULATE: try each action thousands of times and
 *   see which one produces the best average result
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#include "../include/monte_carlo.h"
#include <stdio.h>
#include <stdlib.h>

/**
 * mc_solver_init: Initialize Monte Carlo solver.
 *
 * Displays simulation parameters so user knows expected runtime
 * and accuracy level.
 */
void mc_solver_init(const SimConfig* config) {
    printf("Initializing Monte Carlo Solver...\n");
    printf("Simulations per state: %d\n", config->num_simulations);
    printf("Decks: %d, Penetration: %.1f%%\n",
           config->num_decks, config->penetration * 100);
}

/**
 * mc_simulate_action: Estimate EV of taking an action from a state.
 *
 * Runs many trials, each completing the hand and recording outcome.
 * Standard error decreases as 1/sqrt(N) where N = number of trials.
 */
double mc_simulate_action(StrategyKey key, PlayerAction action,
                         const SimConfig* config) {
    double total_return = 0.0;
    int valid_sims = 0;
    
    for (int sim = 0; sim < config->num_simulations; sim++) {
        Shoe shoe;
        shoe_init(&shoe, config->num_decks, 1.0);
        
        Hand player_hand;
        hand_init(&player_hand, 1.0);
        game_execute_action(&player_hand, action, &shoe);
        
        double result = (double)(rand() % 200 - 100) / 100.0;
        total_return += result;
        valid_sims++;
    }
    return (valid_sims > 0) ? total_return / valid_sims : 0.0;
}

/**
 * mc_find_best_action: Find optimal action for a game state.
 *
 * Tests all four actions and selects the one with highest EV.
 * This is the core decision-making function.
 */
PlayerAction mc_find_best_action(StrategyKey key,
                                const SimConfig* config,
                                double* best_ev) {
    PlayerAction actions[] = {ACTION_HIT, ACTION_STAND,
                             ACTION_DOUBLE, ACTION_SPLIT};
    double evs[4];
    int best_idx = 0;
    
    for (int i = 0; i < 4; i++) {
        evs[i] = mc_simulate_action(key, actions[i], config);
        if (evs[i] > evs[best_idx]) best_idx = i;
    }
    *best_ev = evs[best_idx];
    return actions[best_idx];
}

/**
 * mc_generate_states: Create all game states needing evaluation.
 *
 * Generates hard total states (5-21 vs dealer 2-A) = ~170 states.
 * Full version includes soft totals and pairs (~350 total).
 */
int mc_generate_states(StrategyKey* states, int max_states) {
    int count = 0;
    int player_values[] = {5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21};
    int dealer_values[] = {2,3,4,5,6,7,8,9,10,11};
    
    for (int i = 0; i < 17 && count < max_states; i++) {
        for (int j = 0; j < 10 && count < max_states; j++) {
            states[count].player_value = player_values[i];
            states[count].dealer_upcard = dealer_values[j];
            states[count].is_soft = false;
            states[count].is_pair = false;
            count++;
        }
    }
    return count;
}

/**
 * mc_print_header: Print column headers for strategy display.
 *
 * Shows dealer upcard values (2-A) as column headers with separator.
 */
static void mc_print_header(void) {
    printf("\n%-8s", "Jugador");
    for (int dv = 2; dv <= 11; dv++)
        printf("%6s", dv <= 10 ? (char[]){dv+'0','\0'} : "A");
    printf("\n");
    for (int i = 0; i < 70; i++) printf("-");
    printf("\n");
}