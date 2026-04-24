"""
Blackjack Game Engine - Core Implementation
=============================================

This module implements a complete, casino-accurate blackjack simulation engine.
Every aspect of the game is modeled to match real casino conditions:

CARD REPRESENTATION:
    Cards are represented with their rank (Ace through King), suit, and
    blackjack-specific attributes. Each card knows its game value (Aces are
    initially 11 but can become 1), and its Hi-Lo counting value.

THE SHOE (MULTI-DECK CONTAINER):
    Modern casinos use 4-8 deck "shoes" to make card counting harder.
    The shoe tracks how many cards have been dealt and automatically signals
    when it's time to reshuffle (when the "cut card" is reached).

HAND VALUATION:
    The trickiest part of blackjack programming is handling Aces correctly.
    An Ace can be worth either 1 or 11, and a hand can have multiple Aces.
    For example, A+A+A+A could be 4, 14, 24, 34, or 44 depending on how
    many Aces we count as 11. The "best value" is the highest total not
    exceeding 21, or the lowest total if all combinations bust.

GAME FLOW:
    1. Player places bet
    2. Dealer deals 2 cards to player (face up) and 2 to dealer (one face up)
    3. If dealer shows Ace, player can buy insurance
    4. Player acts on their hand (hit, stand, double, split)
    5. Dealer reveals hole card and plays according to fixed rules
    6. Hands are compared and payouts determined

WHY THIS MATTERS FOR JANE STREET:
    Jane Street has a famously playful culture around strategy games.
    Building a correct blackjack engine demonstrates:
    - Attention to edge cases (Ace handling, split rules, etc.)
    - Understanding of probabilistic systems
    - Ability to model real-world processes exactly
    - Careful state management (the game has many interacting states)

Author: Claudia Maria Lopez Bombin
License: MIT
Reference: Thorp, E.O. "Beat the Dealer" (1966)
"""

import random
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Set
from collections import defaultdict

# ============================================================================
# ENUMERATIONS - Defining the possible states and choices in the game
# ============================================================================

class Action(Enum):
    """
    Every legal player decision in blackjack.
    
    Each action has a specific effect on the game state:
    
    HIT (H):
        Player receives one additional card. Can be requested multiple times
        until the player busts (exceeds 21) or decides to stand. This is the
        most common action and represents the player's assessment that another
        card is more likely to help than hurt their position.
    
    STAND (S):
        Player declines additional cards, locking in their current hand total.
        This signals that the player believes their current total has a better
        chance of beating the dealer than any total they might reach by hitting.
        The dealer will then play their hand to completion.
    
    DOUBLE_DOWN (D):
        Player doubles their initial bet and receives exactly ONE more card.
        This is only allowed on the first two cards. It's the most aggressive
        move in blackjack - the player is so confident in their position that
        they're willing to double their risk for one more card. Mathematically,
        this is correct when the player has a strong advantage (like 11 vs
        dealer 6).
    
    SPLIT (P):
        When the player has a pair (two cards of the same rank), they can
        split them into two separate hands, each with its own bet. An
        additional card is dealt to each new hand. This effectively gives
        the player two chances to beat the dealer. Aces split are special
        - most casinos only allow one card per split Ace.
    
    The value attribute provides a single-character representation for
    displaying strategy tables compactly.
    """
    HIT = "H"           # Request another card
    STAND = "S"         # Keep current hand
    DOUBLE_DOWN = "D"   # Double bet, take one card
    SPLIT = "P"         # Split pair into two hands (P for "Pair split")

class Suit(Enum):
    """
    Card suits for a standard French deck.
    
    In blackjack, suits don't affect strategy or card values.
    They are included for complete card representation and
    potential display/logging purposes.
    
    The string values use Unicode suit symbols:
    ♥ = Hearts, ♦ = Diamonds, ♣ = Clubs, ♠ = Spades
    """
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"
    SPADES = "♠"
    
class HandStatus(Enum):
    """
    Tracks the current state of a blackjack hand throughout its lifecycle.
    
    A hand goes through several possible states:
    
    ACTIVE → Player is still making decisions
    ACTIVE → STANDING (player chose to stop)
    ACTIVE → BUST (hand exceeded 21 - automatic loss)
    ACTIVE → BLACKJACK (natural 21 on first two cards)
    ACTIVE → DOUBLED (player doubled down)
    
    The status determines what actions are still available and how
    the hand will be evaluated against the dealer's hand.
    """
    ACTIVE = "active"           # Player still deciding
    STANDING = "standing"       # Player locked in their total
    BUST = "bust"              # Hand exceeded 21
    BLACKJACK = "blackjack"    # Natural 21 (A + 10-value card)
    DOUBLED = "doubled"        # Player doubled down


# ============================================================================
# CARD REPRESENTATION - The fundamental unit of the game
# ============================================================================

