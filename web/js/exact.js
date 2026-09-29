// Exact infinite-deck solver, a port of python/src/blackjack/exact.py.
// Fast enough (a few ms) to re-solve the whole game whenever a rule changes.

import { ACE, addCard } from "./engine.js";

const TEN = 10;
export const UPCARDS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
export const CARD_PROBS = new Map([
  [2, 1 / 13], [3, 1 / 13], [4, 1 / 13], [5, 1 / 13], [6, 1 / 13],
  [7, 1 / 13], [8, 1 / 13], [9, 1 / 13], [10, 4 / 13], [11, 1 / 13],
]);
const BUST = 22;

function dealerDist(up, h17) {
  const memo = new Map();
  const finish = (total, soft) => {
    const key = total * 2 + (soft ? 1 : 0);
    if (memo.has(key)) return memo.get(key);
    let out;
    if (total > 21) out = new Map([[BUST, 1]]);
    else if (total > 17 || (total === 17 && !(soft && h17))) out = new Map([[total, 1]]);
    else {
      out = new Map();
      for (const [c, p] of CARD_PROBS)
        for (const [k, q] of finish(...addCard(total, soft, c))) out.set(k, (out.get(k) || 0) + p * q);
    }
    memo.set(key, out);
    return out;
  };
  const hole = new Map(CARD_PROBS);
  if (up === ACE) hole.delete(TEN);
  else if (up === TEN) hole.delete(ACE);
  let norm = 0;
  for (const p of hole.values()) norm += p;
  const start = up === ACE ? [11, true] : [up, false];
  const dist = new Map();
  for (const [c, p] of hole)
    for (const [k, q] of finish(...addCard(...start, c))) dist.set(k, (dist.get(k) || 0) + (p / norm) * q);
  return dist;
}

export const pDealerBJ = (up) => (up === ACE ? 4 / 13 : up === TEN ? 1 / 13 : 0);

class UpcardTables {
  constructor(rules, up) {
    this.rules = rules;
    this.up = up;
    this.dist = dealerDist(up, rules.h17);
    this.stands = new Float64Array(23);
    for (let t = 4; t <= 22; t++) {
      if (t > 21) {
        this.stands[t] = -1;
        continue;
      }
      let v = 0;
      for (const [k, p] of this.dist) v += k === BUST || k < t ? p : k > t ? -p : 0;
      this.stands[t] = v;
    }
    this.multi = new Map();
  }
  stand(t) {
    return t > 21 ? -1 : this.stands[Math.max(t, 4)];
  }
  afterDraw(total, soft, f) {
    let ev = 0;
    for (const [c, p] of CARD_PROBS) {
      const [t, s] = addCard(total, soft, c);
      ev += p * (t > 21 ? -1 : f(t, s));
    }
    return ev;
  }
  hit(total, soft) {
    return this.afterDraw(total, soft, (t, s) => this.multiCard(t, s));
  }
  double(total, soft) {
    return 2 * this.afterDraw(total, soft, (t) => this.stand(t));
  }
  multiCard(total, soft) {
    const key = total * 2 + (soft ? 1 : 0);
    if (!this.multi.has(key)) {
      const v = total >= 21 ? this.stand(total) : Math.max(this.stand(total), this.hit(total, soft));
      this.multi.set(key, v);
    }
    return this.multi.get(key);
  }
  twoCard(total, soft, canDouble) {
    if (total >= 21) return this.stand(total);
    let v = Math.max(this.stand(total), this.hit(total, soft));
    if (canDouble) v = Math.max(v, this.double(total, soft));
    return v;
  }
  split(v) {
    const start = v === ACE ? [11, true] : [v, false];
    const one =
      v === ACE
        ? this.afterDraw(...start, (t) => this.stand(t))
        : this.afterDraw(...start, (t, s) => this.twoCard(t, s, this.rules.das));
    return 2 * one;
  }
  /** EVs of each legal action, per unit of the hand's current bet. */
  actionEVs(total, soft, canDouble = true) {
    const evs = { S: this.stand(total) };
    if (total < 21) {
      evs.H = this.hit(total, soft);
      if (canDouble) evs.D = this.double(total, soft);
    }
    return evs;
  }
  pairEVs(v) {
    const [t, s] = pairTotal(v);
    return { ...this.actionEVs(t, s, true), P: this.split(v) };
  }
  chartCode(total, soft) {
    if (total >= 21) return "S";
    const s = this.stand(total),
      h = this.hit(total, soft),
      d = this.double(total, soft);
    if (d > Math.max(s, h)) return h >= s ? "Dh" : "Ds";
    return h > s ? "H" : "S";
  }
}

