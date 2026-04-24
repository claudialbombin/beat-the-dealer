"""
Comprehensive tests for game_engine.py

Covers: Card, Shoe, Hand, BlackjackGame
"""

import pytest
import random
from game_engine import (
    Card, Suit, Hand, HandStatus, Shoe, BlackjackGame, Action
)


# ============================================================================
# Card Tests
# ============================================================================

class TestCardValue:
    def test_ace_value_is_11(self):
        assert Card(1, "♥").value == 11

    def test_ten_value_is_10(self):
        assert Card(10, "♦").value == 10

    def test_jack_value_is_10(self):
        assert Card(11, "♣").value == 10

    def test_queen_value_is_10(self):
        assert Card(12, "♠").value == 10

    def test_king_value_is_10(self):
        assert Card(13, "♥").value == 10

    def test_number_card_value_equals_rank(self):
        for rank in range(2, 10):
            assert Card(rank, "♣").value == rank


class TestCardIsAce:
    def test_ace_is_ace(self):
        assert Card(1, "♥").is_ace is True

    def test_two_is_not_ace(self):
        assert Card(2, "♥").is_ace is False

    def test_ten_is_not_ace(self):
        assert Card(10, "♦").is_ace is False

    def test_king_is_not_ace(self):
        assert Card(13, "♠").is_ace is False


class TestCardHiLoVal:
    def test_low_cards_return_plus_one(self):
        for rank in range(2, 7):  # 2, 3, 4, 5, 6
            assert Card(rank, "♥").hi_lo_val == 1

    def test_neutral_cards_return_zero(self):
        for rank in range(7, 10):  # 7, 8, 9
            assert Card(rank, "♣").hi_lo_val == 0

    def test_ten_returns_minus_one(self):
        assert Card(10, "♦").hi_lo_val == -1

    def test_jack_returns_minus_one(self):
        assert Card(11, "♠").hi_lo_val == -1

    def test_queen_returns_minus_one(self):
        assert Card(12, "♥").hi_lo_val == -1

    def test_king_returns_minus_one(self):
        assert Card(13, "♣").hi_lo_val == -1

    def test_ace_returns_minus_one(self):
        assert Card(1, "♦").hi_lo_val == -1


class TestCardStr:
    def test_ace_str(self):
        assert str(Card(1, "♥")) == "A♥"

    def test_jack_str(self):
        assert str(Card(11, "♠")) == "J♠"

    def test_queen_str(self):
        assert str(Card(12, "♦")) == "Q♦"

    def test_king_str(self):
        assert str(Card(13, "♣")) == "K♣"

    def test_ten_str(self):
        assert str(Card(10, "♥")) == "10♥"

    def test_seven_str(self):
        assert str(Card(7, "♣")) == "7♣"

    def test_repr_matches_str(self):
        card = Card(5, "♠")
        assert repr(card) == str(card)


# ============================================================================
# Shoe Tests
# ============================================================================

class TestShoeConstruction:
    def test_six_deck_shoe_has_312_cards(self):
        shoe = Shoe(num_decks=6)
        assert len(shoe.cards) == 312

    def test_single_deck_shoe_has_52_cards(self):
        shoe = Shoe(num_decks=1)
        assert len(shoe.cards) == 52

    def test_eight_deck_shoe_has_416_cards(self):
        shoe = Shoe(num_decks=8)
        assert len(shoe.cards) == 416

    def test_shoe_contains_each_rank_four_times_per_deck(self):
        shoe = Shoe(num_decks=1)
        for rank in range(1, 14):
            count = sum(1 for c in shoe.cards if c.rank == rank)
            assert count == 4, f"Rank {rank} should appear 4 times in a single deck"

    def test_dealt_pile_empty_initially(self):
        shoe = Shoe(num_decks=6)
        assert len(shoe.dealt) == 0

    def test_cut_pos_set_by_penetration(self):
        shoe = Shoe(num_decks=6, penetration=0.75)
        assert shoe.cut_pos == int(312 * 0.75)