@dataclass
class Card:
    """
    A playing card with blackjack-specific properties.
    
    In blackjack, cards have THREE different values depending on context:
    
    1. GAME VALUE (the `value` property):
       - Number cards (2-10): worth their face value
       - Face cards (J, Q, K): all worth 10
       - Ace: worth 11 (can become 1 if needed, handled by Hand class)
    
    2. HI-LO COUNTING VALUE (the `hi_lo_val` property):
       Used by card counters to track deck composition:
       - 2, 3, 4, 5, 6: +1 (low cards - good for dealer when removed)
       - 7, 8, 9: 0 (neutral cards)
       - 10, J, Q, K, A: -1 (high cards - good for player when remain)
       
       WHY THIS MATTERS: When the running count is positive, it means
       more low cards have been dealt than high cards, so the remaining
       deck is rich in high cards (10s and Aces). This favors the player
       because:
       a) More blackjacks (which pay 3:2 to player but only 1:1 to dealer)
       b) Dealer busts more often (must hit stiff hands)
       c) Double downs are more successful
    
    3. RANK (the `rank` attribute):
       - 1 = Ace
       - 2-10 = Number cards
       - 11 = Jack
       - 12 = Queen
       - 13 = King
    
    Attributes:
        rank: Numeric rank (1-13)
        suit: Card suit (♥, ♦, ♣, or ♠) - decorative only in blackjack
    """
    rank: int   # 1=Ace, 2-10=Number, 11=Jack, 12=Queen, 13=King
    suit: str   # ♥ ♣ ♠ ♦ - purely cosmetic in blackjack
    
    @property
    def value(self) -> int:
        """
        Calculate the card's blackjack game value.
        
        This is the value used for hand totaling:
        - Ace (rank 1) → 11 (the Hand class handles making it 1 if needed)
        - Face cards (rank ≥ 10) → 10
        - Number cards (rank 2-10) → their rank
        
        The Ace is special: it starts at 11 but becomes 1 if counting it
        as 11 would cause a bust. This "soft/hard" dual nature is what
        makes blackjack strategy interesting. A "soft" hand contains an
        Ace counted as 11; a "hard" hand either has no Ace or must count
        Aces as 1 to avoid busting.
        """
        if self.rank == 1:
            return 11  # Ace starts high, Hand class adjusts if needed
        if self.rank >= 10:
            return 10  # All face cards = 10
        return self.rank  # Number cards = their number
    
    @property
    def is_ace(self) -> bool:
        """
        Check if this card is an Ace.
        
        Aces require special handling because they have two possible values.
        This property allows the Hand class to quickly identify when it
        needs to calculate soft vs hard totals.
        """
        return self.rank == 1
    
    @property
    def hi_lo_val(self) -> int:
        """
        The Hi-Lo card counting value of this card.
        
        THE HI-LO SYSTEM (invented by Harvey Dubner, refined by Julian Braun):
        
        Card counters assign point values to keep a "running count" of the
        deck's composition. The system exploits the fact that high cards
        (10s, face cards, Aces) favor the player while low cards favor
        the dealer.
        
        Value assignments:
        +1 for LOW cards (2, 3, 4, 5, 6):
            These cards help the dealer because the dealer MUST hit stiff
            hands (12-16). When these cards are dealt, they're gone from
            the deck, leaving more high cards → better for player.
        
        0 for NEUTRAL cards (7, 8, 9):
            These don't strongly favor either side. A 7 gives the dealer
            17 (a common stopping point). An 8 or 9 puts the dealer in
            a decent position.
        
        -1 for HIGH cards (10, J, Q, K, A):
            These cards help the player by creating blackjacks, making
            double downs successful, and causing dealer busts. When they're
            dealt, they're gone → worse for player.
        
        The running count starts at 0 after a shuffle. After each card is
        revealed, add its Hi-Lo value. A positive running count means the
        remaining deck has more high cards → player advantage.
        
        TRUE COUNT = Running Count / Decks Remaining
        This normalizes the count for different shoe sizes. +6 with 3 decks
        left (TC=+2) is different from +6 with 1 deck left (TC=+6).
        """
        if 2 <= self.rank <= 6:
            return 1    # Low card dealt → remaining deck richer in high cards
        if 7 <= self.rank <= 9:
            return 0    # Neutral card → no change in deck composition edge
        return -1       # High card dealt → remaining deck weaker for player
    
    def __str__(self) -> str:
        """
        Human-readable card representation.
        
        Examples: "A♥", "7♣", "K♠", "10♦"
        
        The rank is shown as A/2-10/J/Q/K and combined with the suit symbol.
        """
        rank_names = {1: 'A', 11: 'J', 12: 'Q', 13: 'K'}
        rank_str = rank_names.get(self.rank, str(self.rank))
        return f"{rank_str}{self.suit}"
    
    def __repr__(self) -> str:
        """Debug representation - same as string for cards."""
        return self.__str__()


