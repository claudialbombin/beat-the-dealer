"""Table rules.

Only the rules that change the maths are configurable. The rest are fixed and
apply everywhere in the project (Python, C and the web app):

* the dealer peeks for blackjack with an Ace or ten-value upcard, so a player
  never loses a double or split bet to a dealer natural;
* one split per round (no re-splitting); split Aces receive one card each and
  a two-card 21 after a split is not a blackjack;
* no surrender, and insurance is never taken (basic strategy never takes it).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Rules:
    decks: int = 6
    dealer_hits_soft_17: bool = True
    blackjack_payout: float = 1.5
    double_after_split: bool = True
    penetration: float = 0.75

    def describe(self) -> str:
        return (
            f"{self.decks} decks, dealer {'hits' if self.dealer_hits_soft_17 else 'stands on'} soft 17, "
            f"blackjack pays {self.blackjack_payout:g}:1, "
            f"{'double after split' if self.double_after_split else 'no double after split'}, "
            f"{self.penetration:.0%} penetration"
        )