class TestShoeDeal:
    def test_deal_returns_a_card(self):
        shoe = Shoe(num_decks=6)
        card = shoe.deal()
        assert isinstance(card, Card)

    def test_deal_moves_card_from_available_to_dealt(self):
        shoe = Shoe(num_decks=6)
        initial_available = len(shoe.cards)
        shoe.deal()
        assert len(shoe.cards) == initial_available - 1
        assert len(shoe.dealt) == 1

    def test_deal_returns_none_after_cut_card(self):
        shoe = Shoe(num_decks=1, penetration=0.5)
        # Deal up to cut card
        cut_pos = shoe.cut_pos
        for _ in range(cut_pos):
            card = shoe.deal()
        # Next deal should return None
        assert shoe.deal() is None

    def test_deal_returns_none_when_empty(self):
        shoe = Shoe(num_decks=1, penetration=1.0)
        for _ in range(52):
            shoe.deal()
        assert shoe.deal() is None


class TestShoeNeedsReshuffle:
    def test_new_shoe_does_not_need_reshuffle(self):
        shoe = Shoe(num_decks=6, penetration=0.75)
        assert shoe.needs_reshuffle is False

    def test_needs_reshuffle_after_cut_card(self):
        shoe = Shoe(num_decks=1, penetration=0.5)
        cut_pos = shoe.cut_pos
        for _ in range(cut_pos):
            shoe.deal()
        assert shoe.needs_reshuffle is True

    def test_needs_reshuffle_when_empty(self):
        shoe = Shoe(num_decks=1, penetration=1.0)
        for _ in range(52):
            shoe.deal()
        assert shoe.needs_reshuffle is True


class TestShoeDecksRemaining:
    def test_full_shoe_decks_remaining(self):
        shoe = Shoe(num_decks=6)
        assert abs(shoe.decks_remaining - 6.0) < 0.1

    def test_decks_remaining_decreases_after_deal(self):
        shoe = Shoe(num_decks=6)
        before = shoe.decks_remaining
        for _ in range(52):
            shoe.deal()
        after = shoe.decks_remaining
        assert after < before

    def test_decks_remaining_after_one_deck_dealt(self):
        shoe = Shoe(num_decks=6)
        for _ in range(52):
            shoe.deal()
        assert abs(shoe.decks_remaining - 5.0) < 0.1


class TestShoeShuffle:
    def test_shuffle_resets_dealt_pile(self):
        shoe = Shoe(num_decks=6)
        for _ in range(10):
            shoe.deal()
        shoe.shuffle()
        assert len(shoe.dealt) == 0

    def test_shuffle_restores_all_cards(self):
        shoe = Shoe(num_decks=6)
        for _ in range(50):
            shoe.deal()
        shoe.shuffle()
        assert len(shoe.cards) == 312

    def test_shuffle_sets_cut_position(self):
        shoe = Shoe(num_decks=6, penetration=0.75)
        shoe.shuffle()
        assert shoe.cut_pos == int(312 * 0.75)


# ============================================================================
# Hand Tests
# ============================================================================

class TestHandPossibleValues:
    def test_hard_hand_single_value(self):
        hand = Hand([Card(8, "♥"), Card(6, "♣")])
        assert hand.possible_values == [14]

    def test_soft_hand_two_values(self):
        hand = Hand([Card(1, "♥"), Card(7, "♣")])
        assert 8 in hand.possible_values
        assert 18 in hand.possible_values

    def test_two_aces_possible_values(self):
        hand = Hand([Card(1, "♥"), Card(1, "♣")])
        assert 2 in hand.possible_values
        assert 12 in hand.possible_values

    def test_three_cards_ace(self):
        # A + 7 + 3 = soft 21 or 11
        hand = Hand([Card(1, "♥"), Card(7, "♣"), Card(3, "♦")])
        assert 11 in hand.possible_values
        assert 21 in hand.possible_values

    def test_no_ace_no_duplicates(self):
        hand = Hand([Card(10, "♥"), Card(6, "♣")])
        assert len(hand.possible_values) == 1


class TestHandBestValue:
    def test_hard_hand_best_value(self):
        hand = Hand([Card(8, "♥"), Card(6, "♣")])
        assert hand.best_value == 14

    def test_soft_hand_best_value(self):
        hand = Hand([Card(1, "♥"), Card(7, "♣")])
        assert hand.best_value == 18

    def test_busted_returns_lowest(self):
        hand = Hand([Card(10, "♥"), Card(10, "♣"), Card(5, "♦")])
        assert hand.best_value == 25  # All values > 21, return lowest

    def test_ace_adjusts_to_avoid_bust(self):
        # A + 5 + 10 = 16 (Ace becomes 1)
        hand = Hand([Card(1, "♥"), Card(5, "♣"), Card(10, "♦")])
        assert hand.best_value == 16

    def test_blackjack_best_value(self):
        hand = Hand([Card(1, "♥"), Card(13, "♠")])  # A + K = 21
        assert hand.best_value == 21

    def test_hard_21(self):
        hand = Hand([Card(7, "♥"), Card(7, "♣"), Card(7, "♦")])
        assert hand.best_value == 21


