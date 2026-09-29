// A deliberately small SVG plotting layer: scales, axes, lines, bands, error
// bars, bars and a hover crosshair. Each chart redraws from scratch on resize.

import { showTip, hideTip } from "./ui.js";

const NS = "http://www.w3.org/2000/svg";
const s = (tag, attrs = {}) => {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v != null) el.setAttribute(k, v);
  return el;
};

export function niceTicks(lo, hi, count = 5) {
  if (!(hi > lo)) return [lo];
  const span = hi - lo;
  const step0 = span / count;
  const mag = 10 ** Math.floor(Math.log10(step0));
  const err = step0 / mag;
  const step = (err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1) * mag;
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) out.push(+v.toFixed(12));
  return out;
}

export function extent(values, pad = 0.06) {
  let lo = Infinity,
    hi = -Infinity;
  for (const v of values) if (Number.isFinite(v)) (lo = Math.min(lo, v)), (hi = Math.max(hi, v));
  if (!Number.isFinite(lo)) return [0, 1];
  if (lo === hi) return [lo - 1, hi + 1];
  const p = (hi - lo) * pad;
  return [lo - p, hi + p];
}

/** Re-run `draw` whenever the container is resized (debounced to one frame). */
export function responsive(el, draw) {
  let raf = 0;
  const ro = new ResizeObserver(() => {
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(draw);
  });
  ro.observe(el);
  return () => ro.disconnect();
}

export class Plot {
  constructor(el, { x, y, margin = {} }) {
    this.el = el;
    this.x = { type: "linear", format: (v) => String(v), ...x };
    this.y = { type: "linear", format: (v) => String(v), ...y };
    this.m = { top: 12, right: 16, bottom: 36, left: 54, ...margin };
    el.innerHTML = "";
    const W = Math.max(el.clientWidth, 200),
      H = Math.max(el.clientHeight, 100);
    this.W = W;
    this.H = H;
    this.iw = W - this.m.left - this.m.right;
    this.ih = H - this.m.top - this.m.bottom;
    this.svg = s("svg", { viewBox: `0 0 ${W} ${H}`, role: "img" });
    if (x.ariaLabel) this.svg.setAttribute("aria-label", x.ariaLabel);
    el.append(this.svg);
    this.root = s("g", { transform: `translate(${this.m.left},${this.m.top})` });
    this.svg.append(this.root);
    const clipId = `clip${Math.random().toString(36).slice(2)}`;
    const defs = s("defs");
    const cp = s("clipPath", { id: clipId });
    cp.append(s("rect", { x: 0, y: -4, width: this.iw, height: this.ih + 8 }));
    defs.append(cp);
    this.svg.append(defs);
    this.gridG = s("g", { class: "grid" });
    this.axisG = s("g", { class: "axis" });
    this.plotG = s("g", { "clip-path": `url(#${clipId})` });
    this.topG = s("g");
    this.root.append(this.gridG, this.axisG, this.plotG, this.topG);
    this._axes();
  }

  sx(v) {
    const [a, b] = this.x.domain;
    if (this.x.type === "log") return ((Math.log10(v) - Math.log10(a)) / (Math.log10(b) - Math.log10(a))) * this.iw;
    if (this.x.type === "band") return this.bandX(v);
    return ((v - a) / (b - a)) * this.iw;
  }
  sy(v) {
    const [a, b] = this.y.domain;
    return this.ih - ((v - a) / (b - a)) * this.ih;
  }
  bandX(v) {
    const cats = this.x.domain;
    const i = cats.indexOf(v);
    const bw = this.iw / cats.length;
    return i * bw + bw / 2;
  }
  get bandWidth() {
    return this.iw / this.x.domain.length;
  }

