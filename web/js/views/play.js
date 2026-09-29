// The playable table with a basic-strategy coach and a count trainer.

import { Game, DEFAULT_RULES, upcardLabel } from "../engine.js";
import { solve, recommend } from "../exact.js";
import { sparkline } from "../charts.js";
import { PRESETS, betFor } from "../counting-math.js";
import { $, $$, h, cardEl, evBars, rulesControls, ACTION_NAMES, pct, signed } from "../ui.js";

const DEALER_DELAY = 480;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let app, game, solution, rules;
let bet = 1;
let busy = false;
let opts = { coach: true, hint: false, count: false, quiz: false };
let S; // session stats
let roundDecisions = [];

function resetSession() {
  S = { hands: 0, net: 0, decisions: 0, correct: 0, cost: 0, history: [0] };
}

function setRules(r, announce = true) {
  rules = r;
  game = new Game(rules);
  solution = JSON.stringify(r) === JSON.stringify(DEFAULT_RULES) ? app.exact : solve(r);
  $("#felt-payout").textContent = r.bjPayout === 1.5 ? "3 to 2" : r.bjPayout === 1.2 ? "6 to 5" : "1 to 1";
  $("#felt-h17").textContent = r.h17 ? "Dealer hits soft 17" : "Dealer stands on all 17s";
  if (announce) message(`New ${r.decks}-deck shoe`);
  render();
}

// ---------------------------------------------------------------- rendering
function totalLabel(hand, full = true) {
  const { total, soft } = hand.value;
  if (hand.blackjack) return "Blackjack";
  if (total > 21) return `Bust ${total}`;
  return soft && total < 21 && full ? `soft ${total}` : String(total);
}

function render() {
  // dealer
  const dealerEl = $("#dealer-cards");
  dealerEl.replaceChildren(...game.dealer.map((c, i) => cardEl(c, i === 1 && !game.holeRevealed)));
  const dt = $("#dealer-total");
  if (!game.dealer.length) dt.textContent = "";
  else if (!game.holeRevealed) dt.textContent = upcardLabel(game.upcard);
  else {
    const t = game.dealerTotal;
    dt.textContent = t > 21 ? `Bust ${t}` : game.dealer.length === 2 && t === 21 ? "Blackjack" : String(t);
  }

  // player
  const handsEl = $("#player-hands");
  handsEl.replaceChildren(
    ...game.hands.map((hand, i) => {
      const active = game.phase === "player" && i === game.active && game.hands.length > 1;
      const res =
        hand.result == null
          ? null
          : h("span", { class: `result ${hand.result > 0 ? "win" : hand.result < 0 ? "lose" : "push"}` }, hand.result === 0 ? "Push" : signed(hand.result, hand.result % 1 ? 1 : 0));
      return h(
        "div",
        { class: `hand${active ? " active" : ""}` },
        h("div", { class: "cards" }, hand.cards.map((c) => cardEl(c))),
        h("div", { class: "seat-label" }, "You ", h("span", { class: "total" }, totalLabel(hand))),
        h("div", {}, h("span", { class: "bet-chip" }, `${hand.bet}u${hand.doubled ? " ×2" : ""}`), " ", res),
      );
    }),
  );

  // actions
  const legal = game.legal();
  const rec = game.phase === "player" ? recommend(solution.chart, game.context()) : null;
  for (const b of $$("#actions .act")) {
    const a = b.dataset.act;
    b.disabled = busy || !legal[a];
    b.classList.toggle("hint", opts.hint && rec === a && !busy);
  }
  $("#deal-btn").disabled = busy || game.phase === "player" || game.phase === "dealer";
  $("#bet-out").textContent = bet;

  // shoe & count
  const sh = game.shoe;
  $("#shoe-fill").style.width = `${(100 * sh.pos) / sh.cards.length}%`;
  $("#shoe-cut").style.left = `${(100 * sh.cut) / sh.cards.length}%`;
  $("#shoe-label").textContent = `${sh.remaining} cards`;
  $("#count-box").hidden = !opts.count;
  $("#rc").textContent = signed(game.running, 0);
  const tc = game.trueCount;
  $("#tc").textContent = tc.toFixed(1);
  $("#decks-left").textContent = sh.decksRemaining.toFixed(1);
  $("#rc").className = `v ${game.running > 0 ? "pos" : game.running < 0 ? "neg" : ""}`;
  const idle = game.phase === "idle" || game.phase === "done";
  $("#bet-hint").textContent =
    opts.count && idle
      ? `True count ${tc.toFixed(1)}: a 1–8 ramp would bet ${betFor(PRESETS["1–8"], Math.floor(tc))}u`
      : "";

  // session
  $("#s-hands").textContent = S.hands;
  $("#s-net").textContent = signed(S.net, S.net % 1 ? 1 : 0);
  $("#s-net").className = `v ${S.net > 0 ? "pos" : S.net < 0 ? "neg" : ""}`;
  $("#s-acc").textContent = S.decisions ? `${Math.round((100 * S.correct) / S.decisions)}%` : "–";
  $("#s-cost").textContent = `${S.cost.toFixed(2)}u`;
  sparkline($("#s-spark"), S.history);
}

