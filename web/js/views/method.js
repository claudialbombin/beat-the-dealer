// Methodology, results and limitations, with numbers read from the data files.

import { $, pct, pctAbs, int } from "../ui.js";
import { rampStats, PRESETS, fitLine } from "../counting-math.js";

export function init(app) {
  const s = app.strategy,
    c = app.counting;
  const fit = fitLine(c.bins);
  const ramps = ["Flat", "1–4", "1–8", "1–12", "Wong out, 1–8"].map((name) => [name, rampStats(c.bins, PRESETS[name])]);
  const closeCalls = s.states.filter((st) => st.margin_se > 0 && st.margin < 1.96 * st.margin_se).length;
  const repo = "https://github.com/claudialbombin/beat-the-dealer/blob/main/";

  $("#method-body").innerHTML = `
<h2>How it works</h2>
<p>The project answers two questions with simulation, and checks every simulated answer against something it can be compared with.</p>
<div class="pipeline">
  <div><b>1 · Monte Carlo solver</b>Python + NumPy. ${int(s.n_per_action)} hands per state and action, solved by backward induction.</div>
  <div><b>2 · Exact solver</b>Recursion over every hand state (infinite deck). The yardstick for step 1.</div>
  <div><b>3 · Shoe simulator</b>C, multithreaded. ${(c.rounds / 1e9).toFixed(0)} billion rounds of the real 6-deck game with a Hi-Lo count.</div>
  <div><b>4 · This page</b>Vanilla JS. Re-solves the game live, runs Monte Carlo in a Web Worker, and replays the simulated counts.</div>
</div>

<h3>Rules</h3>
<p>6 decks, dealer hits soft 17, blackjack pays 3:2, double on any two cards and after splits, one split per hand (split Aces get one card each), dealer peeks for blackjack, no surrender, 75% penetration. Insurance is never taken. The Strategy tab re-solves the chart for other rules.</p>

<h3>1. Basic strategy by Monte Carlo</h3>
<p>For each decision (player total, soft or hard, dealer upcard) and each legal action, the solver simulates the rest of the hand ${int(s.n_per_action)} times and averages the profit. Two details make this a correct solver rather than a heuristic:</p>
<ul>
  <li><b>Backward induction.</b> After a hit, the hand has to be played on optimally. States are solved in an order where everything a hit can lead to is already solved (hard 21 down to 11, then soft 21 down to 12, then hard 10 down to 4), and the continuation uses the policy estimated so far.</li>
  <li><b>Common random numbers.</b> All actions for one upcard face the same simulated dealer hands, and all actions in one state share the same player cards. The comparison between actions then reflects the decision, not sampling luck, and the standard error of the difference is reported for every cell.</li>
</ul>
<p>Draws come from an infinite deck, so the estimates can be compared one-to-one with the exact solver: all ${s.states.length} chart decisions match, the estimates are unbiased (a test checks the z-scores), and the exact expected value of the Monte Carlo chart is ${pct(s.house_edge_exact_mc_chart, 3)} against ${pct(s.house_edge_exact_optimal, 3)} for the true optimum. ${closeCalls} cells are statistical ties at this sample size (the lead is under 1.96 standard errors); the exact solver confirms the Monte Carlo pick in each.</p>

<h3>2. Validation</h3>
<ul>
  <li>The exact solver reproduces the standard dealer bust probabilities and the published 6-deck H17 chart in every cell except soft 13 vs 5, a known card-removal effect (doubling is right in a 6-deck shoe, hitting with an infinite deck).</li>
  <li>The C simulator is a port of the Python engine; a test runs both and checks the house edge, the true-count distribution and per-count EVs agree within sampling error. Rule edge cases (peek, split Aces, one split, DAS, H17, the cut card, when the hole card is counted) have unit tests in Python, C and JavaScript.</li>
  <li>The JavaScript solver used on this page is checked against the Python values to 10<sup>−6</sup>.</li>
</ul>

<h3>3. Results</h3>
<table class="plain">
  <tr><th>Quantity</th><th>Value</th></tr>
  <tr><td>House edge, basic strategy, 6-deck shoe (simulated)</td><td class="num">${pctAbs(-c.overall.mean, 3)} ± ${(196 * c.overall.se).toFixed(3)}%</td></tr>
  <tr><td>House edge, infinite deck (exact)</td><td class="num">${pctAbs(-s.house_edge_exact_optimal, 3)}</td></tr>
  <tr><td>Standard deviation per round</td><td class="num">${c.overall.sd.toFixed(3)} units</td></tr>
  <tr><td>Edge gained per +1 true count (fit over −5…+6)</td><td class="num">${pct(fit.slope, 3)}</td></tr>
  <tr><td>True count at which the player gains the edge</td><td class="num">+${(-fit.intercept / fit.slope).toFixed(2)}</td></tr>
</table>
<table class="plain">
  <tr><th>Betting ramp (units by true count)</th><th>Edge per unit bet</th><th>Win / 100 rounds</th><th>SD / round</th></tr>
  ${ramps.map(([n, r]) => `<tr><td>${n}</td><td class="num">${pct(r.edge, 2)}</td><td class="num">${(100 * r.ev).toFixed(2)}u</td><td class="num">${r.sd.toFixed(2)}u</td></tr>`).join("")}
</table>
<p>Counting works, in the sense that the true count predicts the next hand very reliably. But with these rules (H17, no surrender) and basic strategy only, the advantage is small: a 1–8 spread roughly breaks even, and it takes a 1–12 spread or leaving the table at negative counts to get a real edge. This is why shoe games where the dealer hits soft 17 and surrender is not offered are considered hard to beat with a modest spread.</p>

<h3>Limitations</h3>
<ul>
  <li>The counter uses basic strategy only. Real counters also deviate from the chart at high counts (the “Illustrious 18”), which is worth roughly another 0.1–0.2%.</li>
  <li>The chart is derived under the infinite-deck approximation (see above). The shoe simulation is exact for a 6-deck game.</li>
  <li>The bankroll simulation draws rounds independently from the simulated (true count, outcome) distribution, which ignores how counts persist within a shoe. It is a teaching tool; the risk-of-ruin formula is the standard diffusion approximation.</li>
  <li>Coach and drill costs are exact infinite-deck EVs for the decision in isolation, not composition-dependent.</li>
  <li>Surrender, re-splitting and insurance are not modelled.</li>
</ul>

<h3>Code</h3>
<ul>
  <li><a href="${repo}python/src/blackjack/solver.py">solver.py</a>: vectorised Monte Carlo solver</li>
  <li><a href="${repo}python/src/blackjack/exact.py">exact.py</a>: exact dynamic-programming reference</li>
  <li><a href="${repo}C/src/round.c">C/src/round.c</a>: the C shoe simulator</li>
  <li><a href="${repo}web/js/mc-worker.js">web/js/mc-worker.js</a>: the in-browser Monte Carlo lab</li>
</ul>`;
}