export const pairTotal = (v) => (v === ACE ? [12, true] : [2 * v, false]);

/** Solve the game for `rules`. Returns chart, EVs and house edge. */
export function solve(rules) {
  const tables = new Map(UPCARDS.map((u) => [u, new UpcardTables(rules, u)]));
  const chart = { hard: {}, soft: {}, pairs: {} };
  for (const u of UPCARDS) {
    const T = tables.get(u);
    for (let t = 4; t <= 21; t++) (chart.hard[t] ||= {})[u] = T.chartCode(t, false);
    for (let t = 12; t <= 21; t++) (chart.soft[t] ||= {})[u] = T.chartCode(t, true);
    for (const v of [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]) {
      const e = T.pairEVs(v);
      const best = Math.max(...Object.entries(e).filter(([a]) => a !== "P").map(([, x]) => x));
      (chart.pairs[v] ||= {})[u] = e.P > best;
    }
  }

  let edge = 0;
  for (const [up, pu] of CARD_PROBS) {
    const pbj = pDealerBJ(up);
    const T = tables.get(up);
    for (const [c1, p1] of CARD_PROBS)
      for (const [c2, p2] of CARD_PROBS) {
        const p = pu * p1 * p2;
        if ((c1 === ACE && c2 === TEN) || (c1 === TEN && c2 === ACE)) {
          edge += p * (1 - pbj) * rules.bjPayout;
          continue;
        }
        let play;
        if (c1 === c2) {
          const [t, s] = pairTotal(c1);
          play = Math.max(T.twoCard(t, s, true), T.split(c1));
        } else {
          const [t, s] = addCard(...addCard(0, false, c1), c2);
          play = T.twoCard(t, s, true);
        }
        edge += p * ((1 - pbj) * play - pbj);
      }
  }

  return {
    rules,
    chart,
    houseEdge: edge,
    tables,
    dealer: (up) => tables.get(up).dist,
    bustProb: (up) => tables.get(up).dist.get(BUST) || 0,
    /** Hit/stand policy arrays for simulations: hitHard[t], hitSoft[t]. */
    policy(up) {
      const T = tables.get(up);
      const hitHard = new Uint8Array(23),
        hitSoft = new Uint8Array(23);
      for (let t = 4; t < 21; t++) hitHard[t] = T.hit(t, false) > T.stand(t) ? 1 : 0;
      for (let t = 12; t < 21; t++) hitSoft[t] = T.hit(t, true) > T.stand(t) ? 1 : 0;
      const codeHard = new Uint8Array(23),
        codeSoft = new Uint8Array(23); // 0 hit, 1 stand, 2 double
      const enc = (c) => (c[0] === "D" ? 2 : c === "S" ? 1 : 0);
      for (let t = 4; t <= 21; t++) codeHard[t] = enc(chart.hard[t][up]);
      for (let t = 12; t <= 21; t++) codeSoft[t] = enc(chart.soft[t][up]);
      return { hitHard, hitSoft, codeHard, codeSoft };
    },
    /** EVs for a live decision (see Game.context()). */
    decisionEVs(ctx) {
      const T = tables.get(ctx.up);
      const evs = T.actionEVs(ctx.total, ctx.soft, ctx.canDouble);
      if (ctx.canSplit) evs.P = T.split(ctx.pairValue);
      return evs;
    },
  };
}

/** The basic-strategy action for a live decision. */
export function recommend(chart, ctx) {
  if (ctx.canSplit && chart.pairs[ctx.pairValue][ctx.up]) return "P";
  const code = (ctx.soft ? chart.soft : chart.hard)[ctx.total]?.[ctx.up] ?? (ctx.total >= 17 ? "S" : "H");
  if (code[0] === "D") return ctx.canDouble ? "D" : code === "Dh" ? "H" : "S";
  return code;
}