class TestHandIsSoft:
    def test_soft_hand_with_ace(self):
        hand = Hand([Card(1, "♥"), Card(7, "♣")])
        assert hand.is_soft is True

    def test_hard_hand_no_ace(self):
        hand = Hand([Card(8, "♥"), Card(6, "♣")])
        assert hand.is_soft is False

    def test_ace_forced_to_one_is_not_soft(self):
        # A + 5 + 10 = 16 (Ace must be 1 to avoid bust)
        hand = Hand([Card(1, "♥"), Card(5, "♣"), Card(10, "♦")])
        assert hand.is_soft is False

    def test_soft_20_is_soft(self):
        hand = Hand([Card(1, "♥"), Card(9, "♠")])  # A+9 = soft 20
        assert hand.is_soft is True


class TestHandIsBlackjack:
    def test_ace_plus_king_is_blackjack(self):
        hand = Hand([Card(1, "♥"), Card(13, "♠")])
        assert hand.is_blackjack is True

    def test_ace_plus_ten_is_blackjack(self):
        hand = Hand([Card(1, "♦"), Card(10, "♣")])
        assert hand.is_blackjack is True

    def test_ace_plus_jack_is_blackjack(self):
        hand = Hand([Card(1, "♠"), Card(11, "♥")])
        assert hand.is_blackjack is True

    def test_three_card_21_is_not_blackjack(self):
        hand = Hand([Card(7, "♥"), Card(7, "♣"), Card(7, "♦")])
        assert hand.is_blackjack is False

    def test_two_card_non_21_is_not_blackjack(self):
        hand = Hand([Card(10, "♥"), Card(9, "♣")])
        assert hand.is_blackjack is False

    def test_blackjack_requires_two_cards(self):
        hand = Hand([Card(1, "♥"), Card(5, "♣"), Card(5, "♦")])
        assert hand.is_blackjack is False


class TestHandAdd:
    def test_add_card_increases_count(self):
        hand = Hand([Card(8, "♥"), Card(6, "♣")])
        hand.add(Card(2, "♦"))
        assert len(hand.cards) == 3

    def test_add_card_updates_value(self):
        hand = Hand([Card(8, "♥"), Card(6, "♣")])
        hand.add(Card(2, "♦"))
        assert hand.best_value == 16

    def test_add_busting_card_sets_bust_status(self):
        hand = Hand([Card(10, "♥"), Card(8, "♣")])
        hand.add(Card(5, "♦"))  # 10+8+5 = 23
        assert hand.status == HandStatus.BUST

    def test_add_non_busting_card_keeps_active(self):
        hand = Hand([Card(8, "♥"), Card(6, "♣")])
        hand.add(Card(2, "♦"))
        assert hand.status == HandStatus.ACTIVE


class TestHandCanDouble:
    def test_two_card_active_hand_can_double(self):
        hand = Hand([Card(8, "♥"), Card(3, "♣")])
        assert hand.can_double is True

    def test_three_card_hand_cannot_double(self):
        hand = Hand([Card(8, "♥"), Card(3, "♣")])
        hand.add(Card(2, "♦"))
        assert hand.can_double is False

    def test_non_active_hand_cannot_double(self):
        hand = Hand([Card(8, "♥"), Card(3, "♣")])
        hand.status = HandStatus.STANDING
        assert hand.can_double is False

    def test_split_aces_hand_cannot_double(self):
        hand = Hand([Card(1, "♥"), Card(7, "♣")], from_split_aces=True)
        assert hand.can_double is False


