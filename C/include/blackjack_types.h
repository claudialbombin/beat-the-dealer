/**
 * @file blackjack_types.h
 * @brief Core type definitions for the Blackjack Monte Carlo Solver
 *
 * CENTRAL TYPE SYSTEM:
 * This header defines every data structure used throughout the project.
 * By centralizing types, we ensure consistency across all modules and
 * make the codebase easier to understand, maintain, and extend.
 *
 * DESIGN PHILOSOPHY:
 * All structures use static memory allocation (fixed-size arrays) rather
 * than dynamic allocation (malloc/free). This decision was made because:
 *
 * 1. PERFORMANCE: Stack allocation is faster than heap allocation. In
 *    Monte Carlo simulations running millions of iterations, avoiding
 *    malloc/free overhead significantly improves speed.
 *
 * 2. RELIABILITY: No memory leaks are possible. No null pointer checks
 *    are needed after allocation. This eliminates entire categories of bugs.
 *
 * 3. PREDICTABILITY: Memory usage is known at compile time. The program
 *    will never fail at runtime due to memory exhaustion from fragmentation.
 *
 * 4. SIMPLICITY: No need for destructor functions or careful cleanup.
 *    Structures can be copied with simple assignment.
 *
 * The trade-off is that we must choose maximum sizes carefully. These
 * limits are based on the actual requirements of blackjack:
 * - Maximum 21 cards per hand (impossible to exceed with blackjack rules)
 * - Maximum 4 split hands (standard casino limit)
 * - Maximum 8 decks (standard casino maximum)
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 * Repository: github.com/claudia-lopez/blackjack-monte-carlo
 */

#ifndef BLACKJACK_TYPES_H
#define BLACKJACK_TYPES_H

#include <stdbool.h>  /* For bool type */

/* =========================================================================
 * DIMENSIONAL CONSTANTS
 * These define the maximum sizes for all static arrays in the project.
 * Each value is derived from the physical constraints of blackjack.
 * ========================================================================= */

/**
 * MAX_CARDS_PER_HAND: Maximum cards a player could theoretically hold.
 *
 * DERIVATION: The worst case occurs when splitting Aces multiple times
 * and drawing only small cards. A hand of A,2,2,2,2,2,2,2,2,2,2
 * totals 21 with 11 cards. Setting to 21 per hand provides ample
 * safety margin for any realistic scenario.
 */
#define MAX_CARDS_PER_HAND 21

/**
 * MAX_SPLIT_HANDS: Maximum number of hands from splitting.
 *
 * CASINO STANDARD: Most casinos allow splitting up to 3 times,
 * creating a maximum of 4 hands from one starting pair.
 */
#define MAX_SPLIT_HANDS 4

/**
 * MAX_DECKS: Maximum number of 52-card decks in the shoe.
 *
 * CASINO STANDARD: Single deck (1), double deck (2), or
 * multi-deck shoes of 4, 6, or 8 decks. We support up to 8.
 */
#define MAX_DECKS 8

/**
 * TOTAL_CARDS: Total cards in a fully loaded shoe.
 *
 * CALCULATION: 52 cards per deck × MAX_DECKS decks
 * For 8 decks: 416 cards maximum
 * For 6 decks: 312 cards (most common configuration)
 */
#define TOTAL_CARDS (52 * MAX_DECKS)

/**
 * BLACKJACK_VALUE: The magic number 21 - the target value.
 *
 * Any hand totaling exactly 21 with the first two cards is a
 * "natural blackjack" and pays 3:2 (not 1:1 like normal wins).
 * A hand totaling 21 with 3+ cards is just "21" and pays 1:1.
 */
#define BLACKJACK_VALUE 21

/**
 * DEALER_STAND_VALUE: The dealer's mandatory standing threshold.
 *
 * CASINO RULE: The dealer MUST hit any total below 17 and
 * MUST stand on any total of 17 or higher.
 *
 * EXCEPTION - SOFT 17: Some casinos require the dealer to hit
 * "soft 17" (a hand containing an Ace counted as 11, totaling 17).
 * Example: Ace + 6 = soft 17 → dealer hits (H17 rule)
 * This adds about 0.2% to the house edge.
 */
#define DEALER_STAND_VALUE 17

