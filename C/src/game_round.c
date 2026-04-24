/**
 * @file game_round.c
 * @brief Complete round with strategy table - 5 functions
 *
 * This module implements the full game round using the computed
 * basic strategy table. Unlike the simplified round elsewhere,
 * this version makes optimal decisions by consulting the
 * Monte Carlo-derived strategy table.
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#include "../include/game_core.h"
#include "../include/counting_system.h"
#include "../include/hand_utils.h"  /* NEEDED: for hand_best_value(), hand_is_soft() */
#include "../include/shoe_utils.h"  /* NEEDED: for shoe_deal_card() */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

/**
 * select_action: Look up optimal action from strategy table.
 *
 * Linear search through strategy table for matching state.
 * Defaults to STAND if no match found (conservative fallback).
 */
static PlayerAction select_action(StrategyKey key,
                                  const StrategyEntry* table,
                                  int table_size) {
    for (int i = 0; i < table_size; i++) {
        if (table[i].key.player_value == key.player_value &&
            table[i].key.dealer_upcard == key.dealer_upcard &&
            table[i].key.is_soft == key.is_soft &&
            table[i].key.is_pair == key.is_pair) {
            return table[i].action;
        }
    }
    return ACTION_STAND;
}

/**
 * create_state_key: Build strategy lookup key from current state.
 *
 * Extracts player value, dealer upcard, and soft flag.
 */
static StrategyKey create_state_key(const Hand* player,
                                    const Card* dealer_up) {
    StrategyKey key;
    key.player_value = hand_best_value(player);
    key.dealer_upcard = dealer_up->value;
    key.is_soft = hand_is_soft(player);
    key.is_pair = false;
    return key;
}

/**
 * play_player_hand: Play a hand using optimal strategy.
 *
 * For each decision point: look up state in strategy table,
 * execute recommended action, update running count.
 */
static void play_player_hand(Hand* hand, const Card* dealer_up,
                            Shoe* shoe, int* running_count,
                            const StrategyEntry* table, int table_size) {
    while (hand->status == HAND_ACTIVE) {
        StrategyKey key = create_state_key(hand, dealer_up);
        PlayerAction action = select_action(key, table, table_size);
        game_execute_action(hand, action, shoe);

        Card* last = &hand->cards[hand->num_cards - 1];
        count_update(running_count, last);
    }
}

/**
 * game_play_full_round: Execute complete round with optimal strategy.
 *
 * Sequence: deal, count cards, play optimally, dealer plays, payout.
 * Returns net profit/loss for the round.
 */
double game_play_full_round(Shoe* shoe, double bet,
                           const StrategyEntry* strategy_table,
                           int table_size, int* running_count) {
    Hand player_hand, dealer_hand;
    game_deal_initial(&player_hand, &dealer_hand, shoe);
    player_hand.bet = bet;
    
    for (int i = 0; i < player_hand.num_cards; i++)
        count_update(running_count, &player_hand.cards[i]);
    for (int i = 0; i < dealer_hand.num_cards; i++)
        count_update(running_count, &dealer_hand.cards[i]);
    
    if (player_hand.status != HAND_BLACKJACK)
        play_player_hand(&player_hand, &dealer_hand.cards[0],
                        shoe, running_count, strategy_table, table_size);
    
    game_play_dealer(&dealer_hand, shoe, true);
    return game_calculate_payout(&player_hand, &dealer_hand);
}

/**
 * game_init: Display game configuration.
 *
 * Seeds random number generator and shows parameters.
 */
void game_init(SimConfig config) {
    srand(time(NULL));
    printf("Game initialized: %d decks, %.0f%% penetration\n",
           config.num_decks, config.penetration * 100);
    printf("Blackjack pays %.1f:1, Max splits: %d\n",
           config.blackjack_payout, config.max_splits);
}