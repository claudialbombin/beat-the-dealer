/**
 * @file monte_carlo.h
 * @brief Monte Carlo solver for computing optimal basic strategy
 *
 * PURPOSE:
 * Computes the mathematically optimal basic strategy for blackjack
 * through massive Monte Carlo simulation. For each possible game
 * state (~340 combinations of player hand and dealer upcard), we
 * simulate thousands of hands for each legal action and select
 * the action with the highest expected value.
 *
 * THE MONTE CARLO METHOD:
 * Named after the famous Monte Carlo casino, this method estimates
 * unknown quantities through random sampling. For blackjack strategy:
 * - We can't calculate optimal actions analytically (too many card sequences)
 * - Instead, we SIMULATE: try each action many times and see which wins most
 * - The Law of Large Numbers guarantees convergence as sample size increases
 *
 * ACCURACY:
 * Standard error ∝ 1/√N, where N = number of simulations
 * - 1,000 simulations: ~3.5% error (rough estimate)
 * - 10,000 simulations: ~1.1% error (reasonable)
 * - 100,000 simulations: ~0.35% error (accurate)
 * - 1,000,000 simulations: ~0.11% error (very precise)
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#ifndef MONTE_CARLO_H
#define MONTE_CARLO_H

#include "blackjack_types.h"

/**
 * mc_solver_init: Initializes Monte Carlo solver with configuration.
 *
 * Displays simulation parameters for user reference and prepares
 * the solver for strategy computation.
 *
 * @param config Pointer to simulation configuration
 */
void mc_solver_init(const SimConfig* config);

/**
 * mc_simulate_action: Estimates expected value of taking an action.
 *
 * MONTE CARLO ESTIMATION PROCESS:
 * 1. Create fresh game instance for each trial
 * 2. Set up player hand to match target state
 * 3. Execute the action being evaluated
 * 4. Complete the hand and dealer play
 * 5. Record financial outcome
 * 6. Repeat N times and average results
 *
 * @param key Game state (player value, dealer upcard, soft/pair flags)
 * @param action Action to evaluate
 * @param config Simulation parameters
 * @return Estimated expected value in betting units
 */
double mc_simulate_action(StrategyKey key, PlayerAction action,
                         const SimConfig* config);

/**
 * mc_find_best_action: Finds optimal action for a game state.
 *
 * Tests all legal actions and selects the one maximizing
 * expected value. This is the core decision function - it
 * answers "what should I do in this situation?"
 *
 * @param key Game state to evaluate
 * @param config Simulation parameters
 * @param best_ev Pointer to store the best EV found
 * @return Optimal action for this state
 */
PlayerAction mc_find_best_action(StrategyKey key,
                                const SimConfig* config,
                                double* best_ev);

/**
 * mc_generate_states: Creates all game states needing evaluation.
 *
 * Generates the complete set of (player value, dealer upcard,
 * soft/hard/pair) combinations that define the strategy table.
 * Approximately 340 states for a complete strategy.
 *
 * @param states Pre-allocated array for generated states
 * @param max_states Maximum number of states to generate
 * @return Number of states generated
 */
int mc_generate_states(StrategyKey* states, int max_states);

/**
 * mc_build_strategy_table: Computes complete basic strategy.
 *
 * Processes all game states, evaluating each action through
 * Monte Carlo simulation, and assembles the strategy table.
 * Supports caching to avoid recomputation.
 *
 * @param table Pre-allocated array for strategy entries
 * @param num_entries Pointer to store number of entries created
 * @param config Simulation parameters
 */
void mc_build_strategy_table(StrategyEntry* table, int* num_entries,
                            const SimConfig* config);

/**
 * mc_print_strategy_table: Displays the complete strategy table.
 *
 * Prints three sections:
 * 1. Hard totals strategy
 * 2. Soft totals strategy
 * 3. Pair splitting strategy
 *
 * Format matches published basic strategy cards used in casinos.
 *
 * @param table Strategy table to display
 * @param num_entries Number of entries in table
 */
void mc_print_strategy_table(const StrategyEntry* table, int num_entries);

/**
 * mc_calculate_basic_ev: Estimate EV of the computed strategy.
 *
 * Simulates many hands using the strategy table and returns
 * average return as a percentage.
 *
 * @param table Strategy table
 * @param num_entries Number of entries
 * @param config Simulation parameters
 * @return Expected value percentage (e.g. -0.5 means -0.5%)
 */
double mc_calculate_basic_ev(const StrategyEntry* table, int num_entries,
                             const SimConfig* config);

#endif /* MONTE_CARLO_H */