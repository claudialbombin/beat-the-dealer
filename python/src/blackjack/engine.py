"""A finite-shoe blackjack engine.

Used for the shoe simulations (the real, finite 6-deck game with a cut card)
and as the executable specification the tests check. Rules are described in
`rules.py`.

Card counting follows what a player at the table actually sees: every
face-up card is counted when it is dealt, and the dealer's hole card only
when it is turned over.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Protocol

from .cards import ACE, HI_LO, RANK_VALUES, hand_value
from .rules import Rules
from .strategy import Action, Decision


class ShoeExhausted(RuntimeError):
    pass


class Shoe:
    def __init__(self, decks: int, penetration: float, rng: random.Random):
        if not 0 < penetration < 1:
            raise ValueError("penetration must be in (0, 1)")
        self.cards: List[int] = list(RANK_VALUES) * 4 * decks
        self.penetration = penetration
        self.rng = rng
        self.shuffle()

    def shuffle(self) -> None:
        self.rng.shuffle(self.cards)  # Fisher-Yates
        self.pos = 0
        self.cut = int(len(self.cards) * self.penetration)

    def draw(self) -> int:
        # The cut card only stops play *between* rounds; a round in progress
        # always finishes. Running out entirely cannot happen at sane
        # penetrations, so treat it as a bug rather than silently continuing.
        if self.pos >= len(self.cards):
            raise ShoeExhausted("shoe ran out mid-round")
        c = self.cards[self.pos]
        self.pos += 1
        return c

    @property
    def needs_shuffle(self) -> bool:
        return self.pos >= self.cut

    @property
    def decks_remaining(self) -> float:
        return (len(self.cards) - self.pos) / 52


class HiLoCounter:
    def __init__(self) -> None:
        self.running = 0

    def reset(self) -> None:
        self.running = 0

    def see(self, card: int) -> None:
        self.running += HI_LO[card]

    def true_count(self, shoe: Shoe) -> float:
        return self.running / max(shoe.decks_remaining, 0.25)


class Policy(Protocol):
    def decide(self, d: Decision) -> Action: ...


@dataclass
class Hand:
    cards: List[int]
    bet: float
    from_split: bool = False
    split_aces: bool = False
    doubled: bool = False
    done: bool = False

    @property
    def value(self):
        return hand_value(self.cards)

    @property
    def total(self) -> int:
        return self.value[0]

    @property
    def bust(self) -> bool:
        return self.total > 21

    @property
    def blackjack(self) -> bool:
        return len(self.cards) == 2 and self.total == 21 and not self.from_split


@dataclass
class RoundResult:
    net: float                 # player's profit, in currency units
    initial_bet: float
    player_hands: List[Hand] = field(default_factory=list)
    dealer_cards: List[int] = field(default_factory=list)


def dealer_should_hit(cards: List[int], rules: Rules) -> bool:
    total, soft = hand_value(cards)
    return total < 17 or (total == 17 and soft and rules.dealer_hits_soft_17)


def settle(hand: Hand, dealer_total: int) -> float:
    if hand.bust:
        return -hand.bet
    if dealer_total > 21 or hand.total > dealer_total:
        return hand.bet
    if hand.total < dealer_total:
        return -hand.bet
    return 0.0


def play_round(
    shoe: Shoe,
    rules: Rules,
    policy: Policy,
    bet: float = 1.0,
    counter: Optional[HiLoCounter] = None,
) -> RoundResult:
    see: Callable[[int], None] = counter.see if counter else (lambda c: None)

    def draw_seen() -> int:
        c = shoe.draw()
        see(c)
        return c

    p1, up, p2 = draw_seen(), draw_seen(), draw_seen()
    hole = shoe.draw()  # face down: not counted yet
    dealer = [up, hole]
    player = Hand([p1, p2], bet)
    result = RoundResult(0.0, bet, [player], dealer)

    dealer_bj = hand_value(dealer)[0] == 21
    if dealer_bj or player.blackjack:
        # Peek (or player natural): the round ends immediately.
        see(hole)
        if dealer_bj and player.blackjack:
            result.net = 0.0
        elif dealer_bj:
            result.net = -bet
        else:
            result.net = bet * rules.blackjack_payout
        return result

    hands = [player]
    i = 0
    while i < len(hands):
        hand = hands[i]
        _play_hand(hand, hands, up, shoe, rules, policy, draw_seen)
        i += 1
    result.player_hands = hands

    see(hole)
    if any(not h.bust for h in hands):
        while dealer_should_hit(dealer, rules):
            dealer.append(draw_seen())
    dealer_total = hand_value(dealer)[0]
    result.net = sum(settle(h, dealer_total) for h in hands)
    return result


def _play_hand(hand, hands, up, shoe, rules, policy, draw_seen) -> None:
    if hand.split_aces:
        hand.cards.append(draw_seen())
        hand.done = True
        return
    if hand.from_split and len(hand.cards) == 1:
        hand.cards.append(draw_seen())

    while not hand.done:
        total, soft = hand.value
        if total >= 21:
            hand.done = True
            break
        two_cards = len(hand.cards) == 2
        is_pair = two_cards and hand.cards[0] == hand.cards[1]
        can_split = is_pair and len(hands) == 1  # one split per round
        can_double = two_cards and (not hand.from_split or rules.double_after_split)
        action = policy.decide(
            Decision(total, soft, up, can_double, can_split, hand.cards[0] if is_pair else None)
        )
        if action == Action.STAND:
            hand.done = True
        elif action == Action.HIT:
            hand.cards.append(draw_seen())
        elif action == Action.DOUBLE:
            if not can_double:
                raise ValueError("policy doubled when it was not allowed")
            hand.bet *= 2
            hand.doubled = True
            hand.cards.append(draw_seen())
            hand.done = True
        elif action == Action.SPLIT:
            if not can_split:
                raise ValueError("policy split when it was not allowed")
            aces = hand.cards[0] == ACE
            second = Hand([hand.cards[1]], hand.bet, from_split=True, split_aces=aces)
            hand.cards = [hand.cards[0]]
            hand.from_split = True
            hand.split_aces = aces
            hands.append(second)
            if aces:
                hand.cards.append(draw_seen())
                hand.done = True
            else:
                hand.cards.append(draw_seen())
        else:  # pragma: no cover
            raise ValueError(action)
