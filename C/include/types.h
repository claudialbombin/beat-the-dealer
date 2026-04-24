/**
 * @file types.h
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
 */

#ifndef TYPES_H
#define TYPES_H 

#include <stdbool.h>  /* For bool type */

/* =========================================================================
 * DIMENSIONAL CONSTANTS
 * These define the maximum sizes for all static arrays in the project.
 * Each value is derived from the physical constraints of blackjack.
 * ========================================================================= */

/**
 * MAX_HAND_CARDS: Maximum cards a player could theoretically hold.
 *
 * DERIVATION: The worst case occurs when splitting Aces multiple times
 * and drawing only small cards. With 4 split hands, each receiving
 * multiple cards, we could reach:
 * - Initial 2 cards
 * - Split to 2 hands (+0 cards, just separating)
 * - Re-split to 4 hands (+0 cards)
 * - Each hand hits multiple times with small cards
 *
 * A hand of A,2,2,2,2,2,2,2,2,2,2 totals 21 with 11 cards.
 * With 4 such hands, that's 44 cards total.
 * Setting to 21 per hand is more than sufficient for practical play
 * and keeps array sizes reasonable.
 */
#define MAX_HAND_CARDS 21

/**
 * MAX_SPLITS: Maximum number of times a pair can be split.
 *
 * CASINO STANDARD: Most casinos allow splitting up to 3 times,
 * creating a maximum of 4 hands from one starting pair.
 * Some allow unlimited re-splitting of Aces, but we follow
 * the more common restrictive rule.
 */
#define MAX_SPLITS 4

/**
 * MAX_DECKS: Maximum number of 52-card decks in the shoe.
 *
 * CASINO STANDARD: Single deck (1), double deck (2), or
 * multi-deck shoes of 4, 6, or 8 decks. We support up to 8.
 * More decks = harder to count, smaller true count fluctuations.
 */
#define MAX_DECKS 8

/**
 * TOTAL_CARDS: Total cards in a fully loaded shoe.
 *
 * CALCULATION: 52 cards per deck × MAX_DECKS decks
 * For 8 decks: 416 cards
 * For 6 decks: 312 cards
 * For 1 deck: 52 cards
 *
 * This constant determines the size of the shoe's card array.
 */
#define TOTAL_CARDS (52 * MAX_DECKS)

/**
 * BLACKJACK: The magic number 21 - the target value.
 *
 * Any hand totaling exactly 21 with the first two cards is a
 * "natural blackjack" and pays 3:2 (not 1:1 like normal wins).
 * A hand totaling 21 with 3+ cards is just "21" and pays 1:1.
 */
#define BLACKJACK 21

/**
 * DEALER_STAND: The dealer's mandatory standing threshold.
 *
 * CASINO RULE: The dealer MUST hit any total below 17 and
 * MUST stand on any total of 17 or higher.
 *
 * EXCEPTION - SOFT 17: Some casinos require the dealer to hit
 * "soft 17" (a hand containing an Ace counted as 11, totaling 17).
 * Example: Ace + 6 = soft 17 → dealer hits (H17 rule)
 * This adds about 0.2% to the house edge.
 */
#define DEALER_STAND 17

/**
 * MAX_STRATEGY_ENTRIES: Maximum entries in the strategy table.
 *
 * DERIVATION: The complete basic strategy has approximately:
 * - Hard totals: 17 values × 10 dealer upcards = 170
 * - Soft totals: 8 values × 10 dealer upcards = 80
 * - Pairs: ~10 pair types × 10 dealer upcards = 100
 * Total: ~350 entries
 *
 * We allocate 500 to have a safety margin.
 */
#define MAX_STRATEGY_ENTRIES 500

/**
 * MAX_TC_POINTS: Maximum true count data points for visualization.
 *
 * True counts typically range from -10 to +10, so 50 points
 * provides more than enough resolution for any practical distribution.
 */
#define MAX_TC_POINTS 50

/**
 * MAX_STATES: Maximum game states for Monte Carlo evaluation.
 *
 * Same as MAX_STRATEGY_ENTRIES - the complete state space.
 */
#define MAX_STATES 350

/* =========================================================================
 * ENUMERATION TYPES
 * These define the discrete choices and states in the game.
 * ========================================================================= */

/**
 * Suit: The four suits of a standard deck.
 *
 * While suits don't affect blackjack strategy (a 10♥ is identical
 * to a 10♠), we include them for complete card representation and
 * potential future use in display or analysis.
 */
typedef enum {
    HEARTS,     /* ♥ - Red */
    DIAMONDS,   /* ♦ - Red */
    CLUBS,      /* ♣ - Black */
    SPADES      /* ♠ - Black */
} Suit;

