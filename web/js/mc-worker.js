// Monte Carlo estimation of one decision's action EVs, run off the main thread.
// Same model as python/src/blackjack/solver.py: infinite deck, dealer peeks,
// after the first action the hand continues with the solved policy.

const VALUES = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11];

class Rng {
  // sfc32: small, fast, and its state can be copied for common random numbers
  constructor(seed) {
    this.a = 0x9e3779b9;
    this.b = 0x243f6a88;
    this.c = 0xb7e15162;
    this.d = seed | 0;
    for (let i = 0; i < 12; i++) this.next();
  }
  next() {
    let { a, b, c, d } = this;
    const t = (((a + b) | 0) + d) | 0;
    d = (d + 1) | 0;
    a = b ^ (b >>> 9);
    b = (c + (c << 3)) | 0;
    c = (c << 21) | (c >>> 11);
    c = (c + t) | 0;
    this.a = a; this.b = b; this.c = c; this.d = d;
    return (t >>> 0) / 4294967296;
  }
  card() {
    return VALUES[(this.next() * 13) | 0];
  }
  /** Deterministically re-seed from a 32-bit key (used for common random numbers). */
  reseed(key) {
    let x = key | 0;
    const mix = () => {
      x = (x + 0x9e3779b9) | 0;
      let z = x;
      z = Math.imul(z ^ (z >>> 16), 0x85ebca6b);
      z = Math.imul(z ^ (z >>> 13), 0xc2b2ae35);
      return (z ^ (z >>> 16)) | 0;
    };
    this.a = mix(); this.b = mix(); this.c = mix(); this.d = mix();
    for (let i = 0; i < 4; i++) this.next();
  }
}

let T = 0, S = false; // scratch hand state (total, soft)
function add(total, soft, v) {
  let hard = soft ? total - 10 : total;
  let ace = soft;
  if (v === 11) { hard += 1; ace = true; } else hard += v;
  if (ace && hard + 10 <= 21) { T = hard + 10; S = true; } else { T = hard; S = false; }
}

let job = null;
let running = false;

function dealerFinal(rng, up, h17) {
  let hole;
  for (;;) {
    hole = rng.card();
    if (!((up === 11 && hole === 10) || (up === 10 && hole === 11))) break; // peek: no blackjack
  }
  add(up === 11 ? 11 : up, up === 11, hole);
  let t = T, s = S;
  while (t < 17 || (t === 17 && s && h17)) {
    add(t, s, rng.card());
    t = T; s = S;
  }
  return t > 21 ? 22 : t;
}

const payoff = (p, d) => (p > 21 ? -1 : d > 21 || p > d ? 1 : p < d ? -1 : 0);

function playOut(t, s, rng, pol) {
  while (t < 21 && (s ? pol.hitSoft[t] : pol.hitHard[t])) {
    add(t, s, rng.card());
    t = T; s = S;
  }
  return t;
}

function playAction(a, st, rng, d, pol, rules) {
  const { total, soft } = st;
  if (a === "S") return payoff(total, d);
  if (a === "H") {
    add(total, soft, rng.card());
    return payoff(playOut(T, S, rng, pol), d);
  }
  if (a === "D") {
    add(total, soft, rng.card());
    return 2 * payoff(T, d);
  }
  // split
  const v = st.pairValue;
  let net = 0;
  for (let k = 0; k < 2; k++) {
    add(v === 11 ? 11 : v, v === 11, rng.card());
    let t = T, s = S;
    if (v === 11 || t >= 21) {
      net += payoff(t, d);
      continue;
    }
    let code = s ? pol.codeSoft[t] : pol.codeHard[t];
    if (code === 2 && !rules.das) code = (s ? pol.hitSoft[t] : pol.hitHard[t]) ? 0 : 1;
    if (code === 1) net += payoff(t, d);
    else if (code === 2) {
      add(t, s, rng.card());
      net += 2 * payoff(T, d);
    } else net += payoff(playOut(t, s, rng, pol), d);
  }
  return net;
}

function batch(size) {
  const { acts, st, pol, rules, crn } = job;
  const k = acts.length;
  const x = new Float64Array(k);
  for (let i = 0; i < size; i++) {
    if (crn) {
      const d = dealerFinal(job.dealerRng, st.up, rules.h17);
      // every action sees the same dealer hand and the same player cards
      const key = Math.imul(job.seed + 1, 0x01000193) ^ (job.n + i);
      for (let j = 0; j < k; j++) {
        job.work.reseed(key);
        x[j] = playAction(acts[j], st, job.work, d, pol, rules);
      }
    } else {
      for (let j = 0; j < k; j++) {
        const d = dealerFinal(job.indep[j], st.up, rules.h17);
        x[j] = playAction(acts[j], st, job.indep[j], d, pol, rules);
      }
    }
    for (let j = 0; j < k; j++) {
      job.sum[j] += x[j];
      job.sq[j] += x[j] * x[j];
      for (let l = j + 1; l < k; l++) {
        const df = x[j] - x[l];
        job.dsum[j * k + l] += df;
        job.dsq[j * k + l] += df * df;
      }
    }
  }
  job.n += size;
}

function loop() {
  if (!running || !job) return;
  // Pace the first few decades so the convergence is visible (one decade
  // per ~0.9 s), then run flat out.
  const t0 = performance.now();
  const target = Math.min(job.max, 100 * 10 ** ((t0 - job.started) / 900));
  while (performance.now() - t0 < 50 && job.n < target) batch(Math.max(50, Math.min(20000, Math.ceil((target - job.n) / 4))));
  postMessage({
    type: "progress",
    id: job.id,
    n: job.n,
    sum: Array.from(job.sum),
    sq: Array.from(job.sq),
    dsum: Array.from(job.dsum),
    dsq: Array.from(job.dsq),
    rate: job.n / ((performance.now() - job.started) / 1000),
  });
  if (job.n >= job.max) {
    running = false;
    postMessage({ type: "done", id: job.id });
    return;
  }
  setTimeout(loop, job.n < 1e6 ? 30 : 0);
}

globalThis.onmessage = (e) => {
  const m = e.data;
  if (m.type === "start") {
    const k = m.acts.length;
    job = {
      ...m,
      n: 0,
      max: m.max || 20_000_000,
      sum: new Float64Array(k),
      sq: new Float64Array(k),
      dsum: new Float64Array(k * k),
      dsq: new Float64Array(k * k),
      dealerRng: new Rng(m.seed * 7 + 1),
      work: new Rng(0),
      indep: m.acts.map((_, j) => new Rng(m.seed * 7 + 3 + j * 101)),
      started: performance.now(),
    };
    running = true;
    loop();
  } else if (m.type === "pause") running = false;
  else if (m.type === "resume" && job) {
    running = true;
    job.started = performance.now() - (job.n / Math.max(1, m.rate || 1)) * 1000;
    loop();
  }
};
