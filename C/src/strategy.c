#include "bj.h"

#include <stdio.h>
#include <string.h>

/* Reads the CSV written by `python -m blackjack solve`:
       kind,total,upcard,action
       hard,16,10,H
       soft,18,3,Ds
       pair,8,10,P                                                        */
int strategy_load(Strategy *st, const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) return -1;
    memset(st, 0, sizeof *st);
    char line[128], kind[8], action[4];
    int total, up, rows = 0;
    if (!fgets(line, sizeof line, f)) { fclose(f); return -1; } /* header */
    while (fgets(line, sizeof line, f)) {
        if (sscanf(line, "%7[^,],%d,%d,%3s", kind, &total, &up, action) != 4) continue;
        if (total < 2 || total > 21 || up < 2 || up > 11) continue;
        if (strcmp(kind, "hard") == 0) strcpy(st->hard[total][up], action);
        else if (strcmp(kind, "soft") == 0) strcpy(st->soft[total][up], action);
        else if (strcmp(kind, "pair") == 0) st->pair[total][up] = action[0] == 'P';
        else continue;
        rows++;
    }
    fclose(f);
    return rows > 0 ? 0 : -1;
}

Action strategy_decide(const Strategy *st, int total, bool soft, int up,
                       bool can_double, int pair_value) {
    if (pair_value && st->pair[pair_value][up]) return SPLIT;
    const char *code = soft ? st->soft[total][up] : st->hard[total][up];
    if (code[0] == '\0') return total >= 17 ? STAND : HIT;
    if (code[0] == 'D') {
        if (can_double) return DOUBLE;
        return code[1] == 'h' ? HIT : STAND;
    }
    return (Action)code[0];
}
