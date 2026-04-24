"""
Blackjack Game Engine Module
============================

Core implementation of casino blackjack rules including multi-deck shoes,
player decisions (hit, stand, double down, split), and dealer rules.

This module provides the foundational classes and logic for:
- Card representation with Hi-Lo counting values
- Multi-deck shoe management with penetration tracking
- Hand valuation with soft/hard ace handling
- Complete game round simulation

Author: Claudia Maria Lopez Bombin
License: MIT
"""

import random
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

class Action(Enum):
    """Available player actions in blackjack."""
    HIT = "H"
    STAND = "S"
    DOUBLE_DOWN = "D"
    SPLIT = "P"

class HandStatus(Enum):
    """Possible states of a blackjack hand."""
    ACTIVE = "active"
    STANDING = "standing"
    BUST = "bust"
    BLACKJACK = "blackjack"
    DOUBLED = "doubled"

@dataclass
class Card:
    """
    Represents a playing card with blackjack-specific attributes.
    
    Attributes:
        rank: Numeric rank (1=Ace, 2-10, 11=Jack, 12=Queen, 13=King)
        suit: Card suit (hearts, diamonds, clubs, spades)
        value: Blackjack value (Ace=11, faces=10, others=rank)
        hi_lo_val: Hi-Lo counting value (2-6:+1, 7-9:0, 10-A:-1)
    """
    rank: int
    suit: str
    
    @property
    def value(self) -> int:
        """Calculate blackjack value. Aces count as 11 initially."""
        if self.rank == 1:
            return 11
        if self.rank >= 10:
            return 10
        return self.rank
    
    @property
    def is_ace(self) -> bool:
        """Check if this card is an Ace."""
        return self.rank == 1
    
    @property
    def hi_lo_val(self) -> int:
        """
        Hi-Lo counting system value assignment.
        
        Low cards (2-6): +1 (player favorable when removed)
        Neutral cards (7-9): 0
        High cards (10-A): -1 (dealer favorable when removed)
        """
        if 2 <= self.rank <= 6:
            return 1
        if 7 <= self.rank <= 9:
            return 0
        return -1

@dataclass
class Shoe:
    """
    Multi-deck card shoe with penetration tracking.
    
    Modern casinos use 6-8 deck shoes to counter card counting.
    The cut card (penetration) determines when to reshuffle.
    
    Attributes:
        num_decks: Number of 52-card decks
        penetration: Fraction of cards dealt before reshuffle
    """
    num_decks: int = 6
    penetration: float = 0.75
    
    def __post_init__(self):
        """Initialize and shuffle the complete shoe."""
        self.cards: List[Card] = []
        self.dealt: List[Card] = []
        self._build_shoe()
        self.shuffle()
    
    def _build_shoe(self):
        """Create all cards for the configured number of decks."""
        suits = ["♥", "♦", "♣", "♠"]
        self.cards = [
            Card(rank, suit)
            for _ in range(self.num_decks)
            for suit in suits
            for rank in range(1, 14)
        ]
    
    def shuffle(self):
        """Fisher-Yates shuffle and reset penetration marker."""
        self.cards.extend(self.dealt)
        self.dealt = []
        random.shuffle(self.cards)
        self.cut_pos = int(len(self.cards) * self.penetration)
    
    def deal(self) -> Optional[Card]:
        """Deal one card. Returns None if reshuffle needed."""
        if len(self.dealt) >= self.cut_pos or not self.cards:
            return None
        card = self.cards.pop()
        self.dealt.append(card)
        return card
    
    @property
    def needs_reshuffle(self) -> bool:
        """Check if the cut card has been reached."""
        return len(self.dealt) >= self.cut_pos or not self.cards
    
    @property
    def decks_remaining(self) -> float:
        """Estimate remaining decks for true count calculation."""
        return (len(self.cards)) / 52.0

