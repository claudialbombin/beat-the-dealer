/**
 * @file game_core.h
 * @brief Core blackjack game mechanics - dealing, actions, dealer play, payouts
 *
 * PURPOSE:
 * This module implements the complete rules of casino blackjack.
 * It orchestrates the game flow from initial deal through player
 * decisions to final payout calculation.
 *
 * GAME FLOW:
 * 1. Player places bet
 * 2. Dealer deals 2 cards to player and 2 to dealer (one face down)
 * 3. Player makes decisions (hit, stand, double, split)
 * 4. Dealer reveals hole card and plays according to fixed rules
 * 5. Hands are compared and payouts determined
 *
 * CASINO RULES IMPLEMENTED:
 * - 6-8 deck shoe with cut card
 * - Dealer hits soft 17 (H17 - modern rule)
 * - Blackjack pays 3:2 (1.5x bet)
 * - Double down on any two cards
 * - Split up to 3 times (4 hands maximum)
 * - No surrender (not offered in most casinos)
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#ifndef GAME_CORE_H
#define GAME_CORE_H

#include "blackjack_types.h"

/**
 * game_init: Initializes game configuration and random seed.
 *
 * Displays the game parameters for user verification and
 * seeds the random number generator for shuffle variability.
 *
 * @param config Simulation configuration parameters
 */
void game_init(SimConfig config);

/**
 * game_deal_initial: Deals the initial two-card hands.
 *
 * DEALING PROCEDURE (standard casino protocol):
 * 1. One card face-up to player
 * 2. One card face-up to dealer (the "upcard")
 * 3. Second card face-up to player
 * 4. Second card face-DOWN to dealer (the "hole card")
 *
 * After dealing, checks for natural blackjack on either hand.
 *
 * @param player Pointer to player's Hand to populate
 * @param dealer Pointer to dealer's Hand to populate
 * @param shoe Pointer to Shoe to deal from
 */
void game_deal_initial(Hand* player, Hand* dealer, Shoe* shoe);

/**
 * game_execute_action: Executes a chosen player action.
 *
 * ACTION EFFECTS:
 * - HIT: Add one card from shoe (may cause bust)
 * - STAND: Mark hand as standing (total locked in)
 * - DOUBLE: Double bet, add exactly one card, mark complete
 * - SPLIT: Handled separately due to complexity (creates two hands)
 *
 * @param hand Pointer to Hand to act on
 * @param action Action to execute (HIT, STAND, DOUBLE, or SPLIT)
 * @param shoe Pointer to Shoe to deal from
 */
void game_execute_action(Hand* hand, PlayerAction action, Shoe* shoe);

/**
 * game_calculate_payout: Determines financial result of hand vs dealer.
 *
 * PAYOUT RULES (in order of precedence):
 * 1. Player bust → automatic loss (-bet)
 * 2. Dealer bust → player wins (+bet)
 * 3. Player blackjack, no dealer blackjack → +1.5×bet
 * 4. Both blackjack → push (0)
 * 5. Only dealer blackjack → -bet
 * 6. Compare totals: higher wins, equal pushes
 *
 * @param player Pointer to player's Hand
 * @param dealer Pointer to dealer's Hand
 * @return Net payout (positive = player wins)
 */
double game_calculate_payout(const Hand* player, const Hand* dealer);

/**
 * game_get_available_actions: Lists legal actions for a hand.
 *
 * Available actions depend on hand state:
 * - Active + 2 cards: Hit, Stand, Double, (Split if pair)
 * - Active + 3+ cards: Hit, Stand only
 * - Bust/Blackjack/Doubled: No actions available
 *
 * @param hand Pointer to Hand to evaluate
 * @param count Pointer to store number of available actions
 * @return Array of available actions (caller must NOT free)
 */
PlayerAction* game_get_available_actions(const Hand* hand, int* count);

#endif /* GAME_CORE_H */