// Card counting: EV by true count, betting-ramp designer, bankroll paths and a
// speed-count drill. All numbers come from web/data/counting.json (C simulator).

import { hiLo, RANK_VALUE } from "../engine.js";
import { Plot, responsive } from "../charts.js";
import { RAMP_KEYS, rampLabel, PRESETS, rampStats, fitLine, simulatePaths } from "../counting-math.js";
import { $, $$, h, cardEl, pct, pctAbs, signed, int, compact } from "../ui.js";

let app, bins, ramp, bankroll = 400;
let pathsResult = null;
const TC_SHOW = [-6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8];
const tcLabel = (t) => (t > 0 ? `+${t}` : String(t));

function intro() {
  const c = app.counting;
  const fit = fitLine(bins);
  const crossing = -fit.intercept / fit.slope;
  const pos = bins.filter((b) => b.tc >= 1).reduce((a, b) => a + b.n, 0) / c.rounds;
  $("#count-intro").textContent =
    `${(c.rounds / 1e9).toFixed(0)} billion simulated rounds of a 6-deck shoe dealt to 75%, dealer hits soft 17, played with perfect basic strategy. ` +
    `Flat betting loses ${pctAbs(-c.overall.mean)} of every bet. The count does predict the next hand: each +1 of true count is worth about ${pct(fit.slope, 2)}, ` +
    `and the player has the edge from a true count of about +${crossing.toFixed(1)}. The catch: only ${Math.round(100 * pos)}% of rounds are dealt at +1 or better, ` +
    `so the edge comes entirely from betting more in those rounds, and in this game it is thin.`;
}

function drawEV() {
  const el = $("#ev-tc-chart");
  const pts = TC_SHOW.map((t) => bins.find((b) => b.tc === t))
    .filter(Boolean)
    .map((b) => {
      const se = Math.sqrt((b.m2 - b.mean ** 2) / b.n);
      return { x: tcLabel(b.tc), tc: b.tc, y: b.mean, lo: b.mean - 1.96 * se, hi: b.mean + 1.96 * se, n: b.n };
    });
  const fit = fitLine(bins);
  const plot = new Plot(el, {
    x: { type: "band", domain: TC_SHOW.map(tcLabel), label: "True count when the bet is placed" },
    y: { domain: [Math.min(...pts.map((p) => p.lo)) - 0.004, Math.max(...pts.map((p) => p.hi)) + 0.006], format: (v) => `${(v * 100).toFixed(0)}%`, label: "Player edge" },
    margin: { left: 50 },
  });
  plot.hline(0, { color: "var(--ink-2)", dash: null, width: 1 });
  // fitted line, drawn over the fitted range
  const fx = (t) => ({ x: tcLabel(t), y: fit.intercept + fit.slope * t });
  const segs = [];
  for (let t = -5; t <= 6; t++) segs.push(fx(t));
  plot.line(segs, { color: "var(--a-S)", width: 1.5, dash: "5 4", opacity: 0.8 });
  plot.errorPoints(pts, { color: "var(--ink)" });
  plot.text(tcLabel(-6), plot.y.domain[1], `dashed: fitted line, ${pct(fit.slope, 2)} per true count`, { color: "var(--a-S)", dy: 12 });
  plot.hover((x) => {
    const p = pts.find((q) => q.x === x);
    return (
      p && {
        x: p.x,
        html: `<b>True count ${p.x}</b><div class="tt-row"><span>Player edge</span><span>${pct(p.y, 2)}</span></div><div class="tt-row"><span>95% CI</span><span>${pct(p.lo, 2)} … ${pct(p.hi, 2)}</span></div><div class="tt-row"><span>Rounds</span><span>${compact(p.n)}</span></div>`,
      }
    );
  });
}

function drawFreq() {
  const el = $("#ev-tc-freq");
  const N = app.counting.rounds;
  const pts = TC_SHOW.map((t) => bins.find((b) => b.tc === t))
    .filter(Boolean)
    .map((b) => ({ x: tcLabel(b.tc), y: b.n / N, tc: b.tc }));
  const plot = new Plot(el, {
    x: { type: "band", domain: TC_SHOW.map(tcLabel) },
    y: { domain: [0, 0.3], format: (v) => `${Math.round(v * 100)}%`, ticks: [0, 0.1, 0.2, 0.3], label: "Share of rounds" },
    margin: { left: 50, bottom: 24 },
  });
  plot.bars(pts, { colorFn: (p) => (p.tc >= 1 ? "var(--a-D)" : "var(--line-2)") });
  plot.hover((x) => {
    const p = pts.find((q) => q.x === x);
    return p && { x: p.x, html: `<b>True count ${p.x}</b>: ${(100 * p.y).toFixed(1)}% of rounds` };
  });
}