/**
 * MAX_STRATEGY_ENTRIES: Maximum entries in the strategy table.
 *
 * DERIVATION: The complete basic strategy has approximately:
 * - Hard totals: 17 values × 10 dealer upcards = 170
 * - Soft totals: 8 values × 10 dealer upcards = 80
 * - Pairs: ~10 pair types × 10 dealer upcards = 100
 * Total: ~350 entries (500 provides safety margin)
 */
#define MAX_STRATEGY_ENTRIES 500

/**
 * MAX_TC_POINTS: Maximum true count data points for analysis.
 *
 * True counts typically range from -10 to +10, so 50 points
 * provides more than enough resolution for distribution analysis.
 */
#define MAX_TC_POINTS 50

/* =========================================================================
 * ENUMERATION TYPES
 * These define the discrete choices and states in the game.
 * ========================================================================= */

/**
 * CardSuit: The four suits of a standard French deck.
 *
 * While suits don't affect blackjack strategy (a 10♥ is identical
 * to a 10♠ for game purposes), we include them for complete card
 * representation and potential display/logging features.
 */
typedef enum {
    HEARTS,      /* ♥ - Red suit */
    DIAMONDS,    /* ♦ - Red suit */
    CLUBS,       /* ♣ - Black suit */
    SPADES       /* ♠ - Black suit */
} CardSuit;

/**
 * PlayerAction: Every possible player decision in blackjack.
 *
 * ACTION_HIT (H): Request an additional card. The player can hit
 * multiple times until they either stand or bust (exceed 21).
 * This is the most common action.
 *
 * ACTION_STAND (S): Decline additional cards and lock in the
 * current total. The dealer will then play their hand to completion.
 *
 * ACTION_DOUBLE (D): Double the initial bet and receive exactly
 * ONE more card. Only allowed on the first two cards.
 * This is an aggressive move indicating strong confidence.
 * Mathematically correct when player has a clear advantage,
 * such as 11 vs dealer 6.
 *
 * ACTION_SPLIT (P): Separate a pair into two independent hands,
 * each with its own bet equal to the original wager.
 * One additional card is dealt to each new hand.
 * "P" stands for "Pair split" in traditional strategy notation.
 */
typedef enum {
    ACTION_HIT,       /* H - Take another card */
    ACTION_STAND,     /* S - Keep current total */
    ACTION_DOUBLE,    /* D - Double bet, one more card */
    ACTION_SPLIT      /* P - Split pair into two hands */
} PlayerAction;

/**
 * HandStatus: Tracks the lifecycle of a blackjack hand.
 *
 * HAND_ACTIVE: Player is still making decisions on this hand.
 * Hit, stand, double, or split may be available.
 *
 * HAND_STANDING: Player has chosen to stop taking cards.
 * The hand's current total is locked in for comparison.
 *
 * HAND_BUST: The hand's total exceeds 21.
 * This is an automatic loss regardless of the dealer's result.
 * No further actions are possible on a busted hand.
 *
 * HAND_BLACKJACK: Natural blackjack - an Ace plus a 10-value
 * card as the initial two cards. Pays 3:2 unless dealer also
 * has blackjack (then push/tie).
 *
 * HAND_DOUBLED: Player has doubled down. The hand is complete
 * after receiving exactly one additional card.
 */
typedef enum {
    HAND_ACTIVE,       /* Player still deciding */
    HAND_STANDING,     /* Player locked in total */
    HAND_BUST,         /* Exceeded 21 - automatic loss */
    HAND_BLACKJACK,    /* Natural blackjack (Ace + 10-value) */
    HAND_DOUBLED       /* Doubled down - hand complete */
} HandStatus;

/* =========================================================================
 * STRUCTURE DEFINITIONS
 * These are the fundamental data objects of the simulation.
 * Each represents a core concept in the blackjack domain.
 * ========================================================================= */

