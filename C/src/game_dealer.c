/**
 * @file game_dealer.c
 * @brief Dealer hand logic - 5 functions
 *
 * THE DEALER: A DETERMINISTIC OPPONENT
 *
 * Unlike the player, the dealer has NO choices. They follow a
 * strict, published set of rules that never vary:
 * 1. Must hit any total below 17
 * 2. Must stand on any total of 17 or higher
 * 3. Exception (H17 rule): Must hit soft 17
 *
 * This predictability is what makes basic strategy possible.
 * Because we know exactly how the dealer will play, we can
 * compute the optimal counter-strategy.
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#include "../include/game_core.h"

/**
 * game_deal_initial: Deal initial two-card hands.
 *
 * Standard casino procedure: alternating cards starting with player.
 * Checks for natural blackjack after dealing.
 */
void game_deal_initial(Hand* player, Hand* dealer, Shoe* shoe) {
    Card* card;
    hand_init(player, 1.0);
    hand_init(dealer, 0.0);
    
    card = shoe_deal_card(shoe);
    if (card) hand_add_card(player, card);
    card = shoe_deal_card(shoe);
    if (card) hand_add_card(dealer, card);
    card = shoe_deal_card(shoe);
    if (card) hand_add_card(player, card);
    card = shoe_deal_card(shoe);
    if (card) hand_add_card(dealer, card);
    
    if (hand_is_blackjack_val(player)) player->status = HAND_BLACKJACK;
}

/**
 * dealer_should_hit: Determine if dealer must take a card.
 *
 * Fixed rules: hit below 17, stand on 17+.
 * Exception: H17 rule means hit soft 17 (Ace+6).
 */
static bool dealer_should_hit(const Hand* hand, bool hits_soft_17) {
    int value = hand_best_value(hand);
    if (value < DEALER_STAND_VALUE) return true;
    if (value == DEALER_STAND_VALUE && hand_is_soft(hand) && hits_soft_17)
        return true;
    return false;
}

/**
 * game_play_dealer: Execute dealer's fixed strategy.
 *
 * Dealer draws cards until stopping condition met or bust.
 * Completely deterministic - no decision-making involved.
 */
void game_play_dealer(Hand* dealer, Shoe* shoe, bool hits_soft_17) {
    Card* card;
    while (dealer_should_hit(dealer, hits_soft_17)) {
        card = shoe_deal_card(shoe);
        if (card) hand_add_card(dealer, card);
        else break;
    }
    if (!hand_is_bust_val(dealer)) dealer->status = HAND_STANDING;
}

/**
 * hand_is_bust_val: Check if hand exceeded 21.
 *
 * Busted hand = automatic loss, even if dealer also busts.
 */
bool hand_is_bust_val(const Hand* hand) {
    return hand_best_value(hand) > BLACKJACK_VALUE;
}

/**
 * game_calculate_payout: Determine financial result.
 *
 * Rules in order: bust, blackjack (3:2), compare totals.
 * Player bust = automatic loss (-bet).
 * Dealer bust = player wins (+bet).
 */
double game_calculate_payout(const Hand* player, const Hand* dealer) {
    if (hand_is_bust_val(player)) return -player->bet;
    if (hand_is_bust_val(dealer)) return player->bet;
    if (hand_is_blackjack_val(player) && !hand_is_blackjack_val(dealer))
        return player->bet * 1.5;
    if (hand_is_blackjack_val(player) && hand_is_blackjack_val(dealer))
        return 0.0;
    if (hand_is_blackjack_val(dealer)) return -player->bet;
    
    int pv = hand_best_value(player), dv = hand_best_value(dealer);
    if (pv > dv) return player->bet;
    if (pv < dv) return -player->bet;
    return 0.0;
}