# ============================================================================
# THE SHOE - Multi-deck card container with penetration tracking
# ============================================================================

@dataclass
class Shoe:
    """
    A casino-style card shoe holding multiple decks.
    
    REAL CASINO PRACTICE:
    Casinos use 4-8 deck shoes for several reasons:
    1. Makes card counting harder (more decks = smaller true count swings)
    2. Reduces shuffling frequency (more hands per hour = more profit)
    3. Counters single-deck strategies (different basic strategy for 1 deck)
    
    PENETRATION:
    The "cut card" (usually a colored plastic card) is inserted into the
    shoe. When the dealer reaches this card, they finish the current round
    and reshuffle. Penetration is how deep into the shoe they deal before
    reshuffling:
    - 75% penetration: 6-deck shoe → deal ~4.5 decks before reshuffle
    - 50% penetration: 6-deck shoe → deal ~3 decks before reshuffle
    
    WHY PENETRATION MATTERS FOR CARD COUNTERS:
    Better penetration (deeper deal) = more cards seen before reshuffle
    = higher true counts possible = bigger player advantage.
    
    A game with 50% penetration is almost unbeatable; 75%+ gives counters
    a real edge. This is why counters "shop" for good penetration.
    
    Attributes:
        num_decks: Number of 52-card decks (typically 6 or 8)
        penetration: Fraction of cards dealt before reshuffle (0.0-1.0)
    """
    num_decks: int = 6
    penetration: float = 0.75
    
    def __post_init__(self):
        """
        Build the shoe with all cards and perform initial shuffle.
        
        This is called automatically after the dataclass __init__.
        Creates all cards for the configured number of decks,
        then randomizes their order via shuffling.
        """
        self.cards: List[Card] = []      # Cards available to be dealt
        self.dealt: List[Card] = []      # Cards already dealt (tracked for reshuffle)
        self._build_initial_shoe()       # Create all cards
        self.shuffle()                    # Randomize order
    
    def _build_initial_shoe(self):
        """
        Create all cards for all decks in the shoe.
        
        A standard deck has 52 cards: 4 suits × 13 ranks.
        For a 6-deck shoe: 312 cards total.
        For an 8-deck shoe: 416 cards total.
        
        Each card is created with its appropriate rank, suit,
        and all derived properties (value, Hi-Lo value, etc.)
        are automatically calculated by the Card class.
        """
        suits = ["♥", "♦", "♣", "♠"]
        self.cards = []
        for _ in range(self.num_decks):
            for suit in suits:
                for rank in range(1, 14):  # 1=Ace through 13=King
                    self.cards.append(Card(rank, suit))
    
    def shuffle(self):
        """
        Randomize card order using Fisher-Yates shuffle.
        
        FISHER-YATES SHUFFLE:
        This algorithm produces a uniformly random permutation.
        For each position from the end, swap the card at that position
        with a randomly selected card from positions 0 to current.
        
        Why this matters: A fair shuffle ensures each of the 312! possible
        orderings is equally likely. This is crucial for simulation accuracy.
        
        THE CUT CARD:
        After shuffling, we calculate where the cut card goes:
        cut_pos = total_cards × penetration
        Example: 312 cards × 0.75 = 234 cards before reshuffle
        
        In a real casino, the player to the dealer's right inserts the cut
        card. This prevents the dealer from manipulating which cards are dealt.
        """
        # Fisher-Yates shuffle algorithm
        self.cards.extend(self.dealt)  # Recombine all cards
        self.dealt = []                # Clear dealt pile
        random.shuffle(self.cards)     # Randomize (uses Fisher-Yates internally)
        
        # Calculate cut card position
        self.cut_pos = int(len(self.cards) * self.penetration)
        # Example: 312 cards × 0.75 = card 234 triggers reshuffle
    
    def deal(self) -> Optional[Card]:
        """
        Deal one card from the shoe. Returns None if reshuffle needed.
        
        DEALING PROCESS:
        1. Check if we've reached the cut card
        2. If yes, signal reshuffle by returning None
        3. If no, take the next card, move it to dealt pile
        
        In a real casino, the dealer burns the first card (places it face
        down in the discard tray). We don't simulate this as it doesn't
        affect the mathematics (burned cards are just unseen cards).
        
        Returns:
            Card if available, None if cut card reached or shoe empty
        """
        # Check cut card: have we dealt through the penetration point?
        if len(self.dealt) >= self.cut_pos:
            return None  # Signal: time to reshuffle
        
        # Check if any cards remain
        if not self.cards:
            return None  # Shoe completely empty
            
        # Deal: remove from available pool, add to dealt pile
        card = self.cards.pop()
        self.dealt.append(card)
        return card
    
    @property
    def needs_reshuffle(self) -> bool:
        """
        Check if the shoe should be reshuffled before the next hand.
        
        Returns True when:
        - We've dealt past the cut card (penetration reached)
        - There are no cards left at all
        
        The game engine should check this before each round.
        """
        return (len(self.dealt) >= self.cut_pos or 
                len(self.cards) == 0)
    
    @property
    def decks_remaining(self) -> float:
        """
        Estimate how many full decks remain in the shoe.
        
        This is CRITICAL for card counting:
        TRUE COUNT = RUNNING COUNT / DECKS REMAINING
        
        Example: Running count = +8, decks remaining = 4.0
        True Count = +8 / 4 = +2
        
        Example: Running count = +8, decks remaining = 0.5
        True Count = +8 / 0.5 = +16 (extremely favorable!)
        
        The same running count means very different things depending
        on how many cards are left. A +8 count with 4 decks is mildly
        positive; with half a deck it's extraordinarily good.
        
        Returns:
            Estimated number of full 52-card decks remaining
        """
        return len(self.cards) / 52.0


