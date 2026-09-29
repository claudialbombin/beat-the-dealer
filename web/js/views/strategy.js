// Interactive strategy chart: exact EVs per cell, Monte Carlo estimates with
// confidence intervals, and live re-solving when the rules change.

import { DEFAULT_RULES, upcardLabel } from "../engine.js";
import { solve, UPCARDS, pairTotal } from "../exact.js";
import { Plot, responsive } from "../charts.js";
import { $, $$, h, evBars, rulesControls, ACTION_NAMES, ACTION_ORDER, describeState, showTip, hideTip, pct, pctAbs } from "../ui.js";

let app, sol, rules;
let mode = "action";
let selected = null;

const ROWS = {
  hard: [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
  soft: [13, 14, 15, 16, 17, 18, 19, 20],
  pair: [2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
};
const rowLabel = (kind, r) => (kind === "hard" ? String(r) : kind === "soft" ? `A,${r - 11}` : r === 11 ? "A,A" : r === 10 ? "T,T" : `${r},${r}`);
const isDefault = () => JSON.stringify(rules) === JSON.stringify(DEFAULT_RULES);

function cellEVs(s, kind, total, up) {
  const T = s.tables.get(up);
  if (kind === "pair") return T.pairEVs(total);
  return T.actionEVs(total, kind === "soft", true);
}

function cellCode(s, kind, total, up) {
  if (kind === "pair") return s.chart.pairs[total][up] ? "P" : "-";
  return s.chart[kind][total][up];
}

function margin(evs, kind) {
  if (kind === "pair") {
    const non = Math.max(...Object.entries(evs).filter(([a]) => a !== "P").map(([, v]) => v));
    return Math.abs(evs.P - non);
  }
  const v = Object.values(evs).sort((a, b) => b - a);
  return v[0] - v[1];
}

// Sequential blue ramp for "how close is the call": darker = closer.
const RAMP = ["#104281", "#1c5cab", "#2a78d6", "#5598e7", "#86b6ef", "#b7d3f6", "#cde2fb"];
const RAMP_EDGES = [0.0025, 0.005, 0.01, 0.02, 0.05, 0.1];
function marginColor(m) {
  let i = RAMP_EDGES.findIndex((e) => m < e);
  if (i < 0) i = RAMP.length - 1;
  return { bg: RAMP[i], fg: i <= 3 ? "#fff" : "#10233f" };
}

function mcFor(kind, total, up) {
  return isDefault() ? app.mc.get(`${kind}:${total}:${up}`) : null;
}

function tooltipHTML(kind, total, up) {
  const evs = cellEVs(sol, kind, total, up);
  const mc = mcFor(kind, total, up);
  const code = cellCode(sol, kind, total, up);
  const rows = ACTION_ORDER.filter((a) => evs[a] != null)
    .map((a) => {
      const m = mc?.mc[a];
      const mcTxt = m ? ` <span style="opacity:.7">MC ${pct(m[0], 2)} ±${(196 * m[1]).toFixed(2)}</span>` : "";
      return `<div class="tt-row"><span><span class="sw" style="background:var(--a-${a})"></span>${ACTION_NAMES[a]}</span><span>${pct(evs[a], 2)}${mcTxt}</span></div>`;
    })
    .join("");
  const best = code === "-" ? "Don't split" : code === "P" ? "Split" : code.startsWith("D") ? `Double (else ${code === "Dh" ? "hit" : "stand"})` : ACTION_NAMES[code];
  return `<b>${describeState(kind, total, up)}</b><br>Play: <b>${best}</b> · margin ${(100 * margin(evs, kind)).toFixed(2)}%<div style="margin-top:4px">${rows}</div>`;
}

function grid(kind, title) {
  const table = h("table", { class: "sgrid", "aria-label": title });
  table.append(h("tr", {}, h("th", { class: "row" }, ""), ...UPCARDS.map((u) => h("th", { scope: "col" }, upcardLabel(u)))));
  for (const r of ROWS[kind]) {
    const tr = h("tr", {}, h("th", { class: "row", scope: "row" }, rowLabel(kind, r)));
    for (const u of UPCARDS) {
      const code = cellCode(sol, kind, r, u);
      const base = cellCode(app.exact, kind, r, u);
      const evs = cellEVs(sol, kind, r, u);
      const letter = code === "-" ? "·" : code === "Dh" ? "D" : code;
      const cls = code === "-" ? "a--" : `a-${code[0]}`;
      const td = h("td", { tabindex: "0", "aria-label": `${describeState(kind, r, u)}: ${letter}` }, letter);
      if (mode === "margin") {
        const c = marginColor(margin(evs, kind));
        td.style.background = c.bg;
        td.style.color = c.fg;
      } else td.className = cls;
      if (code !== base) td.classList.add("changed");
      if (selected && selected.kind === kind && selected.total === r && selected.up === u) td.classList.add("sel");
      td.addEventListener("pointerenter", (e) => showTip(tooltipHTML(kind, r, u), e.clientX, e.clientY));
      td.addEventListener("pointermove", (e) => showTip(tooltipHTML(kind, r, u), e.clientX, e.clientY));
      td.addEventListener("pointerleave", hideTip);
      const pick = () => {
        selected = { kind, total: r, up: u };
        renderGrids();
        renderDetail();
      };
      td.addEventListener("click", pick);
      td.addEventListener("keydown", (e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), pick()));
      tr.append(td);
    }
    table.append(tr);
  }
  return h("div", { class: "grid-block" }, h("h4", {}, title), table);
}

function renderGrids() {
  $("#grids").replaceChildren(grid("hard", "Hard totals"), grid("soft", "Soft totals"), grid("pair", "Pairs"));
  const legend = $("#chart-legend");
  if (mode === "action")
    legend.innerHTML = ["H Hit", "S Stand", "D Double (else hit)", "Ds Double (else stand)", "P Split", "· Don't split"]
      .map((t) => {
        const a = t[0] === "·" ? "-" : t[0];
        return `<span><span class="sw" style="background:${a === "-" ? "var(--surface-2);border:1px solid var(--line-2)" : `var(--a-${a})`}"></span>${t}</span>`;
      })
      .join("") + `<span><span class="sw" style="border:2px dashed var(--ink)"></span>changed by your rules</span>`;
  else legend.innerHTML = `<span>closest call<span class="ramp-sw" style="background:linear-gradient(90deg,${RAMP.join(",")})"></span>clear-cut (≥10% of a bet)</span>`;
}

function renderEdge() {
  const edge = -sol.houseEdge;
  const d = sol.houseEdge - app.exact.houseEdge;
  $("#edge-tile").replaceChildren(
    h("div", { class: "k" }, "House edge with perfect play"),
    h("div", { class: "big" }, pctAbs(edge, 2)),
    h("div", { class: "delta" }, isDefault() ? `exact, infinite deck · the real 6-deck shoe simulates at ${pctAbs(-app.counting.overall.mean, 2)}` : `${Math.abs(100 * d).toFixed(2)} points ${d > 0 ? "lower" : "higher"} than the default table`),
  );
}

function renderDetail() {
  const box = $("#cell-detail");
  if (!selected) return;
  const { kind, total, up } = selected;
  const evs = cellEVs(sol, kind, total, up);
  const mc = mcFor(kind, total, up);
  const code = cellCode(sol, kind, total, up);
  const bestA = code === "-" ? Object.entries(evs).filter(([a]) => a !== "P").sort((a, b) => b[1] - a[1])[0][0] : code[0];
  const m = margin(evs, kind);
  const ci = mc ? Object.fromEntries(Object.entries(mc.mc).map(([a, [, se]]) => [a, 1.96 * se])) : {};
  const mcEvs = mc ? Object.fromEntries(Object.entries(mc.mc).map(([a, [mean]]) => [a, mean])) : null;

  const left = h(
    "div",
    {},
    h("h3", {}, describeState(kind, total, up)),
    h("p", { class: "fine" }, "Exact expected profit per unit bet"),
    evBars(evs, { best: bestA }),
  );
  let right;
  if (mc) {
    const z = mc.margin_se > 0 ? mc.margin / mc.margin_se : Infinity;
    right = h(
      "div",
      {},
      h("h3", {}, `Monte Carlo estimate (${(app.strategy.n_per_action / 1e6).toFixed(0)}M hands per action)`),
      h("p", { class: "fine" }, "With 95% confidence intervals"),
      evBars(mcEvs, { best: mc.best, ci }),
      h(
        "p",
        { class: "coach-sub" },
        `Best action leads by ${(100 * mc.margin).toFixed(3)}% ± ${(196 * mc.margin_se).toFixed(3)}% (paired, common random numbers): ${
          z > 3 ? "a clear decision." : z > 1.96 ? "significant at 95%." : "statistically a coin flip at this sample size; the exact solver breaks the tie."
        }`,
      ),
    );
  } else right = h("div", {}, h("h3", {}, "Monte Carlo estimate"), h("p", { class: "muted" }, "The precomputed simulation used the default rules. Simulate this cell under your rules in the lab."));
  const actions = h(
    "div",
    { style: "margin-top:12px;display:flex;gap:10px;flex-wrap:wrap;align-items:center" },
    h("button", { class: "primary", onclick: () => openInLab() }, "Simulate this decision live →"),
    h("span", { class: "fine" }, m < 0.005 ? "One of the closest calls in the chart." : m > 0.2 ? "Not a close decision." : ""),
  );
  box.replaceChildren(h("div", { class: "detail-layout" }, left, right), actions);
}

function openInLab() {
  app.labRequest = { ...selected, rules };
  app.go("lab").then(() => app.bus.dispatchEvent(new Event("lab-request")));
}

function renderBust() {
  const el = $("#bust-chart");
  const draw = () => {
    const pts = UPCARDS.map((u) => ({ x: upcardLabel(u), y: sol.bustProb(u) }));
    const plot = new Plot(el, {
      x: { type: "band", domain: pts.map((p) => p.x), label: "Dealer upcard" },
      y: { domain: [0, 0.5], format: (v) => `${Math.round(v * 100)}%`, ticks: [0, 0.1, 0.2, 0.3, 0.4, 0.5] },
      margin: { left: 44, bottom: 36 },
    });
    plot.bars(pts, { colorFn: (p) => (["2", "3", "4", "5", "6"].includes(p.x) ? "var(--a-S)" : "var(--line-2)") });
    plot.hover((x) => {
      const p = pts.find((q) => q.x === x);
      return p && { x: p.x, html: `Dealer shows <b>${p.x}</b>: busts <b>${(100 * p.y).toFixed(1)}%</b> of the time` };
    });
  };
  draw();
  if (!renderBust.bound) {
    responsive(el, draw);
    renderBust.bound = true;
  }
  renderBust.draw = draw;
}

function renderAll() {
  renderEdge();
  renderGrids();
  renderDetail();
  renderBust();
}

export function init(a) {
  app = a;
  rules = { ...DEFAULT_RULES };
  sol = app.exact;
  rulesControls($("#chart-rules"), rules, (r) => {
    rules = r;
    sol = isDefault() ? app.exact : solve(rules);
    renderAll();
  });
  for (const b of $$("#color-mode button"))
    b.addEventListener("click", () => {
      for (const x of $$("#color-mode button")) x.classList.toggle("on", x === b);
      mode = b.dataset.m;
      renderGrids();
    });
  selected = { kind: "hard", total: 16, up: 10 };
  renderAll();
}

export function show() {
  renderBust.draw?.();
}
