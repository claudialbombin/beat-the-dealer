// Blackjack rules for the browser: cards, shoe, and a step-by-step round
// state machine for the playable table. Mirrors python/src/blackjack/engine.py
// (same rules, same counting conventions).

export const ACE = 11;
export const RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"];
export const SUITS = ["♠", "♥", "♦", "♣"];
export const RANK_VALUE = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, ACE];

export const DEFAULT_RULES = Object.freeze({
  decks: 6,
  h17: true, // dealer hits soft 17
  bjPayout: 1.5, // 3:2
  das: true, // double after split
  penetration: 0.75,
});

export const hiLo = (v) => (v <= 6 ? 1 : v <= 9 ? 0 : -1);

/** Card = { r: rank index 0..12, s: suit index 0..3 } */
export const cardValue = (c) => RANK_VALUE[c.r];

export function addCard(total, soft, v) {
  let hard = soft ? total - 10 : total;
  let hasAce = soft;
  if (v === ACE) {
    hard += 1;
    hasAce = true;
  } else hard += v;
  if (hasAce && hard + 10 <= 21) return [hard + 10, true];
  return [hard, false];
}

export function handValue(values) {
  let t = 0,
    s = false;
  for (const v of values) [t, s] = addCard(t, s, v);
  return { total: t, soft: s };
}

export const upcardLabel = (v) => (v === ACE ? "A" : String(v));

// -------------------------------------------------------------------- shoe
export class Shoe {
  constructor(decks, penetration, rng = Math.random) {
    this.rng = rng;
    this.penetration = penetration;
    this.cards = [];
    for (let d = 0; d < decks; d++)
      for (let s = 0; s < 4; s++) for (let r = 0; r < 13; r++) this.cards.push({ r, s });
    this.shuffle();
  }
  shuffle() {
    const a = this.cards;
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(this.rng() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    this.pos = 0;
    this.cut = Math.floor(a.length * this.penetration);
  }
  draw() {
    if (this.pos >= this.cards.length) throw new Error("shoe exhausted mid-round");
    return this.cards[this.pos++];
  }
  get needsShuffle() {
    return this.pos >= this.cut;
  }
  get remaining() {
    return this.cards.length - this.pos;
  }
  get decksRemaining() {
    return Math.max(this.remaining / 52, 0.25);
  }
}

// -------------------------------------------------------------------- round
export class Hand {
  constructor(cards, bet, { fromSplit = false, splitAces = false } = {}) {
    this.cards = cards;
    this.bet = bet;
    this.fromSplit = fromSplit;
    this.splitAces = splitAces;
    this.doubled = false;
    this.done = false;
    this.result = null; // net profit once settled
  }
  get values() {
    return this.cards.map(cardValue);
  }
  get value() {
    return handValue(this.values);
  }
  get total() {
    return this.value.total;
  }
  get bust() {
    return this.total > 21;
  }
  get blackjack() {
    return this.cards.length === 2 && this.total === 21 && !this.fromSplit;
  }
}

/**
 * One table seat against the dealer. Usage:
 *   g.deal(bet) -> then while g.phase === "player": g.act("H" | "S" | "D" | "P")
 *   while g.phase === "dealer": g.dealerStep()   (UI animates between steps)
 */
export class Game {
  constructor(rules = DEFAULT_RULES, rng = Math.random) {
    this.rules = { ...rules };
    this.shoe = new Shoe(rules.decks, rules.penetration, rng);
    this.running = 0;
    this.phase = "idle";
    this.hands = [];
    this.dealer = [];
    this.holeRevealed = false;
    this.active = 0;
    this.net = 0;
    this.shuffledThisRound = false;
  }

  get trueCount() {
    return this.running / this.shoe.decksRemaining;
  }

  _draw(visible = true) {
    const c = this.shoe.draw();
    if (visible) this.running += hiLo(cardValue(c));
    return c;
  }

