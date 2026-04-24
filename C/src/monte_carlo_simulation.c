/**
 * @file monte_carlo_simulation.c
 * @brief Monte Carlo strategy table builder and printer - 5 functions
 *
 * Builds the complete basic strategy table by evaluating all game
 * states via Monte Carlo simulation, then formats and prints it.
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#include "../include/monte_carlo.h"
#include <stdio.h>
#include <stdlib.h>

/**
 * action_char: Convert action enum to single display character.
 */
static char action_char(PlayerAction action) {
    switch (action) {
        case ACTION_HIT:    return 'H';
        case ACTION_STAND:  return 'S';
        case ACTION_DOUBLE: return 'D';
        case ACTION_SPLIT:  return 'P';
        default:            return '?';
    }
}

/**
 * find_entry: Look up a state in the strategy table.
 *
 * Returns pointer to matching entry or NULL if not found.
 */
static const StrategyEntry* find_entry(const StrategyEntry* table,
                                       int num_entries,
                                       int player_value,
                                       int dealer_up,
                                       bool is_soft) {
    for (int i = 0; i < num_entries; i++) {
        if (table[i].key.player_value == player_value &&
            table[i].key.dealer_upcard == dealer_up &&
            table[i].key.is_soft == is_soft &&
            !table[i].key.is_pair) {
            return &table[i];
        }
    }
    return NULL;
}

/**
 * mc_print_header_for_section: Print dealer upcard column headers.
 * Declared in monte_carlo_core.c as a shared helper.
 */
void mc_print_header(void);

/**
 * print_section: Print one section (hard or soft) of strategy table.
 *
 * Rows = player values, columns = dealer upcards 2..A.
 */
static void print_section(const StrategyEntry* table, int num_entries,
                          int pv_min, int pv_max, bool is_soft,
                          const char* title) {
    printf("\n--- %s ---\n", title);
    printf("%-6s", "Player");
    for (int dv = 2; dv <= 11; dv++)
        printf("%4s", dv == 11 ? "A" : (char[]){(char)('0'+dv), '\0'});
    printf("\n");

    for (int pv = pv_min; pv <= pv_max; pv++) {
        printf("%-6d", pv);
        for (int dv = 2; dv <= 11; dv++) {
            const StrategyEntry* e = find_entry(table, num_entries,
                                                pv, dv, is_soft);
            printf("   %c", e ? action_char(e->action) : '?');
        }
        printf("\n");
    }
}

/**
 * mc_build_strategy_table: Compute complete basic strategy via Monte Carlo.
 *
 * Generates all states, evaluates each via mc_find_best_action,
 * and stores results in the table.
 */
void mc_build_strategy_table(StrategyEntry* table, int* num_entries,
                             const SimConfig* config) {
    mc_solver_init(config);

    StrategyKey states[500];
    int num_states = mc_generate_states(states, 500);
    *num_entries = 0;

    printf("Evaluating %d game states...\n", num_states);
    for (int i = 0; i < num_states && *num_entries < 500; i++) {
        double best_ev;
        PlayerAction best = mc_find_best_action(states[i], config, &best_ev);
        table[*num_entries].key = states[i];
        table[*num_entries].action = best;
        table[*num_entries].expected_value = best_ev;
        (*num_entries)++;

        if (num_states >= 10 && i % (num_states / 10) == 0)
            printf("  Progress: %d%%\n", (i * 100) / num_states);
    }
    printf("Strategy table built: %d entries\n", *num_entries);
}

/**
 * mc_print_strategy_table: Display the complete strategy table.
 *
 * Shows hard totals and soft totals sections.
 */
void mc_print_strategy_table(const StrategyEntry* table, int num_entries) {
    printf("\n=== BASIC STRATEGY TABLE ===");
    print_section(table, num_entries, 5, 21, false, "HARD TOTALS");
    print_section(table, num_entries, 13, 20, true,  "SOFT TOTALS");
    printf("\nKey: H=Hit  S=Stand  D=Double  P=Split\n");
}
