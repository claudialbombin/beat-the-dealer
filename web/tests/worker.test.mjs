// Run the Monte Carlo worker headless and check it converges to the exact EVs.
import { test } from "node:test";
import assert from "node:assert/strict";
import { solve } from "../js/exact.js";
import { DEFAULT_RULES } from "../js/engine.js";

const S = solve(DEFAULT_RULES);

async function runWorker(msg) {
  const msgs = [];
  let resolve;
  const done = new Promise((r) => (resolve = r));
  globalThis.postMessage = (m) => {
    msgs.push(m);
    if (m.type === "done") resolve();
  };
  await import(`../js/mc-worker.js?${Math.random()}`);
  globalThis.onmessage({ data: msg });
  await done;
  return msgs.filter((m) => m.type === "progress").at(-1);
}

for (const [label, st, up, acts] of [
  ["hard 16 vs 10", { total: 16, soft: false, pairValue: null }, 10, ["H", "S", "D"]],
  ["pair of 8s vs 9", { total: 16, soft: false, pairValue: 8 }, 9, ["H", "S", "D", "P"]],
  ["soft 18 vs 3", { total: 18, soft: true, pairValue: null }, 3, ["H", "S", "D"]],
]) {
  test(`worker estimates are unbiased: ${label}`, async () => {
    const p = S.policy(up);
    const last = await runWorker({
      type: "start", id: 1, acts, crn: true, seed: 12345, max: 150000, rules: DEFAULT_RULES,
      st: { ...st, up },
      pol: { hitHard: [...p.hitHard], hitSoft: [...p.hitSoft], codeHard: [...p.codeHard], codeSoft: [...p.codeSoft] },
    });
    const T = S.tables.get(up);
    const exact = st.pairValue ? T.pairEVs(st.pairValue) : T.actionEVs(st.total, st.soft, true);
    acts.forEach((a, j) => {
      const mean = last.sum[j] / last.n;
      const se = Math.sqrt((last.sq[j] / last.n - mean * mean) / last.n);
      assert.ok(Math.abs(mean - exact[a]) < 4.5 * se, `${a}: ${mean} vs ${exact[a]} (se ${se})`);
    });
  });
}