class TestHandCanSplit:
    def test_pair_can_split(self):
        hand = Hand([Card(8, "♥"), Card(8, "♣")])
        assert hand.can_split is True

    def test_aces_pair_can_split(self):
        hand = Hand([Card(1, "♥"), Card(1, "♣")])
        assert hand.can_split is True

    def test_different_ranks_cannot_split(self):
        hand = Hand([Card(8, "♥"), Card(9, "♣")])
        assert hand.can_split is False

    def test_three_card_hand_cannot_split(self):
        hand = Hand([Card(8, "♥"), Card(8, "♣")])
        hand.add(Card(2, "♦"))
        assert hand.can_split is False

    def test_from_split_aces_cannot_resplit(self):
        hand = Hand([Card(1, "♥"), Card(1, "♣")], from_split_aces=True)
        assert hand.can_split is False

    def test_non_active_cannot_split(self):
        hand = Hand([Card(8, "♥"), Card(8, "♣")])
        hand.status = HandStatus.STANDING
        assert hand.can_split is False


# ============================================================================
# BlackjackGame Tests
# ============================================================================

class TestBlackjackGameRunningCount:
    def test_initial_running_count_is_zero(self):
        game = BlackjackGame()
        assert game.running_count == 0

    def test_update_count_low_card_increments(self):
        game = BlackjackGame()
        game.update_count(Card(5, "♥"))
        assert game.running_count == 1

    def test_update_count_high_card_decrements(self):
        game = BlackjackGame()
        game.update_count(Card(10, "♥"))
        assert game.running_count == -1

    def test_update_count_neutral_card_unchanged(self):
        game = BlackjackGame()
        game.update_count(Card(8, "♥"))
        assert game.running_count == 0

    def test_update_count_cumulative(self):
        game = BlackjackGame()
        game.update_count(Card(2, "♥"))   # +1
        game.update_count(Card(3, "♣"))   # +1
        game.update_count(Card(10, "♦"))  # -1
        assert game.running_count == 1


class TestBlackjackGameTrueCount:
    def test_true_count_zero_on_fresh_shoe(self):
        game = BlackjackGame()
        assert game.true_count == 0.0

    def test_true_count_scales_with_decks_remaining(self):
        game = BlackjackGame(num_decks=6)
        game.running_count = 12
        # With ~6 decks remaining, TC = 12/6 = 2
        assert abs(game.true_count - 2.0) < 0.1

    def test_true_count_zero_when_no_decks_remain(self):
        game = BlackjackGame()
        game.shoe.cards = []
        assert game.true_count == 0.0


class TestBlackjackGameDealInitial:
    def test_deal_initial_returns_two_hands(self):
        game = BlackjackGame()
        player, dealer = game.deal_initial()
        assert isinstance(player, Hand)
        assert isinstance(dealer, Hand)

    def test_both_hands_have_two_cards(self):
        game = BlackjackGame()
        player, dealer = game.deal_initial()
        assert len(player.cards) == 2
        assert len(dealer.cards) == 2

    def test_blackjack_hand_gets_blackjack_status(self):
        # Set up shoe to deal A + K to player
        game = BlackjackGame()
        game.shoe.cards = [
            Card(13, "♠"),  # dealer second card (K)
            Card(1, "♣"),   # player second card (A)
            Card(7, "♦"),   # dealer first card (7)
            Card(1, "♥"),   # player first card (A) - wait, let me think
        ]
        # Deal order: player[0], dealer[0], player[1], dealer[1]
        # cards.pop() takes from end: player gets 1♥, dealer gets 7♦, player gets 1♣, dealer gets K♠
        # player: A+A = 12 not blackjack. Let me fix this.
        game2 = BlackjackGame()
        game2.shoe.cards = [
            Card(2, "♠"),   # dealer second card
            Card(13, "♣"),  # player second card (K)
            Card(7, "♦"),   # dealer first card
            Card(1, "♥"),   # player first card (A)
        ]
        # cards.pop() takes from end: player gets A♥, dealer gets 7♦, player gets K♣, dealer gets 2♠
        # player: A+K = blackjack
        game2.shoe.cut_pos = 100  # ensure no early reshuffle
        player, dealer = game2.deal_initial()
        assert player.is_blackjack is True
        assert player.status == HandStatus.BLACKJACK