/**
 * Action: Every possible player decision in blackjack.
 *
 * ACT_HIT (H): Request an additional card. The player can hit
 * multiple times until they either stand or bust (exceed 21).
 * This is the most common action.
 *
 * ACT_STAND (S): Decline additional cards and lock in the
 * current total. The dealer will then play their hand to
 * completion and hands will be compared.
 *
 * ACT_DOUBLE (D): Double the initial bet and receive exactly
 * ONE more card. Only allowed on the first two cards.
 * This is an aggressive move indicating strong confidence.
 * Mathematically correct when player has a clear advantage,
 * such as 11 vs dealer 6.
 *
 * ACT_SPLIT (P): Separate a pair into two independent hands,
 * each with its own bet equal to the original wager.
 * One additional card is dealt to each new hand.
 * "P" stands for "Pair split" in traditional strategy notation.
 * Splitting Aces is restricted: usually only one card per Ace,
 * and a 10 on a split Ace counts as 21, NOT blackjack.
 */
typedef enum {
    ACT_HIT,      /* H - Take another card */
    ACT_STAND,    /* S - Keep current total */
    ACT_DOUBLE,   /* D - Double bet, one more card */
    ACT_SPLIT     /* P - Split pair into two hands */
} Action;

/**
 * HandState: Tracks the lifecycle of a blackjack hand.
 *
 * HAND_ACTIVE: Player is still making decisions on this hand.
 * Hit, stand, double, or split may be available.
 *
 * HAND_STAND: Player has chosen to stop taking cards.
 * The hand's current total is locked in.
 *
 * HAND_BUST: The hand's total exceeds 21.
 * This is an automatic loss regardless of the dealer's result.
 * No further actions are possible.
 *
 * HAND_BJ: Natural blackjack - an Ace plus a 10-value card
 * as the initial two cards. Pays 3:2 unless the dealer also
 * has blackjack (then it's a push/tie).
 *
 * HAND_DOUBLED: Player has doubled down. The hand is complete
 * after receiving exactly one additional card.
 */
typedef enum {
    HAND_ACTIVE,    /* Player still deciding */
    HAND_STAND,     /* Player locked in total */
    HAND_BUST,      /* Exceeded 21 - automatic loss */
    HAND_BJ,        /* Natural blackjack (A+10) */
    HAND_DOUBLED    /* Doubled down - hand complete */
} HandState;

/* =========================================================================
 * STRUCTURE DEFINITIONS
 * These are the fundamental data objects of the simulation.
 * ========================================================================= */

/**
 * Card: Represents a single playing card with blackjack-specific properties.
 *
 * ATTRIBUTES:
 * - rank: Numeric rank from 1 (Ace) to 13 (King).
 *   Ranks 11, 12, 13 are Jack, Queen, King respectively.
 * - suit: The card's suit (hearts, diamonds, clubs, spades).
 *   Not used in strategy but maintained for completeness.
 * - value: The card's contribution to a hand total.
 *   Ace = 11 (can become 1 if needed, handled by hand evaluation).
 *   Face cards (J,Q,K) = 10.
 *   Number cards (2-10) = their face value.
 * - is_ace: Boolean flag for quick Ace detection.
 *   Faster than checking rank == 1 every time.
 * - hi_lo_val: The card's value in the Hi-Lo counting system.
 *   2-6 → +1 (low cards, favorable when removed)
 *   7-9 → 0 (neutral cards)
 *   10-A → -1 (high cards, unfavorable when removed)
 *
 * WHY SEPARATE VALUE AND HI_LO_VAL:
 * The game value is used for hand totaling (determining winners).
 * The Hi-Lo value is used for deck composition tracking (determining bets).
 * They are completely different concepts despite both being "values."
 */
typedef struct {
    int rank;           /* 1=Ace, 2-10, 11=Jack, 12=Queen, 13=King */
    Suit suit;          /* Hearts, Diamonds, Clubs, Spades */
    int value;          /* Blackjack game value (Ace=11, faces=10) */
    bool is_ace;        /* Quick Ace check without comparing rank */
    int hi_lo_val;      /* Hi-Lo counting value (+1, 0, or -1) */
} Card;