@dataclass
class Hand:
    """
    Represents a blackjack hand with value calculation.
    
    Handles soft/hard totals, bust detection, blackjack checking,
    and tracks betting amount.
    """
    cards: List[Card]
    bet: float = 1.0
    status: HandStatus = HandStatus.ACTIVE
    is_split: bool = False
    from_split_aces: bool = False
    
    def add(self, card: Card):
        """Add a card and check for bust."""
        self.cards.append(card)
        if self.best_value > 21:
            self.status = HandStatus.BUST
    
    @property
    def possible_values(self) -> List[int]:
        """Compute all possible hand values considering soft aces."""
        totals = [0]
        for card in self.cards:
            if card.is_ace:
                totals = [t + v for t in totals for v in (1, 11)]
            else:
                totals = [t + card.value for t in totals]
        return sorted(set(totals))
    
    @property
    def best_value(self) -> int:
        """Highest valid value under 22, or lowest bust value."""
        vals = self.possible_values
        valid = [v for v in vals if v <= 21]
        return max(valid) if valid else min(vals)
    
    @property
    def is_soft(self) -> bool:
        """Check if hand contains an Ace counted as 11."""
        return len(self.possible_values) > 1 and max(self.possible_values) <= 21
    
    @property
    def is_blackjack(self) -> bool:
        """Natural blackjack: exactly 2 cards totaling 21."""
        return len(self.cards) == 2 and self.best_value == 21
    
    @property
    def can_double(self) -> bool:
        """Double down requires exactly 2 cards, active hand."""
        return (len(self.cards) == 2 and 
                self.status == HandStatus.ACTIVE and 
                not self.from_split_aces)
    
    @property
    def can_split(self) -> bool:
        """Split requires a pair of same-rank cards."""
        return (len(self.cards) == 2 and
                self.cards[0].rank == self.cards[1].rank and
                not self.from_split_aces and
                self.status == HandStatus.ACTIVE)