function message(text, ms = 1400) {
  const m = $("#round-msg");
  m.textContent = text;
  m.classList.add("show");
  clearTimeout(message.t);
  message.t = setTimeout(() => m.classList.remove("show"), ms);
}

function coach(ctx, chosen, evs, rec, handBet) {
  if (!opts.coach) return;
  const best = rec;
  const loss = evs[best] - evs[chosen];
  const ok = chosen === best || loss < 1e-9;
  const handName = ctx.canSplit
    ? `${ctx.pairValue === 11 ? "A,A" : `${ctx.pairValue},${ctx.pairValue}`}`
    : `${ctx.soft ? "soft" : "hard"} ${ctx.total}`;
  const where = `${handName} vs ${upcardLabel(ctx.up)}`;
  const others = Object.keys(evs).filter((a) => a !== best);
  const runnerUp = others.sort((a, b) => evs[b] - evs[a])[0];
  const body = $("#coach-body");
  body.replaceChildren(
    h(
      "div",
      { class: "verdict-line" },
      h("span", { class: `badge ${ok ? "ok" : "no"}`, "aria-hidden": "true" }, ok ? "✓" : "✗"),
      h("span", {}, ok ? `Correct: ${ACTION_NAMES[chosen]} on ${where}` : `Basic strategy says ${ACTION_NAMES[best]} on ${where}`),
    ),
    h(
      "p",
      { class: "coach-sub" },
      ok
        ? runnerUp
          ? `${ACTION_NAMES[best]} beats ${ACTION_NAMES[runnerUp]} by ${(100 * (evs[best] - evs[runnerUp])).toFixed(1)}% of the bet.`
          : ""
        : `${ACTION_NAMES[chosen]} gives up ${(100 * loss).toFixed(1)}% of the bet on average (${(loss * handBet).toFixed(3)} units).`,
    ),
    evBars(evs, { best, chosen }),
    h("p", { class: "fine", style: "margin:8px 0 0" }, "Expected profit per unit bet for each action (exact, infinite-deck)."),
  );
}

// ---------------------------------------------------------------- flow
async function deal() {
  if (busy || game.phase === "player" || game.phase === "dealer") return;
  roundDecisions = [];
  game.deal(bet);
  if (game.shuffledThisRound) message("Cut card reached: new shoe");
  render();
  if (game.phase === "done") await finishRound();
}

async function act(a) {
  if (busy || !game.legal()[a]) return;
  const ctx = game.context();
  const evs = solution.decisionEVs(ctx);
  const rec = recommend(solution.chart, ctx);
  const loss = Math.max(0, evs[rec] - evs[a]);
  const handBet = game.hand.bet;
  S.decisions++;
  if (loss < 1e-9) S.correct++;
  S.cost += loss * handBet;
  roundDecisions.push(loss < 1e-9);
  coach(ctx, a, evs, rec, handBet);
  game.act(a);
  render();
  if (game.phase === "dealer") await runDealer();
}