// ---------------------------------------------------------------- ramp editor
function renderRamp() {
  const box = $("#ramp");
  box.replaceChildren(
    ...RAMP_KEYS.map((k) => {
      const bar = h("div", { class: `bar${ramp[k] === 0 ? " zero" : ""}`, style: `height:${Math.max(2, (ramp[k] / 16) * 100)}%` });
      const wrap = h("div", { class: "bar-wrap", role: "slider", tabindex: "0", "aria-label": `Bet at true count ${rampLabel(k)}`, "aria-valuemin": "0", "aria-valuemax": "16", "aria-valuenow": String(ramp[k]) }, bar);
      const set = (v) => {
        ramp = { ...ramp, [k]: Math.max(0, Math.min(16, v)) };
        markPreset();
        renderRamp();
        renderResults();
      };
      const fromPointer = (e) => {
        const r = wrap.getBoundingClientRect();
        set(Math.round(((r.bottom - e.clientY) / r.height) * 16));
      };
      wrap.addEventListener("pointerdown", (e) => {
        wrap.setPointerCapture(e.pointerId);
        fromPointer(e);
        const mv = (ev) => fromPointer(ev);
        wrap.addEventListener("pointermove", mv);
        wrap.addEventListener("pointerup", () => wrap.removeEventListener("pointermove", mv), { once: true });
      });
      wrap.addEventListener("keydown", (e) => {
        if (e.key === "ArrowUp" || e.key === "ArrowRight") (e.preventDefault(), set(ramp[k] + 1));
        if (e.key === "ArrowDown" || e.key === "ArrowLeft") (e.preventDefault(), set(ramp[k] - 1));
      });
      return h(
        "div",
        { class: "ramp-col" },
        h("span", { class: "tc" }, rampLabel(k)),
        wrap,
        h("output", {}, String(ramp[k])),
      );
    }),
  );
}

function markPreset() {
  for (const b of $$("#ramp-presets button")) b.classList.toggle("on", JSON.stringify(PRESETS[b.dataset.p]) === JSON.stringify(ramp));
}

function renderResults() {
  const r = rampStats(bins, ramp);
  const tiles = [
    ["Edge per unit wagered", pct(r.edge, 2), r.edge > 0 ? "pos" : "neg"],
    ["Win per 100 rounds", `${signed(100 * r.ev, 2)}u`, r.ev > 0 ? "pos" : "neg"],
    ["SD per round", `${r.sd.toFixed(2)}u`, ""],
    ["Average bet", `${r.avgBet.toFixed(2)}u`, ""],
    ["Rounds to beat 1 SD (N0)", Number.isFinite(r.n0) ? compact(r.n0) : "never", ""],
    ["Rounds with a bet", `${Math.round(100 * r.playing)}%`, ""],
  ];
  $("#ramp-results").replaceChildren(
    ...tiles.map(([k, v, cls]) => h("div", {}, h("span", { class: "k" }, k), h("span", { class: `v ${cls}` }, v))),
  );
  $("#bankroll-out").textContent = `${bankroll} units`;
  const ror = r.ror(bankroll);
  const need = r.bankrollFor(0.05);
  $("#ror").innerHTML =
    r.ev <= 0
      ? `With a negative expectation the risk of ruin is <b>100%</b> in the long run: no bankroll is big enough.`
      : `Risk of ever going broke with ${bankroll} units, playing indefinitely: <b>${(100 * ror).toFixed(ror < 0.01 ? 2 : 1)}%</b>. For 5% risk you need about <b>${int(need)} units</b> (diffusion approximation, e<sup>−2μB/σ²</sup>).`;
}

// ---------------------------------------------------------------- bankroll paths
function runPaths() {
  const btn = $("#paths-run");
  btn.disabled = true;
  btn.textContent = "Simulating…";
  setTimeout(() => {
    pathsResult = simulatePaths(bins, app.counting.outcomes, ramp, { players: 200, rounds: 20000, bankroll, seed: Math.floor(Math.random() * 1e9) });
    pathsResult.bankroll = bankroll;
    btn.disabled = false;
    btn.textContent = "Run again";
    drawPaths();
  }, 20);
}

