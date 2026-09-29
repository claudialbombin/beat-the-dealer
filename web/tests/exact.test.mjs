// Cross-check the JavaScript port against the Python solver's exported values.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { solve, recommend } from "../js/exact.js";
import { DEFAULT_RULES } from "../js/engine.js";

const data = JSON.parse(readFileSync(new URL("../data/strategy.json", import.meta.url)));
const S = solve(DEFAULT_RULES);

test("house edge matches Python", () => {
  assert.ok(Math.abs(S.houseEdge - data.house_edge_exact_optimal) < 1e-6);
});

test("every exact EV matches Python", () => {
  for (const st of data.states) {
    const T = S.tables.get(st.up);
    const js = st.kind === "pair" ? T.pairEVs(st.total) : T.actionEVs(st.total, st.kind === "soft", true);
    for (const [a, v] of Object.entries(st.exact)) assert.ok(Math.abs(js[a] - v) < 1e-6, `${st.kind} ${st.total} v ${st.up} ${a}`);
  }
});

test("exact chart equals the Monte Carlo chart", () => {
  for (const st of data.states) {
    const js = st.kind === "pair" ? (S.chart.pairs[st.total][st.up] ? "P" : "-") : S.chart[st.kind][st.total][st.up];
    assert.equal(js, st.code, `${st.kind} ${st.total} v ${st.up}`);
  }
});

test("S17 is cheaper than H17; 6:5 costs ~1.4%", () => {
  const s17 = solve({ ...DEFAULT_RULES, h17: false }).houseEdge;
  const sixFive = solve({ ...DEFAULT_RULES, bjPayout: 1.2 }).houseEdge;
  assert.ok(s17 - S.houseEdge > 0.0015 && s17 - S.houseEdge < 0.003);
  assert.ok(S.houseEdge - sixFive > 0.012 && S.houseEdge - sixFive < 0.015);
});

test("recommend resolves double codes", () => {
  const ctx = { total: 11, soft: false, up: 6, canDouble: false, canSplit: false };
  assert.equal(recommend(S.chart, ctx), "H");
  assert.equal(recommend(S.chart, { ...ctx, canDouble: true }), "D");
  assert.equal(recommend(S.chart, { total: 18, soft: true, up: 4, canDouble: false, canSplit: false }), "S");
  assert.equal(recommend(S.chart, { total: 16, soft: false, up: 10, canDouble: true, canSplit: true, pairValue: 8 }), "P");
});
