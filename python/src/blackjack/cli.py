"""Command-line entry point.

    python -m blackjack solve   [--n 2000000]      # MC solver -> web/data/strategy.{json,csv}
    python -m blackjack count   [--rounds 1000000] # Python shoe simulation
    python -m blackjack count   --from-c FILE      # import the C simulator's output
    python -m blackjack chart                      # print the exact and MC charts
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from .counting import BinStats, CountingResult, simulate
from .exact import ExactSolver
from .export import counting_payload, strategy_payload, write_json
from .rules import Rules
from .solver import solve
from .strategy import HARD_TOTALS, PAIR_VALUES, SOFT_TOTALS, UPCARDS, BasicStrategy

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "web" / "data"


def print_chart(s: BasicStrategy, title: str) -> None:
    up_labels = " ".join(f"{'A' if u == 11 else u:>3}" for u in UPCARDS)
    print(f"\n{title}\n{'':8}{up_labels}")
    for t in HARD_TOTALS[4:14]:
        print(f"hard {t:<3}" + " ".join(f"{s.hard[(t, u)]:>3}" for u in UPCARDS))
    for t in SOFT_TOTALS[1:9]:
        print(f"A,{t - 11:<5} " + " ".join(f"{s.soft[(t, u)]:>3}" for u in UPCARDS))
    for v in PAIR_VALUES:
        lab = "A" if v == 11 else v
        print(f"{lab},{lab:<5} " + " ".join(f"{'P' if s.pairs[(v, u)] else '-':>3}" for u in UPCARDS))


def cmd_solve(a) -> None:
    rules = Rules()
    t0 = time.time()
    res = solve(rules, n=a.n, seed=a.seed, processes=a.processes)
    payload = strategy_payload(res)
    write_json(payload, DATA / "strategy.json")
    res.strategy().save_csv(DATA / "strategy.csv")
    print_chart(res.strategy(), f"Monte Carlo chart ({a.n:,} hands per action, {time.time() - t0:.0f}s)")
    print(f"\nExact EV of optimal play:  {payload['house_edge_exact_optimal']:+.4%}")
    print(f"Exact EV of the MC chart:  {payload['house_edge_exact_mc_chart']:+.4%}")
    print(f"Wrote {DATA / 'strategy.json'} and strategy.csv")


def read_c_output(path: Path) -> CountingResult:
    r = CountingResult()
    with open(path) as f:
        rows = [line for line in f if not line.startswith("#")]
    for row in csv.DictReader(rows):
        if row["tc"] == "meta":
            r.rounds, r.shoes = int(row["n"]), int(float(row["sum"]))
            continue
        tc = int(row["tc"])
        r.bins[tc] = BinStats(int(row["n"]), float(row["sum"]), float(row["sumsq"]))
        hist_cols = [k for k in row if k.startswith("h")]
        if hist_cols:
            r.hist[tc] = [int(row[k]) for k in hist_cols]
    return r


def cmd_count(a) -> None:
    if a.from_c:
        res = read_c_output(Path(a.from_c))
        source = "C simulator"
    else:
        strategy = BasicStrategy.load_csv(DATA / "strategy.csv")
        res = simulate(Rules(), strategy, a.rounds, a.seed)
        source = "Python simulator"
    o = res.overall
    print(f"{res.rounds:,} rounds, {res.shoes:,} shoes: edge {o.mean:+.3%} ± {1.96 * o.se:.3%} (95% CI)")
    for tc, b in sorted(res.bins.items()):
        if b.n > 1000:
            print(f"  TC {tc:+3d}: {b.mean:+.3%} ± {1.96 * b.se:.3%}  ({b.n / res.rounds:.1%} of rounds)")
    if a.write:
        write_json(counting_payload(res, source), DATA / "counting.json")
        print(f"Wrote {DATA / 'counting.json'}")


def cmd_chart(a) -> None:
    print_chart(ExactSolver().optimal_strategy(), "Exact infinite-deck optimum")
    if (DATA / "strategy.csv").exists():
        print_chart(BasicStrategy.load_csv(DATA / "strategy.csv"), "Monte Carlo chart (web/data/strategy.csv)")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="blackjack-mc", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("solve", help="Monte Carlo basic strategy")
    s.add_argument("--n", type=int, default=2_000_000, help="hands per state-action")
    s.add_argument("--seed", type=int, default=2026)
    s.add_argument("--processes", type=int, default=None)
    s.set_defaults(fn=cmd_solve)

    c = sub.add_parser("count", help="Hi-Lo shoe simulation")
    c.add_argument("--rounds", type=int, default=1_000_000)
    c.add_argument("--seed", type=int, default=1)
    c.add_argument("--from-c", help="CSV written by the C simulator")
    c.add_argument("--write", action="store_true", help="write web/data/counting.json")
    c.set_defaults(fn=cmd_count)

    sub.add_parser("chart", help="print strategy charts").set_defaults(fn=cmd_chart)

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
