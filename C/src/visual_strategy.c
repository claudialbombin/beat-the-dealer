/**
 * @file visual_strategy.c
 * @brief Strategy table visualization - 5 functions
 *
 * Generates text-based strategy table displays in ASCII format.
 * These work in any terminal and provide clear, information-dense
 * output showing the optimal action for every game situation.
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#include "../include/visualizer.h"
#include <stdio.h>

/**
 * viz_write_heatmap_header: Write section header for strategy display.
 *
 * Creates a titled section with separator line for visual clarity.
 */
static void viz_write_heatmap_header(FILE* file, const char* title) {
    fprintf(file, "\n%s\n", title);
    for (int i = 0; i < 70; i++) fprintf(file, "=");
    fprintf(file, "\n");
}

/**
 * viz_write_dealer_header: Write dealer upcard column headers.
 *
 * Shows dealer values 2 through Ace as column labels.
 */
static void viz_write_dealer_header(FILE* file) {
    fprintf(file, "%-8s", "Jugador");
    for (int dv = 2; dv <= 11; dv++)
        fprintf(file, "%6s", dv <= 10 ? (char[]){dv+'0','\0'} : "A");
    fprintf(file, "\n");
    for (int i = 0; i < 70; i++) fprintf(file, "-");
    fprintf(file, "\n");
}

/**
 * viz_action_symbol: Convert Action enum to display symbol.
 *
 * Returns spaced symbol for consistent column alignment.
 */
static const char* viz_action_symbol(PlayerAction action) {
    switch (action) {
        case ACTION_HIT: return "  H   ";
        case ACTION_STAND: return "  S   ";
        case ACTION_DOUBLE: return "  D   ";
        case ACTION_SPLIT: return "  P   ";
        default: return "  ?   ";
    }
}

/**
 * viz_write_strategy_row: Write one row of strategy table.
 *
 * Shows optimal action for each dealer upcard given a player hand value.
 */
static void viz_write_strategy_row(FILE* file, int player_value,
                                  const StrategyEntry* table,
                                  int num_entries, bool is_soft) {
    fprintf(file, "%-8d", player_value);
    
    for (int dv = 2; dv <= 11; dv++) {
        bool found = false;
        for (int i = 0; i < num_entries; i++) {
            if (table[i].key.player_value == player_value &&
                table[i].key.dealer_upcard == dv &&
                table[i].key.is_soft == is_soft) {
                fprintf(file, "%s", viz_action_symbol(table[i].action));
                found = true;
                break;
            }
        }
        if (!found) fprintf(file, "  ?   ");
    }
    fprintf(file, "\n");
}

/**
 * viz_strategy_heatmap: Generate complete strategy table visualization.
 *
 * Creates hard totals and soft totals sections with optimal actions.
 */
void viz_strategy_heatmap(const StrategyEntry* table, int num_entries,
                         const char* filename) {
    FILE* file = fopen(filename, "w");
    if (!file) return;
    
    viz_write_heatmap_header(file, "BASIC STRATEGY - HARD TOTALS");
    viz_write_dealer_header(file);
    for (int pv = 5; pv <= 21; pv++)
        viz_write_strategy_row(file, pv, table, num_entries, false);
    
    fprintf(file, "\n");
    viz_write_heatmap_header(file, "BASIC STRATEGY - SOFT TOTALS");
    viz_write_dealer_header(file);
    for (int pv = 13; pv <= 20; pv++)
        viz_write_strategy_row(file, pv, table, num_entries, true);
    
    fclose(file);
    printf("Strategy visualization saved: %s\n", filename);
}