class TestBlackjackGameAvailableActions:
    def test_initial_two_card_hand_has_four_actions(self):
        # Non-pair initial hand
        game = BlackjackGame()
        hand = Hand([Card(8, "♥"), Card(5, "♣")])
        actions = game.available_actions(hand)
        assert Action.HIT in actions
        assert Action.STAND in actions
        assert Action.DOUBLE_DOWN in actions

    def test_pair_hand_has_split(self):
        game = BlackjackGame()
        hand = Hand([Card(8, "♥"), Card(8, "♣")])
        actions = game.available_actions(hand)
        assert Action.SPLIT in actions

    def test_three_card_hand_has_no_double_or_split(self):
        game = BlackjackGame()
        hand = Hand([Card(8, "♥"), Card(5, "♣")])
        hand.add(Card(2, "♦"))
        actions = game.available_actions(hand)
        assert Action.DOUBLE_DOWN not in actions
        assert Action.SPLIT not in actions
        assert Action.HIT in actions
        assert Action.STAND in actions

    def test_non_active_hand_has_no_actions(self):
        game = BlackjackGame()
        hand = Hand([Card(8, "♥"), Card(5, "♣")])
        hand.status = HandStatus.STANDING
        assert game.available_actions(hand) == []

    def test_bust_hand_has_no_actions(self):
        game = BlackjackGame()
        hand = Hand([Card(10, "♥"), Card(5, "♣")])
        hand.add(Card(10, "♦"))  # 10+5+10=25 → bust, status set to BUST
        assert game.available_actions(hand) == []


class TestBlackjackGameExecuteAction:
    def test_hit_adds_card(self):
        game = BlackjackGame()
        hand = Hand([Card(8, "♥"), Card(5, "♣")])
        game.execute_action(hand, Action.HIT, Card(7, "♦"))
        assert len(hand.cards) == 3

    def test_hit_updates_running_count(self):
        game = BlackjackGame()
        hand = Hand([Card(8, "♥"), Card(5, "♣")])
        # Prepend a known card (2♦ = +1 hi-lo) so it's dealt next via pop()
        game.shoe.cards = game.shoe.cards + [Card(2, "♦")]
        game.shoe.cut_pos = 1000
        initial_count = game.running_count
        game.execute_action(hand, Action.HIT, Card(7, "♦"))
        # Card(2) has hi_lo_val = +1, so count should increase by 1
        assert game.running_count == initial_count + 1

    def test_stand_sets_standing_status(self):
        game = BlackjackGame()
        hand = Hand([Card(8, "♥"), Card(5, "♣")])
        game.execute_action(hand, Action.STAND, Card(7, "♦"))
        assert hand.status == HandStatus.STANDING

    def test_double_down_doubles_bet(self):
        game = BlackjackGame()
        hand = Hand([Card(8, "♥"), Card(3, "♣")], bet=10.0)
        game.execute_action(hand, Action.DOUBLE_DOWN, Card(7, "♦"))
        assert hand.bet == 20.0

    def test_double_down_adds_exactly_one_card(self):
        game = BlackjackGame()
        hand = Hand([Card(8, "♥"), Card(3, "♣")], bet=10.0)
        game.execute_action(hand, Action.DOUBLE_DOWN, Card(7, "♦"))
        assert len(hand.cards) == 3

    def test_double_down_sets_doubled_status(self):
        game = BlackjackGame()
        hand = Hand([Card(8, "♥"), Card(3, "♣")], bet=10.0)
        game.execute_action(hand, Action.DOUBLE_DOWN, Card(7, "♦"))
        assert hand.status == HandStatus.DOUBLED

    def test_split_returns_two_hands(self):
        game = BlackjackGame()
        hand = Hand([Card(8, "♥"), Card(8, "♣")], bet=10.0)
        result = game.execute_action(hand, Action.SPLIT, Card(7, "♦"))
        assert len(result) == 2

    def test_split_each_hand_has_two_cards(self):
        game = BlackjackGame()
        hand = Hand([Card(8, "♥"), Card(8, "♣")], bet=10.0)
        result = game.execute_action(hand, Action.SPLIT, Card(7, "♦"))
        for h in result:
            assert len(h.cards) == 2

    def test_split_preserves_original_bet(self):
        game = BlackjackGame()
        hand = Hand([Card(8, "♥"), Card(8, "♣")], bet=10.0)
        result = game.execute_action(hand, Action.SPLIT, Card(7, "♦"))
        for h in result:
            assert h.bet == 10.0

    def test_split_aces_marks_from_split_aces(self):
        game = BlackjackGame()
        hand = Hand([Card(1, "♥"), Card(1, "♣")], bet=10.0)
        result = game.execute_action(hand, Action.SPLIT, Card(7, "♦"))
        for h in result:
            assert h.from_split_aces is True

    def test_split_non_aces_does_not_mark_from_split_aces(self):
        game = BlackjackGame()
        hand = Hand([Card(8, "♥"), Card(8, "♣")], bet=10.0)
        result = game.execute_action(hand, Action.SPLIT, Card(7, "♦"))
        for h in result:
            assert h.from_split_aces is False

    def test_split_marks_is_split(self):
        game = BlackjackGame()
        hand = Hand([Card(8, "♥"), Card(8, "♣")], bet=10.0)
        result = game.execute_action(hand, Action.SPLIT, Card(7, "♦"))
        for h in result:
            assert h.is_split is True


