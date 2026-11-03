"""Build docs/img/edge-by-count.svg, the animated chart at the top of the README.

Reads the billion-round C simulation summary in web/data/counting.json and
draws the player's edge per true count (with 95% confidence intervals), the
share of rounds dealt at each count, and the weighted linear fit. The SVG is
self-contained, animates with CSS, follows the viewer's light/dark theme and
is static under prefers-reduced-motion.

    python docs/make_hero_svg.py
"""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "web" / "data" / "counting.json"
OUT = ROOT / "docs" / "img" / "edge-by-count.svg"
TC_MIN, TC_MAX = -5, 6  # same window as the site's slope fit

W, H = 900, 360
L, R, T, B = 70, 30, 70, 56  # plot margins
Y_LO, Y_HI = -3.6, 3.4  # player edge, % of the bet
F_HI = 0.30  # frequency axis (share of rounds) for the background bars


def load():
    c = json.loads(DATA.read_text())
    rows = []
    for b in c["bins"]:
        if TC_MIN <= b["tc"] <= TC_MAX:
            var = max(b["m2"] - b["mean"] ** 2, 0.0)
            rows.append({"tc": b["tc"], "n": b["n"], "mean": 100 * b["mean"], "ci": 100 * 1.96 * math.sqrt(var / b["n"])})
    return c, rows


def wls(rows):
    sw = sum(r["n"] for r in rows)
    mx = sum(r["n"] * r["tc"] for r in rows) / sw
    my = sum(r["n"] * r["mean"] for r in rows) / sw
    sxx = sum(r["n"] * (r["tc"] - mx) ** 2 for r in rows)
    sxy = sum(r["n"] * (r["tc"] - mx) * (r["mean"] - my) for r in rows)
    slope = sxy / sxx
    return slope, my - slope * mx


