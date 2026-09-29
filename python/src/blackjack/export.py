"""Serialise solver and simulation results for the web app and the C simulator."""

from __future__ import annotations

import json
import math
from dataclasses import asdict
from pathlib import Path

from .counting import CountingResult
from .exact import ExactSolver
from .solver import SolveResult


def _r(x: float, nd: int = 6):
    return None if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))) else round(x, nd)


def strategy_payload(result: SolveResult) -> dict:
    exact = ExactSolver(result.rules)
    mc_chart = result.strategy()
    states = []
    for (kind, total, up), st in sorted(result.states.items()):
        tb = exact.tables(up)
        ex = tb.pair_evs(total) if kind == "pair" else tb.action_evs(total, kind == "soft")
        states.append({
            "kind": kind, "total": total, "up": up,
            "code": st.code, "best": st.best,
            "mc": {a: [_r(e.mean), _r(e.se)] for a, e in st.evs.items()},
            "exact": {a: _r(v) for a, v in ex.items() if not math.isnan(v)},
            "margin": _r(st.margin), "margin_se": _r(st.margin_se),
        })
    return {
        "rules": asdict(result.rules),
        "n_per_action": result.n,
        "seed": result.seed,
        "house_edge_exact_optimal": _r(exact.round_ev()),
        "house_edge_exact_mc_chart": _r(ExactSolver(result.rules, mc_chart).round_ev()),
        "states": states,
    }


def counting_payload(result: CountingResult, source: str) -> dict:
    o = result.overall
    return {
        "source": source,
        "outcomes": [x / 2 for x in range(-8, 9)],
        "rounds": result.rounds,
        "shoes": result.shoes,
        "overall": {"mean": _r(o.mean, 7), "se": _r(o.se, 7), "sd": _r(math.sqrt(o.var), 5)},
        "bins": [
            {"tc": tc, "n": b.n, "mean": _r(b.mean, 7), "m2": _r(b.sumsq / b.n, 6),
             **({"hist": result.hist[tc]} if tc in result.hist else {})}
            for tc, b in sorted(result.bins.items())
        ],
    }


def write_json(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, separators=(",", ":")))