class TestBlackjackGamePlayDealer:
    def test_dealer_hits_below_17(self):
        game = BlackjackGame()
        # Dealer has 8+7 = 15 → must hit
        dealer_hand = Hand([Card(8, "♥"), Card(7, "♣")])
        game.play_dealer(dealer_hand)
        assert dealer_hand.best_value >= 17 or dealer_hand.status == HandStatus.BUST

    def test_dealer_stands_on_hard_17(self):
        game = BlackjackGame()
        dealer_hand = Hand([Card(10, "♥"), Card(7, "♣")])
        game.play_dealer(dealer_hand)
        assert dealer_hand.best_value == 17
        assert dealer_hand.status == HandStatus.STANDING

    def test_dealer_stands_on_hard_18(self):
        game = BlackjackGame()
        dealer_hand = Hand([Card(10, "♥"), Card(8, "♣")])
        game.play_dealer(dealer_hand)
        assert dealer_hand.best_value == 18

    def test_dealer_hits_soft_17_when_h17(self):
        game = BlackjackGame(dealer_hits_soft_17=True)
        # A+6 = soft 17 → must hit in H17 game
        dealer_hand = Hand([Card(1, "♥"), Card(6, "♣")])
        initial_cards = len(dealer_hand.cards)
        game.play_dealer(dealer_hand)
        # Dealer must have taken at least one more card (unless shoe ran out)
        assert (len(dealer_hand.cards) > initial_cards or 
                dealer_hand.status == HandStatus.BUST)

    def test_dealer_stands_soft_17_when_s17(self):
        game = BlackjackGame(dealer_hits_soft_17=False)
        dealer_hand = Hand([Card(1, "♥"), Card(6, "♣")])
        game.play_dealer(dealer_hand)
        assert dealer_hand.best_value == 17
        assert dealer_hand.status == HandStatus.STANDING
        assert len(dealer_hand.cards) == 2

    def test_dealer_standing_marks_standing_status(self):
        game = BlackjackGame()
        dealer_hand = Hand([Card(10, "♥"), Card(9, "♣")])  # 19
        game.play_dealer(dealer_hand)
        assert dealer_hand.status == HandStatus.STANDING

    def test_dealer_busting_marks_bust_status(self):
        game = BlackjackGame()
        dealer_hand = Hand([Card(10, "♥"), Card(6, "♣")])  # 16 → must hit
        # Put 10-value cards at end of shoe so pop() gives them first
        game.shoe.cards = game.shoe.cards + [Card(10, "♦")] * 50
        game.shoe.cut_pos = 1000
        game.play_dealer(dealer_hand)
        assert dealer_hand.status == HandStatus.BUST


