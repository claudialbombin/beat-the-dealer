/**
 * @file visual_distribution.c
 * @brief True Count distribution visualization - 5 functions
 *
 * Generates histograms and distribution analysis showing how
 * frequently each true count occurs during play. This explains
 * why counters must be patient - favorable counts are rare.
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#include "../include/visualizer.h"
#include <stdio.h>

/**
 * viz_distribution_header: Write distribution section header.
 *
 * Explains what the distribution shows and why it matters.
 */
static void viz_distribution_header(FILE* file) {
    fprintf(file, "\n=== TRUE COUNT DISTRIBUTION ===\n");
    fprintf(file, "===============================\n\n");
    fprintf(file, "Shows how often each TC occurs.\n");
    fprintf(file, "Most hands at TC -1 to +1.\n\n");
}

/**
 * viz_distribution_bar: Draw a single distribution bar.
 *
 * Bar length proportional to frequency. Maximum bar = 50 chars.
 */
static void viz_distribution_bar(FILE* file, int tc, int count,
                                int max_count) {
    int bar_length = (int)((double)count / max_count * 50);
    
    fprintf(file, "TC %+3d [%6d] |", tc, count);
    for (int i = 0; i < bar_length; i++) fprintf(file, "#");
    fprintf(file, "\n");
}

/**
 * viz_tc_distribution: Generate TC distribution visualization.
 *
 * Histogram showing frequency of each true count value.
 * Includes percentage breakdown for significant counts.
 */
void viz_tc_distribution(const TrueCountData* tc_data, int tc_count,
                        const char* filename) {
    FILE* file = fopen(filename, "w");
    if (!file) return;
    
    viz_distribution_header(file);
    
    int max_count = 0, total_obs = 0;
    for (int i = 0; i < tc_count; i++) {
        if (tc_data[i].num_observations > max_count)
            max_count = tc_data[i].num_observations;
        total_obs += tc_data[i].num_observations;
    }
    
    for (int i = 0; i < tc_count; i++)
        viz_distribution_bar(file, tc_data[i].true_count,
                           tc_data[i].num_observations, max_count);
    
    fprintf(file, "\nTotal observations: %d\n", total_obs);
    fprintf(file, "\nPercentage by TC:\n");
    for (int i = 0; i < tc_count; i++) {
        double pct = 100.0 * tc_data[i].num_observations / total_obs;
        if (pct > 0.5)
            fprintf(file, "TC %+3d: %.1f%%\n", tc_data[i].true_count, pct);
    }
    
    fclose(file);
    printf("Distribution saved: %s\n", filename);
}

/**
 * viz_bankroll_evolution: Plot bankroll changes over time.
 *
 * Shows initial and final bankroll with profit/loss summary,
 * plus ASCII chart of bankroll trajectory.
 */
void viz_bankroll_evolution(const double* bankroll_history, int num_points,
                           const char* filename) {
    FILE* file = fopen(filename, "w");
    if (!file) return;
    
    double initial = bankroll_history[0];
    double final = bankroll_history[num_points - 1];
    double profit = final - initial;
    
    fprintf(file, "\n=== BANKROLL EVOLUTION ===\n");
    fprintf(file, "==========================\n\n");
    fprintf(file, "Initial: $%.2f\n", initial);
    fprintf(file, "Final:   $%.2f\n", final);
    fprintf(file, "Profit:  $%+.2f (%.1f%%)\n\n", profit, profit/initial*100);
    
    fprintf(file, "Trajectory (each * = 1 shoe):\n");
    for (int i = 0; i < num_points; i += num_points / 30) {
        if (i >= num_points) break;
        fprintf(file, "%4d: $%8.2f ", i, bankroll_history[i]);
        int bar = (int)((bankroll_history[i] - initial) / initial * 20);
        if (bar > 0) for (int j = 0; j < bar; j++) fprintf(file, "+");
        else for (int j = 0; j < -bar; j++) fprintf(file, "-");
        fprintf(file, "\n");
    }
    
    fclose(file);
    printf("Bankroll evolution saved: %s\n", filename);
}

/**
 * viz_summary_dashboard: Create comprehensive summary dashboard.
 *
 * Combines key metrics into a single overview display.
 * Perfect for project presentations and quick reference.
 */
void viz_summary_dashboard(const CountResults* results,
                          const TrueCountData* tc_data, int tc_count,
                          const char* filename) {
    FILE* file = fopen(filename, "w");
    if (!file) return;
    
    fprintf(file, "\n============================================\n");
    fprintf(file, "  BLACKJACK MONTE CARLO SOLVER - DASHBOARD\n");
    fprintf(file, "============================================\n\n");
    
    fprintf(file, "SUMMARY:\n");
    fprintf(file, "  Hands: %d\n", results->total_hands);
    fprintf(file, "  Counting Return: %+.3f%%\n", results->counting_return_pct);
    fprintf(file, "  Advantage: %+.3f%%\n", results->advantage_pct);
    
    fprintf(file, "\nBEST TRUE COUNTS:\n");
    for (int i = 0; i < tc_count && i < 5; i++) {
        if (tc_data[i].avg_return > 0)
            fprintf(file, "  TC %+d: %+.2f%%\n",
                   tc_data[i].true_count, tc_data[i].avg_return);
    }
    
    fclose(file);
    printf("Dashboard saved: %s\n", filename);
}