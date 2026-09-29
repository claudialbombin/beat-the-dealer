// Live Monte Carlo lab: estimate one decision's action EVs in a Web Worker and
// watch the estimates converge on the exact values.

import { DEFAULT_RULES, upcardLabel } from "../engine.js";
import { solve, UPCARDS, pairTotal } from "../exact.js";
import { Plot, responsive } from "../charts.js";
import { $, h, ACTION_NAMES, ACTION_ORDER, actionColor, describeState, pct, compact, int } from "../ui.js";

let app, worker;
let state = { kind: "hard", total: 16, up: 10 };
let rules = { ...DEFAULT_RULES };
let sol;
let acts = [];
let exact = {};
let traces = {};
let last = null;
let running = false;
let nextRecord = 100;
let crn = true;
let jobId = 0;

const VALUES = { hard: [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20], soft: [13, 14, 15, 16, 17, 18, 19, 20], pair: [2, 3, 4, 5, 6, 7, 8, 9, 10, 11] };
const valueLabel = (kind, v) => (kind === "hard" ? String(v) : kind === "soft" ? `A,${v - 11} (soft ${v})` : v === 11 ? "A,A" : `${v},${v}`);

function fillSelects() {
  $("#lab-kind").value = state.kind;
  $("#lab-total").replaceChildren(...VALUES[state.kind].map((v) => h("option", { value: v }, valueLabel(state.kind, v))));
  $("#lab-total").value = state.total;
  $("#lab-up").replaceChildren(...UPCARDS.map((u) => h("option", { value: u }, upcardLabel(u))));
  $("#lab-up").value = state.up;
}

function context() {
  if (state.kind === "pair") {
    const [t, s] = pairTotal(state.total);
    return { total: t, soft: s, up: state.up, pairValue: state.total };
  }
  return { total: state.total, soft: state.kind === "soft", up: state.up, pairValue: null };
}

function setup() {
  stop();
  sol = JSON.stringify(rules) === JSON.stringify(DEFAULT_RULES) ? app.exact : solve(rules);
  const ctx = context();
  const T = sol.tables.get(state.up);
  exact = state.kind === "pair" ? T.pairEVs(state.total) : T.actionEVs(ctx.total, ctx.soft, true);
  acts = ACTION_ORDER.filter((a) => exact[a] != null);
  traces = Object.fromEntries(acts.map((a) => [a, []]));
  last = null;
  nextRecord = 100;
  $("#lab-title").textContent = describeState(state.kind, state.total, state.up);
  $("#lab-run").textContent = "Run";
  renderTable();
  draw();
}

function start() {
  if (!worker) {
    worker = new Worker(new URL("../mc-worker.js", import.meta.url), { type: "module" });
    worker.onmessage = onMessage;
  }
  if (last && !running) {
    running = true;
    worker.postMessage({ type: "resume", rate: last.rate });
  } else {
    const ctx = context();
    const p = sol.policy(state.up);
    running = true;
    jobId++;
    worker.postMessage({
      type: "start",
      id: jobId,
      acts,
      st: { total: ctx.total, soft: ctx.soft, up: state.up, pairValue: ctx.pairValue },
      pol: { hitHard: Array.from(p.hitHard), hitSoft: Array.from(p.hitSoft), codeHard: Array.from(p.codeHard), codeSoft: Array.from(p.codeSoft) },
      rules,
      crn,
      seed: Math.floor(Math.random() * 1e9),
    });
  }
  $("#lab-run").textContent = "Pause";
}

function stop() {
  if (worker && running) worker.postMessage({ type: "pause" });
  running = false;
  $("#lab-run").textContent = last ? "Resume" : "Run";
}

function stats(j) {
  const n = last.n;
  const mean = last.sum[j] / n;
  const v = last.sq[j] / n - mean * mean;
  return { mean, se: Math.sqrt(Math.max(v, 0) / n), sd: Math.sqrt(Math.max(v, 0)) };
}
function diffStats(i, j) {
  // difference acts[i] - acts[j]
  const k = acts.length;
  const [a, b, sign] = i < j ? [i, j, 1] : [j, i, -1];
  const n = last.n;
  const mean = (sign * last.dsum[a * k + b]) / n;
  const v = last.dsq[a * k + b] / n - mean * mean;
  return { mean, se: Math.sqrt(Math.max(v, 0) / n), sd: Math.sqrt(Math.max(v, 0)) };
}

