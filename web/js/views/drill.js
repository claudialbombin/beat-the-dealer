// Rapid decision drill with a per-cell mastery map.

import { UPCARDS, CARD_PROBS, recommend, pairTotal } from "../exact.js";
import { $, $$, h, cardEl, cardForValue, evBars, ACTION_NAMES, describeState, showTip, hideTip, upcardLabel } from "../ui.js";

let app, sol;
let filter = "all";
let byFreq = true;
let current = null;
let answered = false;
let advanceTimer = 0;
const stats = { n: 0, right: 0, streak: 0, best: 0 };
const mastery = new Map(); // key -> {seen, wrong}

const HARD_ROWS = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19];
const SOFT_ROWS = [13, 14, 15, 16, 17, 18, 19, 20];
const PAIR_ROWS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
const p = (v) => CARD_PROBS.get(v);

function twoCardCombos(kind, t) {
  if (kind === "pair") return [[t, t]];
  if (kind === "soft") return [[11, t - 11]];
  const out = [];
  for (let a = 2; a <= 10; a++) for (let b = a + 1; b <= 10; b++) if (a + b === t) out.push([a, b]);
  return out;
}

function buildStates() {
  const states = [];
  for (const up of UPCARDS) {
    for (const t of HARD_ROWS) {
      const combos = twoCardCombos("hard", t);
      const w = combos.reduce((s, [a, b]) => s + 2 * p(a) * p(b), 0);
      states.push({ kind: "hard", total: t, up, w: w * p(up), combos });
    }
    for (const t of SOFT_ROWS) states.push({ kind: "soft", total: t, up, w: 2 * p(11) * p(t - 11) * p(up), combos: twoCardCombos("soft", t) });
    for (const v of PAIR_ROWS) states.push({ kind: "pair", total: v, up, w: p(v) ** 2 * p(up), combos: [[v, v]] });
  }
  for (const s of states) {
    s.key = `${s.kind}:${s.total}:${s.up}`;
    s.ctx = contextFor(s);
    s.evs = sol.decisionEVs(s.ctx);
    s.best = recommend(sol.chart, s.ctx);
    const sorted = Object.values(s.evs).sort((a, b) => b - a);
    s.margin = sorted[0] - sorted[1];
  }
  return states;
}

function contextFor(s) {
  if (s.kind === "pair") {
    const [t, soft] = pairTotal(s.total);
    return { total: t, soft, up: s.up, canDouble: true, canSplit: true, pairValue: s.total };
  }
  return { total: s.total, soft: s.kind === "soft", up: s.up, canDouble: true, canSplit: false, pairValue: null };
}

let STATES = [];

function pool() {
  let list = STATES;
  if (["hard", "soft", "pair"].includes(filter)) list = list.filter((s) => s.kind === filter);
  else if (filter === "close") list = list.filter((s) => s.margin < 0.02);
  else if (filter === "missed") list = list.filter((s) => mastery.get(s.key)?.wrong > 0);
  return list;
}

function next() {
  clearTimeout(advanceTimer);
  const list = pool();
  if (!list.length) {
    current = null;
    $("#drill-feedback").replaceChildren(h("p", { class: "muted" }, filter === "missed" ? "No mistakes recorded yet. Nice." : "Nothing to drill here."));
    $("#drill-dealer").replaceChildren();
    $("#drill-player").replaceChildren();
    $("#drill-total").textContent = "";
    return;
  }
  const weights = list.map((s) => (filter === "missed" ? mastery.get(s.key).wrong : byFreq ? s.w : 1));
  let u = Math.random() * weights.reduce((a, b) => a + b, 0);
  let i = 0;
  while (u > weights[i] && i < list.length - 1) u -= weights[i++];
  if (current && list.length > 1 && list[i].key === current.key) i = (i + 1) % list.length;
  current = list[i];
  const combo = current.combos[Math.floor(Math.random() * current.combos.length)];
  const cards = (Math.random() < 0.5 ? combo : [...combo].reverse()).map((v) => cardForValue(v));
  $("#drill-dealer").replaceChildren(cardEl(cardForValue(current.up)), cardEl(null, true));
  $("#drill-player").replaceChildren(...cards.map((c) => cardEl(c)));
  const c = current.ctx;
  $("#drill-total").textContent = current.kind === "pair" ? "pair" : c.soft ? `soft ${c.total}` : String(c.total);
  answered = false;
  for (const b of $$("#drill-actions .act")) {
    b.classList.remove("right", "wrong");
    b.disabled = b.dataset.act === "P" && current.kind !== "pair";
  }
  $("#drill-feedback").replaceChildren(h("p", { class: "muted" }, "Your call? Keys: H, S, D, P."));
}

