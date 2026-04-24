/**
 * @file counting_simulation.c
 * @brief Card counting simulation execution - 5 functions
 *
 * Simulates thousands of shoes with Hi-Lo counting to quantify
 * the advantage gained through card counting.
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#include "../include/counting_system.h"
#include "../include/betting_strategy.h"
#include "../include/game_core.h"      /* NEEDED: for game_play_full_round() */
#include "../include/shoe_utils.h"     /* NEEDED: for shoe_init(), shoe_needs_reshuffle() */
#include <stdio.h>

/**
 * count_init_results: Initialize counting results structure.
 *
 * Sets all fields to zero and basic strategy return to -0.5%
 * (theoretical house edge with perfect basic strategy).
 */
static void count_init_results(CountingResults* results) {
    results->total_wagered = 0.0;
    results->total_won = 0.0;
    results->total_hands = 0;
    results->total_shoes = 0;
    results->counting_return_pct = 0.0;
    results->basic_strategy_return_pct = -0.5;
    results->advantage_pct = 0.0;
}

/**
 * count_simulate_single_shoe: Simulate one complete shoe.
 *
 * Plays hands until cut card reached, adjusting bets based on
 * true count. Returns number of hands played and average return.
 */
static int count_simulate_single_shoe(const SimConfig* config,
                                     const StrategyEntry* strategy_table,
                                     int strategy_entries,
                                     double* shoe_return) {
    Shoe shoe;
    shoe_init(&shoe, config->num_decks, config->penetration);
    int running_count = 0, hands_in_shoe = 0;
    double total_bet = 0.0, total_won = 0.0;
    
    while (!shoe_needs_reshuffle(&shoe)) {
        double true_count = count_calculate_true(running_count, &shoe);
        double bet = bet_calculate(true_count);
        
        total_bet += bet;
        double result = game_play_full_round(&shoe, bet, strategy_table,
                                            strategy_entries, &running_count);
        total_won += result;
        hands_in_shoe++;
    }
    
    *shoe_return = (total_bet > 0) ? (total_won / total_bet) * 100.0 : 0.0;
    return hands_in_shoe;
}

/**
 * count_simulate_shoe: Simulate one shoe and update results.
 *
 * Wrapper that runs a single shoe and accumulates statistics.
 */
void count_simulate_shoe(const SimConfig* config,
                        const StrategyEntry* strategy_table,
                        int strategy_entries,
                        CountingResults* results) {
    double shoe_return;
    int hands = count_simulate_single_shoe(config, strategy_table,
                                          strategy_entries, &shoe_return);
    
    results->total_hands += hands;
    results->total_shoes++;
    printf("Shoe completed: %d hands, Return: %.3f%%\n", hands, shoe_return);
}

/**
 * count_print_results: Display counting simulation results.
 *
 * Shows key metrics and confirms whether counting provides advantage.
 */
void count_print_results(const CountingResults* results) {
    printf("\n=== CARD COUNTING RESULTS ===\n");
    printf("Shoes: %d, Hands: %d\n", results->total_shoes, results->total_hands);
    printf("Total bet: $%.2f, Won: $%.2f\n",
           results->total_wagered, results->total_won);
    printf("Basic Strategy: %+.3f%%\n", results->basic_strategy_return_pct);
    printf("Counting Return: %+.3f%%\n", results->counting_return_pct);
    printf("ADVANTAGE: %+.3f%%\n", results->advantage_pct);
    
    if (results->advantage_pct > 0)
        printf("Card counting PROVIDES player advantage\n");
    else
        printf("Card counting did NOT provide advantage\n");
}

/**
 * count_run_full_simulation: Execute complete counting simulation.
 *
 * Runs multiple shoes and aggregates results for statistical analysis.
 */
void count_run_full_simulation(const SimConfig* config,
                              const StrategyEntry* strategy_table,
                              int strategy_entries,
                              int num_shoes,
                              CountingResults* results) {
    count_init_results(results);
    printf("\nRunning counting simulation: %d shoes\n", num_shoes);
    
    double total_return = 0.0;
    int total_hands = 0;
    
    for (int shoe = 0; shoe < num_shoes; shoe++) {
        double shoe_return;
        int hands = count_simulate_single_shoe(config, strategy_table,
                                              strategy_entries, &shoe_return);
        total_return += shoe_return * hands;
        total_hands += hands;
        
        if (num_shoes >= 5 && shoe % (num_shoes / 5) == 0)
            printf("Progress: %d/%d\n", shoe + 1, num_shoes);
    }
    
    results->total_hands = total_hands;
    results->total_shoes = num_shoes;
    results->counting_return_pct = total_hands > 0 ? total_return / total_hands : 0.0;
    results->advantage_pct = results->counting_return_pct -
                            results->basic_strategy_return_pct;
    printf("\nSimulation completed.\n");
}