# ============================================================================
# HAND REPRESENTATION - Player or dealer hand with value calculation
# ============================================================================

@dataclass
class Hand:
    """
    A blackjack hand with all game-relevant properties.
    
    HAND VALUATION - THE SOFT/HARD DICHOTOMY:
    
    The defining complexity of blackjack is the dual nature of Aces.
    A hand containing an Ace counted as 11 is "soft" because it can't
    bust from one hit. For example:
    
    A+7 = "soft 18" (can be 8 or 18)
    If we hit and receive a 5: A+7+5 = 13 (Ace becomes 1 automatically)
    If we hit and receive a 10: A+7+10 = 18 (Ace stays as 1, but we'd stand)
    
    A hand without Aces (or where Aces must be 1 to avoid busting) is "hard."
    Hard 16 is dangerous because hitting risks busting with any 6+ card;
    Soft 17 (A+6) is favorable because we can hit without risk.
    
    THE BLACKJACK BONUS:
    A "natural" or "blackjack" is an Ace plus any 10-value card as the
    initial two cards. It pays 3:2 (not 1:1 like normal wins). This
    asymmetric payout is crucial: without it, blackjack would have a
    much larger house edge. The 3:2 blackjack bonus is what gives
    players a fighting chance.
    
    Attributes:
        cards: List of cards in this hand
        bet: Amount wagered on this hand
        status: Current state (active, standing, bust, blackjack, doubled)
        is_split: Whether this hand came from a split
        from_split_aces: Whether this hand came from splitting Aces
    """
    cards: List[Card]
    bet: float = 1.0
    status: HandStatus = HandStatus.ACTIVE
    is_split: bool = False
    from_split_aces: bool = False
    
    def add(self, card: Card):
        """
        Add a card to the hand and check for immediate bust.
        
        After adding, we check if all possible values exceed 21.
        If so, the hand is marked BUST immediately - no further
        actions are possible.
        
        Example: Hand is 8+6 = 14, player hits, receives K
        New hand: 8+6+K = 24 → BUST (automatic loss)
        """
        self.cards.append(card)
        # Check if the new card busted us
        if self.best_value > 21:
            self.status = HandStatus.BUST
    
    @property
    def possible_values(self) -> List[int]:
        """
        Calculate ALL possible hand totals considering soft Aces.
        
        This is the most algorithmically interesting part of blackjack.
        Each Ace doubles the number of possible values because it can
        be counted as either 1 or 11.
        
        ALGORITHM EXPLANATION:
        Start with [0] as the only possible total.
        For each card:
          - If it's NOT an Ace: add its value to all existing totals
          - If it IS an Ace: for each existing total, create TWO new
            totals: one with Ace=1 and one with Ace=11
        
        Example: Hand A, 7, A
        Start: [0]
        After A: [1, 11]           (Ace as 1 or 11)
        After 7: [8, 18]           (1+7=8, 11+7=18)
        After A: [9, 19, 19, 29]   (8+1=9, 8+11=19, 18+1=19, 18+11=29)
        
        After removing duplicates: [9, 19, 29]
        
        The "best value" will be 19 (highest ≤ 21). This is a "soft 19"
        because it contains an Ace counted as 11.
        
        Returns:
            Sorted list of unique possible hand values
        """
        totals = [0]  # Start with empty hand = 0
        
        for card in self.cards:
            if card.is_ace:
                # Ace doubles the possibilities
                new_totals = []
                for t in totals:
                    new_totals.append(t + 1)   # Ace as 1
                    new_totals.append(t + 11)  # Ace as 11
                totals = new_totals
            else:
                # Non-Ace: just add its value to each total
                totals = [t + card.value for t in totals]
        
        # Remove duplicates and sort for processing
        return sorted(list(set(totals)))
    
    @property
    def best_value(self) -> int:
        """
        The optimal hand value: highest valid total, or lowest bust total.
        
        Strategy: Find the highest total not exceeding 21.
        If all totals bust, return the lowest one (for comparison purposes,
        though the hand is already marked BUST).
        
        Examples:
        A+7 = [8, 18] → best = 18 (soft 18)
        K+7 = [17] → best = 17 (hard 17)
        A+A+A+A = [4, 14, 24, 34, 44] → best = 14 (hard 14, 
            only 4 is ≤ 21 but we can count only one Ace as 11)
        Actually A+A+A+A: possible combos:
        - All as 1: 4
        - One as 11: 1+1+1+11 = 14
        - Two as 11: 1+1+11+11 = 24
        - Three as 11: 1+11+11+11 = 34
        - Four as 11: 11+11+11+11 = 44
        Best valid: 14 (we count one Ace as 11, rest as 1)
        """
        vals = self.possible_values
        valid = [v for v in vals if v <= 21]
        return max(valid) if valid else min(vals)
    
    @property
    def is_soft(self) -> bool:
        """
        Check if this is a "soft" hand (contains an Ace counted as 11).
        
        A hand is soft if:
        - It has multiple possible values (indicating an Ace)
        - At least one value ≤ 21 (otherwise we're bust anyway)
        
        Why "soft" matters: Soft hands can't bust from one hit because
        the Ace can switch from 11 to 1. This fundamentally changes
        strategy. For example:
        - Hard 16 vs dealer 10: Basic strategy says HIT (even though it
          risks busting, standing is worse)
        - Soft 16 (A+5) vs dealer 10: Basic strategy says HIT (you can't
          bust, and you might improve to 18-21)
        
        The strategic difference between hard and soft totals is why
        basic strategy tables have separate sections for each.
        """
        vals = self.possible_values
        # Must have multiple values (Ace present) AND
        # at least one value not busting
        return len(vals) > 1 and max(vals) <= 21
    
    @property
    def is_blackjack(self) -> bool:
        """
        Check for a "natural" blackjack: exactly 2 cards totaling 21.
        
        A NATURAL BLACKJACK:
        - Must be the initial 2 cards (not 3+ cards totaling 21)
        - Consists of an Ace + 10-value card (10, J, Q, K)
        - Pays 3:2 (bet $10 → win $15)
        - Beats a dealer 21 made from 3+ cards
        - If both have blackjack, it's a push (tie)
        
        The name "blackjack" supposedly comes from a special bonus payout
        offered in early American casinos for an Ace of Spades + black Jack.
        """
        return len(self.cards) == 2 and self.best_value == 21
    
    @property
    def can_double(self) -> bool:
        """
        Check if double down is allowed on this hand.
        
        DOUBLE DOWN RULES:
        1. Must have exactly 2 cards (initial hand only)
        2. Hand must be active (not bust, not already stood)
        3. Cannot double after splitting Aces (casino rule)
        
        Doubling is a high-risk, high-reward play. You're so confident
        that ONE more card will give you a winning hand that you're
        willing to double your bet for it. Common doubling situations:
        - 11 vs dealer 6 (you'll likely get 21 or close; dealer may bust)
        - 10 vs dealer 9 (you have an edge, maximize it)
        - Soft 17 vs dealer 3 (you can't bust, might improve significantly)
        """
        return (len(self.cards) == 2 and 
                self.status == HandStatus.ACTIVE and 
                not self.from_split_aces)
    
    @property
    def can_split(self) -> bool:
        """
        Check if this hand can be split into two separate hands.
        
        SPLIT CONDITIONS:
        1. Exactly 2 cards
        2. Both cards have the same RANK (not just same value)
           - 8♣ and 8♥ can split (same rank)
           - K♠ and Q♥ can split (both rank 13 and 12? No! Different ranks)
           Wait - actually K and Q have DIFFERENT ranks but same value.
           Most casinos DO allow splitting any two 10-value cards.
        3. Haven't already split Aces (most casinos limit this)
        
        Splitting Aces is special because:
        - You can usually only split Aces once
        - You typically get only one additional card per split Ace
        - A 10 on a split Ace counts as 21, NOT blackjack (pays 1:1 not 3:2)
        
        Splitting 8s against dealer 10 is a famous defensive play:
        You'd rather lose two smaller bets on two mediocre hands
        than lose one bigger bet on a terrible 16.
        """
        if len(self.cards) != 2:
            return False
        if self.from_split_aces:
            return False
        if self.status != HandStatus.ACTIVE:
            return False
        # Check if same rank (standard rule)
        return self.cards[0].rank == self.cards[1].rank