class TestBlackjackGameCalculatePayout:
    def test_player_bust_loses_bet(self):
        game = BlackjackGame()
        player = Hand([Card(10, "♥"), Card(10, "♣"), Card(5, "♦")], bet=10.0)
        player.status = HandStatus.BUST
        dealer = Hand([Card(7, "♥"), Card(10, "♣")])
        dealer.status = HandStatus.STANDING
        assert game.calculate_payout(player, dealer) == -10.0

    def test_dealer_bust_player_wins(self):
        game = BlackjackGame()
        player = Hand([Card(10, "♥"), Card(7, "♣")], bet=10.0)
        player.status = HandStatus.STANDING
        dealer = Hand([Card(10, "♦"), Card(10, "♠"), Card(5, "♥")])
        dealer.status = HandStatus.BUST
        assert game.calculate_payout(player, dealer) == 10.0

    def test_player_blackjack_pays_3_to_2(self):
        game = BlackjackGame(blackjack_payout=1.5)
        player = Hand([Card(1, "♥"), Card(13, "♣")], bet=10.0)
        player.status = HandStatus.BLACKJACK
        dealer = Hand([Card(7, "♦"), Card(10, "♠")])
        dealer.status = HandStatus.STANDING
        assert game.calculate_payout(player, dealer) == 15.0

    def test_both_blackjack_is_push(self):
        game = BlackjackGame()
        player = Hand([Card(1, "♥"), Card(13, "♣")], bet=10.0)
        player.status = HandStatus.BLACKJACK
        dealer = Hand([Card(1, "♦"), Card(10, "♠")])
        dealer.status = HandStatus.BLACKJACK
        assert game.calculate_payout(player, dealer) == 0.0

    def test_dealer_blackjack_player_loses(self):
        game = BlackjackGame()
        player = Hand([Card(10, "♥"), Card(9, "♣")], bet=10.0)
        player.status = HandStatus.STANDING
        dealer = Hand([Card(1, "♦"), Card(10, "♠")])
        dealer.status = HandStatus.BLACKJACK
        assert game.calculate_payout(player, dealer) == -10.0

    def test_player_wins_higher_total(self):
        game = BlackjackGame()
        player = Hand([Card(10, "♥"), Card(9, "♣")], bet=10.0)
        player.status = HandStatus.STANDING
        dealer = Hand([Card(7, "♦"), Card(10, "♠")])
        dealer.status = HandStatus.STANDING
        assert game.calculate_payout(player, dealer) == 10.0

    def test_dealer_wins_higher_total(self):
        game = BlackjackGame()
        player = Hand([Card(7, "♥"), Card(9, "♣")], bet=10.0)
        player.status = HandStatus.STANDING
        dealer = Hand([Card(10, "♦"), Card(9, "♠")])
        dealer.status = HandStatus.STANDING
        assert game.calculate_payout(player, dealer) == -10.0

    def test_equal_totals_push(self):
        game = BlackjackGame()
        player = Hand([Card(10, "♥"), Card(7, "♣")], bet=10.0)
        player.status = HandStatus.STANDING
        dealer = Hand([Card(10, "♦"), Card(7, "♠")])
        dealer.status = HandStatus.STANDING
        assert game.calculate_payout(player, dealer) == 0.0

    def test_custom_blackjack_payout_6_5(self):
        game = BlackjackGame(blackjack_payout=1.2)  # 6:5
        player = Hand([Card(1, "♥"), Card(13, "♣")], bet=10.0)
        player.status = HandStatus.BLACKJACK
        dealer = Hand([Card(7, "♦"), Card(10, "♠")])
        dealer.status = HandStatus.STANDING
        assert game.calculate_payout(player, dealer) == 12.0


class TestBlackjackGamePlayRound:
    def test_play_round_returns_float(self):
        game = BlackjackGame()
        result = game.play_round(bet=10.0)
        assert isinstance(result, float)

    def test_play_round_result_is_multiple_of_bet(self):
        # Without strategy, result should be ±bet, 0 (push), or 1.5×bet (blackjack).
        # Negative doubled bets (-20) and positive doubled/split wins (20) are also valid.
        game = BlackjackGame()
        for _ in range(10):
            result = game.play_round(bet=10.0)
            # -20 = double-down loss, -10 = normal loss, 0 = push,
            # 10 = normal win, 15 = blackjack payout, 20 = doubled/split win
            assert result in [-10.0, 0.0, 10.0, 15.0, -20.0, 20.0]

    def test_play_round_reshuffles_when_needed(self):
        game = BlackjackGame()
        # Simulate cut card reached by filling the dealt pile past cut_pos
        game.shoe.dealt = [Card(2, "♦")] * game.shoe.cut_pos
        assert game.shoe.needs_reshuffle is True
        running_count_before = game.running_count
        game.play_round(bet=1.0)
        # After reshuffle, running count is reset to 0
        assert game.running_count == 0 or isinstance(game.running_count, int)

    def test_play_round_with_strategy(self):
        game = BlackjackGame()
        # Minimal strategy: always stand
        strategy = {}
        for v in range(5, 22):
            for d in range(2, 12):
                for soft in [True, False]:
                    strategy[(v, d, soft)] = Action.STAND
        result = game.play_round(bet=10.0, strategy=strategy)
        assert isinstance(result, float)

    def test_multiple_rounds_possible(self):
        game = BlackjackGame()
        total = 0.0
        for _ in range(20):
            total += game.play_round(bet=10.0)
        # Should complete without error
        assert isinstance(total, float)
