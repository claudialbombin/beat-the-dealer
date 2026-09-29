/*
 * Blackjack shoe simulator with Hi-Lo counting.
 *
 * A C port of python/src/blackjack/{engine,counting}.py, used for the large
 * runs behind the counting results. Same rules, same counting conventions,
 * same true-count binning; a Python test checks the two agree.
 */
#ifndef BJ_H
#define BJ_H

#include <stdbool.h>
#include <stdint.h>

#define ACE 11
#define MAX_DECKS 8
#define SHOE_MAX (52 * MAX_DECKS)
#define MAX_CARDS 22 /* more cards than any hand can hold */
#define TC_MIN (-10)
#define TC_MAX 10
#define TC_BINS (TC_MAX - TC_MIN + 1)
#define OUTCOMES 17 /* net result per unit: -4.0, -3.5, ..., +4.0 */

/* ---- rules ------------------------------------------------------------ */
typedef struct {
    int decks;
    bool h17;          /* dealer hits soft 17 */
    double bj_payout;  /* 1.5 = 3:2 */
    bool das;          /* double after split */
    double penetration;
} Rules;

/* ---- random numbers: xoshiro256** ------------------------------------- */
typedef struct { uint64_t s[4]; } Rng;
void rng_seed(Rng *r, uint64_t seed);
uint64_t rng_next(Rng *r);
uint32_t rng_below(Rng *r, uint32_t n); /* unbiased integer in [0, n) */

/* ---- shoe ------------------------------------------------------------- */
typedef struct {
    int8_t cards[SHOE_MAX];
    int size, pos, cut;
} Shoe;
void shoe_init(Shoe *s, const Rules *rules, Rng *rng);
void shoe_shuffle(Shoe *s, Rng *rng);
int shoe_draw(Shoe *s);
bool shoe_needs_shuffle(const Shoe *s);
double shoe_decks_remaining(const Shoe *s);

/* ---- hands -------------------------------------------------------------- */
typedef struct {
    int8_t cards[MAX_CARDS];
    int n;
    double bet;
    bool from_split, split_aces;
} Hand;
int hand_total(const Hand *h, bool *soft);
int hi_lo(int card);

/* ---- strategy ------------------------------------------------------------ */
typedef enum { HIT = 'H', STAND = 'S', DOUBLE = 'D', SPLIT = 'P' } Action;
typedef struct {
    char hard[22][12][3]; /* [total][upcard] -> "H", "S", "Dh", "Ds" */
    char soft[22][12][3];
    bool pair[12][12];    /* [pair value][upcard] -> split? */
} Strategy;
int strategy_load(Strategy *st, const char *csv_path); /* 0 on success */
Action strategy_decide(const Strategy *st, int total, bool soft, int up,
                       bool can_double, int pair_value /* 0 = not a splittable pair */);

/* ---- one round ------------------------------------------------------------ */
typedef struct { int running; } Counter;
double play_round(Shoe *shoe, const Rules *rules, const Strategy *st,
                  double bet, Counter *count);

/* ---- statistics per true-count bin -------------------------------------- */
typedef struct {
    long long n[TC_BINS];
    double sum[TC_BINS], sumsq[TC_BINS];
    long long hist[TC_BINS][OUTCOMES];
    long long rounds, shoes;
} Stats;
int tc_bin(double true_count);
void simulate(const Rules *rules, const Strategy *st, long long rounds,
              uint64_t seed, Stats *out);

#endif