  deal(bet) {
    this.shuffledThisRound = false;
    if (this.shoe.needsShuffle) {
      this.shoe.shuffle();
      this.running = 0;
      this.shuffledThisRound = true;
    }
    this.betCount = this.running; // count at the moment the bet was placed
    this.betTrueCount = this.trueCount;
    const p1 = this._draw(),
      up = this._draw(),
      p2 = this._draw(),
      hole = this._draw(false);
    this.hands = [new Hand([p1, p2], bet)];
    this.dealer = [up, hole];
    this.holeRevealed = false;
    this.active = 0;
    this.net = 0;
    this.phase = "player";

    const dealerBJ = handValue(this.dealer.map(cardValue)).total === 21;
    const playerBJ = this.hands[0].blackjack;
    if (dealerBJ || playerBJ) {
      this._reveal();
      const h = this.hands[0];
      h.done = true;
      h.result = dealerBJ && playerBJ ? 0 : dealerBJ ? -bet : bet * this.rules.bjPayout;
      this.net = h.result;
      this.phase = "done";
      this.endReason = dealerBJ ? (playerBJ ? "push-bj" : "dealer-bj") : "player-bj";
    } else this.endReason = null;
    return this;
  }

  get upcard() {
    return cardValue(this.dealer[0]);
  }

  get hand() {
    return this.hands[this.active];
  }

  /** What the player may do right now. */
  legal() {
    if (this.phase !== "player") return { H: false, S: false, D: false, P: false };
    const h = this.hand;
    const two = h.cards.length === 2;
    const pair = two && cardValue(h.cards[0]) === cardValue(h.cards[1]);
    return {
      H: true,
      S: true,
      D: two && (!h.fromSplit || this.rules.das),
      P: pair && this.hands.length === 1,
    };
  }

  /** The decision in the form the strategy/EV code expects. */
  context() {
    const h = this.hand;
    const { total, soft } = h.value;
    const L = this.legal();
    return {
      total,
      soft,
      up: this.upcard,
      canDouble: L.D,
      canSplit: L.P,
      pairValue: L.P ? cardValue(h.cards[0]) : null,
      cards: h.values,
    };
  }

  act(a) {
    const L = this.legal();
    if (!L[a]) throw new Error(`illegal action ${a}`);
    const h = this.hand;
    if (a === "S") h.done = true;
    else if (a === "H") {
      h.cards.push(this._draw());
      if (h.total >= 21) h.done = true;
    } else if (a === "D") {
      h.bet *= 2;
      h.doubled = true;
      h.cards.push(this._draw());
      h.done = true;
    } else if (a === "P") {
      const aces = cardValue(h.cards[0]) === ACE;
      const second = new Hand([h.cards[1]], h.bet, { fromSplit: true, splitAces: aces });
      h.cards = [h.cards[0]];
      h.fromSplit = true;
      h.splitAces = aces;
      this.hands.push(second);
      h.cards.push(this._draw());
      if (aces || h.total === 21) h.done = true;
    }
    this._advance();
  }

  _advance() {
    while (this.hand.done) {
      if (this.active === this.hands.length - 1) {
        this.phase = "dealer";
        return;
      }
      this.active++;
      const h = this.hand;
      if (h.cards.length === 1) h.cards.push(this._draw());
      if (h.splitAces || h.total === 21) h.done = true;
    }
  }

  _reveal() {
    if (!this.holeRevealed) {
      this.holeRevealed = true;
      this.running += hiLo(cardValue(this.dealer[1]));
    }
  }

  dealerShouldHit() {
    const { total, soft } = handValue(this.dealer.map(cardValue));
    return total < 17 || (total === 17 && soft && this.rules.h17);
  }

  /** Advance the dealer by one visible step. Returns false when the round is over. */
  dealerStep() {
    if (this.phase !== "dealer") return false;
    if (!this.holeRevealed) {
      this._reveal();
      return true;
    }
    const anyLive = this.hands.some((h) => !h.bust);
    if (anyLive && this.dealerShouldHit()) {
      this.dealer.push(this._draw());
      return true;
    }
    this._settle();
    return false;
  }

  get dealerTotal() {
    const vals = (this.holeRevealed ? this.dealer : this.dealer.slice(0, 1)).map(cardValue);
    return handValue(vals).total;
  }

  _settle() {
    const d = handValue(this.dealer.map(cardValue)).total;
    this.net = 0;
    for (const h of this.hands) {
      const t = h.total;
      h.result = t > 21 ? -h.bet : d > 21 || t > d ? h.bet : t < d ? -h.bet : 0;
      this.net += h.result;
    }
    this.phase = "done";
  }
}
