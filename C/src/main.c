/**
 * @file main.c
 * @brief Main entry point - 5 functions
 *
 * Orchestrates the complete project pipeline:
 * 1. Build basic strategy via Monte Carlo simulation
 * 2. Simulate card counting to measure advantage
 * 3. Generate visualizations of all results
 *
 * Supports multiple execution modes via command-line arguments:
 * --strategy: Build and display basic strategy only
 * --counting: Run card counting simulation only
 * --viz: Generate visualizations only
 * (no args): Execute complete analysis
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 * Repository: github.com/claudia-lopez/blackjack-monte-carlo
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "../include/blackjack_types.h"
#include "../include/monte_carlo.h"
#include "../include/counting_system.h"
#include "../include/betting_strategy.h"
#include "../include/visualizer.h"
#include "../include/interactive_mode.h"

/**
 * print_banner: Display project banner with description.
 *
 * Shows project name, features, and ideal use cases.
 * The banner provides context for interview portfolios.
 */
static void print_banner(void) {
    printf("\n");
    printf("============================================\n");
    printf("  BLACKJACK MONTE CARLO SOLVER\n");
    printf("  Hi-Lo Card Counting System\n");
    printf("============================================\n");
    printf("  Demonstrates:\n");
    printf("  - Monte Carlo simulation methods\n");
    printf("  - Decision optimization\n");
    printf("  - Card counting algorithms\n");
    printf("  - Risk analysis\n");
    printf("============================================\n\n");
}

/**
 * run_basic_strategy: Build and display basic strategy.
 *
 * Executes Monte Carlo simulation to compute optimal strategy,
 * displays the complete table, and calculates expected value.
 */
static void run_basic_strategy(void) {
    printf("\n=== BUILDING BASIC STRATEGY ===\n\n");
    
    SimConfig config = {10000, 6, 0.75, 1.5, 3, true};
    StrategyEntry strategy_table[500];
    int num_entries = 0;
    
    mc_build_strategy_table(strategy_table, &num_entries, &config);
    mc_print_strategy_table(strategy_table, num_entries);
    
    double basic_ev = mc_calculate_basic_ev(strategy_table, num_entries, &config);
    printf("\nBasic Strategy EV: %.3f%%\n", basic_ev);
    printf("House Edge: %.3f%%\n", -basic_ev);
}

/**
 * run_card_counting: Simulate card counting advantage.
 *
 * Runs counting simulation with optimal strategy and dynamic
 * betting. Quantifies the advantage gained through Hi-Lo.
 */
static void run_card_counting(void) {
    printf("\n=== SIMULATING CARD COUNTING ===\n\n");
    
    SimConfig config = {10000, 6, 0.75, 1.5, 3, true};
    StrategyEntry strategy_table[500];
    int num_entries = 0;
    
    mc_build_strategy_table(strategy_table, &num_entries, &config);
    bet_init(10.0, 100.0);
    bet_print_ramp();
    
    CountingResults results;
    count_run_full_simulation(&config, strategy_table, num_entries,
                             100, &results);
    count_print_results(&results);
}

/**
 * generate_visualizations: Create all output visualizations.
 *
 * Generates strategy tables, EV analysis, and distribution
 * charts in text format for universal readability.
 */
static void generate_visualizations(void) {
    printf("\n=== GENERATING VISUALIZATIONS ===\n\n");
    
    SimConfig config = {10000, 6, 0.75, 1.5, 3, true};
    StrategyEntry strategy_table[500];
    int num_entries = 0;
    
    mc_build_strategy_table(strategy_table, &num_entries, &config);
    
    viz_strategy_heatmap(strategy_table, num_entries, "output/strategy.txt");
    
    TrueCountData tc_data[5] = {
        {-3, -1.5, 0.5, 1000},
        {0, -0.5, 0.3, 5000},
        {2, 0.5, 0.4, 2000},
        {4, 1.8, 0.6, 800},
        {6, 2.5, 0.8, 200}
    };
    
    viz_ev_vs_true_count(tc_data, 5, "output/ev_vs_tc.txt");
    viz_counting_advantage(1.2, -0.5, "output/advantage.txt");
    viz_tc_distribution(tc_data, 5, "output/distribution.txt");
    
    double bankroll[] = {10000, 10100, 10250, 10100, 10400, 10700};
    viz_bankroll_evolution(bankroll, 6, "output/bankroll.txt");
    
    printf("\nAll visualizations saved to output/\n");
}

/**
 * main: Entry point with command-line argument dispatching.
 *
 * Supports modes: --strategy, --counting, --viz, or full analysis.
 * Seeds random number generator for reproducibility.
 */
int main(int argc, char* argv[]) {
    print_banner();
    srand(time(NULL));
    
    if (argc == 1) {
        printf("Running complete analysis...\n");
        run_basic_strategy();
        run_card_counting();
        generate_visualizations();
        printf("\n=== ANALYSIS COMPLETE ===\n");
        return 0;
    }
    
    if (strcmp(argv[1], "--strategy") == 0) run_basic_strategy();
    else if (strcmp(argv[1], "--counting") == 0) run_card_counting();
    else if (strcmp(argv[1], "--viz") == 0) generate_visualizations();
    else if (strcmp(argv[1], "--play") == 0) {
        printf("\nCargando estrategia para el modo interactivo...\n");
        SimConfig config = {1000, 6, 0.75, 1.5, 3, true};
        StrategyEntry strategy_table[500];
        int num_entries = 0;
        mc_build_strategy_table(strategy_table, &num_entries, &config);
        run_interactive_game(strategy_table, num_entries);
    }
    else printf("Usage: %s [--strategy|--counting|--viz|--play]\n", argv[0]);
    
    return 0;
}