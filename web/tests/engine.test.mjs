import { test } from "node:test";
import assert from "node:assert/strict";
import { Game, DEFAULT_RULES, handValue, ACE } from "../js/engine.js";

// rank index for a blackjack value (10 -> "10", 11 -> Ace)
const R = (v) => (v === ACE ? 12 : v - 2);
function rigged(values, rules = DEFAULT_RULES) {
  const g = new Game(rules, () => 0.5);
  g.shoe.cards = values.map((v) => ({ r: R(v), s: 0 })).concat(g.shoe.cards);
  g.shoe.pos = 0;
  return g;
}
const finish = (g) => { while (g.dealerStep()); return g.net; };

test("hand values", () => {
  assert.deepEqual(handValue([11, 11, 11, 11]), { total: 14, soft: true });
  assert.deepEqual(handValue([11, 7, 5]), { total: 13, soft: false });
});

test("blackjack pays 3:2, dealer peek ends the round", () => {
  assert.equal(rigged([11, 9, 10, 7]).deal(1).net, 1.5);
  const g = rigged([6, 10, 5, 11]).deal(1);
  assert.equal(g.phase, "done");
  assert.equal(g.net, -1);
});

test("double: one card, two units", () => {
  const g = rigged([6, 10, 5, 7, 10]).deal(1);
  g.act("D");
  assert.equal(g.phase, "dealer");
  assert.equal(finish(g), 2);
});

test("split aces: one card each, no blackjack bonus", () => {
  const g = rigged([11, 10, 11, 9, 10, 5]).deal(1);
  g.act("P");
  assert.equal(g.phase, "dealer");
  assert.equal(finish(g), 0);
});

test("only one split, DAS respected", () => {
  const g = rigged([8, 10, 8, 9, 8, 3]).deal(1);
  g.act("P");
  assert.equal(g.legal().P, false);
  g.act("S");
  assert.equal(g.legal().D, true);
  const g2 = rigged([8, 10, 8, 9, 8, 3], { ...DEFAULT_RULES, das: false }).deal(1);
  g2.act("P"); g2.act("S");
  assert.equal(g2.legal().D, false);
});

test("H17 vs S17", () => {
  const cards = [10, 11, 8, 6, 2, 10];
  let g = rigged(cards).deal(1); g.act("S");
  assert.equal(finish(g), -1);
  g = rigged(cards, { ...DEFAULT_RULES, h17: false }).deal(1); g.act("S");
  assert.equal(finish(g), 1);
});

test("hole card counted only when revealed", () => {
  const g = rigged([10, 5, 9, 2, 10]).deal(1);
  assert.equal(g.running, 0); // T(-1) 5(+1) 9(0)
  g.act("S");
  finish(g);
  assert.equal(g.running, 0); // + hole 2 (+1) + dealer T (-1)
});
