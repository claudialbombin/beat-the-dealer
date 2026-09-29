import random

import pytest

from blackjack.cards import ACE, add_card, hand_value
from blackjack.engine import HiLoCounter, Shoe, play_round
from blackjack.rules import Rules
from blackjack.strategy import Action, BasicStrategy, Decision, reference_chart

T = 10
RULES = Rules()


# ---------------------------------------------------------------- helpers
def rigged(cards, penetration=0.75):
    """A shoe that deals `cards` first (order: P, D-up, P, D-hole, ...)."""
    shoe = Shoe(6, penetration, random.Random(0))
    shoe.cards = list(cards) + shoe.cards
    shoe.pos = 0
    return shoe


class Scripted:
    """Policy that plays a fixed list of actions and records what it saw."""

    def __init__(self, *actions):
        self.actions = list(actions)
        self.seen = []

    def decide(self, d: Decision) -> Action:
        self.seen.append(d)
        return self.actions.pop(0)


# ---------------------------------------------------------------- hand maths
@pytest.mark.parametrize(
    "cards,expected",
    [
        ([ACE, 7], (18, True)),
        ([ACE, ACE], (12, True)),
        ([ACE, ACE, ACE, ACE], (14, True)),
        ([ACE, 7, ACE], (19, True)),
        ([ACE, 7, 5], (13, False)),
        ([T, 6, ACE], (17, False)),
        ([T, T, 2], (22, False)),
        ([ACE, T], (21, True)),
    ],
)
def test_hand_value(cards, expected):
    assert hand_value(cards) == expected


def test_add_card_matches_hand_value():
    rng = random.Random(1)
    for _ in range(5000):
        cards = [rng.choice([2, 3, 4, 5, 6, 7, 8, 9, 10, ACE]) for _ in range(rng.randint(1, 6))]
        t, s = 0, False
        for c in cards:
            t, s = add_card(t, s, c)
        assert (t, s) == hand_value(cards)


# ---------------------------------------------------------------- rules
def test_player_blackjack_pays_3_to_2():
    r = play_round(rigged([ACE, 9, T, 7]), RULES, Scripted())
    assert r.net == 1.5


def test_blackjack_vs_blackjack_pushes():
    r = play_round(rigged([ACE, ACE, T, T]), RULES, Scripted())
    assert r.net == 0


def test_dealer_peeks_so_player_never_acts_against_a_natural():
    policy = Scripted(Action.DOUBLE)
    r = play_round(rigged([6, T, 5, ACE]), RULES, policy)
    assert r.net == -1          # loses only the original bet
    assert policy.seen == []    # never asked to act


def test_doubled_hand_that_busts_loses_two_units():
    r = play_round(rigged([6, T, 6, 7, T]), RULES, Scripted(Action.DOUBLE))
    assert r.net == -2


def test_hit_then_double_not_offered():
    policy = Scripted(Action.HIT, Action.STAND)
    play_round(rigged([2, T, 3, 7, 6]), RULES, policy)
    assert policy.seen[0].can_double and not policy.seen[1].can_double


def test_split_aces_get_one_card_and_21_is_not_blackjack():
    # P: A A, dealer T 9 (19). Split hands: A+T = 21, A+5 = 16.
    policy = Scripted(Action.SPLIT)
    r = play_round(rigged([ACE, T, ACE, 9, T, 5]), RULES, policy)
    assert len(policy.seen) == 1            # no decisions after splitting Aces
    assert [len(h.cards) for h in r.player_hands] == [2, 2]
    assert r.net == 0                        # +1 (21 beats 19, paid 1:1) -1


def test_only_one_split_per_round():
    policy = Scripted(Action.SPLIT, Action.STAND, Action.STAND)
    play_round(rigged([8, T, 8, 9, 8, 8]), RULES, policy)
    assert policy.seen[0].can_split
    assert not policy.seen[1].can_split     # 8,8 again after the split


def test_double_after_split_follows_rule():
    for das in (True, False):
        policy = Scripted(Action.SPLIT, Action.STAND, Action.STAND)
        play_round(rigged([8, T, 8, 9, 3, 2]), Rules(double_after_split=das), policy)
        assert policy.seen[1].can_double is das


def test_dealer_hits_soft_17_only_under_h17():
    cards = [T, ACE, 8, 6, 2, T]  # player 18; dealer A,6 = soft 17, then 2 -> 19
    assert play_round(rigged(cards), Rules(dealer_hits_soft_17=True), Scripted(Action.STAND)).net == -1
    assert play_round(rigged(cards), Rules(dealer_hits_soft_17=False), Scripted(Action.STAND)).net == 1


def test_dealer_does_not_draw_when_player_busted():
    shoe = rigged([T, 6, 6, T, T, 5])
    r = play_round(shoe, RULES, Scripted(Action.HIT))
    assert r.net == -1 and r.dealer_cards == [6, T]


def test_cut_card_lets_the_round_finish():
    shoe = rigged([2, T, 2, 7] + [2] * 10)
    shoe.cut = 5   # cut card reached in the middle of the player's hand
    r = play_round(shoe, RULES, Scripted(*[Action.HIT] * 6, Action.STAND))
    assert r.player_hands[0].total > 4
    assert shoe.needs_shuffle


def test_hole_card_is_counted_only_when_revealed():
    counter = HiLoCounter()
    seen_before_decision = []

    class Peek(Scripted):
        def decide(self, d):
            seen_before_decision.append(counter.running)
            return Action.STAND

    play_round(rigged([T, 5, 9, 2, T]), RULES, Peek(), counter=counter)
    assert seen_before_decision == [-1 + 1 + 0]         # T, 5, 9 visible
    assert counter.running == -1 + 1 + 0 + 1 - 1        # + hole 2, + dealer's T


def test_strategy_resolves_double_codes():
    s = BasicStrategy(hard={(11, 5): "Dh"}, soft={(18, 5): "Ds"})
    assert s.decide(Decision(11, False, 5, True, False)) == Action.DOUBLE
    assert s.decide(Decision(11, False, 5, False, False)) == Action.HIT
    assert s.decide(Decision(18, True, 5, False, False)) == Action.STAND


def test_long_run_never_breaks():
    rng = random.Random(7)
    shoe = Shoe(6, 0.9, rng)
    for _ in range(20000):
        if shoe.needs_shuffle:
            shoe.shuffle()
        play_round(shoe, RULES, reference_chart())