  _axes() {
    const { iw, ih } = this;
    // y
    const yt = this.y.ticks || niceTicks(...this.y.domain, Math.max(3, Math.floor(ih / 55)));
    for (const t of yt) {
      const y = this.sy(t);
      this.gridG.append(s("line", { x1: 0, x2: iw, y1: y, y2: y }));
      const tx = s("text", { x: -8, y, "text-anchor": "end", "dominant-baseline": "middle" });
      tx.textContent = this.y.format(t);
      this.axisG.append(tx);
    }
    // x
    let xt;
    if (this.x.type === "band") xt = this.x.domain;
    else if (this.x.type === "log") {
      xt = [];
      for (let p = Math.ceil(Math.log10(this.x.domain[0])); p <= Math.log10(this.x.domain[1]) + 1e-9; p++) xt.push(10 ** p);
    } else xt = this.x.ticks || niceTicks(...this.x.domain, Math.max(3, Math.floor(iw / 80)));
    this.axisG.append(s("line", { x1: 0, x2: iw, y1: ih, y2: ih }));
    const every = this.x.type === "band" ? Math.ceil(xt.length / Math.max(1, Math.floor(iw / 34))) : 1;
    xt.forEach((t, i) => {
      if (i % every) return;
      const x = this.sx(t);
      const tx = s("text", { x, y: ih + 16, "text-anchor": "middle" });
      tx.textContent = this.x.format(t);
      this.axisG.append(tx);
    });
    if (this.x.label) {
      const t = s("text", { class: "axis-title", x: iw / 2, y: ih + 32, "text-anchor": "middle" });
      t.textContent = this.x.label;
      this.axisG.append(t);
    }
    if (this.y.label) {
      const t = s("text", { class: "axis-title", transform: `translate(${-this.m.left + 12},${ih / 2}) rotate(-90)`, "text-anchor": "middle" });
      t.textContent = this.y.label;
      this.axisG.append(t);
    }
  }

  hline(y, { color = "var(--ink-2)", dash = "4 4", width = 1.25, label, opacity = 1 } = {}) {
    const yy = this.sy(y);
    this.plotG.append(s("line", { x1: 0, x2: this.iw, y1: yy, y2: yy, stroke: color, "stroke-width": width, "stroke-dasharray": dash, opacity }));
    if (label) {
      const t = s("text", { x: this.iw - 4, y: yy - 5, "text-anchor": "end", fill: color, "font-size": 11, "font-family": "var(--font)" });
      t.textContent = label;
      this.topG.append(t);
    }
  }

  vline(x, { color = "var(--ink-2)", dash = "3 3" } = {}) {
    const xx = this.sx(x);
    this.plotG.append(s("line", { x1: xx, x2: xx, y1: 0, y2: this.ih, stroke: color, "stroke-dasharray": dash }));
  }

  line(pts, { color, width = 2, dash, opacity = 1 } = {}) {
    if (pts.length < 2) return;
    const d = pts.map((p, i) => `${i ? "L" : "M"}${this.sx(p.x).toFixed(1)},${this.sy(p.y).toFixed(1)}`).join("");
    this.plotG.append(s("path", { d, fill: "none", stroke: color, "stroke-width": width, "stroke-dasharray": dash, "stroke-linejoin": "round", opacity }));
  }

  band(pts, { color, opacity = 0.16 } = {}) {
    if (pts.length < 2) return;
    const top = pts.map((p, i) => `${i ? "L" : "M"}${this.sx(p.x).toFixed(1)},${this.sy(p.hi).toFixed(1)}`).join("");
    const bot = pts
      .slice()
      .reverse()
      .map((p) => `L${this.sx(p.x).toFixed(1)},${this.sy(p.lo).toFixed(1)}`)
      .join("");
    this.plotG.append(s("path", { d: top + bot + "Z", fill: color, opacity, stroke: "none" }));
  }

  errorPoints(pts, { color, r = 4 } = {}) {
    for (const p of pts) {
      const x = this.sx(p.x);
      this.plotG.append(s("line", { x1: x, x2: x, y1: this.sy(p.lo), y2: this.sy(p.hi), stroke: color, "stroke-width": 1.5 }));
      this.plotG.append(s("line", { x1: x - 3, x2: x + 3, y1: this.sy(p.lo), y2: this.sy(p.lo), stroke: color, "stroke-width": 1.5 }));
      this.plotG.append(s("line", { x1: x - 3, x2: x + 3, y1: this.sy(p.hi), y2: this.sy(p.hi), stroke: color, "stroke-width": 1.5 }));
      this.plotG.append(s("circle", { cx: x, cy: this.sy(p.y), r, fill: color, stroke: "var(--surface)", "stroke-width": 2 }));
    }
  }