async function runDealer() {
  busy = true;
  render();
  await sleep(DEALER_DELAY / 2);
  while (game.dealerStep()) {
    render();
    await sleep(DEALER_DELAY);
  }
  busy = false;
  await finishRound();
}

async function finishRound() {
  S.hands++;
  S.net += game.net;
  S.history.push(S.net);
  const reasons = {
    "player-bj": `Blackjack! +${game.net}`,
    "dealer-bj": "Dealer blackjack",
    "push-bj": "Both blackjack: push",
  };
  let msg = reasons[game.endReason] || (game.net > 0 ? `You win ${signed(game.net, game.net % 1 ? 1 : 0)}` : game.net < 0 ? `You lose ${Math.abs(game.net)}` : "Push");
  if (!game.endReason && game.dealerTotal > 21 && game.hands.some((x) => !x.bust)) msg = `Dealer busts: ${signed(game.net, 0)}`;
  message(msg, 1800);
  if (opts.coach && game.net < 0 && roundDecisions.length && roundDecisions.every(Boolean)) {
    $("#coach-body").append(h("p", { class: "fine", style: "margin-top:8px" }, "Every decision this round was right; the loss is variance."));
  }
  render();
  if (opts.quiz && S.hands % 5 === 0) quiz();
}

function quiz() {
  const dlg = $("#quiz-dialog");
  $("#quiz-input").value = "";
  $("#quiz-result").textContent = "";
  $("#quiz-submit").hidden = false;
  dlg.showModal();
}

// ---------------------------------------------------------------- init
export function init(a) {
  app = a;
  resetSession();
  rulesControls($("#play-rules"), DEFAULT_RULES, (r) => setRules(r), { withShoe: true });
  setRules({ ...DEFAULT_RULES }, false);

  for (const b of $$("#actions .act")) b.addEventListener("click", () => act(b.dataset.act));
  $("#deal-btn").addEventListener("click", deal);
  $("#bet-up").addEventListener("click", () => ((bet = Math.min(50, bet + 1)), render()));
  $("#bet-down").addEventListener("click", () => ((bet = Math.max(1, bet - 1)), render()));
  $("#reset-session").addEventListener("click", () => {
    resetSession();
    $("#coach-body").replaceChildren(h("p", { class: "muted" }, "Session reset."));
    render();
  });
  for (const [id, key] of [["opt-coach", "coach"], ["opt-hint", "hint"], ["opt-count", "count"], ["opt-quiz", "quiz"]]) {
    $(`#${id}`).addEventListener("change", (e) => {
      opts[key] = e.target.checked;
      render();
    });
  }

  $("#quiz-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const guess = parseInt($("#quiz-input").value, 10);
    const ok = guess === game.running;
    $("#quiz-result").textContent = ok ? `Correct: the running count is ${game.running}.` : `Not quite: it is ${game.running} (true count ${game.trueCount.toFixed(1)}).`;
    $("#quiz-result").style.color = ok ? "var(--good)" : "var(--bad)";
    $("#quiz-submit").hidden = true;
    setTimeout(() => $("#quiz-dialog").close(), ok ? 900 : 2200);
  });
  $("#quiz-skip").addEventListener("click", () => $("#quiz-dialog").close());

  document.addEventListener("keydown", (e) => {
    if ($("#panel-play").hidden || e.target.closest("input, select, textarea, dialog[open]") || e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.key.toUpperCase();
    if ("HSDP".includes(k) && k.length === 1) {
      e.preventDefault();
      act(k);
    } else if (e.key === " " || e.key === "Enter") {
      if (e.target.closest("button")) return; // let the focused button handle it
      e.preventDefault();
      deal();
    }
  });
  window.addEventListener("resize", () => sparkline($("#s-spark"), S.history));
}

export function show() {
  render();
}
