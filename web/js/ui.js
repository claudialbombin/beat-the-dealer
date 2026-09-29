// Small DOM helpers shared by the views.

import { RANKS, SUITS, upcardLabel } from "./engine.js";

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) if (c != null) el.append(c instanceof Node ? c : document.createTextNode(c));
  return el;
}

export const ACTION_NAMES = { H: "Hit", S: "Stand", D: "Double", P: "Split" };
export const ACTION_ORDER = ["H", "S", "D", "P"];
export const actionColor = (a) => `var(--a-${a})`;

// ---------------------------------------------------------------- formatting
export const pct = (x, d = 2) => `${x >= 0 ? "+" : "−"}${Math.abs(100 * x).toFixed(d)}%`;
export const pctAbs = (x, d = 2) => `${(100 * x).toFixed(d)}%`;
export const signed = (x, d = 2) => (Math.abs(x) < 0.5 * 10 ** -d ? (0).toFixed(d) : `${x > 0 ? "+" : "−"}${Math.abs(x).toFixed(d)}`);
export const int = (n) => Math.round(n).toLocaleString("en-US");
export function compact(n) {
  if (n >= 1e9) return `${+(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `${+(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${+(n / 1e3).toFixed(1)}k`;
  return String(Math.round(n));
}

export function describeState(kind, total, up) {
  const u = upcardLabel(up);
  if (kind === "pair") return `pair of ${total === 11 ? "Aces" : total === 10 ? "tens" : total + "s"} vs ${u}`;
  if (kind === "soft") return `soft ${total} (A,${total - 11}) vs ${u}`;
  return `hard ${total} vs ${u}`;
}

// ---------------------------------------------------------------- playing cards
export function cardEl(card, faceDown = false) {
  if (faceDown) return h("div", { class: "pcard back", "aria-label": "face-down card" });
  const rank = RANKS[card.r];
  const suit = SUITS[card.s];
  const red = card.s === 1 || card.s === 2;
  return h(
    "div",
    { class: `pcard${red ? " red" : ""}`, "aria-label": `${rank}${suit}` },
    h("div", { class: "corner" }, rank, h("small", {}, suit)),
    h("div", { class: "pip" }, suit),
    h("div", { class: "corner bottom" }, rank, h("small", {}, suit)),
  );
}

/** A card for a blackjack value (2..11) with a random suit and, for 10, a random face. */
export function cardForValue(v, rng = Math.random) {
  const r = v === 11 ? 12 : v === 10 ? 8 + Math.floor(rng() * 4) : v - 2;
  return { r, s: Math.floor(rng() * 4) };
}

// ---------------------------------------------------------------- tooltip
const tip = () => document.getElementById("tooltip");
export function showTip(html, x, y) {
  const t = tip();
  t.innerHTML = html;
  t.hidden = false;
  const r = t.getBoundingClientRect();
  let left = x + 14,
    top = y + 14;
  if (left + r.width > window.innerWidth - 8) left = x - r.width - 14;
  if (top + r.height > window.innerHeight - 8) top = y - r.height - 14;
  t.style.left = `${Math.max(8, left)}px`;
  t.style.top = `${Math.max(8, top)}px`;
}
export const hideTip = () => (tip().hidden = true);

// ---------------------------------------------------------------- controls
/** Segmented control. options: [[value, label]]; returns element. */
export function segmented(label, options, value, onChange) {
  const wrap = h("div", { class: "seg" }, h("span", {}, label));
  const btns = h("div", { class: "seg-buttons", role: "radiogroup", "aria-label": label });
  for (const [v, text] of options) {
    const b = h("button", { type: "button", role: "radio", "aria-checked": String(v === value) }, text);
    if (v === value) b.classList.add("on");
    b.addEventListener("click", () => {
      for (const x of btns.children) {
        x.classList.remove("on");
        x.setAttribute("aria-checked", "false");
      }
      b.classList.add("on");
      b.setAttribute("aria-checked", "true");
      onChange(v);
    });
    btns.append(b);
  }
  wrap.append(btns);
  return wrap;
}

/** Rule controls shared by the table and the chart view. */
export function rulesControls(container, rules, onChange, { withShoe = false } = {}) {
  container.innerHTML = "";
  const set = (k) => (v) => {
    rules = { ...rules, [k]: v };
    onChange(rules);
  };
  container.append(
    segmented("Soft 17", [[true, "Dealer hits"], [false, "Dealer stands"]], rules.h17, set("h17")),
    segmented("Double after split", [[true, "Allowed"], [false, "Not allowed"]], rules.das, set("das")),
    segmented("Blackjack pays", [[1.5, "3:2"], [1.2, "6:5"], [1, "1:1"]], rules.bjPayout, set("bjPayout")),
  );
  if (withShoe) {
    container.append(
      segmented("Decks", [[1, "1"], [2, "2"], [6, "6"], [8, "8"]], rules.decks, set("decks")),
      segmented("Penetration", [[0.5, "50%"], [0.75, "75%"], [0.85, "85%"]], rules.penetration, set("penetration")),
    );
  }
}

/** Horizontal bars of action EVs around zero. evs: {a: value}; ci: {a: halfwidth} optional. */
export function evBars(evs, { best, ci = {}, chosen } = {}) {
  const acts = ACTION_ORDER.filter((a) => evs[a] != null && !Number.isNaN(evs[a]));
  const lo = Math.min(-0.2, ...acts.map((a) => evs[a] - (ci[a] || 0)));
  const hi = Math.max(0.2, ...acts.map((a) => evs[a] + (ci[a] || 0)));
  const X = (v) => ((v - lo) / (hi - lo)) * 100;
  const box = h("div", { class: "ev-bars" });
  for (const a of acts) {
    const v = evs[a];
    const left = Math.min(X(0), X(v)),
      width = Math.abs(X(v) - X(0));
    const track = h(
      "div",
      { class: "track" },
      h("div", { class: "fill", style: `left:${left}%;width:${width}%;background:${actionColor(a)}` }),
      h("div", { class: "zero", style: `left:${X(0)}%` }),
    );
    const label = `${ACTION_NAMES[a]}${a === chosen ? " •" : ""}`;
    box.append(
      h(
        "div",
        { class: `ev-bar${a === best ? " best" : ""}`, title: a === chosen ? "your choice" : "" },
        h("span", { class: "name" }, label),
        track,
        h("span", { class: "val" }, pct(v, 1) + (ci[a] ? ` ±${(100 * ci[a]).toFixed(1)}` : "")),
      ),
    );
  }
  return box;
}

export { upcardLabel };
