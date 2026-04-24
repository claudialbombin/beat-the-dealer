/**
 * @file visual_ev.c
 * @brief EV vs True Count visualization - 5 functions
 *
 * Generates THE KEY VISUALIZATION of the project: Expected Value
 * plotted against True Count. This graph empirically proves that
 * card counting works by showing the direct relationship between
 * count and player advantage.
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#include "../include/visualizer.h"
#include <stdio.h>
#include <math.h>

/**
 * viz_ev_header: Write EV analysis section header.
 *
 * Titles the visualization and provides context for interpretation.
 */
static void viz_ev_header(FILE* file) {
    fprintf(file, "\n=== EXPECTED VALUE vs TRUE COUNT ===\n");
    fprintf(file, "====================================\n\n");
    fprintf(file, "This graph PROVES card counting works.\n");
    fprintf(file, "Positive slope = higher counts = higher returns.\n\n");
}

/**
 * viz_ev_data_point: Write a single TC data point.
 *
 * Shows true count, average return, standard deviation, and
 * number of observations for statistical context.
 */
static void viz_ev_data_point(FILE* file, const TrueCountData* data) {
    fprintf(file, "TC %+3d: EV=%+6.2f%% (std=%.2f%%) [%d hands]\n",
            data->true_count, data->avg_return,
            data->std_return, data->num_observations);
}

/**
 * viz_ev_advantage_zones: Show advantage/disadvantage zones.
 *
 * Identifies which true counts give player advantage versus
 * which give the house advantage.
 */
static void viz_ev_advantage_zones(FILE* file, double min_ev, double max_ev) {
    fprintf(file, "\nAdvantage Zones:\n");
    fprintf(file, "----------------\n");
    if (max_ev > 0)
        fprintf(file, "Player advantage: TC with EV > 0%%\n");
    if (min_ev < 0)
        fprintf(file, "House advantage: TC with EV < 0%%\n");
    fprintf(file, "Break-even: EV = 0%% (fair game)\n");
}

/**
 * viz_ev_ascii_chart: Create ASCII chart of EV vs True Count.
 *
 * Simple text-based plot showing the relationship between
 * true count and expected value.
 */
static void viz_ev_ascii_chart(FILE* file, const TrueCountData* tc_data,
                               int tc_count) {
    fprintf(file, "\nASCII Chart: EV vs True Count\n");
    fprintf(file, "-----------------------------\n");
    
    for (int row = 20; row >= -20; row -= 2) {
        fprintf(file, "%+5.1f%% |", row * 0.5);
        for (int tc = -10; tc <= 10; tc++) {
            bool found = false;
            for (int i = 0; i < tc_count; i++) {
                if (tc_data[i].true_count == tc &&
                    fabs(tc_data[i].avg_return - row * 0.5) < 0.5) {
                    fprintf(file, " *");
                    found = true;
                    break;
                }
            }
            if (!found) fprintf(file, "  ");
        }
        fprintf(file, "\n");
    }
    
    fprintf(file, "        ");
    for (int tc = -10; tc <= 10; tc += 2)
        fprintf(file, "%+3d", tc);
    fprintf(file, "\n        True Count\n");
}

/**
 * viz_ev_vs_true_count: Generate complete EV vs TC visualization.
 *
 * THE KEY GRAPH: Shows empirical proof of counting advantage.
 * Data points, advantage zones, and ASCII chart combined.
 */
void viz_ev_vs_true_count(const TrueCountData* tc_data, int tc_count,
                          const char* filename) {
    FILE* file = fopen(filename, "w");
    if (!file) return;
    
    viz_ev_header(file);
    
    double min_ev = 999, max_ev = -999;
    for (int i = 0; i < tc_count; i++) {
        viz_ev_data_point(file, &tc_data[i]);
        if (tc_data[i].avg_return < min_ev) min_ev = tc_data[i].avg_return;
        if (tc_data[i].avg_return > max_ev) max_ev = tc_data[i].avg_return;
    }
    
    viz_ev_advantage_zones(file, min_ev, max_ev);
    viz_ev_ascii_chart(file, tc_data, tc_count);
    
    fclose(file);
    printf("EV vs TC analysis saved: %s\n", filename);
}

/**
 * viz_counting_advantage: Compare returns with and without counting.
 *
 * Shows side-by-side comparison proving counting advantage.
 */
void viz_counting_advantage(double counting_ev, double basic_ev,
                           const char* filename) {
    FILE* file = fopen(filename, "w");
    if (!file) return;
    
    double advantage = counting_ev - basic_ev;
    
    fprintf(file, "\n=== COUNTING ADVANTAGE ===\n");
    fprintf(file, "==========================\n\n");
    fprintf(file, "Basic Strategy: %+.3f%%\n", basic_ev);
    fprintf(file, "Card Counting:  %+.3f%%\n", counting_ev);
    fprintf(file, "--------------------------\n");
    fprintf(file, "ADVANTAGE:      %+.3f%%\n\n", advantage);
    
    if (advantage > 0)
        fprintf(file, "Card counting PROVIDES player edge!\n");
    
    fclose(file);
    printf("Advantage comparison saved: %s\n", filename);
}