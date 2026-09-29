/*
 * bjsim: simulate many rounds of 6-deck blackjack with Hi-Lo counting and
 * write per-true-count statistics as CSV.
 *
 *   ./bin/bjsim --rounds 200000000 --threads 8 --out ../results/counting_c.csv
 *
 * Each thread plays its own independent shoe with its own RNG stream; the
 * per-bin sums are merged at the end.
 */
#include "bj.h"

#include <math.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef struct {
    const Rules *rules;
    const Strategy *st;
    long long rounds;
    uint64_t seed;
    Stats stats;
} Job;

static void *worker(void *arg) {
    Job *j = arg;
    simulate(j->rules, j->st, j->rounds, j->seed, &j->stats);
    return NULL;
}

static void usage(const char *prog) {
    fprintf(stderr,
            "usage: %s [--rounds N] [--threads T] [--seed S] [--strategy CSV] [--out CSV] [--s17]\n",
            prog);
}

int main(int argc, char **argv) {
    long long rounds = 10000000;
    int threads = 4;
    uint64_t seed = 2026;
    const char *strategy_path = "../web/data/strategy.csv";
    const char *out_path = NULL;
    Rules rules = {.decks = 6, .h17 = true, .bj_payout = 1.5, .das = true, .penetration = 0.75};

    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        const char *v = i + 1 < argc ? argv[i + 1] : NULL;
        if (!strcmp(a, "--rounds") && v) { rounds = atoll(v); i++; }
        else if (!strcmp(a, "--threads") && v) { threads = atoi(v); i++; }
        else if (!strcmp(a, "--seed") && v) { seed = strtoull(v, NULL, 10); i++; }
        else if (!strcmp(a, "--strategy") && v) { strategy_path = v; i++; }
        else if (!strcmp(a, "--out") && v) { out_path = v; i++; }
        else if (!strcmp(a, "--s17")) rules.h17 = false;
        else { usage(argv[0]); return 2; }
    }
    if (rounds <= 0 || threads <= 0 || threads > 256) { usage(argv[0]); return 2; }

    Strategy st;
    if (strategy_load(&st, strategy_path) != 0) {
        fprintf(stderr, "could not read strategy from %s (run `python -m blackjack solve` first)\n",
                strategy_path);
        return 1;
    }

    Job *jobs = calloc((size_t)threads, sizeof *jobs);
    pthread_t *tids = calloc((size_t)threads, sizeof *tids);
    if (!jobs || !tids) return 1;
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (int t = 0; t < threads; t++) {
        jobs[t].rules = &rules;
        jobs[t].st = &st;
        jobs[t].rounds = rounds / threads + (t < rounds % threads);
        jobs[t].seed = seed * 1000003ULL + (uint64_t)t;
        pthread_create(&tids[t], NULL, worker, &jobs[t]);
    }
    Stats all = {0};
    for (int t = 0; t < threads; t++) {
        pthread_join(tids[t], NULL);
        for (int b = 0; b < TC_BINS; b++) {
            all.n[b] += jobs[t].stats.n[b];
            all.sum[b] += jobs[t].stats.sum[b];
            all.sumsq[b] += jobs[t].stats.sumsq[b];
            for (int k = 0; k < OUTCOMES; k++) all.hist[b][k] += jobs[t].stats.hist[b][k];
        }
        all.rounds += jobs[t].stats.rounds;
        all.shoes += jobs[t].stats.shoes;
    }
    clock_gettime(CLOCK_MONOTONIC, &t1);
    double secs = (double)(t1.tv_sec - t0.tv_sec) + (double)(t1.tv_nsec - t0.tv_nsec) / 1e9;

    double sum = 0, sumsq = 0;
    for (int b = 0; b < TC_BINS; b++) { sum += all.sum[b]; sumsq += all.sumsq[b]; }
    double mean = sum / (double)all.rounds;
    double se = sqrt((sumsq / (double)all.rounds - mean * mean) / (double)all.rounds);
    fprintf(stderr, "%lld rounds, %lld shoes in %.1fs (%.1fM rounds/s)\n",
            all.rounds, all.shoes, secs, (double)all.rounds / secs / 1e6);
    fprintf(stderr, "player edge: %+.4f%% +/- %.4f%% (95%% CI)\n", 100 * mean, 196 * se);

    FILE *out = out_path ? fopen(out_path, "w") : stdout;
    if (!out) { perror(out_path); return 1; }
    fprintf(out, "# bjsim: %d decks, %s, %.0f%% penetration, seed %llu, %d threads\n",
            rules.decks, rules.h17 ? "H17" : "S17", 100 * rules.penetration,
            (unsigned long long)seed, threads);
    fprintf(out, "tc,n,sum,sumsq");
    for (int k = 0; k < OUTCOMES; k++) fprintf(out, ",h%+.1f", (k - OUTCOMES / 2) / 2.0);
    fprintf(out, "\n");
    for (int b = 0; b < TC_BINS; b++) {
        if (!all.n[b]) continue;
        fprintf(out, "%d,%lld,%.6f,%.6f", b + TC_MIN, all.n[b], all.sum[b], all.sumsq[b]);
        for (int k = 0; k < OUTCOMES; k++) fprintf(out, ",%lld", all.hist[b][k]);
        fprintf(out, "\n");
    }
    fprintf(out, "meta,%lld,%lld,0", all.rounds, all.shoes);
    for (int k = 0; k < OUTCOMES; k++) fprintf(out, ",0");
    fprintf(out, "\n");
    if (out != stdout) fclose(out);
    free(jobs);
    free(tids);
    return 0;
}
