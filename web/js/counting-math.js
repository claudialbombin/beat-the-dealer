// Betting-ramp maths on the per-true-count results of the C simulation.
// bins: [{tc, n, mean, m2, hist}] where mean/m2 are the first two moments of
// the round's profit per unit bet and hist counts outcomes −4.0 … +4.0 by 0.5.

export const RAMP_KEYS = [-1, 0, 1, 2, 3, 4, 5, 6, 7]; // -1 means "≤ −1", 7 means "≥ +7"
export const rampLabel = (k) => (k === -1 ? "≤−1" : k === 7 ? "≥+7" : k > 0 ? `+${k}` : "0");

const mk = (arr) => Object.fromEntries(RAMP_KEYS.map((k, i) => [k, arr[i]]));
export const PRESETS = {
  Flat: mk([1, 1, 1, 1, 1, 1, 1, 1, 1]),
  "1–4": mk([1, 1, 1, 2, 3, 4, 4, 4, 4]),
  "1–8": mk([1, 1, 1, 2, 4, 6, 8, 8, 8]),
  "1–12": mk([1, 1, 1, 2, 4, 8, 10, 12, 12]),
  "Wong out, 1–8": mk([0, 1, 1, 2, 4, 6, 8, 8, 8]),
};

export const betFor = (ramp, tc) => ramp[Math.max(-1, Math.min(7, tc))];

export function rampStats(bins, ramp) {
  const N = bins.reduce((a, b) => a + b.n, 0);
  let e = 0,
    e2 = 0,
    avg = 0,
    playing = 0;
  for (const b of bins) {
    const f = b.n / N,
      bet = betFor(ramp, b.tc);
    e += f * bet * b.mean;
    e2 += f * bet * bet * b.m2;
    avg += f * bet;
    if (bet > 0) playing += f;
  }
  const sd = Math.sqrt(Math.max(e2 - e * e, 0));
  return {
    ev: e, // units per round observed
    sd,
    avgBet: avg,
    edge: avg > 0 ? e / avg : 0, // per unit wagered
    playing, // fraction of rounds with a bet on the table
    n0: e > 0 ? (sd / e) ** 2 : Infinity,
    ror: (bankroll) => (e <= 0 ? 1 : Math.exp((-2 * e * bankroll) / (sd * sd))),
    bankrollFor: (ror) => (e <= 0 ? Infinity : (-Math.log(ror) * sd * sd) / (2 * e)),
  };
}

/** Weighted (1/variance) least-squares line of EV on true count, over the
 *  well-populated bins. Returns {slope, intercept}. */
export function fitLine(bins, lo = -5, hi = 6) {
  const pts = bins.filter((b) => b.tc >= lo && b.tc <= hi);
  let sw = 0,
    sx = 0,
    sy = 0,
    sxx = 0,
    sxy = 0;
  for (const b of pts) {
    const w = b.n / Math.max(b.m2 - b.mean ** 2, 1e-9);
    sw += w;
    sx += w * b.tc;
    sy += w * b.mean;
    sxx += w * b.tc * b.tc;
    sxy += w * b.tc * b.mean;
  }
  const slope = (sw * sxy - sx * sy) / (sw * sxx - sx * sx);
  return { slope, intercept: (sy - slope * sx) / sw };
}
export const fitSlope = (bins, lo, hi) => fitLine(bins, lo, hi).slope;

export function sfc32(a, b, c, d) {
  return function () {
    a |= 0; b |= 0; c |= 0; d |= 0;
    const t = (((a + b) | 0) + d) | 0;
    d = (d + 1) | 0;
    a = b ^ (b >>> 9);
    b = (c + (c << 3)) | 0;
    c = (c << 21) | (c >>> 11);
    c = (c + t) | 0;
    return (t >>> 0) / 4294967296;
  };
}

/**
 * Bootstrap bankroll paths: every round draws a (true count, outcome) pair
 * from the simulated distribution. Rounds are treated as independent, which
 * ignores how counts persist within a shoe; the diffusion risk-of-ruin
 * formula is shown alongside for comparison.
 */
export function simulatePaths(bins, outcomes, ramp, { players = 200, rounds = 20000, bankroll = 400, seed = 7, checkpoints = 200 } = {}) {
  const rng = sfc32(seed, 0x9e3779b9, 0x243f6a88, 0xb7e15162);
  const N = bins.reduce((a, b) => a + b.n, 0);
  const cumTc = [];
  let acc = 0;
  for (const b of bins) cumTc.push((acc += b.n / N));
  const cumOut = bins.map((b) => {
    const tot = b.hist.reduce((a, x) => a + x, 0);
    let c = 0;
    return b.hist.map((x) => (c += x / tot));
  });
  const pick = (cum, u) => {
    let lo = 0,
      hi = cum.length - 1;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (cum[mid] < u) lo = mid + 1;
      else hi = mid;
    }
    return lo;
  };
  const step = Math.max(1, Math.floor(rounds / checkpoints));
  const xs = [];
  for (let r = 0; r <= rounds; r += step) xs.push(r);
  const paths = [];
  let ruined = 0;
  for (let p = 0; p < players; p++) {
    let bank = bankroll;
    const trace = new Float32Array(xs.length);
    trace[0] = bank;
    let dead = false;
    for (let r = 1; r <= rounds; r++) {
      if (!dead) {
        const bi = pick(cumTc, rng());
        let bet = betFor(ramp, bins[bi].tc);
        if (bet > bank) bet = bank;
        if (bet > 0) bank += bet * outcomes[pick(cumOut[bi], rng())];
        if (bank <= 0) {
          bank = 0;
          dead = true;
          ruined++;
        }
      }
      if (r % step === 0) trace[r / step] = bank;
    }
    paths.push(trace);
  }
  const pctl = (q) =>
    xs.map((x, i) => {
      const col = paths.map((t) => t[i]).sort((a, b) => a - b);
      return col[Math.min(col.length - 1, Math.floor(q * col.length))];
    });
  const finals = paths.map((t) => t[t.length - 1]).sort((a, b) => a - b);
  return {
    xs,
    paths,
    ruined,
    p05: pctl(0.05),
    p25: pctl(0.25),
    p50: pctl(0.5),
    p75: pctl(0.75),
    p95: pctl(0.95),
    medianFinal: finals[Math.floor(finals.length / 2)],
    meanFinal: finals.reduce((a, b) => a + b, 0) / finals.length,
    ahead: finals.filter((f) => f > bankroll).length / finals.length,
  };
}