function onMessage(e) {
  const m = e.data;
  if (m.id !== jobId) return; // a message from a job that was reset
  if (m.type === "done") {
    running = false;
    $("#lab-run").textContent = "Done";
    return;
  }
  last = m;
  if (m.n >= nextRecord || !running) {
    acts.forEach((a, j) => {
      const s = stats(j);
      traces[a].push({ x: m.n, y: s.mean, lo: s.mean - 1.96 * s.se, hi: s.mean + 1.96 * s.se });
    });
    while (nextRecord <= m.n) nextRecord *= 1.12;
  }
  renderTable();
  draw();
}

function renderTable() {
  const rows = acts.map((a, j) => {
    const s = last ? stats(j) : null;
    const z = s && s.se > 0 ? (s.mean - exact[a]) / s.se : null;
    return h(
      "tr",
      {},
      h("td", {}, h("span", { class: "sw", style: `display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;background:${actionColor(a)}` }), ACTION_NAMES[a]),
      h("td", {}, s ? `${pct(s.mean, 2)} ± ${(196 * s.se).toFixed(2)}` : "–"),
      h("td", {}, pct(exact[a], 2)),
      h("td", { title: "estimate minus exact, in standard errors" }, z == null ? "–" : z.toFixed(1)),
    );
  });
  $("#lab-table").replaceChildren(
    h("table", { class: "data" }, h("tr", {}, h("th", {}, "Action"), h("th", {}, "Estimate (95%)"), h("th", {}, "Exact"), h("th", {}, "z")), ...rows),
  );

  const v = $("#lab-verdict");
  const bestExact = acts.reduce((b, a) => (exact[a] > exact[b] ? a : b), acts[0]);
  if (!last) {
    v.replaceChildren(h("p", { class: "muted" }, `Exact answer: ${ACTION_NAMES[bestExact]}. Press Run and see how many hands Monte Carlo needs to find it.`));
    return;
  }
  const means = acts.map((a, j) => stats(j).mean);
  const lead = means.indexOf(Math.max(...means));
  const others = acts.map((_, j) => j).filter((j) => j !== lead);
  const runner = others.reduce((b, j) => (means[j] > means[b] ? j : b), others[0]);
  const d = diffStats(lead, runner);
  const conf = d.se > 0 ? normCdf(d.mean / d.se) : 1;
  // hands needed to separate the exact best from the exact runner-up at 95%
  const ib = acts.indexOf(bestExact);
  const exactRunner = acts.filter((a) => a !== bestExact).reduce((b, a) => (exact[a] > exact[b] ? a : b));
  const ir = acts.indexOf(exactRunner);
  const dd = diffStats(ib, ir);
  const gap = exact[bestExact] - exact[exactRunner];
  const need = gap > 0 ? (1.96 * dd.sd / gap) ** 2 : Infinity;
  v.replaceChildren(
    h("span", { class: "k" }, "Hands simulated"),
    h("span", { class: "big" }, int(last.n)),
    h("p", { class: "fine" }, last.n < 1e6 ? "Paced for the first million hands so you can watch it converge" : `${compact(last.rate)} hands/s in your browser`),
    h(
      "p",
      {},
      `Leading: `,
      h("b", {}, ACTION_NAMES[acts[lead]]),
      ` by ${(100 * d.mean).toFixed(2)}% ± ${(196 * d.se).toFixed(2)}% over ${ACTION_NAMES[acts[runner]]}. `,
      `Confidence it is truly ahead: `,
      h("b", {}, `${(100 * conf).toFixed(conf > 0.999 ? 2 : 1)}%`),
      acts[lead] === bestExact ? " (it is the exact optimum)." : " (the exact optimum is " + ACTION_NAMES[bestExact] + ").",
    ),
    h(
      "p",
      { class: "fine" },
      `With ${crn ? "common random numbers" : "independent samples"}, separating ${ACTION_NAMES[bestExact]} from ${ACTION_NAMES[exactRunner]} (true gap ${(100 * gap).toFixed(2)}%) at 95% takes about `,
      h("b", {}, Number.isFinite(need) ? compact(need) : "∞"),
      " hands per action.",
    ),
  );
}

function normCdf(z) {
  // Abramowitz-Stegun 26.2.17
  const t = 1 / (1 + 0.2316419 * Math.abs(z));
  const d = 0.3989423 * Math.exp((-z * z) / 2);
  const p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))));
  return z > 0 ? 1 - p : p;
}