function drawPaths() {
  const el = $("#paths-chart");
  if (!pathsResult) {
    el.replaceChildren(h("p", { class: "muted", style: "padding:40px 0;text-align:center" }, "Set a ramp and bankroll above, then run the simulation."));
    $("#paths-summary").replaceChildren();
    return;
  }
  const R = pathsResult;
  const hi = Math.max(R.bankroll * 2, ...R.p95) * 1.05;
  const plot = new Plot(el, {
    x: { domain: [0, R.xs[R.xs.length - 1]], format: compact, label: "Rounds played" },
    y: { domain: [0, hi], format: (v) => compact(v), label: "Bankroll (units)" },
    margin: { left: 58 },
  });
  const P = (arr) => R.xs.map((x, i) => ({ x, y: arr[i] }));
  const band = (a, b) => R.xs.map((x, i) => ({ x, lo: a[i], hi: b[i] }));
  for (let k = 0; k < 14; k++) plot.line(R.xs.map((x, i) => ({ x, y: R.paths[k][i] })), { color: "var(--ink-2)", width: 1, opacity: 0.25 });
  plot.band(band(R.p05, R.p95), { color: "var(--a-S)", opacity: 0.12 });
  plot.band(band(R.p25, R.p75), { color: "var(--a-S)", opacity: 0.22 });
  plot.line(P(R.p50), { color: "var(--a-S)", width: 2.5 });
  plot.hline(R.bankroll, { color: "var(--ink-2)", label: "starting bankroll" });
  plot.hover((xv) => {
    let i = Math.round((xv / R.xs[R.xs.length - 1]) * (R.xs.length - 1));
    i = Math.max(0, Math.min(R.xs.length - 1, i));
    return {
      x: R.xs[i],
      html: `<b>After ${int(R.xs[i])} rounds</b><div class="tt-row"><span>95th pct</span><span>${int(R.p95[i])}</span></div><div class="tt-row"><span>75th</span><span>${int(R.p75[i])}</span></div><div class="tt-row"><span>Median</span><span>${int(R.p50[i])}</span></div><div class="tt-row"><span>25th</span><span>${int(R.p25[i])}</span></div><div class="tt-row"><span>5th</span><span>${int(R.p05[i])}</span></div>`,
    };
  });
  $("#paths-summary").replaceChildren(
    ...[
      ["Ruined", `${Math.round((100 * R.ruined) / R.paths.length)}%`],
      ["Ahead after 20k rounds", `${Math.round(100 * R.ahead)}%`],
      ["Median final bankroll", `${int(R.medianFinal)}u`],
      ["Mean final bankroll", `${int(R.meanFinal)}u`],
    ].map(([k, v]) => h("div", {}, h("span", { class: "k" }, k), h("span", { class: "v" }, v))),
  );
}

// ---------------------------------------------------------------- speed drill
let speedTimer = 0;
function speedDrill() {
  clearTimeout(speedTimer);
  const n = +$("#speed-n").value,
    ms = +$("#speed-ms").value;
  const stage = $("#speed-stage");
  const cards = Array.from({ length: n }, () => ({ r: Math.floor(Math.random() * 13), s: Math.floor(Math.random() * 4) }));
  const count = cards.reduce((a, c) => a + hiLo(RANK_VALUE[c.r]), 0);
  let i = 0;
  const step = () => {
    if (i < cards.length) {
      stage.replaceChildren(h("div", {}, cardEl(cards[i]), h("p", { class: "fine", style: "margin-top:8px" }, `${i + 1} / ${n}`)));
      i++;
      speedTimer = setTimeout(step, ms);
    } else {
      const input = h("input", { type: "number", inputmode: "numeric", "aria-label": "Your running count" });
      const out = h("p", { class: "quiz-result", "aria-live": "polite" });
      const check = () => {
        const g = parseInt(input.value, 10);
        const ok = g === count;
        out.textContent = ok ? `Correct: ${count}.` : `The count was ${count > 0 ? "+" : ""}${count}. ${cards.map((c) => ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"][c.r]).join(" ")}`;
        out.style.color = ok ? "var(--good)" : "var(--bad)";
      };
      input.addEventListener("keydown", (e) => e.key === "Enter" && check());
      stage.replaceChildren(h("div", {}, h("p", {}, "What's the running count?"), h("div", { class: "speed-answer" }, input, h("button", { class: "primary", onclick: check }, "Check")), out));
      input.focus();
    }
  };
  step();
}

export function init(a) {
  app = a;
  bins = app.counting.bins;
  ramp = { ...PRESETS["1–8"] };
  intro();
  $("#ramp-presets").replaceChildren(
    ...Object.keys(PRESETS).map((name) =>
      h("button", { "data-p": name, onclick: () => ((ramp = { ...PRESETS[name] }), markPreset(), renderRamp(), renderResults()) }, name),
    ),
  );
  markPreset();
  renderRamp();
  renderResults();
  $("#bankroll").addEventListener("input", (e) => {
    bankroll = +e.target.value;
    renderResults();
  });
  $("#paths-run").addEventListener("click", runPaths);
  $("#speed-go").addEventListener("click", speedDrill);
  const drawAll = () => {
    drawEV();
    drawFreq();
    drawPaths();
  };
  drawAll();
  responsive($("#ev-tc-chart"), drawAll);
}

export function show() {
  drawEV();
  drawFreq();
  drawPaths();
}
