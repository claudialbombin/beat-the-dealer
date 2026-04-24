/**
 * @file visualizer.h
 * @brief ASCII-based visualization generation for terminal output
 *
 * PURPOSE:
 * Generates text-based visualizations of blackjack strategy and
 * analysis results. While not as visually striking as matplotlib
 * charts, these ASCII visualizations work in any terminal and
 * provide clear, information-dense output.
 *
 * VISUALIZATIONS PROVIDED:
 * 1. Strategy tables (heatmap-style with action indicators)
 * 2. EV vs True Count plots (ASCII chart)
 * 3. Counting advantage comparison
 * 4. True Count distribution histograms
 * 5. Bankroll evolution over time
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#ifndef VISUALIZER_H
#define VISUALIZER_H

#include "blackjack_types.h"

/**
 * viz_strategy_heatmap: Generates complete strategy table display.
 *
 * Creates three sections:
 * - Hard totals strategy (5-21 vs dealer 2-A)
 * - Soft totals strategy (A2-A9 vs dealer 2-A)
 * - Pair splitting strategy (22-AA vs dealer 2-A)
 *
 * Each cell shows the recommended action:
 * H = Hit, S = Stand, D = Double, P = Split
 *
 * @param table Strategy table to display
 * @param num_entries Number of entries in table
 * @param filename Output file path
 */
void viz_strategy_heatmap(const StrategyEntry* table, int num_entries,
                         const char* filename);

/**
 * viz_ev_vs_true_count: Creates EV vs True Count visualization.
 *
 * THIS IS THE KEY VISUALIZATION that proves card counting works.
 * Shows the empirical relationship between true count and player
 * expected value. A clear positive correlation demonstrates that
 * higher counts correspond to higher returns.
 *
 * @param tc_data True count data points
 * @param tc_count Number of data points
 * @param filename Output file path
 */
void viz_ev_vs_true_count(const TrueCountData* tc_data, int tc_count,
                          const char* filename);

/**
 * viz_counting_advantage: Compares returns with and without counting.
 *
 * Side-by-side comparison showing:
 * - Basic strategy return (negative = house edge)
 * - Counting return (should be positive if counting works)
 * - Calculated advantage (difference between the two)
 *
 * @param counting_ev Expected return with counting (%)
 * @param basic_ev Expected return without counting (%)
 * @param filename Output file path
 */
void viz_counting_advantage(double counting_ev, double basic_ev,
                           const char* filename);

/**
 * viz_tc_distribution: Visualizes true count frequency distribution.
 *
 * Shows how often each true count occurs during play. Most hands
 * cluster around TC = 0, with extreme counts being rare. This
 * explains why counters must be patient and bet big when
 * favorable counts finally appear.
 *
 * @param tc_data True count data
 * @param tc_count Number of data points
 * @param filename Output file path
 */
void viz_tc_distribution(const TrueCountData* tc_data, int tc_count,
                        const char* filename);

/**
 * viz_bankroll_evolution: Plots bankroll changes over time.
 *
 * Shows the typical experience of a card counter:
 * - General upward trend (positive expectation)
 * - Significant volatility (large swings are normal)
 * - Occasional drawdowns (testing emotional discipline)
 *
 * @param bankroll_history Array of bankroll values over time
 * @param num_points Number of data points
 * @param filename Output file path
 */
void viz_bankroll_evolution(const double* bankroll_history, int num_points,
                           const char* filename);

#endif /* VISUALIZER_H */