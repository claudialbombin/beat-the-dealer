/* Minimal unit tests for the C port: hand arithmetic and the rules on
   rigged shoes. Run with `make test`. */
#include "bj.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond); failures++; } } while (0)

static Rules RULES = {.decks = 6, .h17 = true, .bj_payout = 1.5, .das = true, .penetration = 0.75};

static int total_of(const int *cards, int n, bool *soft) {
    Hand h = {.n = n};
    for (int i = 0; i < n; i++) h.cards[i] = (int8_t)cards[i];
    return hand_total(&h, soft);
}

static void rig(Shoe *s, const int *cards, int n) {
    Rng rng;
    rng_seed(&rng, 1);
    shoe_init(s, &RULES, &rng);
    for (int i = 0; i < n; i++) s->cards[i] = (int8_t)cards[i];
    s->pos = 0;
}

/* A strategy that always stands, except the given cell. */
static void stand_all(Strategy *st) {
    memset(st, 0, sizeof *st);
    for (int t = 4; t <= 21; t++)
        for (int u = 2; u <= 11; u++) { strcpy(st->hard[t][u], "S"); strcpy(st->soft[t][u], "S"); }
}

int main(void) {
    bool soft;
    CHECK(total_of((int[]){ACE, 7}, 2, &soft) == 18 && soft);
    CHECK(total_of((int[]){ACE, ACE, ACE, ACE}, 4, &soft) == 14 && soft);
    CHECK(total_of((int[]){ACE, 7, 5}, 3, &soft) == 13 && !soft);
    CHECK(total_of((int[]){10, 10, 2}, 3, &soft) == 22);

    Strategy st;
    Shoe shoe;
    Counter c = {0};

    stand_all(&st);
    rig(&shoe, (int[]){ACE, 9, 10, 7}, 4);
    CHECK(play_round(&shoe, &RULES, &st, 1, &c) == 1.5);            /* 3:2 */

    rig(&shoe, (int[]){6, 10, 5, ACE}, 4);
    strcpy(st.hard[11][10], "Dh");
    CHECK(play_round(&shoe, &RULES, &st, 1, &c) == -1);             /* peek: lose 1 only */

    rig(&shoe, (int[]){6, 10, 5, 7, 10}, 5);                         /* double 11 vs 10 -> 21 */
    CHECK(play_round(&shoe, &RULES, &st, 1, &c) == 2);

    stand_all(&st);
    st.pair[ACE][10] = true;
    rig(&shoe, (int[]){ACE, 10, ACE, 9, 10, 5}, 6);                  /* split aces: 21 & 16 vs 19 */
    CHECK(play_round(&shoe, &RULES, &st, 1, &c) == 0);

    stand_all(&st);
    rig(&shoe, (int[]){10, ACE, 8, 6, 2, 10}, 6);                    /* 18 vs soft 17 -> H17 draws 2 */
    CHECK(play_round(&shoe, &RULES, &st, 1, &c) == -1);
    Rules s17 = RULES;
    s17.h17 = false;
    rig(&shoe, (int[]){10, ACE, 8, 6, 2, 10}, 6);
    CHECK(play_round(&shoe, &s17, &st, 1, &c) == 1);

    Counter hc = {0};
    rig(&shoe, (int[]){10, 5, 9, 2, 10}, 5);                         /* hole card counted at reveal */
    play_round(&shoe, &RULES, &st, 1, &hc);
    CHECK(hc.running == -1 + 1 + 0 + 1 - 1); /* T,5,9 + hole 2 + dealer draws T */

    CHECK(tc_bin(2.7) == 2 && tc_bin(-0.2) == -1 && tc_bin(99) == TC_MAX);

    Rng r;
    rng_seed(&r, 42);
    int counts[6] = {0};
    for (int i = 0; i < 600000; i++) counts[rng_below(&r, 6)]++;
    for (int i = 0; i < 6; i++) CHECK(abs(counts[i] - 100000) < 1500);

    if (failures == 0) printf("all C tests passed\n");
    return failures != 0;
}
