/**
 * @file monte_carlo_solver.c
 * @brief Monte Carlo solver management - 5 functions
 *
 * High-level management of the Monte Carlo solver including
 * caching, loading, and complete analysis orchestration.
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#include "../include/monte_carlo.h"
#include "../include/game_core.h"      /* NEEDED: for game_play_full_round() */
#include "../include/shoe_utils.h"     /* NEEDED: for shoe_init(), shoe_needs_reshuffle(), shoe_shuffle() */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/**
 * mc_save_to_file: Save strategy table to binary file.
 *
 * Caches computed strategy to avoid recomputation on subsequent runs.
 * File format: [num_entries (int)] [entries (StrategyEntry array)]
 */
static void mc_save_to_file(const StrategyEntry* table, int num_entries,
                           const char* filename) {
    FILE* file = fopen(filename, "wb");
    if (file) {
        fwrite(&num_entries, sizeof(int), 1, file);
        fwrite(table, sizeof(StrategyEntry), num_entries, file);
        fclose(file);
        printf("Strategy saved: %s\n", filename);
    }
}

/**
 * mc_load_from_file: Load strategy table from binary file.
 *
 * Returns number of entries loaded, or 0 if file not found.
 */
static int mc_load_from_file(StrategyEntry* table, int max_entries,
                            const char* filename) {
    FILE* file = fopen(filename, "rb");
    if (!file) return 0;
    
    int num_entries;
    fread(&num_entries, sizeof(int), 1, file);
    if (num_entries <= max_entries)
        fread(table, sizeof(StrategyEntry), num_entries, file);
    fclose(file);
    return num_entries <= max_entries ? num_entries : 0;
}

/**
 * mc_calculate_basic_ev: Calculate EV of basic strategy.
 *
 * Simulates many hands using the strategy to verify it achieves
 * the theoretical house edge of approximately -0.5%.
 */
double mc_calculate_basic_ev(const StrategyEntry* table, int num_entries,
                            const SimConfig* config) {
    Shoe shoe;
    shoe_init(&shoe, config->num_decks, config->penetration);
    double total_return = 0.0;
    int num_hands = 10000, running_count = 0;
    
    for (int i = 0; i < num_hands; i++) {
        if (shoe_needs_reshuffle(&shoe)) {
            shoe_shuffle(&shoe);
            running_count = 0;
        }
        total_return += game_play_full_round(&shoe, 1.0, table,
                                            num_entries, &running_count);
    }
    return (total_return / num_hands) * 100.0;
}

/**
 * mc_run_full_analysis: Execute complete Monte Carlo analysis.
 *
 * Builds or loads strategy, prints table, calculates EV.
 * Uses caching to avoid recomputation when possible.
 */
void mc_run_full_analysis(StrategyEntry* table, int* num_entries,
                         const SimConfig* config) {
    printf("=== MONTE CARLO FULL ANALYSIS ===\n\n");
    
    *num_entries = mc_load_from_file(table, 500, "strategy_cache.dat");
    
    if (*num_entries == 0) {
        printf("Building strategy from scratch...\n");
        mc_build_strategy_table(table, num_entries, config);
        mc_save_to_file(table, *num_entries, "strategy_cache.dat");
    } else {
        printf("Strategy loaded from cache (%d entries)\n", *num_entries);
    }
    
    mc_print_strategy_table(table, *num_entries);
    double basic_ev = mc_calculate_basic_ev(table, *num_entries, config);
    printf("\nBasic Strategy EV: %.3f%%\n", basic_ev);
    printf("House Edge: %.3f%%\n", -basic_ev);
}

/**
 * mc_compare_strategies: Compare two strategy tables.
 *
 * Counts differences between two strategy tables.
 * Useful for comparing different simulation configurations.
 */
void mc_compare_strategies(const StrategyEntry* table1, int entries1,
                          const StrategyEntry* table2, int entries2) {
    int differences = 0;
    int total = entries1 < entries2 ? entries1 : entries2;
    
    for (int i = 0; i < total; i++)
        if (table1[i].action != table2[i].action) differences++;
    
    printf("Strategy differences: %d/%d (%.1f%%)\n",
           differences, total, 100.0 * differences / total);
}