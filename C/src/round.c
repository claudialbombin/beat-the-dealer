#include "bj.h"

#include <math.h>
#include <stddef.h>

static int deal(Shoe *s, Counter *c) {
    int card = shoe_draw(s);
    c->running += hi_lo(card);
    return card;
}

static void add(Hand *h, int card) { h->cards[h->n++] = (int8_t)card; }

static bool dealer_hits(const Hand *d, const Rules *r) {
    bool soft;
    int t = hand_total(d, &soft);
    return t < 17 || (t == 17 && soft && r->h17);
}

static double settle(const Hand *h, int dealer_total) {
    int t = hand_total(h, NULL);
    if (t > 21) return -h->bet;
    if (dealer_total > 21 || t > dealer_total) return h->bet;
    if (t < dealer_total) return -h->bet;
    return 0.0;
}

/* Play one player hand to completion; may append a second hand on split. */
static void play_hand(Hand *hands, int *n_hands, int i, int up, Shoe *shoe,
                      const Rules *r, const Strategy *st, Counter *c) {
    Hand *h = &hands[i];
    if (h->split_aces) { add(h, deal(shoe, c)); return; }
    if (h->from_split && h->n == 1) add(h, deal(shoe, c));

    for (;;) {
        bool soft;
        int total = hand_total(h, &soft);
        if (total >= 21) return;
        bool two = h->n == 2;
        bool pair = two && h->cards[0] == h->cards[1] && *n_hands == 1;
        bool can_double = two && (!h->from_split || r->das);
        Action a = strategy_decide(st, total, soft, up, can_double, pair ? h->cards[0] : 0);
        switch (a) {
        case STAND: return;
        case HIT: add(h, deal(shoe, c)); break;
        case DOUBLE: h->bet *= 2; add(h, deal(shoe, c)); return;
        case SPLIT: {
            bool aces = h->cards[0] == ACE;
            Hand *second = &hands[(*n_hands)++];
            *second = (Hand){.n = 1, .bet = h->bet, .from_split = true, .split_aces = aces};
            second->cards[0] = h->cards[1];
            h->n = 1;
            h->from_split = true;
            h->split_aces = aces;
            add(h, deal(shoe, c));
            if (aces) return;
            break;
        }
        }
    }
}

double play_round(Shoe *shoe, const Rules *r, const Strategy *st, double bet, Counter *c) {
    Hand hands[2] = {{.n = 0, .bet = bet}};
    Hand dealer = {.n = 0};
    int n_hands = 1;

    add(&hands[0], deal(shoe, c));
    int up = deal(shoe, c);
    add(&dealer, up);
    add(&hands[0], deal(shoe, c));
    int hole = shoe_draw(shoe); /* face down: counted when revealed */
    add(&dealer, hole);

    bool dealer_bj = hand_total(&dealer, NULL) == 21;
    bool player_bj = hand_total(&hands[0], NULL) == 21;
    if (dealer_bj || player_bj) {
        c->running += hi_lo(hole);
        if (dealer_bj && player_bj) return 0.0;
        return dealer_bj ? -bet : bet * r->bj_payout;
    }

    for (int i = 0; i < n_hands; i++) play_hand(hands, &n_hands, i, up, shoe, r, st, c);

    c->running += hi_lo(hole);
    bool any_live = false;
    for (int i = 0; i < n_hands; i++) any_live |= hand_total(&hands[i], NULL) <= 21;
    if (any_live)
        while (dealer_hits(&dealer, r)) add(&dealer, deal(shoe, c));

    int dt = hand_total(&dealer, NULL);
    double net = 0.0;
    for (int i = 0; i < n_hands; i++) net += settle(&hands[i], dt);
    return net;
}

int tc_bin(double tc) {
    int b = (int)floor(tc);
    return b < TC_MIN ? TC_MIN : b > TC_MAX ? TC_MAX : b;
}

void simulate(const Rules *r, const Strategy *st, long long rounds, uint64_t seed, Stats *out) {
    Rng rng;
    Shoe shoe;
    Counter c = {0};
    rng_seed(&rng, seed);
    shoe_init(&shoe, r, &rng);
    *out = (Stats){.shoes = 1};
    for (long long i = 0; i < rounds; i++) {
        if (shoe_needs_shuffle(&shoe)) {
            shoe_shuffle(&shoe, &rng);
            c.running = 0;
            out->shoes++;
        }
        int b = tc_bin(c.running / shoe_decks_remaining(&shoe)) - TC_MIN;
        double x = play_round(&shoe, r, st, 1.0, &c);
        out->n[b]++;
        out->sum[b] += x;
        out->sumsq[b] += x * x;
        out->hist[b][(int)lround(2 * x) + OUTCOMES / 2]++;
    }
    out->rounds = rounds;
}