/**
 * Card: Represents a single playing card with blackjack-specific properties.
 *
 * A card in blackjack has THREE different "values" depending on context:
 *
 * 1. GAME VALUE (value field):
 *    Used for hand totaling. Ace=11 (can become 1 if needed).
 *    Face cards (J,Q,K)=10. Number cards=their face value.
 *
 * 2. HI-LO COUNTING VALUE (hi_lo_value field):
 *    Used by card counters. 2-6:+1, 7-9:0, 10-A:-1.
 *
 * 3. RANK (rank field):
 *    1=Ace, 2-10=Numbers, 11=Jack, 12=Queen, 13=King
 *
 * ATTRIBUTES:
 * - rank: Numeric rank from 1 (Ace) to 13 (King)
 * - suit: Card suit (hearts, diamonds, clubs, spades)
 * - value: Blackjack game value for hand totaling
 * - is_ace: Boolean flag for quick Ace detection (optimization)
 * - hi_lo_value: Hi-Lo counting system value (+1, 0, or -1)
 */
typedef struct {
    int rank;            /* 1=Ace, 2-10, 11=Jack, 12=Queen, 13=King */
    CardSuit suit;        /* Hearts, Diamonds, Clubs, Spades */
    int value;            /* Blackjack game value (Ace=11, faces=10) */
    bool is_ace;          /* Quick Ace check without comparing rank */
    int hi_lo_value;      /* Hi-Lo counting value (+1, 0, or -1) */
} Card;

/**
 * Hand: Represents a blackjack hand (player or dealer).
 *
 * A hand is a collection of cards plus metadata about its state
 * in the game. The cards array has a fixed maximum size
 * (MAX_CARDS_PER_HAND = 21) which is sufficient for any
 * realistic blackjack scenario.
 *
 * SOFT vs HARD HANDS:
 * A "soft" hand contains an Ace counted as 11 and cannot bust
 * from one hit (the Ace can become 1). A "hard" hand either
 * has no Ace or must count all Aces as 1 to avoid busting.
 *
 * ATTRIBUTES:
 * - cards[]: Array of cards in this hand
 * - num_cards: How many cards currently in the hand
 * - bet: Amount wagered on this hand
 * - status: Current lifecycle state
 * - is_split: Whether this hand resulted from splitting a pair
 * - from_split_aces: Whether this hand came from splitting Aces
 */
typedef struct {
    Card cards[MAX_CARDS_PER_HAND];  /* Cards in this hand */
    int num_cards;                    /* Number of cards currently held */
    double bet;                       /* Amount wagered on this hand */
    HandStatus status;                /* Current lifecycle state */
    bool is_split;                    /* Result of splitting a pair? */
    bool from_split_aces;            /* Result of splitting Aces? */
} Hand;

/**
 * Shoe: The multi-deck card dispensing device.
 *
 * In casino blackjack, cards are dealt from a "shoe" - a plastic
 * box containing 4, 6, or 8 shuffled decks. The shoe was introduced
 * in the 1960s specifically to combat card counting.
 *
 * PENETRATION:
 * A colored "cut card" is inserted. When reached, the dealer
 * finishes the current round and reshuffles. Penetration critically
 * affects counting profitability:
 * - 75% penetration: ~4.5 decks dealt from 6-deck shoe
 * - 50% penetration: much harder to beat
 *
 * ATTRIBUTES:
 * - cards[]: Complete set of cards (312 for 6 decks)
 * - total_cards: Total cards (num_decks × 52)
 * - current_position: Index of next card to deal
 * - cut_card_position: Position triggering reshuffle
 * - num_decks: Number of 52-card decks
 * - penetration: Fraction dealt before reshuffle
 */
typedef struct {
    Card cards[TOTAL_CARDS];       /* All cards in the shoe */
    int total_cards;                /* Total cards (num_decks × 52) */
    int current_position;           /* Next card to deal */
    int cut_card_position;          /* Cut card position */
    int num_decks;                  /* Number of decks in shoe */
    double penetration;             /* Fraction dealt before reshuffle */
} Shoe;

/**
 * StrategyKey: Lookup key for the strategy table.
 *
 * The basic strategy table maps game states to optimal actions.
 * A "state" is defined by three pieces of information visible
 * to the player when making a decision:
 *
 * player_value: The player's hand value.
 *   For hard totals: 5-21
 *   For soft totals: 13-20 (A2 through A9)
 *   For pairs: encoded as rank × 100 (200=twos) or 112 for Aces
 *
 * dealer_upcard: The dealer's visible card value.
 *   2-10 for numbers, 11 for Ace.
 *
 * is_soft: Whether the hand contains an Ace counted as 11.
 *   Soft hands cannot bust from one hit, changing strategy.
 *
 * is_pair: Whether this state represents a paired hand.
 *   Pairs can be split, adding that action to consideration.
 */
