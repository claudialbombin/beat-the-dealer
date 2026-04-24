/**
 * @file simulation_engine.h
 * @brief High-level simulation orchestration and analysis
 *
 * PURPOSE:
 * Coordinates the complete simulation pipeline:
 * 1. Generates or loads basic strategy via Monte Carlo
 * 2. Simulates thousands of shoes with Hi-Lo counting
 * 3. Collects and analyzes results by true count
 * 4. Calculates risk metrics and optimal parameters
 *
 * This module ties together all the lower-level components
 * into a coherent analysis that proves whether card counting
 * provides a real mathematical advantage.
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#ifndef SIMULATION_ENGINE_H
#define SIMULATION_ENGINE_H

#include "blackjack_types.h"

/**
 * sim_run_counting_simulation: Executes complete counting analysis.
 *
 * Runs the specified number of shoe simulations with Hi-Lo counting,
 * collecting results for statistical analysis. This is the main
 * experiment that quantifies counting advantage.
 *
 * @param config Simulation parameters
 * @param strategy_table Basic strategy table
 * @param strategy_entries Number of strategy entries
 * @param num_shoes Number of shoes to simulate
 * @param results Pointer to CountResults to populate
 */
void sim_run_counting_simulation(const SimConfig* config,
                                const StrategyEntry* strategy_table,
                                int strategy_entries,
                                int num_shoes,
                                CountResults* results);

/**
 * sim_collect_tc_data: Aggregates results by true count.
 *
 * Groups hand outcomes by the true count at which they were
 * played, enabling the EV vs True Count analysis that is
 * the centerpiece of proving counting effectiveness.
 *
 * @param results Counting results to analyze
 * @param shoe_results_count Number of shoe results
 * @param tc_data Array to populate with TC data points
 * @param tc_data_count Pointer to store number of TC points
 */
void sim_collect_tc_data(const CountResults* results,
                        int shoe_results_count,
                        TrueCountData* tc_data,
                        int* tc_data_count);

/**
 * sim_calculate_ror: Estimates risk of ruin for a bankroll.
 *
 * RISK OF RUIN (RoR):
 * The probability of losing the entire bankroll before doubling it.
 * Even with a positive expectation, variance can cause ruin.
 * Professional counters target RoR < 5%.
 *
 * Formula: RoR = ((1 - EV/σ) / (1 + EV/σ)) ^ (bankroll/σ)
 *
 * @param bankroll Starting bankroll amount
 * @param num_simulations Monte Carlo trials for RoR estimation
 * @param config Simulation parameters
 * @param strategy_table Strategy table
 * @param strategy_entries Number of entries
 * @param ror Pointer to store calculated risk of ruin
 */
void sim_calculate_ror(double bankroll, int num_simulations,
                      const SimConfig* config,
                      const StrategyEntry* strategy_table,
                      int strategy_entries,
                      double* ror);

/**
 * sim_analyze_distribution: Analyzes true count frequency distribution.
 *
 * Understanding how often each true count occurs is crucial for
 * optimizing the bet spread. Most hands (~70%) occur at TC between
 * -1 and +1. High counts (TC ≥ +4) occur only ~5-10% of the time,
 * which is why a wide bet spread is necessary for profitability.
 *
 * @param tc_data True count data to analyze
 * @param tc_data_count Number of TC data points
 * @param distribution Array to populate with frequency percentages
 */
void sim_analyze_distribution(const TrueCountData* tc_data,
                             int tc_data_count,
                             double* distribution);

/**
 * sim_optimize_betting: Finds optimal bet ramp for risk tolerance.
 *
 * Uses Kelly criterion to balance profit maximization against
 * risk of ruin. Adjusts bet ramp to ensure long-term growth
 * while maintaining acceptable risk levels.
 *
 * @param config Simulation parameters
 * @param strategy_table Strategy table
 * @param strategy_entries Number of entries
 * @param bankroll Total playing bankroll
 * @param target_ror Maximum acceptable risk (e.g., 0.05)
 */
void sim_optimize_betting(const SimConfig* config,
                         const StrategyEntry* strategy_table,
                         int strategy_entries,
                         double bankroll,
                         double target_ror);

#endif /* SIMULATION_ENGINE_H */