/**
 * Hand: Represents a blackjack hand (player or dealer).
 *
 * A hand is a collection of cards plus metadata about its state.
 * The cards array has a fixed maximum size (MAX_HAND_CARDS) which
 * is more than sufficient for any realistic blackjack scenario.
 *
 * KEY FIELDS:
 * - cards[]: The cards in this hand, stored in order dealt.
 * - num_cards: How many cards are currently in the hand.
 *   This is always ≤ MAX_HAND_CARDS and is used to know
 *   which array elements are valid.
 * - bet: The amount wagered on this hand.
 *   For the dealer, this is always 0.
 *   For the player, this starts as the initial bet and
 *   may double (if doubling down) or be replicated (if splitting).
 * - state: The current lifecycle state of the hand.
 *   Determines what actions are available and how the hand
 *   will be evaluated against the dealer.
 * - is_split: Whether this hand resulted from splitting a pair.
 *   Affects some rule variations (e.g., some casinos don't
 *   allow doubling after splitting).
 * - from_split_aces: Whether this hand came from splitting Aces.
 *   Special restrictions apply: usually only one card per split Ace,
 *   and 21 on a split Ace is NOT a blackjack (pays 1:1, not 3:2).
 */
typedef struct {
    Card cards[MAX_HAND_CARDS];  /* Cards in this hand */
    int num_cards;                /* Number of cards currently held */
    double bet;                   /* Amount wagered */
    HandState state;              /* Current lifecycle state */
    bool is_split;                /* Result of splitting a pair? */
    bool from_split_aces;        /* Result of splitting Aces? */
} Hand;

/**
 * Shoe: The multi-deck card dispensing device.
 *
 * In casino blackjack, cards are dealt from a "shoe" - a box
 * containing 4, 6, or 8 shuffled decks. The shoe provides:
 *
 * 1. RANDOMIZATION: Multiple decks shuffled together make it
 *    harder to predict upcoming cards (countering card counting).
 *
 * 2. EFFICIENCY: Dealing from a shoe is faster than hand-held
 *    decks. More hands per hour = more profit for the casino.
 *
 * 3. PENETRATION CONTROL: A colored "cut card" is inserted into
 *    the shoe. When the dealer reaches this card, they finish the
 *    current round and reshuffle. Penetration (how deep they deal)
 *    critically affects card counting profitability.
 *
 * IMPLEMENTATION DETAILS:
 * - cards[]: The complete set of cards (312 for 6 decks).
 *   This array is initialized once and shuffled.
 * - total: Total cards in the shoe (num_decks × 52).
 * - position: Index of the next card to deal.
 *   Advances with each deal, never resets until reshuffle.
 * - cut_pos: Position of the cut card.
 *   When position reaches cut_pos, the shoe needs reshuffling.
 *   Calculated as: total × penetration.
 * - num_decks: Number of 52-card decks (typically 6).
 * - penetration: Fraction of cards dealt before reshuffle.
 *   0.75 means 75% of cards are dealt (the rest are behind the cut card).
 */
typedef struct {
    Card cards[TOTAL_CARDS];  /* All cards in the shoe */
    int total;                 /* Total cards (num_decks × 52) */
    int position;              /* Next card to deal */
    int cut_pos;               /* Cut card position */
    int num_decks;             /* Number of decks in shoe */
    double penetration;        /* Fraction dealt before reshuffle */
} Shoe;

/**
 * StratKey: Lookup key for the strategy table.
 *
 * The basic strategy table maps game states to optimal actions.
 * A "state" is defined by three pieces of information:
 *
 * player_val: The player's hand value.
 *   For hard totals: 5-21
 *   For soft totals: 13-20 (representing A2 through A9)
 *   For pairs: encoded as rank × 100 (200=twos, 1000=tens)
 *   or 112 for Ace pairs
 *
 * dealer_up: The dealer's visible card value.
 *   2-10 for number cards, 11 for Ace.
 *   This is the primary strategic variable because the
 *   dealer's bust probability varies dramatically:
 *   Dealer 6 → busts 42% (favorable for player)
 *   Dealer Ace → busts 12% (favorable for dealer)
 *
 * is_soft: Whether the player's hand contains an Ace counted as 11.
 *   Soft hands cannot bust from one hit, which fundamentally
 *   changes the optimal strategy. Soft 18 vs dealer 10 should
 *   HIT (you can't bust, might improve to 19-21), while hard
 *   18 vs dealer 10 should STAND.
 *
 * is_pair: Whether this state represents a paired hand.
 *   Pairs can be split, adding the split action to consideration.
 */
typedef struct {
    int player_val;    /* Player's hand total (possibly encoded) */
    int dealer_up;     /* Dealer's visible card value (2-11) */
    bool is_soft;      /* Hand contains Ace counted as 11 */
    bool is_pair;      /* Two cards of identical rank */
} StratKey;

