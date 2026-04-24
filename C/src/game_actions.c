/**
 * @file game_actions.c
 * @brief Player action handling - 5 functions
 *
 * PLAYER DECISIONS IN BLACKJACK:
 * The player's choices are what make blackjack a game of skill
 * rather than pure chance. Unlike the dealer (who follows fixed
 * rules), the player can optimize their decisions based on the
 * specific situation using the computed basic strategy.
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#include "../include/game_core.h"
#include <stdlib.h>

/**
 * hand_can_double: Check if double down is legal.
 *
 * Requirements: exactly 2 cards, hand active, not from split Aces.
 * Double down is the most aggressive move - doubling the bet
 * for exactly one more card.
 */
static bool hand_can_double(const Hand* hand) {
    return hand->num_cards == 2 &&
           hand->status == HAND_ACTIVE &&
           !hand->from_split_aces;
}

/**
 * hand_can_split: Check if splitting is legal.
 *
 * Requirements: exactly 2 cards of same rank, not from split Aces.
 * Splitting creates two independent hands from a pair.
 */
static bool hand_can_split(const Hand* hand) {
    if (hand->num_cards != 2 || hand->from_split_aces) return false;
    return hand->cards[0].rank == hand->cards[1].rank;
}

/**
 * game_get_available_actions: List legal actions for a hand.
 *
 * Returns array of available actions. Hit and Stand always available.
 * Double and Split available only under specific conditions.
 */
PlayerAction* game_get_available_actions(const Hand* hand, int* count) {
    static PlayerAction actions[4];
    *count = 0;
    
    if (hand->status != HAND_ACTIVE) return actions;
    
    actions[(*count)++] = ACTION_HIT;
    actions[(*count)++] = ACTION_STAND;
    if (hand_can_double(hand)) actions[(*count)++] = ACTION_DOUBLE;
    if (hand_can_split(hand)) actions[(*count)++] = ACTION_SPLIT;
    return actions;
}

/**
 * game_execute_action: Execute a chosen player action.
 *
 * HIT: Add one card, may bust.
 * STAND: Lock in current total.
 * DOUBLE: Double bet, one card, hand complete.
 * SPLIT: Handled by round logic due to complexity.
 */
void game_execute_action(Hand* hand, PlayerAction action, Shoe* shoe) {
    Card* dealt;
    switch (action) {
        case ACTION_HIT:
            dealt = shoe_deal_card(shoe);
            if (dealt) hand_add_card(hand, dealt);
            break;
        case ACTION_STAND:
            hand->status = HAND_STANDING;
            break;
        case ACTION_DOUBLE:
            hand->bet *= 2;
            dealt = shoe_deal_card(shoe);
            if (dealt) hand_add_card(hand, dealt);
            hand->status = HAND_DOUBLED;
            break;
        case ACTION_SPLIT:
            break;
    }
}

/**
 * hand_is_blackjack_val: Check if hand is a natural blackjack.
 *
 * Natural blackjack: exactly 2 cards totaling 21 (Ace + 10-value).
 * Pays 3:2 unless dealer also has blackjack (then push).
 */
bool hand_is_blackjack_val(const Hand* hand) {
    return hand->num_cards == 2 && hand_best_value(hand) == BLACKJACK_VALUE;
}