function draw() {
  const el = $("#lab-chart");
  const ex = acts.map((a) => exact[a]);
  const lo = Math.max(-2.05, Math.min(...ex) - 0.3);
  const hi = Math.min(2.05, Math.max(...ex) + 0.3);
  const maxN = Math.max(1e5, last ? last.n * 1.5 : 0);
  const plot = new Plot(el, {
    x: { type: "log", domain: [100, 10 ** Math.ceil(Math.log10(maxN))], format: compact, label: "Hands simulated per action (log scale)" },
    y: { domain: [lo, hi], format: (v) => `${Math.round(v * 100)}%`, label: "Expected profit per unit bet" },
    margin: { left: 58, right: 70 },
  });
  plot.hline(0, { color: "var(--line-2)", dash: null, width: 1 });
  for (const a of acts) {
    const tr = traces[a];
    plot.band(tr.map((p) => ({ x: p.x, lo: Math.max(lo, p.lo), hi: Math.min(hi, p.hi) })), { color: actionColor(a), opacity: 0.14 });
    plot.hline(exact[a], { color: actionColor(a), dash: "5 4", width: 1.25, opacity: 0.9 });
    plot.line(tr, { color: actionColor(a), width: 2 });
  }
  // Direct labels at the right edge, nudged apart so close values stay legible.
  const labels = acts.map((a) => ({ a, y: plot.sy(exact[a]) })).sort((p, q) => p.y - q.y);
  for (let i = 1; i < labels.length; i++) labels[i].y = Math.max(labels[i].y, labels[i - 1].y + 14);
  for (const l of labels) {
    const t = document.createElementNS("http://www.w3.org/2000/svg", "text");
    t.setAttribute("x", plot.iw + 6);
    t.setAttribute("y", Math.min(plot.ih, l.y) + 4);
    t.setAttribute("fill", actionColor(l.a));
    t.setAttribute("font-size", "11");
    t.textContent = `${ACTION_NAMES[l.a]} ${pct(exact[l.a], 1)}`;
    plot.topG.append(t);
  }
  if (!acts.length || !traces[acts[0]].length) plot.text(Math.sqrt(plot.x.domain[0] * plot.x.domain[1]), (lo + hi) / 2, "Press Run", { anchor: "middle", size: 13 });
  plot.hover((xv) => {
    const tr0 = traces[acts[0]];
    if (!tr0.length) return null;
    let i = 0;
    while (i < tr0.length - 1 && Math.abs(Math.log(tr0[i + 1].x / xv)) < Math.abs(Math.log(tr0[i].x / xv))) i++;
    const rows = acts
      .map((a) => {
        const p = traces[a][i];
        return `<div class="tt-row"><span><span class="sw" style="background:${actionColor(a)}"></span>${ACTION_NAMES[a]}</span><span>${pct(p.y, 2)} ± ${(50 * (p.hi - p.lo)).toFixed(2)}</span></div>`;
      })
      .join("");
    return { x: tr0[i].x, html: `<b>${int(tr0[i].x)} hands</b>${rows}` };
  });
}

function loadRequest() {
  if (!app.labRequest) return;
  const r = app.labRequest;
  app.labRequest = null;
  state = { kind: r.kind, total: r.total, up: r.up };
  rules = r.rules || { ...DEFAULT_RULES };
  fillSelects();
  setup();
  start();
}

export function init(a) {
  app = a;
  fillSelects();
  $("#lab-kind").addEventListener("change", (e) => {
    state.kind = e.target.value;
    state.total = { hard: 16, soft: 18, pair: 8 }[state.kind];
    fillSelects();
    setup();
  });
  $("#lab-total").addEventListener("change", (e) => ((state.total = +e.target.value), setup()));
  $("#lab-up").addEventListener("change", (e) => ((state.up = +e.target.value), setup()));
  $("#lab-crn").addEventListener("change", (e) => {
    crn = e.target.checked;
    setup();
  });
  $("#lab-run").addEventListener("click", () => {
    if (running) stop();
    else if ($("#lab-run").textContent !== "Done") start();
  });
  $("#lab-reset").addEventListener("click", setup);
  app.bus.addEventListener("lab-request", loadRequest);
  setup();
  responsive($("#lab-chart"), draw);
  loadRequest();
}

export function show() {
  draw();
}
