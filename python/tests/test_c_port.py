"""The C simulator must reproduce the Python reference statistically."""

import math
import shutil
import subprocess
from pathlib import Path

import pytest

from blackjack.cli import read_c_output
from blackjack.counting import simulate
from blackjack.rules import Rules
from blackjack.strategy import reference_chart

C_DIR = Path(__file__).resolve().parents[2] / "C"
BIN = C_DIR / "bin" / "bjsim"


@pytest.fixture(scope="module")
def c_result(tmp_path_factory):
    if not BIN.exists():
        if shutil.which("make") is None:
            pytest.skip("C simulator not built and make unavailable")
        subprocess.run(["make", "-C", str(C_DIR)], check=True, capture_output=True)
    tmp = tmp_path_factory.mktemp("c")
    reference_chart().save_csv(tmp / "s.csv")
    subprocess.run(
        [str(BIN), "--rounds", "4000000", "--threads", "2", "--seed", "3",
         "--strategy", str(tmp / "s.csv"), "--out", str(tmp / "out.csv")],
        check=True, capture_output=True,
    )
    return read_c_output(tmp / "out.csv")


@pytest.fixture(scope="module")
def py_result():
    return simulate(Rules(), reference_chart(), rounds=200_000, seed=9)


def test_same_house_edge(c_result, py_result):
    c, p = c_result.overall, py_result.overall
    z = (c.mean - p.mean) / math.hypot(c.se, p.se)
    assert abs(z) < 4


def test_same_true_count_distribution(c_result, py_result):
    for tc in range(-3, 4):
        fc = c_result.bins[tc].n / c_result.rounds
        fp = py_result.bins[tc].n / py_result.rounds
        assert abs(fc - fp) < 0.01, tc


def test_same_per_count_ev(c_result, py_result):
    for tc in range(-2, 3):
        c, p = c_result.bins[tc], py_result.bins[tc]
        assert abs(c.mean - p.mean) < 4 * math.hypot(c.se, p.se), tc
