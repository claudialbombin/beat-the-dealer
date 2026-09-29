"""Card values and hand arithmetic.

Suits never matter in blackjack and J/Q/K behave exactly like a 10, so a card
is represented by its blackjack value: 2..10, and 11 for an Ace.
"""

from typing import Iterable, Tuple

ACE = 11
TEN = 10

# The 13 ranks of one suit, as blackjack values.
RANK_VALUES: Tuple[int, ...] = (2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, ACE)

# Infinite-deck draw probabilities (used by the solvers).
CARD_PROBS = {v: RANK_VALUES.count(v) / 13 for v in sorted(set(RANK_VALUES))}

# Hi-Lo tags: low cards +1, 7-9 neutral, tens and Aces -1.
HI_LO = {2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 0, 8: 0, 9: 0, 10: -1, ACE: -1}


def hand_value(cards: Iterable[int]) -> Tuple[int, bool]:
    """Return (best total, is_soft).

    Count every Ace as 1, then promote one Ace to 11 if that does not bust.
    Two Aces can never both be 11 (22), so this is all the "multiple Aces"
    logic a blackjack hand needs.
    """
    hard = 0
    has_ace = False
    for c in cards:
        if c == ACE:
            hard += 1
            has_ace = True
        else:
            hard += c
    if has_ace and hard + 10 <= 21:
        return hard + 10, True
    return hard, False


def add_card(total: int, soft: bool, card: int) -> Tuple[int, bool]:
    """Add one card to a hand summarised as (total, soft)."""
    hard = total - 10 if soft else total
    has_ace = soft
    if card == ACE:
        hard += 1
        has_ace = True
    else:
        hard += card
    if has_ace and hard + 10 <= 21:
        return hard + 10, True
    return hard, False