typedef struct {
    int player_value;      /* Player's hand total (possibly encoded) */
    int dealer_upcard;     /* Dealer's visible card value (2-11) */
    bool is_soft;          /* Hand contains Ace counted as 11 */
    bool is_pair;          /* Two cards of identical rank */
} StrategyKey;

/**
 * StrategyEntry: A single entry in the basic strategy table.
 *
 * Each entry answers: "Given this hand and dealer upcard,
 * what action maximizes the player's expected value?"
 *
 * The table is computed through Monte Carlo simulation.
 *
 * ATTRIBUTES:
 * - key: The game state this entry applies to
 * - action: The optimal action (hit, stand, double, or split)
 * - expected_value: The EV of taking this action
 */
typedef struct {
    StrategyKey key;          /* Game state */
    PlayerAction action;      /* Optimal action for this state */
    double expected_value;    /* Expected value of this action */
} StrategyEntry;

/**
 * SimConfig: Configuration parameters for simulations.
 *
 * These settings control accuracy and scope. Different
 * configurations serve different purposes:
 *
 * QUICK TEST: simulations=1000 → ~10 seconds
 * STANDARD: simulations=100000 → ~20 minutes
 * HIGH PRECISION: simulations=1000000 → ~3 hours
 *
 * ATTRIBUTES:
 * - num_simulations: Monte Carlo trials per state-action pair
 * - num_decks: Number of decks in shoe (1-8)
 * - penetration: Fraction dealt before reshuffle
 * - blackjack_payout: Blackjack multiplier (1.5 = 3:2)
 * - max_splits: Maximum split hands allowed
 * - dealer_hits_soft_17: Whether dealer hits soft 17
 */
typedef struct {
    int num_simulations;          /* Trials per state-action pair */
    int num_decks;                /* Decks in shoe (1-8) */
    double penetration;           /* Fraction dealt before reshuffle */
    double blackjack_payout;      /* Blackjack multiplier (1.5=3:2) */
    int max_splits;               /* Maximum split hands allowed */
    bool dealer_hits_soft_17;     /* Dealer hits soft 17? */
} SimConfig;

/**
 * CountingResults: Aggregated statistics from counting simulation.
 *
 * After simulating thousands of shoes with Hi-Lo counting,
 * this summarizes the key findings.
 *
 * KEY METRIC - advantage_pct:
 * Calculated as counting_return_pct - basic_strategy_return_pct.
 * Should be positive (typically 1.0-1.5%) if counting works.
 *
 * ATTRIBUTES:
 * - total_hands: Hands played across all shoes
 * - total_shoes: Shoes simulated
 * - total_wagered: Sum of all wagers placed
 * - total_won: Net profit or loss
 * - counting_return_pct: EV with counting (%)
 * - basic_strategy_return_pct: EV without counting (%)
 * - advantage_pct: Improvement from counting (should be positive)
 */
typedef struct {
    int total_hands;                    /* Hands played */
    int total_shoes;                    /* Shoes simulated */
    double total_wagered;               /* Total amount wagered */
    double total_won;                   /* Net profit/loss */
    double counting_return_pct;         /* EV with counting (%) */
    double basic_strategy_return_pct;   /* EV without counting (%) */
    double advantage_pct;               /* Counting edge (%) */
} CountingResults;

/**
 * TrueCountData: EV data for a specific true count value.
 *
 * Tracks the empirical relationship between true count and
 * player advantage - THE KEY DATA for proving counting works.
 *
 * EXAMPLE:
 * true_count = +3
 * avg_return = +1.52% (player has 1.52% advantage)
 * std_return = 1.08% (variability measure)
 * num_observations = 2847 (sample size)
 *
 * ATTRIBUTES:
 * - true_count: True count value (typically -10 to +10)
 * - avg_return: Average return at this TC (%)
 * - std_return: Standard deviation of returns (%)
 * - num_observations: Number of hands at this TC
 */
typedef struct {
    int true_count;              /* True count value */
    double avg_return;           /* Average return (%) */
    double std_return;           /* Standard deviation (%) */
    int num_observations;        /* Number of hands at this TC */
} TrueCountData;

#endif /* BLACKJACK_TYPES_H */