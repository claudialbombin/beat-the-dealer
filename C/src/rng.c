#include "bj.h"

static uint64_t splitmix64(uint64_t *x) {
    uint64_t z = (*x += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

void rng_seed(Rng *r, uint64_t seed) {
    for (int i = 0; i < 4; i++) r->s[i] = splitmix64(&seed);
}

static inline uint64_t rotl(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }

uint64_t rng_next(Rng *r) {
    uint64_t *s = r->s;
    uint64_t result = rotl(s[1] * 5, 7) * 9;
    uint64_t t = s[1] << 17;
    s[2] ^= s[0];
    s[3] ^= s[1];
    s[1] ^= s[2];
    s[0] ^= s[3];
    s[2] ^= t;
    s[3] = rotl(s[3], 45);
    return result;
}

/* Lemire's multiply-and-reject: no modulo bias. */
uint32_t rng_below(Rng *r, uint32_t n) {
    uint64_t m = (uint64_t)(uint32_t)(rng_next(r) >> 32) * n;
    uint32_t low = (uint32_t)m;
    if (low < n) {
        uint32_t threshold = -n % n;
        while (low < threshold) {
            m = (uint64_t)(uint32_t)(rng_next(r) >> 32) * n;
            low = (uint32_t)m;
        }
    }
    return (uint32_t)(m >> 32);
}