/**
 * StratEntry: A single entry in the basic strategy table.
 *
 * Each entry answers: "Given this specific hand and dealer upcard,
 * what action maximizes the player's expected value?"
 *
 * The table is computed through Monte Carlo simulation - for each
 * state, we simulate thousands of hands for each possible action
 * and select the one with the highest average return.
 *
 * ATTRIBUTES:
 * - key: The game state this entry applies to
 * - action: The optimal action (hit, stand, double, or split)
 * - ev: The expected value of taking this action
 *   (in betting units; 0.01 means 1% expected profit)
 */
typedef struct {
    StratKey key;      /* Game state */
    Action action;     /* Optimal action for this state */
    double ev;         /* Expected value of this action */
} StratEntry;

/**
 * SimConfig: Configuration parameters for the simulation.
 *
 * These settings control the accuracy and scope of the Monte Carlo
 * simulation. Different configurations are appropriate for different
 * purposes:
 *
 * QUICK TEST: simulations=1000, decks=6 → ~10 seconds
 *   Good for verifying code changes and pipeline integrity.
 *
 * STANDARD: simulations=100000, decks=6 → ~20 minutes
 *   Produces accurate basic strategy matching published charts.
 *
 * HIGH PRECISION: simulations=1000000, decks=6 → ~3 hours
 *   Very precise EV estimates, but usually unnecessary.
 *
 * ATTRIBUTES:
 * - simulations: Monte Carlo trials per state-action pair.
 *   More = more accurate but slower.
 * - num_decks: Number of decks in the shoe (affects strategy slightly).
 * - penetration: How deep into the shoe to deal before reshuffle.
 * - bj_payout: Blackjack payout multiplier (1.5 = standard 3:2).
 * - max_splits: Maximum number of times a pair can be split.
 * - hit_soft_17: Whether dealer hits soft 17 (modern rule).
 */
typedef struct {
    int simulations;       /* Trials per state-action pair */
    int num_decks;         /* Decks in shoe (1-8) */
    double penetration;    /* Fraction dealt (0.0-1.0) */
    double bj_payout;      /* Blackjack multiplier (1.5 = 3:2) */
    int max_splits;        /* Max split hands */
    bool hit_soft_17;      /* Dealer hits soft 17? */
} SimConfig;

/**
 * CountResults: Aggregated statistics from counting simulation.
 *
 * After simulating thousands of shoes with Hi-Lo counting,
 * this structure summarizes the key findings:
 *
 * total_hands: How many individual hands were played.
 *   A typical shoe produces ~40-50 hands.
 *
 * total_shoes: How many complete shoes were simulated.
 *   More shoes = more statistical confidence.
 *
 * total_bet: Sum of all wagers placed.
 *   With dynamic betting, this varies significantly per shoe.
 *
 * total_won: Net profit or loss across all hands.
 *   Should be positive if counting provides an edge.
 *
 * count_return: Expected return WITH counting (percentage).
 *   Example: 1.2 means winning $1.20 per $100 wagered.
 *
 * basic_return: Expected return WITHOUT counting (percentage).
 *   Example: -0.5 means losing $0.50 per $100 wagered.
 *   This is the theoretical house edge.
 *
 * advantage: The improvement from counting.
 *   Calculated as: count_return - basic_return.
 *   Should be positive if counting works.
 */
typedef struct {
    int total_hands;           /* Hands played */
    int total_shoes;           /* Shoes simulated */
    double total_bet;          /* Total amount wagered */
    double total_won;          /* Net profit/loss */
    double count_return;       /* EV with counting (%) */
    double basic_return;       /* EV without counting (%) */
    double advantage;          /* Counting edge (%) */
} CountResults;

/**
 * TCData: Expected value data for a specific true count.
 *
 * This structure tracks the relationship between true count
 * and player advantage, which is the empirical proof that
 * card counting works.
 *
 * EXAMPLE DATA POINT:
 * true_count = +3
 * avg_return = +1.52 (player has 1.52% advantage)
 * std_dev = 1.08 (returns vary by about 1.08 percentage points)
 * observations = 2,847 (this count occurred 2,847 times)
 *
 * The relationship should be approximately linear:
 * EV ≈ -0.5 + 0.5 × true_count
 *
 * true_count: The true count value (running / decks remaining).
 *   Typically ranges from -10 to +10.
 *
 * avg_return: Average return per bet at this true count (%).
 *   Positive means player advantage, negative means house edge.
 *
 * std_dev: Standard deviation of returns at this count.
 *   Measures variability. Higher at extreme counts due to
 *   fewer observations.
 *
 * observations: How many hands were played at this count.
 *   Most hands occur near TC = 0. Extreme counts are rare.
 */
typedef struct {
    int true_count;            /* True count value */
    double avg_return;         /* Average return (%) */
    double std_dev;            /* Standard deviation (%) */
    int observations;          /* Number of hands at this TC */
} TCData;

#endif /* TYPES_H */