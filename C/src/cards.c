#include "bj.h"
#include <stddef.h>

static const int8_t RANK_VALUES[13] = {2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, ACE};

void shoe_init(Shoe *s, const Rules *rules, Rng *rng) {
    s->size = 0;
    for (int d = 0; d < rules->decks * 4; d++)
        for (int r = 0; r < 13; r++) s->cards[s->size++] = RANK_VALUES[r];
    s->cut = (int)(s->size * rules->penetration);
    shoe_shuffle(s, rng);
}

void shoe_shuffle(Shoe *s, Rng *rng) { /* Fisher-Yates */
    for (int i = s->size - 1; i > 0; i--) {
        int j = (int)rng_below(rng, (uint32_t)i + 1);
        int8_t t = s->cards[i];
        s->cards[i] = s->cards[j];
        s->cards[j] = t;
    }
    s->pos = 0;
}

int shoe_draw(Shoe *s) {
    /* The cut card stops play between rounds only; running out entirely
       would be a bug, so wrap defensively rather than read past the end. */
    if (s->pos >= s->size) s->pos = 0;
    return s->cards[s->pos++];
}

bool shoe_needs_shuffle(const Shoe *s) { return s->pos >= s->cut; }

double shoe_decks_remaining(const Shoe *s) {
    double d = (s->size - s->pos) / 52.0;
    return d < 0.25 ? 0.25 : d;
}

int hand_total(const Hand *h, bool *soft) {
    int hard = 0;
    bool ace = false;
    for (int i = 0; i < h->n; i++) {
        if (h->cards[i] == ACE) { hard += 1; ace = true; }
        else hard += h->cards[i];
    }
    bool s = ace && hard + 10 <= 21;
    if (soft) *soft = s;
    return s ? hard + 10 : hard;
}

int hi_lo(int card) {
    if (card <= 6) return 1;
    if (card <= 9) return 0;
    return -1;
}