class BlackjackGame:
    """
    Complete blackjack game engine.
    
    Implements standard casino rules:
    - Dealer hits on soft 17 (configurable)
    - Blackjack pays 3:2
    - Double down on any two cards
    - Split up to 3 times (4 hands max)
    
    Parameters:
        num_decks: Number of decks in shoe
        penetration: Shoe penetration (0-1)
        blackjack_payout: Multiplier for natural blackjack
        max_splits: Maximum number of split hands
        dealer_hits_soft_17: Whether dealer hits soft 17
    """
    
    def __init__(self, num_decks: int = 6, penetration: float = 0.75,
                 blackjack_payout: float = 1.5, max_splits: int = 3,
                 dealer_hits_soft_17: bool = True):
        
        self.shoe = Shoe(num_decks, penetration)
        self.bj_payout = blackjack_payout
        self.max_splits = max_splits
        self.hit_soft_17 = dealer_hits_soft_17
        self.running_count = 0
    
    def update_count(self, card: Card):
        """Update Hi-Lo running count when card is revealed."""
        self.running_count += card.hi_lo_val
    
    @property
    def true_count(self) -> float:
        """True count = running count / decks remaining."""
        decks = self.shoe.decks_remaining
        return self.running_count / decks if decks > 0 else 0.0
    
    def deal_initial(self, bet: float = 1.0) -> Tuple[Hand, Hand]:
        """Deal initial two cards each to player and dealer."""
        player = Hand([], bet)
        dealer = Hand([], 0)
        
        for _ in range(2):
            card = self.shoe.deal()
            self.update_count(card)
            player.add(card)
            
            card = self.shoe.deal()
            self.update_count(card)
            dealer.add(card)
        
        if player.is_blackjack:
            player.status = HandStatus.BLACKJACK
        
        return player, dealer
    
    def available_actions(self, hand: Hand) -> List[Action]:
        """Determine available actions for a hand."""
        if hand.status != HandStatus.ACTIVE:
            return []
        
        actions = [Action.HIT, Action.STAND]
        if hand.can_double:
            actions.append(Action.DOUBLE_DOWN)
        if hand.can_split:
            actions.append(Action.SPLIT)
        return actions
    
    def execute_action(self, hand: Hand, action: Action,
                      dealer_up: Card) -> List[Hand]:
        """Execute a player action and return resulting hands."""
        
        if action == Action.HIT:
            card = self.shoe.deal()
            self.update_count(card)
            hand.add(card)
            return [hand]
        
        elif action == Action.STAND:
            hand.status = HandStatus.STANDING
            return [hand]
        
        elif action == Action.DOUBLE_DOWN:
            hand.bet *= 2
            card = self.shoe.deal()
            self.update_count(card)
            hand.add(card)
            hand.status = HandStatus.DOUBLED
            return [hand]
        
        elif action == Action.SPLIT:
            h1 = Hand([hand.cards[0]], hand.bet, is_split=True)
            h2 = Hand([hand.cards[1]], hand.bet, is_split=True)
            
            if hand.cards[0].is_ace:
                h1.from_split_aces = h2.from_split_aces = True
            
            card = self.shoe.deal()
            self.update_count(card)
            h1.add(card)
            
            card = self.shoe.deal()
            self.update_count(card)
            h2.add(card)
            
            return [h1, h2]
        
        return [hand]
    
    def play_dealer(self, dealer_hand: Hand):
        """Play dealer hand according to house rules."""
        while True:
            value = dealer_hand.best_value
            should_hit = (value < 17 or 
                         (value == 17 and dealer_hand.is_soft 
                          and self.hit_soft_17))
            
            if not should_hit:
                break
            
            card = self.shoe.deal()
            self.update_count(card)
            dealer_hand.add(card)
        
        if not dealer_hand.best_value > 21:
            dealer_hand.status = HandStatus.STANDING
    
    def calculate_payout(self, player_hand: Hand, 
                        dealer_hand: Hand) -> float:
        """Calculate net payout for a hand against dealer."""
        
        if player_hand.best_value > 21:
            return -player_hand.bet
        
        if dealer_hand.best_value > 21:
            return player_hand.bet
        
        if player_hand.is_blackjack and not dealer_hand.is_blackjack:
            return player_hand.bet * self.bj_payout
        
        if player_hand.is_blackjack and dealer_hand.is_blackjack:
            return 0.0
        
        if dealer_hand.is_blackjack:
            return -player_hand.bet
        
        pv, dv = player_hand.best_value, dealer_hand.best_value
        if pv > dv:
            return player_hand.bet
        if pv < dv:
            return -player_hand.bet
        return 0.0
    
    def get_state_key(self, hand: Hand, dealer_up: Card) -> Tuple:
        """Generate strategy table lookup key for current state."""
        pv = hand.best_value
        
        if hand.cards[0].rank == hand.cards[1].rank and len(hand.cards) == 2:
            rank = hand.cards[0].rank
            pv = 112 if rank == 1 else rank * 100
        
        return (pv, dealer_up.value, hand.is_soft)
    
    def play_round(self, bet: float = 1.0,
                   strategy: Dict = None) -> float:
        """Play a complete blackjack round. Returns net profit/loss."""
        
        if self.shoe.needs_reshuffle:
            self.shoe.shuffle()
            self.running_count = 0
        
        player_hand, dealer_hand = self.deal_initial(bet)
        dealer_up = dealer_hand.cards[0]
        active_hands = [player_hand]
        queue = [player_hand]
        
        # Play all player hands
        while queue:
            hand = queue.pop(0)
            if hand.is_blackjack:
                continue
            
            while hand.status == HandStatus.ACTIVE:
                actions = self.available_actions(hand)
                if not actions:
                    break
                
                # Select action from strategy or default
                if strategy:
                    key = self.get_state_key(hand, dealer_up)
                    action = strategy.get(key, Action.HIT)
                    if action not in actions:
                        action = Action.STAND
                else:
                    action = Action.STAND if Action.STAND in actions else actions[0]
                
                result = self.execute_action(hand, action, dealer_up)
                
                if action == Action.SPLIT and len(result) > 1:
                    active_hands.remove(hand)
                    active_hands.extend(result)
                    queue.extend(result)
                    break
        
        # Play dealer hand
        self.play_dealer(dealer_hand)
        
        # Calculate total payout
        total_payout = sum(
            self.calculate_payout(h, dealer_hand) 
            for h in active_hands
        )
        
        return total_payout