function answer(a) {
  if (!current || answered) return;
  if (a === "P" && current.kind !== "pair") return;
  answered = true;
  const s = current;
  const ok = s.evs[a] >= s.evs[s.best] - 1e-9;
  stats.n++;
  if (ok) {
    stats.right++;
    stats.streak++;
    stats.best = Math.max(stats.best, stats.streak);
  } else stats.streak = 0;
  const m = mastery.get(s.key) || { seen: 0, wrong: 0 };
  m.seen++;
  if (!ok) m.wrong++;
  mastery.set(s.key, m);

  for (const b of $$("#drill-actions .act")) {
    if (b.dataset.act === s.best) b.classList.add("right");
    else if (b.dataset.act === a) b.classList.add("wrong");
  }
  const loss = s.evs[s.best] - s.evs[a];
  const title = ok ? `Correct: ${ACTION_NAMES[a]}` : `The right play is ${ACTION_NAMES[s.best]}`;
  const why = ok
    ? s.margin < 0.01
      ? `A close call: the runner-up is only ${(100 * s.margin).toFixed(2)}% of a bet behind.`
      : `Beats the next best action by ${(100 * s.margin).toFixed(1)}% of the bet.`
    : `${ACTION_NAMES[a]} costs ${(100 * loss).toFixed(1)}% of your bet on average.`;
  $("#drill-feedback").replaceChildren(
    h("div", { class: "verdict-line" }, h("span", { class: `badge ${ok ? "ok" : "no"}` }, ok ? "✓" : "✗"), h("span", {}, `${title} on ${describeState(s.kind, s.total, s.up)}`)),
    h("p", { class: "coach-sub" }, why),
    evBars(s.evs, { best: s.best, chosen: a }),
    h(
      "div",
      { class: "next-row" },
      h("span", { class: "fine" }, ok ? "Next hand in a moment…" : "Take a look, then continue."),
      h("button", { class: "primary", onclick: next }, "Next ", h("kbd", {}, "Space")),
    ),
  );
  if (ok) advanceTimer = setTimeout(next, 1100);
  renderStats();
  renderMastery();
}

function renderStats() {
  $("#d-n").textContent = stats.n;
  $("#d-acc").textContent = stats.n ? `${Math.round((100 * stats.right) / stats.n)}%` : "–";
  $("#d-streak").textContent = stats.streak;
  $("#d-best").textContent = stats.best;
}

function masteryGrid(title, kind, rows, label) {
  const table = h("table", { class: "sgrid" });
  table.append(h("tr", {}, h("th", { class: "row" }), ...UPCARDS.map((u) => h("th", {}, upcardLabel(u)))));
  for (const r of rows) {
    const tr = h("tr", {}, h("th", { class: "row" }, label(r)));
    for (const u of UPCARDS) {
      const key = `${kind}:${r}:${u}`;
      const m = mastery.get(key);
      const st = STATES.find((s) => s.key === key);
      let bg = "var(--surface-2)";
      if (m) bg = m.wrong ? `color-mix(in srgb, var(--bad) ${40 + 60 * (m.wrong / m.seen)}%, var(--surface))` : "color-mix(in srgb, var(--good) 70%, var(--surface))";
      const td = h("td", { style: `background:${bg}` });
      td.addEventListener("pointerenter", (e) =>
        showTip(`<b>${describeState(kind, r, u)}</b><br>Right play: ${ACTION_NAMES[st.best]}<br>${m ? `Seen ${m.seen}×, wrong ${m.wrong}×` : "Not seen yet"}`, e.clientX, e.clientY),
      );
      td.addEventListener("pointerleave", hideTip);
      tr.append(td);
    }
    table.append(tr);
  }
  return h("div", { class: "grid-block" }, h("h4", {}, title), table);
}

function renderMastery() {
  $("#mastery").replaceChildren(
    h(
      "div",
      { class: "mastery" },
      masteryGrid("Hard totals", "hard", HARD_ROWS, String),
      masteryGrid("Soft totals", "soft", SOFT_ROWS, (t) => `A,${t - 11}`),
      masteryGrid("Pairs", "pair", PAIR_ROWS, (v) => (v === 11 ? "A,A" : `${v},${v}`)),
    ),
  );
}

export function init(a) {
  app = a;
  sol = app.exact;
  STATES = buildStates();
  for (const b of $$("#drill-filter button"))
    b.addEventListener("click", () => {
      for (const x of $$("#drill-filter button")) x.classList.toggle("on", x === b);
      filter = b.dataset.f;
      next();
    });
  $("#drill-freq").addEventListener("change", (e) => {
    byFreq = e.target.checked;
    next();
  });
  for (const b of $$("#drill-actions .act")) b.addEventListener("click", () => answer(b.dataset.act));
  document.addEventListener("keydown", (e) => {
    if ($("#panel-drill").hidden || e.target.closest("input, select, textarea") || e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.key.toUpperCase();
    if ("HSDP".includes(k) && k.length === 1) {
      e.preventDefault();
      answer(k);
    } else if ((e.key === " " || e.key === "Enter") && answered && !e.target.closest("button")) {
      e.preventDefault();
      next();
    }
  });
  renderStats();
  renderMastery();
  next();
}