# ============================================================================
# THE GAME ENGINE - Complete blackjack simulation
# ============================================================================

class BlackjackGame:
    """
    Complete blackjack game engine with all standard casino rules.
    
    This class orchestrates the entire game flow:
    1. Manages the shoe (shuffles when needed)
    2. Deals initial hands
    3. Processes player decisions
    4. Plays dealer hand according to house rules
    5. Calculates payouts for all outcomes
    
    CONFIGURABLE HOUSE RULES:
    - Number of decks: 1-8 (typically 6 in modern casinos)
    - Dealer soft 17: Hit (H17) or Stand (S17)
      H17 is more common now and slightly worse for players
    - Blackjack payout: 3:2 (1.5x) standard, 6:5 is terrible
    - Double down: Any two cards, or only 9/10/11
    - Maximum splits: Usually 3 or 4 (creating up to 4 hands)
    
    HOUSE EDGE:
    With perfect basic strategy and standard rules (6 decks, H17, DAS):
    House edge ≈ 0.5-0.6%. This means for every $100 bet, the player
    expects to lose about 50-60 cents in the long run.
    
    With card counting (Hi-Lo, 1-10 bet spread, 75% penetration):
    Player edge ≈ 1.0-1.5%. Now the player expects to WIN $1.00-1.50
    per $100 bet in the long run.
    """
    
    def __init__(self, num_decks: int = 6, penetration: float = 0.75,
                 blackjack_payout: float = 1.5, max_splits: int = 3,
                 dealer_hits_soft_17: bool = True):
        """
        Initialize the game with specified house rules.
        
        Parameters:
            num_decks: Number of decks in shoe (1, 2, 4, 6, or 8)
            penetration: How deep to deal before reshuffle (0.5-0.85)
            blackjack_payout: Multiplier for natural blackjack (1.5 = 3:2)
            max_splits: Maximum number of allowed splits (creates max_splits+1 hands)
            dealer_hits_soft_17: Whether dealer hits soft 17 (modern rule)
        """
        self.shoe = Shoe(num_decks, penetration)
        self.bj_payout = blackjack_payout
        self.max_splits = max_splits
        self.hit_soft_17 = dealer_hits_soft_17
        self.running_count = 0  # Hi-Lo running count
    
    def update_count(self, card: Card):
        """
        Update the Hi-Lo running count when a card is revealed.
        
        CARD COUNTER'S PROCESS:
        1. Start at 0 after shuffle
        2. For each card seen, add its Hi-Lo value
        3. Convert to True Count before betting decisions
        4. Bet more when True Count is positive (player advantage)
        5. Bet minimum when True Count is negative or zero
        
        The counter must see the cards to count them, which is why
        they stand behind the table watching. In modern casinos,
        continuous shuffle machines defeat this by never letting
        the count deviate far from zero.
        """
        self.running_count += card.hi_lo_val
    
    @property
    def true_count(self) -> float:
        """
        Calculate the True Count from the running count.
        
        TRUE COUNT FORMULA:
        TC = Running Count / Estimated Decks Remaining
        
        This normalizes the count for different shoe depths.
        
        Example scenarios (6-deck shoe):
        1. RC = +12, decks left = 6 → TC = +2 (slight edge)
        2. RC = +12, decks left = 3 → TC = +4 (good edge)
        3. RC = +12, decks left = 1 → TC = +12 (huge edge!)
        4. RC = +12, decks left = 0.5 → TC = +24 (extremely rare)
        
        Most counters increase bets at TC ≥ +2 and max out around TC ≥ +5.
        
        Returns 0.0 if no decks remain (shouldn't happen if checked properly).
        """
        decks = self.shoe.decks_remaining
        if decks <= 0:
            return 0.0
        return self.running_count / decks
    
    def deal_initial(self, bet: float = 1.0) -> Tuple[Hand, Hand]:
        """
        Deal the initial two-card hands for both player and dealer.
        
        DEALING SEQUENCE (standard casino procedure):
        1. Player places bet
        2. Dealer deals one card face-up to player
        3. Dealer deals one card face-up to themselves (the "upcard")
        4. Dealer deals second card face-up to player
        5. Dealer deals second card face-DOWN to themselves (the "hole card")
        
        In American-style blackjack, the dealer checks for blackjack
        immediately if the upcard is an Ace or 10-value. If the dealer
        has blackjack, the hand ends immediately (unless player also
        has blackjack, then it's a push).
        
        Returns:
            Tuple of (player_hand, dealer_hand)
        """
        player = Hand([], bet)
        dealer = Hand([], 0)  # Dealer doesn't bet
        
        # Deal in alternating pattern (standard procedure)
        for _ in range(2):
            # Player's card (both face up)
            card = self.shoe.deal()
            self.update_count(card)
            player.add(card)
            
            # Dealer's card (first face up, second face down)
            card = self.shoe.deal()
            self.update_count(card)
            dealer.add(card)
        
        # Check for natural blackjack
        if player.is_blackjack:
            player.status = HandStatus.BLACKJACK
        
        return player, dealer
    
    def available_actions(self, hand: Hand) -> List[Action]:
        """
        Determine which actions are legal for a given hand.
        
        ACTION AVAILABILITY:
        - HIT: Always available on active hands
        - STAND: Always available on active hands
        - DOUBLE DOWN: Only on first two cards, not after split Aces
        - SPLIT: Only on pairs, not after split Aces, within split limit
        
        The available actions change as the hand evolves:
        - After hitting (3+ cards): Only HIT and STAND remain
        - After doubling: No actions (hand is complete)
        - After busting: No actions (hand is lost)
        - After standing: No actions (player locked in)
        """
        if hand.status != HandStatus.ACTIVE:
            return []  # No actions available on completed hands
        
        # Hit and Stand are always available
        actions = [Action.HIT, Action.STAND]
        
        # Double down: only on first two cards
        if hand.can_double:
            actions.append(Action.DOUBLE_DOWN)
        
        # Split: only on pairs
        if hand.can_split:
            actions.append(Action.SPLIT)
        
        return actions
    
    def execute_action(self, hand: Hand, action: Action,
                      dealer_up: Card) -> List[Hand]:
        """
        Execute a player's chosen action and return resulting hands.
        
        ACTION EFFECTS:
        
        HIT: Add one card. Hand may bust. Player can act again.
        
        STAND: Freeze current total. Dealer will play against this.
        
        DOUBLE DOWN: 
            Double the bet, receive exactly one card, hand ends.
            This is the most aggressive move - you're so confident
            that you double your risk for just one more card.
        
        SPLIT:
            Divide a pair into two separate hands, each with original bet.
            One new card is dealt to each. Each hand can then be played
            independently (can hit, stand, or double).
            
            SPECIAL SPLIT RULES:
            - Splitting Aces: Usually only one card per Ace, and a 10
              on a split Ace is just 21 (not blackjack, pays 1:1)
            - Re-splitting: Most casinos allow up to 3 splits (4 hands)
            - Doubling after split (DAS): Common modern rule
        
        Returns:
            List of Hand objects (usually 1, can be 2 after split)
        """
        if action == Action.HIT:
            card = self.shoe.deal()
            self.update_count(card)
            hand.add(card)
            return [hand]
        
        elif action == Action.STAND:
            hand.status = HandStatus.STANDING
            return [hand]
        
        elif action == Action.DOUBLE_DOWN:
            hand.bet *= 2  # Double the wager
            card = self.shoe.deal()
            self.update_count(card)
            hand.add(card)
            hand.status = HandStatus.DOUBLED  # Hand is complete
            return [hand]
        
        elif action == Action.SPLIT:
            # Separate the pair into two hands
            h1 = Hand([hand.cards[0]], hand.bet, is_split=True)
            h2 = Hand([hand.cards[1]], hand.bet, is_split=True)
            
            # If splitting Aces, mark special restrictions
            if hand.cards[0].is_ace:
                h1.from_split_aces = h2.from_split_aces = True
            
            # Deal one card to each new hand
            card = self.shoe.deal()
            self.update_count(card)
            h1.add(card)
            
            card = self.shoe.deal()
            self.update_count(card)
            h2.add(card)
            
            return [h1, h2]
        
        return [hand]
    
    def play_dealer(self, dealer_hand: Hand):
        """
        Play the dealer's hand according to fixed house rules.
        
        DEALER RULES (non-negotiable, it's a robot):
        
        The dealer has NO choices - they follow a strict algorithm:
        1. Must hit any total below 17
        2. Must stand on any total of 17 or higher
        
        SOFT 17 EXCEPTION:
        Some casinos require dealer to hit soft 17 (H17 game).
        "Soft 17" means Ace + 6 (also Ace + 2 + 4, etc.)
        
        Why this matters: H17 adds about 0.2% to the house edge.
        Always prefer S17 (stand on soft 17) games if available.
        
        Dealer hitting soft 17: Ace+6=17 → dealer takes another card
        Dealer standing soft 17: Ace+6=17 → dealer stops
        
        The dealer busts about 28% of the time in a typical game.
        This is the main source of player advantage in blackjack.
        """
        while True:
            value = dealer_hand.best_value
            is_soft = dealer_hand.is_soft
            
            # Determine if dealer should continue hitting
            should_hit = False
            
            if value < 17:
                # Below 17: always must hit
                should_hit = True
            elif value == 17 and is_soft and self.hit_soft_17:
                # Soft 17 with H17 rule: dealer must hit
                should_hit = True
            
            if not should_hit:
                break
            
            # Dealer takes a card
            card = self.shoe.deal()
            self.update_count(card)
            dealer_hand.add(card)
        
        # Mark dealer as standing (unless busted)
        if dealer_hand.best_value <= 21:
            dealer_hand.status = HandStatus.STANDING
    
    def calculate_payout(self, player_hand: Hand, 
                        dealer_hand: Hand) -> float:
        """
        Determine the financial result of a hand against the dealer.
        
        PAYOUT RULES:
        
        1. PLAYER BUSTS (> 21):
           Immediate loss, regardless of dealer's result
           Net result: -bet
        
        2. DEALER BUSTS (> 21):
           Player wins even money (1:1)
           Net result: +bet
        
        3. PLAYER BLACKJACK (A + 10-value on first two cards):
           Special payout 3:2 (or 1.5x)
           Example: $10 bet → win $15 → net +$15
           Exception: If dealer also has blackjack → push (tie) → net $0
        
        4. DEALER BLACKJACK:
           Player loses unless they also have blackjack
           Net result: -bet
        
        5. NO BUSTS, NO BLACKJACKS:
           Compare totals: higher wins, equal pushes
           Net result: +bet (win), -bet (lose), $0 (push)
        
        IMPORTANT: A 21 made with 3+ cards is NOT a blackjack.
        It loses to a dealer blackjack (which only needs 2 cards).
        """
        # Player bust: automatic loss
        if player_hand.best_value > 21:
            return -player_hand.bet
        
        # Dealer bust: automatic win for surviving player hands
        if dealer_hand.best_value > 21:
            return player_hand.bet
        
        # Player has natural blackjack
        if player_hand.is_blackjack and not dealer_hand.is_blackjack:
            return player_hand.bet * self.bj_payout  # 3:2 payout
        
        # Both have blackjack: push (tie, bet returned)
        if player_hand.is_blackjack and dealer_hand.is_blackjack:
            return 0.0
        
        # Only dealer has blackjack: player loses
        if dealer_hand.is_blackjack:
            return -player_hand.bet
        
        # Neither busted, neither has blackjack: compare totals
        pv = player_hand.best_value
        dv = dealer_hand.best_value
        
        if pv > dv:
            return player_hand.bet   # Player wins 1:1
        elif pv < dv:
            return -player_hand.bet  # Player loses
        else:
            return 0.0               # Push (tie)
    
    def play_round(self, bet: float = 1.0,
                   strategy: Dict = None) -> float:
        """
        Execute one complete blackjack round.
        
        ROUND FLOW:
        1. Check if shoe needs reshuffling
        2. Deal initial hands
        3. If dealer shows Ace, offer insurance
        4. Play all player hands (including splits)
        5. Play dealer hand
        6. Calculate and return net payout
        
        This function handles split hands by maintaining a queue
        of hands that need to be played. When a split occurs,
        both resulting hands are added to the queue.
        
        Parameters:
            bet: Initial bet amount
            strategy: Dictionary mapping game states to actions
            
        Returns:
            Net profit/loss for this round (can be negative)
        """
        # Reshuffle if needed
        if self.shoe.needs_reshuffle:
            self.shoe.shuffle()
            self.running_count = 0
        
        # Deal initial hands
        player_hand, dealer_hand = self.deal_initial(bet)
        dealer_up = dealer_hand.cards[0]  # Dealer's visible card
        
        # Track all active hands (grows with splits)
        active_hands = [player_hand]
        queue = [player_hand]
        
        # PLAY ALL PLAYER HANDS
        # Queue processes each hand. Splits add new hands to queue.
        while queue:
            hand = queue.pop(0)
            
            # Skip blackjacks (no actions needed)
            if hand.is_blackjack:
                continue
            
            # Play this hand until it's no longer active
            while hand.status == HandStatus.ACTIVE:
                actions = self.available_actions(hand)
                
                if not actions:
                    break
                
                # Choose action: from strategy table or default
                if strategy:
                    state_key = (hand.best_value, dealer_up.value, 
                                hand.is_soft)
                    chosen_action = strategy.get(state_key, Action.HIT)
                    # Verify the chosen action is legal
                    if chosen_action not in actions:
                        chosen_action = Action.STAND
                else:
                    # Default: stand if possible, otherwise first available
                    chosen_action = (Action.STAND if Action.STAND in actions 
                                   else actions[0])
                
                # Execute the chosen action
                result = self.execute_action(hand, chosen_action, dealer_up)
                
                # If split occurred, manage the new hands
                if chosen_action == Action.SPLIT and len(result) > 1:
                    active_hands.remove(hand)
                    active_hands.extend(result)
                    queue.extend(result)
                    break  # Stop processing this hand
        
        # PLAY DEALER HAND
        self.play_dealer(dealer_hand)
        
        # CALCULATE TOTAL PAYOUT
        total_payout = 0.0
        for hand in active_hands:
            payout = self.calculate_payout(hand, dealer_hand)
            total_payout += payout
        
        return total_payout