def main():
    c, rows = load()
    slope, icept = wls(rows)
    zero_tc = -icept / slope
    total = c["rounds"]
    pw, ph = W - L - R, H - T - B
    step = pw / (TC_MAX - TC_MIN + 1)
    X = lambda tc: L + (tc - TC_MIN + 0.5) * step
    Y = lambda v: T + (Y_HI - v) / (Y_HI - Y_LO) * ph

    out = []
    a = out.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
      f'aria-label="Player edge by Hi-Lo true count over a billion simulated blackjack rounds: about {slope:+.2f}% per true count, breaking even near {zero_tc:+.1f}">')
    a("""<style>
  :root { --bg:#fbfaf6; --ink:#1d1f1e; --muted:#6b6f6c; --grid:#e4e2da; --bar:#e9e5d8; --pos:#0c8a0c; --neg:#d03b3b; --fit:#1f5fbf; --felt:#0e5a43; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#111614; --ink:#e8ebe9; --muted:#9aa39e; --grid:#26302c; --bar:#1e2a25; --pos:#3cc03c; --neg:#e66767; --fit:#6ea8ff; --felt:#1d8a68; }
  }
  text { font-family: Inter, "Segoe UI", Helvetica, Arial, sans-serif; fill: var(--ink); }
  .muted { fill: var(--muted); }
  .mono { font-family: "JetBrains Mono", ui-monospace, Menlo, Consolas, monospace; }
  .bar { fill: var(--bar); transform-box: fill-box; transform-origin: bottom; animation: grow .7s cubic-bezier(.2,.8,.2,1) both; }
  .pt { transform-box: fill-box; transform-origin: center; animation: pop .45s cubic-bezier(.3,1.6,.5,1) both; }
  .fit { stroke: var(--fit); stroke-width: 2.5; fill: none; stroke-dasharray: 900; stroke-dashoffset: 900; animation: draw 1.4s ease-out 1.5s forwards; }
  .late { opacity: 0; animation: fade .6s ease-out 2.6s forwards; }
  @keyframes grow { from { transform: scaleY(0); } }
  @keyframes pop { from { transform: scale(0); opacity: 0; } }
  @keyframes draw { to { stroke-dashoffset: 0; } }
  @keyframes fade { to { opacity: 1; } }
  @media (prefers-reduced-motion: reduce) {
    .bar, .pt, .late { animation: none; opacity: 1; }
    .fit { animation: none; stroke-dashoffset: 0; }
  }
</style>""")
    a(f'<rect width="{W}" height="{H}" rx="14" fill="var(--bg)"/>')
    a(f'<text x="{L}" y="32" font-size="17" font-weight="700">Card counting works, but the edge is thin</text>')
    a(f'<text x="{L}" y="52" font-size="12.5" class="muted">Player edge by Hi-Lo true count, {total / 1e9:.0f} billion simulated rounds of 6-deck H17 '
      f'with basic strategy · bars: share of rounds dealt at each count</text>')

    # grid and axes
    for v in range(-3, 4):
        y = Y(v)
        a(f'<line x1="{L}" x2="{W - R}" y1="{y:.1f}" y2="{y:.1f}" stroke="var(--grid)"/>')
        lab = "0%" if v == 0 else f"{v:+d}%"
        a(f'<text x="{L - 10}" y="{y + 4:.1f}" font-size="11" text-anchor="end" class="muted mono">{lab}</text>')
    a(f'<line x1="{L}" x2="{W - R}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" stroke="var(--muted)" stroke-width="1.2"/>')

    # frequency bars (background), staggered
    for i, r in enumerate(rows):
        share = r["n"] / total
        bh = share / F_HI * ph * 0.55
        a(f'<rect class="bar" style="animation-delay:{i * 45}ms" x="{X(r["tc"]) - step * 0.36:.1f}" y="{T + ph - bh:.1f}" '
          f'width="{step * 0.72:.1f}" height="{bh:.1f}" rx="3"/>')
        a(f'<text x="{X(r["tc"]):.1f}" y="{H - B + 18}" font-size="11.5" text-anchor="middle" class="mono">{r["tc"]:+d}</text>')
    a(f'<text x="{L + pw / 2:.0f}" y="{H - 12}" font-size="12" text-anchor="middle" class="muted">True count at the start of the round</text>')

    # fitted line
    x0, x1 = TC_MIN - 0.4, TC_MAX + 0.4
    a(f'<clipPath id="plot"><rect x="{L}" y="{T}" width="{pw}" height="{ph}"/></clipPath>')
    a(f'<path class="fit" clip-path="url(#plot)" d="M{X(x0):.1f},{Y(icept + slope * x0):.1f} L{X(x1):.1f},{Y(icept + slope * x1):.1f}"/>')

    # points with confidence intervals
    for i, r in enumerate(rows):
        col = "var(--pos)" if r["mean"] > 0 else "var(--neg)"
        x, y = X(r["tc"]), Y(r["mean"])
        a(f'<g class="pt" style="animation-delay:{600 + i * 70}ms">'
          f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{Y(r["mean"] + r["ci"]):.1f}" y2="{Y(r["mean"] - r["ci"]):.1f}" stroke="{col}" stroke-width="2"/>'
          f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="{col}"/></g>')

    # annotations
    zx = X(zero_tc)
    a(f'<g class="late"><line x1="{zx:.1f}" x2="{zx:.1f}" y1="{T}" y2="{T + ph}" stroke="var(--felt)" stroke-dasharray="4 4"/>'
      f'<text x="{zx + 8:.1f}" y="{T + 14}" font-size="12.5" font-weight="600" fill="var(--felt)">break-even ≈ {zero_tc:+.1f}</text>'
      f'<text x="{L + 12}" y="{T + 16}" font-size="13" font-weight="700" fill="var(--fit)">{slope:+.2f}% edge per +1 true count</text>'
      f'<text x="{L + 12}" y="{T + 33}" font-size="11.5" class="muted">house edge ignoring the count: {-100 * c["overall"]["mean"]:.3f}% ± {196 * c["overall"]["se"]:.3f}%</text></g>')
    a("</svg>")
    OUT.write_text("\n".join(out) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: slope {slope:+.3f}%/TC, break-even {zero_tc:+.2f}")


if __name__ == "__main__":
    main()