  bars(pts, { color, widthFrac = 0.62, colorFn } = {}) {
    const bw = (this.x.type === "band" ? this.bandWidth : this.iw / pts.length) * widthFrac;
    const y0 = this.sy(Math.max(this.y.domain[0], 0));
    for (const p of pts) {
      const x = this.sx(p.x) - bw / 2;
      const y = this.sy(p.y);
      const top = Math.min(y, y0),
        hgt = Math.max(1, Math.abs(y0 - y));
      const r = Math.min(4, bw / 2);
      // rounded data end, square base
      const d =
        p.y >= 0
          ? `M${x},${top + hgt}V${top + r}Q${x},${top} ${x + r},${top}H${x + bw - r}Q${x + bw},${top} ${x + bw},${top + r}V${top + hgt}Z`
          : `M${x},${top}V${top + hgt - r}Q${x},${top + hgt} ${x + r},${top + hgt}H${x + bw - r}Q${x + bw},${top + hgt} ${x + bw},${top + hgt - r}V${top}Z`;
      this.plotG.append(s("path", { d, fill: colorFn ? colorFn(p) : color }));
    }
  }

  text(x, y, str, { anchor = "start", color = "var(--ink-2)", size = 11, dy = 0 } = {}) {
    const t = s("text", { x: this.sx(x), y: this.sy(y) + dy, "text-anchor": anchor, fill: color, "font-size": size, "font-family": "var(--font)" });
    t.textContent = str;
    this.topG.append(t);
  }

  /** Crosshair + tooltip. `pick(xValue)` returns {x, html} for the nearest datum or null. */
  hover(pick, { invert } = {}) {
    const overlay = s("rect", { x: 0, y: 0, width: this.iw, height: this.ih, fill: "transparent" });
    const cross = s("line", { y1: 0, y2: this.ih, stroke: "var(--ink-2)", "stroke-width": 1, opacity: 0 });
    this.topG.append(cross, overlay);
    const toX = invert || ((px) => this.invertX(px));
    const move = (ev) => {
      const pt = this.svg.getBoundingClientRect();
      const scale = this.W / pt.width;
      const px = (ev.clientX - pt.left) * scale - this.m.left;
      const hit = pick(toX(px));
      if (!hit) return leave();
      const cx = this.sx(hit.x);
      cross.setAttribute("x1", cx);
      cross.setAttribute("x2", cx);
      cross.setAttribute("opacity", 0.5);
      showTip(hit.html, ev.clientX, ev.clientY);
    };
    const leave = () => {
      cross.setAttribute("opacity", 0);
      hideTip();
    };
    overlay.addEventListener("pointermove", move);
    overlay.addEventListener("pointerleave", leave);
    overlay.addEventListener("pointerdown", move);
  }

  invertX(px) {
    const [a, b] = this.x.domain;
    const f = px / this.iw;
    if (this.x.type === "log") return 10 ** (Math.log10(a) + f * (Math.log10(b) - Math.log10(a)));
    if (this.x.type === "band") {
      const i = Math.max(0, Math.min(this.x.domain.length - 1, Math.floor(px / this.bandWidth)));
      return this.x.domain[i];
    }
    return a + f * (b - a);
  }
}

/** Small inline sparkline (no axes). */
export function sparkline(el, values, { color = "var(--felt)" } = {}) {
  el.innerHTML = "";
  if (values.length < 2) return;
  const W = el.clientWidth || 280,
    H = el.clientHeight || 56;
  const [lo, hi] = extent([...values, 0], 0.1);
  const X = (i) => (i / (values.length - 1)) * (W - 4) + 2;
  const Y = (v) => H - 2 - ((v - lo) / (hi - lo)) * (H - 4);
  const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: "100%" });
  svg.append(s("line", { x1: 0, x2: W, y1: Y(0), y2: Y(0), stroke: "var(--line-2)", "stroke-dasharray": "3 3" }));
  svg.append(s("path", { d: values.map((v, i) => `${i ? "L" : "M"}${X(i)},${Y(v)}`).join(""), fill: "none", stroke: color, "stroke-width": 2 }));
  el.append(svg);
}
