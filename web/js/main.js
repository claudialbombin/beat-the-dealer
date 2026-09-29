import { DEFAULT_RULES } from "./engine.js";
import { solve } from "./exact.js";
import { $, $$, h, pct, pctAbs } from "./ui.js";
import { rampStats, PRESETS, fitSlope } from "./counting-math.js";

const views = {
  play: () => import("./views/play.js"),
  drill: () => import("./views/drill.js"),
  strategy: () => import("./views/strategy.js"),
  lab: () => import("./views/lab.js"),
  counting: () => import("./views/counting.js"),
  method: () => import("./views/method.js"),
};
const started = new Map();

async function loadJSON(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json();
}

function initTheme() {
  const btn = $("#theme-toggle");
  let stored = null;
  try {
    stored = localStorage.getItem("theme");
  } catch {}
  if (stored) document.documentElement.dataset.theme = stored;
  btn.addEventListener("click", () => {
    const dark =
      document.documentElement.dataset.theme === "dark" ||
      (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
    const next = dark ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch {}
    window.dispatchEvent(new Event("themechange"));
  });
}

function heroStats(app) {
  const c = app.counting;
  const matches = app.strategy.states.filter((st) => {
    const js = st.kind === "pair" ? (app.exact.chart.pairs[st.total][st.up] ? "P" : "-") : app.exact.chart[st.kind][st.total][st.up];
    return js === st.code;
  }).length;
  const slope = fitSlope(c.bins);
  const r12 = rampStats(c.bins, PRESETS["1–12"]);
  const tiles = [
    ["House edge, basic strategy", pctAbs(-c.overall.mean), `± ${(196 * c.overall.se).toFixed(3)}% over ${(c.rounds / 1e9).toFixed(0)} billion simulated rounds`],
    ["Chart vs exact solver", `${matches} / ${app.strategy.states.length}`, `cells agree; Monte Carlo with ${(app.strategy.n_per_action / 1e6).toFixed(0)}M hands per action`],
    ["Edge per +1 true count", pct(slope, 2), "Hi-Lo, weighted fit over true counts −5 … +6"],
    ["Counter's edge, 1–12 spread", pct(r12.edge, 2), "basic strategy only, no index plays"],
  ];
  $("#hero-stats").replaceChildren(
    ...tiles.map(([l, v, sub]) => h("div", { class: "stat" }, h("div", { class: "label" }, l), h("div", { class: "value" }, v), h("div", { class: "sub" }, sub))),
  );
}

async function show(tab) {
  if (!views[tab]) tab = "play";
  for (const b of $$(".tabs button")) b.setAttribute("aria-selected", String(b.dataset.tab === tab));
  for (const p of $$(".panel")) p.hidden = p.id !== `panel-${tab}`;
  if (!started.has(tab)) {
    const mod = await views[tab]();
    started.set(tab, mod);
    mod.init(window.app);
  } else started.get(tab).show?.();
}

async function main() {
  initTheme();
  try {
    const [strategy, counting] = await Promise.all([loadJSON("data/strategy.json"), loadJSON("data/counting.json")]);
    window.app = {
      strategy,
      counting,
      exact: solve(DEFAULT_RULES),
      mc: new Map(strategy.states.map((s) => [`${s.kind}:${s.total}:${s.up}`, s])),
      bus: new EventTarget(),
    };
  } catch (e) {
    const box = $("#load-error");
    box.hidden = false;
    box.textContent = `Could not load the results data (${e.message}). If you opened index.html from disk, serve the folder instead: python -m http.server -d web`;
    return;
  }
  heroStats(window.app);
  for (const b of $$(".tabs button"))
    b.addEventListener("click", () => {
      history.replaceState(null, "", `#${b.dataset.tab}`);
      show(b.dataset.tab);
    });
  window.addEventListener("hashchange", () => show(location.hash.slice(1)));
  window.app.go = (tab) => {
    history.replaceState(null, "", `#${tab}`);
    return show(tab);
  };
  show(location.hash.slice(1) || "play");
}

main();
