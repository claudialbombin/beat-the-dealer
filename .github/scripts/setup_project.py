#!/usr/bin/env python3
"""
setup_project.py  —  Create the Beat the Dealer GitHub Project board.

This script is called by the  setup-project.yml  workflow (workflow_dispatch).
It uses the  gh  CLI (authenticated via GITHUB_TOKEN) to:

  1. Create issue labels.
  2. Create a GitHub Projects v2 board.
  3. Link the board to this repository.
  4. Add custom fields: Priority, Component, Phase.
  5. Create ~20 richly-documented GitHub Issues.
  6. Add every issue to the project with field values.

Run manually (requires  gh auth login  first):
    python .github/scripts/setup_project.py --owner <login> --repo <name>
"""

import json
import subprocess
import sys
import textwrap
import argparse
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return its CompletedProcess."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"ERROR running: {' '.join(cmd)}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return result


def gh(*args: str, check: bool = True) -> dict | str:
    """Run  gh <args>  and return parsed JSON if --format json was passed."""
    cmd = ["gh"] + list(args)
    result = run(cmd, check=check)
    if "--format" in args and "json" in args:
        return json.loads(result.stdout)
    return result.stdout.strip()


def graphql(query: str, **variables: str) -> dict:
    """Run a GitHub GraphQL mutation/query."""
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        cmd += ["-f", f"{k}={v}"]
    result = run(cmd)
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------

LABELS = [
    # name,            hex colour,  description
    ("simulation",        "0075ca", "Game simulation engine & logic"),
    ("card-counting",     "2ea44f", "Hi-Lo & other counting systems"),
    ("visualization",     "d93f0b", "Data plots & interactive dashboards"),
    ("testing",           "e4e669", "Test coverage & quality assurance"),
    ("documentation",     "f9d0c4", "Docs, comments & explanations"),
    ("c-implementation",  "c5def5", "C language port of the engine"),
    ("ci-cd",             "0e8a16", "Automation, CI/CD & tooling"),
    ("performance",       "fbca04", "Speed, memory & benchmarking"),
    ("phase-2",           "b60205", "Phase 2 — Enhancement"),
    ("phase-3",           "0052cc", "Phase 3 — Advanced Features"),
    ("ongoing",           "5319e7", "Ongoing maintenance task"),
    ("good-first-issue",  "7057ff", "Good starting point for contributors"),
    ("help-wanted",       "008672", "Extra attention needed"),
]


def create_labels(owner: str, repo: str) -> None:
    print("\n── Creating labels ───────────────────────────────────────────────")
    for name, color, description in LABELS:
        gh("label", "create", name,
           "--color", color,
           "--description", description,
           "--repo", f"{owner}/{repo}",
           "--force")
        print(f"  ✓ {name}")


# ---------------------------------------------------------------------------
# Project board
# ---------------------------------------------------------------------------

def create_project(owner: str) -> tuple[int, str, str]:
    """Return (number, id, url)."""
    print("\n── Creating project board ────────────────────────────────────────")
    data = gh("project", "create",
              "--owner", owner,
              "--title", "Beat the Dealer - Development Roadmap",
              "--format", "json")
    number = data["number"]
    project_id = data["id"]
    url = data["url"]
    print(f"  ✓ Created: {url}")
    return number, project_id, url


def link_project_to_repo(owner: str, repo: str, project_id: str) -> None:
    print("\n── Linking project to repository ─────────────────────────────────")
    repo_node_id = gh("api", f"repos/{owner}/{repo}", "--jq", ".node_id")
    graphql(
        """
        mutation($projectId: ID!, $repositoryId: ID!) {
          linkProjectV2ToRepository(input: {
            projectId: $projectId
            repositoryId: $repositoryId
          }) {
            repository { nameWithOwner }
          }
        }
        """,
        projectId=project_id,
        repositoryId=repo_node_id,
    )
    print(f"  ✓ Linked to {owner}/{repo}")


# ---------------------------------------------------------------------------
# Custom fields
# ---------------------------------------------------------------------------

@dataclass
class FieldConfig:
    name: str
    options: list[str]
    field_id: str = ""
    option_ids: dict[str, str] = field(default_factory=dict)


def create_fields(project_number: int, owner: str) -> dict[str, FieldConfig]:
    """Create single-select fields; return a mapping of field_name → FieldConfig."""
    print("\n── Adding custom fields ──────────────────────────────────────────")

    configs = {
        "Priority":  FieldConfig("Priority",  ["Critical", "High", "Medium", "Low"]),
        "Component": FieldConfig("Component", [
            "Simulation Engine", "Card Counting", "Visualization",
            "Testing", "Documentation", "C Implementation", "CI-CD", "Performance",
        ]),
        "Phase": FieldConfig("Phase", [
            "Phase 1: Foundation (Done)",
            "Phase 2: Enhancement",
            "Phase 3: Advanced",
            "Ongoing",
        ]),
    }

    for cfg in configs.values():
        data = gh(
            "project", "field-create", str(project_number),
            "--owner", owner,
            "--name", cfg.name,
            "--data-type", "SINGLE_SELECT",
            "--single-select-options", ",".join(cfg.options),
            "--format", "json",
        )
        cfg.field_id = data["id"]
        cfg.option_ids = {opt["name"]: opt["id"] for opt in data["options"]}
        print(f"  ✓ {cfg.name}: {list(cfg.option_ids.keys())}")

    return configs


# ---------------------------------------------------------------------------
# Issue + project-item creation
# ---------------------------------------------------------------------------

def create_issue(owner: str, repo: str, title: str, body: str, labels: list[str]) -> str:
    """Create a GitHub Issue; return its URL."""
    data = gh(
        "issue", "create",
        "--repo", f"{owner}/{repo}",
        "--title", title,
        "--body", textwrap.dedent(body).strip(),
        "--label", ",".join(labels),
        "--format", "json",
    )
    return data["url"]


def add_to_project(
    owner: str,
    project_number: int,
    project_id: str,
    issue_url: str,
    fields: dict[str, FieldConfig],
    priority: str,
    component: str,
    phase: str,
) -> None:
    """Add a GitHub Issue to the project and set its custom field values."""
    item_data = gh(
        "project", "item-add", str(project_number),
        "--owner", owner,
        "--url", issue_url,
        "--format", "json",
    )
    item_id = item_data["id"]

    for field_name, option_name in [
        ("Priority", priority),
        ("Component", component),
        ("Phase", phase),
    ]:
        cfg = fields[field_name]
        option_id = cfg.option_ids.get(option_name)
        if option_id:
            gh(
                "project", "item-edit",
                "--id", item_id,
                "--project-id", project_id,
                "--field-id", cfg.field_id,
                "--single-select-option-id", option_id,
            )


# ---------------------------------------------------------------------------
# Issue catalogue
# ---------------------------------------------------------------------------

@dataclass
class IssueSpec:
    title: str
    body: str
    labels: list[str]
    priority: str    # must match an option in the Priority field
    component: str   # must match an option in the Component field
    phase: str       # must match an option in the Phase field


ISSUES: list[IssueSpec] = [

    # =========================================================================
    # PHASE 2 — Enhancement
    # =========================================================================

    IssueSpec(
        title="[Testing] Improve card_counting.py test coverage: 58% → 90%+",
        body="""
            ## Overview

            The `card_counting.py` module currently has **58% line coverage** (as measured by
            `pytest --cov`). This is the lowest-covered module in the codebase and represents a
            significant quality gap.

            ## Why It Matters

            Card counting is the *core novelty* of this project — it transforms a basic Monte Carlo
            simulation into a strategy that can actually beat the dealer. Untested code paths could
            hide bugs in the counting logic, true-count calculation, bet-sizing formulas, or
            performance-metric output. A 58% coverage rate means nearly half the code is never
            exercised by automated tests.

            ## Current State

            | Attribute | Value |
            |-----------|-------|
            | Module | `python/src/card_counting.py` |
            | Test file | `python/tests/test_card_counting.py` |
            | Current coverage | **58%** |
            | Target coverage | **≥ 90%** |

            Run the current coverage report:
            ```bash
            cd python && python -m pytest tests/test_card_counting.py \\
              --cov=src/card_counting --cov-report=term-missing -v
            ```

            ## Acceptance Criteria

            - [ ] `pytest --cov=src/card_counting` reports ≥ 90% line coverage.
            - [ ] All Hi-Lo tag assignments (+1, 0, −1) are exercised for every rank (2–A).
            - [ ] Running-count accumulation tested across ≥ 3 different multi-deck shoes.
            - [ ] True-count formula `TC = RC / decks_remaining` tested at boundary values
                  (RC=0, RC positive, RC negative, decks_remaining approaching 0).
            - [ ] Bet-spread logic tested: minimum bet at TC ≤ 1, scaled bets at TC 2–6.
            - [ ] Player-advantage estimation `−0.5% + 0.5% × TC` verified for representative counts.
            - [ ] Edge case: zero remaining decks handled gracefully (no `ZeroDivisionError`).
            - [ ] All new tests pass in CI.

            ## Key Symbols to Target

            | Symbol | Likely gap |
            |--------|-----------|
            | `HiLoCounter.update(card)` | Cards 7/8/9 (count = 0) rarely tested explicitly |
            | `HiLoCounter.true_count` | Near-zero `decks_remaining` not tested |
            | `BettingStrategy.bet_size(tc)` | TC ≤ 0 and TC > 6 extremes |
            | `CountingSimulation.simulate_shoe()` | Cut-card / `None` return paths |
            | Performance metric helpers | Rarely exercised aggregate paths |

            ## How to Verify

            1. Run `pytest --cov=src/card_counting --cov-report=html`.
            2. Open `htmlcov/index.html` and confirm ≥ 90%.
            3. Review each new test for readability and correctness.

            ## References

            - `python/tests/test_card_counting.py`
            - `python/src/card_counting.py`
        """,
        labels=["testing", "card-counting", "phase-2"],
        priority="High",
        component="Testing",
        phase="Phase 2: Enhancement",
    ),

    IssueSpec(
        title="[Testing] Improve monte_carlo_solver.py test coverage: 54% → 90%+",
        body="""
            ## Overview

            `monte_carlo_solver.py` has the **lowest coverage** in the project at 54%. This module
            contains the Monte Carlo expected-value engine — the most computationally critical piece
            of the codebase. Gaps here could mean silent errors in the strategy table that every
            other feature depends on.

            ## Why It Matters

            The Monte Carlo solver:
            - Simulates millions of blackjack hands to estimate expected values (EVs).
            - Selects the optimal action (Hit / Stand / Double / Split) for every game state.
            - Builds the 340-entry basic-strategy table that drives the counting simulation.

            A bug hidden in an untested branch could produce an incorrect strategy table and
            invalidate *all downstream EV analysis* without any obvious error signal.

            ## Current State

            | Attribute | Value |
            |-----------|-------|
            | Module | `python/src/monte_carlo_solver.py` |
            | Test file | `python/tests/test_monte_carlo_solver.py` |
            | Current coverage | **54%** |
            | Target coverage | **≥ 90%** |

            ```bash
            cd python && python -m pytest tests/test_monte_carlo_solver.py \\
              --cov=src/monte_carlo_solver --cov-report=term-missing -v
            ```

            ## Acceptance Criteria

            - [ ] Line coverage ≥ 90% for `monte_carlo_solver.py`.
            - [ ] All four actions (Hit, Stand, Double, Split) exercised as optimal outcomes
                  in at least one test each.
            - [ ] Soft-hand states (Ace + X) covered — they have different optimal strategies
                  than hard hands.
            - [ ] Split-pair states covered (A+A, 8+8, 10+10, etc.).
            - [ ] Convergence test: EV estimates stabilize within ±1% after 10 000 simulations.
            - [ ] Parallel-processing path tested alongside the sequential path.
            - [ ] `None` return from `Shoe.deal()` (cut-card) handled without crash mid-simulation.
            - [ ] All tests complete in < 60 s with `N_SIMS=1000` (fast mode).

            ## Key Symbols to Target

            | Symbol | Likely gap |
            |--------|-----------|
            | `MonteCarloSolver.solve_state(state, action='split')` | Split action for non-pair hands |
            | `MonteCarloSolver._simulate_split()` | Multi-hand split sequences |
            | `MonteCarloSolver.build_strategy_table()` | State enumeration edge cases |
            | Parallel worker functions | Rarely triggered in unit-test context |

            ## How to Verify

            1. `pytest tests/test_monte_carlo_solver.py --cov=src/monte_carlo_solver --cov-report=html`
            2. Confirm ≥ 90% in the HTML report.
            3. Ensure no test relies on a hardcoded seed that makes coverage artificially easy.

            ## References

            - `python/src/monte_carlo_solver.py`
            - `python/tests/test_monte_carlo_solver.py`
            - Edward Thorp — *Beat the Dealer*, Ch. 4 (strategy derivation)
        """,
        labels=["testing", "simulation", "phase-2"],
        priority="High",
        component="Testing",
        phase="Phase 2: Enhancement",
    ),

    IssueSpec(
        title="[Testing] Add integration tests for full-shoe simulation lifecycle",
        body="""
            ## Overview

            Unit tests verify individual functions in isolation. But the real correctness criterion
            is: *does a complete shoe simulation — from shuffle to reshuffle — produce statistically
            sound results?* Integration tests answer this question.

            ## Why It Matters

            - Several bugs only appear when multiple modules interact (e.g., the cut-card signal
              from `Shoe.deal()` propagating correctly through `BlackjackGame`, the counting state
              updating in lock-step with dealt cards).
            - Integration tests catch regressions that unit tests miss by exercising the full
              call stack.
            - They serve as living documentation of the intended end-to-end behaviour.

            ## Proposed Scenarios

            ### Scenario 1 — Shoe lifecycle
            1. Create a 6-deck shoe with 75% penetration.
            2. Simulate hands until `shoe.deal()` returns `None`.
            3. Assert total dealt cards ≈ 75% of 312 (±5 cards).
            4. Assert running count and true count update correctly throughout.
            5. Assert reshuffling resets the running count to 0.

            ### Scenario 2 — Count-driven bet sizing end-to-end
            1. Force-feed cards to create a known high true count (remove all low cards).
            2. Run `CountingSimulation.simulate_shoe()`.
            3. Assert bet amounts at high TC ≥ bet amounts at TC=0.
            4. Assert player advantage estimate is positive at TC ≥ +2.

            ### Scenario 3 — Strategy table correctness spot-checks
            Run the solver at `N_SIMS=5000` and assert these known-correct decisions:

            | Hand | Dealer | Expected action |
            |------|--------|----------------|
            | Hard 16 | 10 | Hit |
            | Hard 16 | 6 | Stand |
            | Soft 18 | 10 | Hit |
            | A+A | any | Split |
            | 8+8 | any | Split |
            | 10+10 | any | Stand (never split) |

            ### Scenario 4 — Statistical property
            1. Run a 1 000-shoe simulation.
            2. Assert overall return at TC=0 is within [−1.5%, +0.5%] (standard house-edge range).
            3. Assert Pearson correlation between TC and EV is positive (r > 0.7).

            ## Acceptance Criteria

            - [ ] All 4 scenarios implemented as `pytest` test cases.
            - [ ] Tests marked `@pytest.mark.integration`; skippable with `-m 'not integration'`.
            - [ ] Total runtime of integration suite ≤ 5 minutes.
            - [ ] No hardcoded magic numbers — assertions use computed tolerance bounds.

            ## References

            - `python/src/game_engine.py` — `BlackjackGame`, `Shoe`
            - `python/src/card_counting.py` — `CountingSimulation`
            - `python/src/monte_carlo_solver.py` — `MonteCarloSolver`
        """,
        labels=["testing", "simulation", "card-counting", "phase-2"],
        priority="High",
        component="Testing",
        phase="Phase 2: Enhancement",
    ),

    IssueSpec(
        title="[CI/CD] Set up GitHub Actions CI/CD pipeline",
        body="""
            ## Overview

            There is currently no automated Continuous Integration (CI) pipeline. Adding one is
            the highest-leverage quality improvement available: it makes every pull request safe
            to merge and turns the test suite from a manual chore into an automatic gate.

            ## Why It Matters

            Without CI:
            - Contributors must remember to run tests locally before pushing.
            - Coverage regressions go undetected.
            - Style drift and type errors accumulate silently.

            With CI, every push and PR will automatically:
            1. Run the full `pytest` suite.
            2. Report per-module coverage and fail if it drops below a threshold.
            3. Run `mypy` type-checking.
            4. Run `black --check` and `flake8` linting.
            5. Build the C implementation and verify it compiles without warnings.

            ## Proposed Workflow: `.github/workflows/ci.yml`

            ```yaml
            name: CI
            on: [push, pull_request]
            jobs:
              python-tests:
                runs-on: ubuntu-latest
                strategy:
                  matrix:
                    python-version: ['3.9', '3.11', '3.12']
                steps:
                  - uses: actions/checkout@v4
                  - uses: actions/setup-python@v5
                    with: { python-version: '${{ matrix.python-version }}' }
                  - run: pip install -r python/requirements.txt
                  - run: cd python && python -m pytest tests/ --cov=src --cov-fail-under=85
                  - run: cd python && python -m mypy src/
                  - run: cd python && python -m black --check src/ tests/
                  - run: cd python && python -m flake8 src/ tests/ --max-line-length=100

              c-build:
                runs-on: ubuntu-latest
                steps:
                  - uses: actions/checkout@v4
                  - run: cd C && make all
                  - run: cd C && make clean
            ```

            ## Acceptance Criteria

            - [ ] Workflow file at `.github/workflows/ci.yml`.
            - [ ] Triggers on every push to `main` and on every PR targeting `main`.
            - [ ] Python matrix covers Python 3.9, 3.11, and 3.12.
            - [ ] Coverage threshold enforced at ≥ 85% overall.
            - [ ] C build verified with `-Wall -Wextra -Werror`.
            - [ ] CI badge added to README.
            - [ ] First green run confirmed on `main`.

            ## References

            - `python/requirements.txt`
            - GitHub Actions documentation: https://docs.github.com/en/actions
        """,
        labels=["ci-cd", "testing", "phase-2"],
        priority="High",
        component="CI-CD",
        phase="Phase 2: Enhancement",
    ),

    IssueSpec(
        title="[Quality] Add mypy static type checking",
        body="""
            ## Overview

            The Python codebase already uses type hints in many places (e.g., `game_engine.py`).
            Adding `mypy` will catch type errors at development time rather than runtime and will
            enforce consistent annotation going forward.

            ## Why It Matters

            Type errors in simulation code are particularly dangerous because:
            - Python silently coerces types, so errors rarely raise exceptions.
            - A `float` where an `int` was expected in a card-value calculation could bias EV
              results by a tiny, hard-to-detect amount.
            - `mypy` provides IDE autocomplete benefits that improve contributor experience.

            ## Implementation Plan

            1. Run `mypy python/src/ python/tests/ --ignore-missing-imports` and fix errors.
            2. Add a `mypy.ini` or `[mypy]` section in `setup.cfg`:
               ```ini
               [mypy]
               python_version = 3.9
               ignore_missing_imports = true
               strict = true
               ```
            3. Add `mypy` to `requirements.txt` (or `requirements-dev.txt`).
            4. Add a `mypy src/` step to the CI pipeline.
            5. Annotate all function signatures in `src/`.

            ## Key Annotations Needed

            - `Shoe.deal() -> Optional[Card]` — returns `None` at the cut card.
            - `BlackjackGame.execute_action(...) -> Optional[float]` — returns `None` mid-hand.
            - All dataclass fields typed explicitly.

            ## Acceptance Criteria

            - [ ] `mypy src/` passes with zero errors.
            - [ ] `mypy.ini` (or equivalent) committed to the repo.
            - [ ] `mypy` pinned in `requirements.txt` / `requirements-dev.txt`.
            - [ ] mypy check added to CI pipeline.
            - [ ] All function signatures in `src/` annotated.

            ## References

            - mypy documentation: https://mypy.readthedocs.io
            - `python/src/game_engine.py` — already has many type hints, good starting point
        """,
        labels=["ci-cd", "testing", "phase-2", "good-first-issue"],
        priority="Medium",
        component="CI-CD",
        phase="Phase 2: Enhancement",
    ),

    IssueSpec(
        title="[Quality] Enforce code style with black and flake8",
        body="""
            ## Overview

            Consistent code style reduces cognitive load, speeds up reviews, and prevents noisy
            diffs. `black` (opinionated auto-formatter) plus `flake8` (style/error linter) give a
            comprehensive style baseline.

            ## Why It Matters

            - Without enforced formatting, every PR risks style-noise diffs that obscure real changes.
            - `flake8` catches common bugs (undefined names, unreachable code, shadowed variables)
              that type checkers miss.
            - `black` is deterministic — there is exactly one valid formatting, eliminating
              style debates in code review.

            ## Implementation Plan

            1. Run `black python/` once to reformat the entire codebase.
            2. Commit as a standalone formatting commit (so `git blame` history stays clean).
            3. Add a `.flake8` config:
               ```ini
               [flake8]
               max-line-length = 100
               extend-ignore = E203, W503   # compatible with black
               exclude = .git,__pycache__
               ```
            4. Add both tools to `requirements.txt` / `requirements-dev.txt`.
            5. Add `black --check` and `flake8` steps to CI.
            6. (Optional) Add a `.pre-commit-config.yaml` with both hooks.

            ## Acceptance Criteria

            - [ ] `black --check python/` exits 0.
            - [ ] `flake8 python/src/ python/tests/` exits 0.
            - [ ] Both tools pinned in requirements files.
            - [ ] CI pipeline runs both checks.
            - [ ] (Optional) `.pre-commit-config.yaml` added.

            ## References

            - black: https://black.readthedocs.io
            - flake8: https://flake8.pycqa.org
            - pre-commit: https://pre-commit.com
        """,
        labels=["ci-cd", "phase-2", "good-first-issue"],
        priority="Medium",
        component="CI-CD",
        phase="Phase 2: Enhancement",
    ),

    IssueSpec(
        title="[C Implementation] Write C unit test suite using Unity or cmocka",
        body="""
            ## Overview

            The C implementation currently has **zero automated tests**. It is verified only by
            visual inspection and comparison with Python output. Adding a proper C unit test suite
            is essential before the C engine can be trusted for performance-critical use.

            ## Why It Matters

            The C implementation is 17 source files with 85 functions total. Without tests:
            - Any refactoring risks silent regressions.
            - The 25-line-per-function constraint makes off-by-one errors easy to introduce.
            - Static-allocation bugs (buffer overflows in fixed-size arrays) are not caught at
              compile time.

            ## Recommended Framework: Unity

            **Unity** (https://github.com/ThrowTheSwitch/Unity) is a minimal, header-only C testing
            framework that integrates easily with Make. Alternative: **cmocka**.

            ## Test Scope (priority order)

            ### Tier 1 — Pure functions (no randomness)
            | Function | Tests |
            |----------|-------|
            | `card_value(rank)` | All 13 ranks → correct point value; Ace returns 11 |
            | `hand_total(hand)` | Hard totals; soft totals with Ace; bust; multiple Aces |
            | `is_bust(hand)` | Total > 21 → true; total ≤ 21 → false |
            | `is_blackjack(hand)` | Ace+10-value → true; others → false |
            | `hi_lo_tag(rank)` | 2–6 → +1; 7–9 → 0; 10/J/Q/K/A → −1 |
            | `true_count(rc, decks)` | Division; near-zero denominator |

            ### Tier 2 — Deterministic game logic
            - Dealer play (hits soft 17, stands on hard 17+).
            - Split pair logic (correct hand duplication).
            - Double-down (one extra card, no further hits).

            ### Tier 3 — Statistical (seeded RNG)
            - EV for hard 16 vs 10 is negative (player loses more than wins).
            - EV for double-down on 11 vs 6 is highly positive.

            ## Acceptance Criteria

            - [ ] Test runner target added to `Makefile` (`make test`).
            - [ ] All Tier 1 functions have ≥ 2 tests (happy path + edge case).
            - [ ] At least 3 Tier 2 scenarios tested.
            - [ ] At least 1 Tier 3 statistical test.
            - [ ] Tests compile without warnings under `-Wall -Wextra`.
            - [ ] CI pipeline builds and runs C tests.

            ## References

            - `C/` directory — all source files
            - Unity: https://github.com/ThrowTheSwitch/Unity
            - Project constraint: ≤ 5 functions per file, ≤ 25 lines per function
        """,
        labels=["testing", "c-implementation", "phase-2"],
        priority="High",
        component="C Implementation",
        phase="Phase 2: Enhancement",
    ),

    IssueSpec(
        title="[C Implementation] Validate Python/C result equivalence automatically",
        body="""
            ## Overview

            The Python and C engines are claimed to implement identical blackjack logic. There is
            currently no automated test verifying this. A systematic equivalence check would give
            confidence that any optimization in one port does not silently diverge from the other.

            ## Why It Matters

            - Both engines are referenced in the README and published graphs. If they disagree,
              the documentation is unreliable.
            - Future contributors modifying one engine need to know if they broke parity.
            - This is a necessary precondition before the C implementation can be called a
              validated fast version of the Python engine.

            ## Proposed Validation Method

            1. Run both engines with the same seeded random state on a fixed set of game states.
            2. Compare EV estimates for 10 important strategy-table cells:
               - Hard 16 vs 10, Hard 11 vs 6, Soft 18 vs 10, A+A vs 7, 8+8 vs 10, etc.
            3. Tolerance: EV estimates within ±0.5% (accounting for Monte Carlo variance at N=10 000).
            4. Automated as a CI step so any future drift is caught immediately.

            ## Implementation Sketch

            ```bash
            # Generate Python reference output
            cd python && python -m src.main --mode validate --seed 42 --output /tmp/py_ev.json

            # Generate C output
            cd C && ./blackjack --mode validate --seed 42 --output /tmp/c_ev.json

            # Compare
            python tools/compare_ev.py /tmp/py_ev.json /tmp/c_ev.json --tolerance 0.005
            ```

            ## Deliverables

            1. Both engines accept a `--seed` flag for reproducibility.
            2. A comparison script `tools/compare_ev.py`.
            3. CI step that runs the comparison and fails if any EV differs by > 0.5%.
            4. A `EQUIVALENCE.md` file documenting results.

            ## Acceptance Criteria

            - [ ] Comparison script runs end-to-end without error.
            - [ ] All 10 strategy cells match within ±0.5%.
            - [ ] CI step added and green.
            - [ ] `EQUIVALENCE.md` committed.

            ## References

            - `python/src/game_engine.py`, `python/src/monte_carlo_solver.py`
            - `C/` source directory
        """,
        labels=["testing", "c-implementation", "phase-2"],
        priority="Medium",
        component="C Implementation",
        phase="Phase 2: Enhancement",
    ),

    IssueSpec(
        title="[Performance] Benchmark Python vs C: measure and document the speedup",
        body="""
            ## Overview

            The README claims the C implementation is ~40× faster than Python (~30 s vs ~20–30 min
            for a full analysis). This claim needs to be measured systematically and kept up-to-date
            as the code evolves.

            ## Why It Matters

            - The speedup is a key selling point of the dual-language design.
            - Performance regressions in C (e.g., accidental O(N²) loops) should be caught early.
            - Profiling reveals *where* Python time is spent, guiding future optimisation.

            ## Benchmark Design

            ### Metric: Simulations per second (sims/s)

            | Engine | Scenario | Expected sims/s |
            |--------|----------|-----------------|
            | Python | Single-threaded, 10 000 sims/state | ~2 000 |
            | Python | Multiprocessing (all cores) | ~8 000 |
            | C | Single-threaded, 10 000 sims/state | ~80 000 |

            ### Tool: `hyperfine`

            ```bash
            hyperfine \\
              'cd python && python -m src.main --mode quick' \\
              'cd C && ./blackjack --mode quick' \\
              --warmup 2 --runs 5
            ```

            ### Python profiling

            ```bash
            cd python && python -m cProfile -s cumtime -m src.main --mode quick | head -30
            ```

            ## Deliverables

            1. A `benchmark/` directory with runner scripts.
            2. A `BENCHMARKS.md` with a results table (machine specs, Python version, compiler flags).
            3. README updated with verified speedup ratio.
            4. (Optional) CI step that benchmarks and comments results on PRs.

            ## Acceptance Criteria

            - [ ] Benchmark script runs end-to-end without error.
            - [ ] Results are reproducible across two consecutive runs within ±10%.
            - [ ] README speedup claim updated to match measured result.
            - [ ] `BENCHMARKS.md` documents hardware/software environment.
        """,
        labels=["performance", "c-implementation", "phase-2"],
        priority="Medium",
        component="Performance",
        phase="Phase 2: Enhancement",
    ),

    IssueSpec(
        title="[Documentation] Write C implementation architecture guide",
        body="""
            ## Overview

            The C implementation spans 17 source files with a strict 5-functions-per-file
            constraint. New contributors need a map of how these files relate, what each module
            owns, and why the design constraints exist.

            ## Why It Matters

            Without documentation:
            - Contributors spend hours reverse-engineering the file structure.
            - The design rationale (static allocation, line limits) is invisible.
            - Adding a new feature risks constraint violations.

            ## Proposed Document: `C/ARCHITECTURE.md`

            ### Sections

            1. **Design Philosophy** — why C, why static allocation, why 5 functions / 25 lines.
            2. **Module Map** — table of all 17 source files with purpose and key functions.
            3. **Data Flow** — diagram from `main.c` through the engine to output.
            4. **Memory Layout** — static stack allocations: sizes, types, max-capacity rationale.
            5. **Build System** — how to use `make`, available targets, compiler flags.
            6. **Adding a New Feature** — step-by-step guide respecting all constraints.
            7. **Known Limitations** — what the C port does and does not support vs Python.

            ### Module Map (template)

            | File | Functions | Responsibility |
            |------|-----------|---------------|
            | `main.c` | 5 | Entry point, mode dispatch |
            | `card_utils.c` | 5 | Rank/suit, Hi-Lo tag |
            | `hand_utils.c` | 5 | Hand total, soft/hard, bust |
            | `shoe_utils.c` | 5 | Deck init, Fisher-Yates shuffle, deal |
            | `game_actions.c` | 5 | Hit, stand, double, split |
            | `game_dealer.c` | 5 | Dealer play-through |
            | `game_round.c` | 5 | Full round orchestration |
            | `monte_carlo_core.c` | 5 | Single-state EV simulation |
            | `monte_carlo_simulation.c` | 5 | Multi-state batch |
            | `monte_carlo_solver.c` | 5 | Strategy table builder |
            | `counting_core.c` | 5 | Running/true count |
            | `counting_simulation.c` | 5 | Full-shoe counting |
            | `betting_core.c` | 4 | Bet spread, advantage estimation |
            | `interactive_mode.c` | varies | CLI interactive play |
            | `visual_strategy.c` | 5 | ASCII strategy table |
            | `visual_ev.c` | 5 | EV bar chart |
            | `visual_distribution.c` | 5 | EV distribution histogram |

            ## Acceptance Criteria

            - [ ] `C/ARCHITECTURE.md` created with all 7 sections.
            - [ ] Module map table complete and accurate.
            - [ ] At least one ASCII data-flow diagram.
            - [ ] Build instructions verified on a fresh Ubuntu/macOS environment.
            - [ ] Linked from main `README.md`.
        """,
        labels=["documentation", "c-implementation", "phase-2", "good-first-issue"],
        priority="Medium",
        component="Documentation",
        phase="Phase 2: Enhancement",
    ),

    # =========================================================================
    # PHASE 3 — Advanced Features
    # =========================================================================

    IssueSpec(
        title="[Feature] Implement Illustrious 18 index plays",
        body="""
            ## Overview

            The *Illustrious 18* (Don Schlesinger, *Blackjack Attack*) are the 18 basic-strategy
            deviations that account for ~80% of the EV gain from index plays. When the true count
            reaches a threshold (the *index*), the correct action differs from basic strategy.

            ## Why It Matters

            Basic strategy gives approximately −0.5% house edge. Card counting and bet variation
            recovers ~+1% at high counts. Strategy deviations (index plays) add another 0.15–0.30%
            EV on top. The Illustrious 18 are the most studied and most impactful deviations.

            ## The Illustrious 18 (standard 6-deck, S17 rules)

            | # | Hand | Dealer | Basic strategy | Index | Deviation |
            |---|------|--------|---------------|-------|-----------|
            | 1 | 16 | 10 | Hit | 0 | Stand at TC ≥ 0 |
            | 2 | 15 | 10 | Hit | +4 | Stand at TC ≥ +4 |
            | 3 | 10,10 | 5 | Stand | +5 | Split at TC ≥ +5 |
            | 4 | 10,10 | 6 | Stand | +4 | Split at TC ≥ +4 |
            | 5 | 10 | 10 | Hit | +4 | Double at TC ≥ +4 |
            | 6 | 12 | 3 | Hit | +2 | Stand at TC ≥ +2 |
            | 7 | 12 | 2 | Hit | +3 | Stand at TC ≥ +3 |
            | 8 | 11 | A | Hit | +1 | Double at TC ≥ +1 |
            | 9 | 9 | 2 | Hit | +1 | Double at TC ≥ +1 |
            | 10 | 10 | A | Hit | +4 | Double at TC ≥ +4 |
            | 11 | 9 | 7 | Hit | +3 | Double at TC ≥ +3 |
            | 12 | 16 | 9 | Hit | +5 | Stand at TC ≥ +5 |
            | 13 | 13 | 2 | Stand | −1 | Hit at TC ≤ −1 |
            | 14 | 12 | 4 | Stand | 0 | Hit at TC ≤ 0 |
            | 15 | 12 | 5 | Stand | −2 | Hit at TC ≤ −2 |
            | 16 | 12 | 6 | Stand | −1 | Hit at TC ≤ −1 |
            | 17 | 13 | 3 | Stand | −2 | Hit at TC ≤ −2 |
            | 18 | A,8 | 6 | Stand | +1 | Double at TC ≥ +1 |

            ## Implementation Plan

            1. Add an `IndexPlays` class to `card_counting.py` (or a new `index_plays.py`).
            2. Modify `BlackjackGame.decide_action()` to accept an optional `true_count` param
               and check index plays before falling back to basic strategy.
            3. Add a `use_illustrious_18: bool` flag to simulation configuration.
            4. Run A/B comparison (with vs without I18) and confirm EV improvement.

            ## Acceptance Criteria

            - [ ] All 18 index plays implemented and tested.
            - [ ] EV improvement of ≥ 0.1% observed with N ≥ 100 000 shoes.
            - [ ] New tests cover each index boundary (TC = index−1, index, index+1).
            - [ ] `use_illustrious_18` flag documented in README.

            ## References

            - Schlesinger, D. (2005). *Blackjack Attack*, Ch. 10.
            - `python/src/card_counting.py`
            - `python/src/game_engine.py` — `BlackjackGame`
        """,
        labels=["card-counting", "simulation", "phase-3"],
        priority="High",
        component="Card Counting",
        phase="Phase 3: Advanced",
    ),

    IssueSpec(
        title="[Feature] Simulate Wonging (back-counting / mid-shoe entry)",
        body="""
            ## Overview

            *Wonging* (named after Stanford Wong) is a technique where the player watches a table
            without betting, enters when the count rises above a threshold, and leaves when it
            drops below another. This dramatically increases effective EV by playing only when the
            deck favours the player.

            ## Why It Matters

            Wonging is the most EV-efficient real-world counting technique. Simulating it:
            1. Demonstrates the maximum theoretical advantage from Hi-Lo counting.
            2. Shows practical limitations (casinos actively counter back-counters).
            3. Provides a more realistic model of professional counting income.

            ## Mechanics

            - **Entry threshold**: player enters when TC ≥ T_enter (e.g., TC ≥ +2).
            - **Exit threshold**: player leaves when TC < T_exit (e.g., TC < 0).
            - **Hands per shoe**: Wonger plays fewer hands but with higher average advantage.
            - **Realistic constraint**: mid-shoe entry is now widely banned by casinos.

            ## Implementation Plan

            1. Add a `WongingSimulation` class to `card_counting.py`.
            2. Wrap `CountingSimulation` but skip rounds when TC < T_enter.
            3. Track: hands played, hands skipped, net EV, hourly EV (100 hands/hr when seated).
            4. Produce a comparison plot: standard counting vs Wonging EV per hour.

            ## Acceptance Criteria

            - [ ] `WongingSimulation` implemented and tested.
            - [ ] Entry/exit thresholds configurable.
            - [ ] Wonging EV measurably higher than flat full-shoe play.
            - [ ] Comparison visualisation added to `visualization.py`.
            - [ ] README section explaining Wonging added.

            ## References

            - Wong, S. (1975). *Professional Blackjack*. Pi Yee Press.
            - `python/src/card_counting.py`
        """,
        labels=["card-counting", "simulation", "phase-3"],
        priority="Medium",
        component="Card Counting",
        phase="Phase 3: Advanced",
    ),

    IssueSpec(
        title="[Feature] Implement Risk of Ruin calculator and Kelly Criterion bet sizing",
        body="""
            ## Overview

            Knowing you have a positive edge is not enough — you must also know the probability of
            going broke before realising that edge. Risk of Ruin (RoR) quantifies this risk, and
            the Kelly Criterion provides the theoretically optimal bet size to minimise it.

            ## Mathematical Definitions

            ### Risk of Ruin

            For bankroll B, edge μ (per unit bet), and variance σ²:
            ```
            RoR = exp(−2 × μ × B / σ²)
            ```
            For blackjack: μ ≈ −0.5% + 0.5% × TC, σ ≈ 1.14 betting units per hand.

            Example: TC = +2, B = 100 units → RoR ≈ exp(−2 × 0.005 × 100 / 1.30) ≈ 46%.

            ### Kelly Criterion (fractional Kelly)
            ```
            Kelly fraction  f  = μ / σ²
            Recommended bet    = f × Bankroll  (use ½ Kelly for safety)
            ```

            ## Implementation Plan

            1. Add `RiskOfRuin` class to `card_counting.py` with:
               - `calculate(bankroll, edge, variance) → float`
               - `kelly_bet(bankroll, edge, variance, fraction=0.5) → float`
            2. Add a *RoR vs Bankroll* plot to `visualization.py`.
            3. Add a *Kelly Bet vs True Count* plot.
            4. Integrate into the main analysis output.

            ## Acceptance Criteria

            - [ ] `RiskOfRuin.calculate()` matches published tables within ±1%.
            - [ ] `kelly_bet()` never returns negative or zero.
            - [ ] Half-Kelly safeguard configurable.
            - [ ] Tested against Schlesinger's *Blackjack Attack* appendix tables.
            - [ ] Two new visualisation plots produced.
            - [ ] README section on risk management added.

            ## References

            - Thorp, E.O. (1966). *Beat the Dealer*, Appendix — Risk formulae.
            - Schlesinger, D. (2005). *Blackjack Attack*, Ch. — SCORE and bankroll management.
            - Kelly, J.L. (1956). *A New Interpretation of Information Rate*. Bell System Technical Journal.
        """,
        labels=["card-counting", "simulation", "phase-3"],
        priority="Medium",
        component="Card Counting",
        phase="Phase 3: Advanced",
    ),

    IssueSpec(
        title="[Feature] Implement Hi-Opt II and Omega II counting systems for comparison",
        body="""
            ## Overview

            The current implementation supports only Hi-Lo. Adding Hi-Opt II and Omega II allows
            direct comparison of counting systems and demonstrates the trade-off between complexity
            and EV gain.

            ## System Tag Definitions

            ### Hi-Opt II (Humble, 1970s)
            | Cards | Tag |
            |-------|-----|
            | 2, 3, 6, 7 | +1 |
            | 4, 5 | +2 |
            | 8, 9 | 0 |
            | 10, J, Q, K | −2 |
            | Ace | 0 (side count) |

            Betting Correlation: **0.91**

            ### Omega II (Caniglia, 1980s)
            | Cards | Tag |
            |-------|-----|
            | 2, 3, 7 | +1 |
            | 4, 5, 6 | +2 |
            | 8 | 0 |
            | 9 | −1 |
            | 10, J, Q, K | −2 |
            | Ace | 0 (side count) |

            Betting Correlation: **0.92**

            ## System Comparison

            | System | BC | Playing Efficiency | Level | Ace Side Count |
            |--------|----|--------------------|-------|----------------|
            | Hi-Lo | 0.97 | 0.51 | 1 | No |
            | Hi-Opt II | 0.91 | 0.67 | 2 | Yes |
            | Omega II | 0.92 | 0.67 | 2 | Yes |

            Hi-Lo wins on betting correlation (the most important property), which is why it
            dominates professionally despite being simpler.

            ## Implementation Plan

            1. Add `HiOptIICounter` and `OmegaIICounter` following the same interface as
               `HiLoCounter`.
            2. Add an `AceSideCount` mixin for systems that track Aces separately.
            3. Run comparative simulations: EV vs TC for each system.
            4. Produce a comparison plot: 3 lines on the same EV vs TC graph.

            ## Acceptance Criteria

            - [ ] Both systems implemented and tested.
            - [ ] Ace side count correction implemented.
            - [ ] Comparative simulation confirms Hi-Lo superiority for betting decisions.
            - [ ] All tag assignments verified against published sources.
            - [ ] Comparison visualisation added.

            ## References

            - Humble, L. & Cooper, C. (1980). *The World's Greatest Blackjack Book*.
            - Schlesinger, D. (2005). *Blackjack Attack* — System comparison table.
        """,
        labels=["card-counting", "phase-3"],
        priority="Low",
        component="Card Counting",
        phase="Phase 3: Advanced",
    ),

    IssueSpec(
        title="[Visualization] Build interactive analysis dashboard",
        body="""
            ## Overview

            Current visualisations are static matplotlib PNGs. An interactive dashboard lets users
            explore data — zoom into EV curves, filter by game rules, compare counting systems —
            without re-running simulations.

            ## Why It Matters

            - Static PNGs are great for a README but don't allow exploration.
            - An interactive dashboard makes this project a *tool*, not just a report.
            - Users can ask "what if I change penetration?" and get immediate visual feedback.

            ## Recommended Approach: Plotly Dash

            A standalone web app (no Jupyter required), sharable via URL.

            ## Dashboard Pages

            1. **Strategy Table Explorer** — hover over any cell to see exact EV, click to see
               Monte Carlo distribution.
            2. **EV vs True Count** — interactive line chart; sliders for N_SIMS, penetration,
               deck count.
            3. **Bankroll Simulator** — input bankroll and bet spread; output simulated bankroll
               growth over 10 000 hands.
            4. **Counting System Comparison** — overlay Hi-Lo, Hi-Opt II, Omega II EV curves.
            5. **Risk of Ruin Calculator** — slide bankroll and edge, see RoR update in real time.

            ## Acceptance Criteria

            - [ ] Dashboard launches with `python -m src.dashboard` (or `python app.py`).
            - [ ] Pages 1 and 2 implemented at minimum.
            - [ ] All charts responsive (zoom, pan, hover tooltips).
            - [ ] README section with screenshot and launch instructions.
            - [ ] Dependencies added to `requirements.txt`.

            ## References

            - `python/src/visualization.py` — existing static plots to port
            - Plotly Dash: https://dash.plotly.com
        """,
        labels=["visualization", "phase-3"],
        priority="Low",
        component="Visualization",
        phase="Phase 3: Advanced",
    ),

    IssueSpec(
        title="[Feature] Simulate casino countermeasures against card counters",
        body="""
            ## Overview

            Real casinos actively detect and counter card counters. Simulating these countermeasures
            gives a realistic picture of long-run EV and answers: *is card counting still profitable
            in a modern casino?*

            ## Countermeasures to Simulate

            ### 1. Shallow Penetration
            Reshuffle after 50% (instead of 75%) of the shoe is dealt.
            Effect: fewer high-count opportunities; advantage roughly halved.

            ### 2. Continuous Shuffle Machine (CSM)
            No discard pile — every hand is from a freshly shuffled shoe.
            Effect: true count always ≈ 0; card counting provides zero advantage.

            ### 3. 6:5 Blackjack Payout
            Natural blackjack pays 6:5 (1.2:1) instead of 3:2 (1.5:1).
            Effect: adds ~1.4% to the house edge, wiping out any counter advantage.

            ### 4. Restricted Bet Spread
            Casino limits max bet to 3× min bet (no high ramp-up at high counts).
            Effect: counter cannot profit enough at good counts to overcome house edge.

            ### 5. Mid-Shoe Entry Ban (anti-Wonging)
            Player must enter from the beginning of a shoe.
            Effect: eliminates Wonging strategy entirely.

            ## Comparative Analysis

            | Scenario | Player EV (approx.) |
            |----------|---------------------|
            | No countermeasures (baseline) | +0.5% |
            | Shallow penetration (50%) | −0.1% |
            | CSM | −0.5% |
            | 6:5 payout | −1.0% |
            | Restricted bet spread (1:3) | +0.1% |
            | Realistic modern casino (all above) | −0.8% |

            ## Acceptance Criteria

            - [ ] Each countermeasure implemented as a configurable parameter.
            - [ ] Comparative simulation produces the results table above.
            - [ ] README FAQ updated to reflect realistic modern-casino EV.
            - [ ] All countermeasures covered by tests.

            ## References

            - Griffin, P. (1999). *The Theory of Blackjack*. Huntington Press.
            - README FAQ — *Does this actually work in real casinos?*
        """,
        labels=["simulation", "card-counting", "phase-3"],
        priority="Low",
        component="Simulation Engine",
        phase="Phase 3: Advanced",
    ),

    IssueSpec(
        title="[Documentation] Create GitHub Pages documentation site with MkDocs",
        body="""
            ## Overview

            The README is excellent but very long (30 KB+). A GitHub Pages site would split it
            into navigable sections, render math equations with MathJax, embed output charts, and
            serve as the canonical public-facing documentation.

            ## Why It Matters

            - A website is more discoverable than a README for external visitors.
            - Math equations (`EV = -0.5% + 0.5% × TC`) render beautifully with MathJax.
            - Charts from `python/output/` can be embedded as images.
            - Automated deployment keeps docs in sync with code.

            ## Proposed Structure (MkDocs Material theme)

            ```
            docs/
            ├── index.md              ← Project overview & quick start
            ├── theory/
            │   ├── monte_carlo.md    ← Monte Carlo methods explained
            │   ├── hi_lo.md          ← Hi-Lo counting system
            │   └── risk.md           ← Risk of Ruin & Kelly Criterion
            ├── usage/
            │   ├── python.md         ← How to run the Python version
            │   └── c.md              ← How to build & run the C version
            ├── results/
            │   ├── strategy_table.md ← Rendered strategy table
            │   └── ev_graphs.md      ← EV vs true count analysis
            └── contributing.md       ← How to contribute
            ```

            ## Deployment Workflow: `.github/workflows/docs.yml`

            ```yaml
            - uses: actions/setup-python@v5
            - run: pip install mkdocs-material
            - run: mkdocs gh-deploy --force
            ```

            ## Acceptance Criteria

            - [ ] `mkdocs.yml` configuration file created.
            - [ ] All 6 pages above drafted.
            - [ ] Math equations rendered via MathJax plugin.
            - [ ] CI workflow deploys on every push to `main`.
            - [ ] `docs.yml` workflow passing (green badge).
            - [ ] Link added to repository *About → Website*.

            ## References

            - MkDocs Material: https://squidfunk.github.io/mkdocs-material
            - `README.md` — source content to port
        """,
        labels=["documentation", "ci-cd", "phase-3"],
        priority="Low",
        component="Documentation",
        phase="Phase 3: Advanced",
    ),

    # =========================================================================
    # ONGOING — Maintenance
    # =========================================================================

    IssueSpec(
        title="[Ongoing] Maintain test coverage above 85% on every PR",
        body="""
            ## Purpose

            This is a *standing policy issue* — not a one-time task. It documents and tracks the
            test-coverage policy for this repository.

            ## Policy

            Every pull request merged into `main` must maintain overall test coverage ≥ 85%.
            The CI pipeline enforces this via:
            ```bash
            pytest --cov=src --cov-fail-under=85
            ```
            If a PR legitimately cannot maintain 85% (e.g., a new hard-to-test module), it must
            include a written justification and a follow-up issue for the missing tests.

            ## Per-Module Targets

            | Module | Current | Target |
            |--------|---------|--------|
            | `game_engine.py` | 97% | ≥ 95% |
            | `card_counting.py` | 58% | ≥ 90% |
            | `monte_carlo_solver.py` | 54% | ≥ 90% |
            | `visualization.py` | ~40% | ≥ 70% |
            | `main.py` | ~30% | ≥ 60% |

            ## How to Check Locally

            ```bash
            cd python && python -m pytest tests/ --cov=src --cov-report=term-missing -v
            ```

            ## Notes

            - This issue should be referenced in `CONTRIBUTING.md`.
            - Coverage thresholds are enforced in `.github/workflows/ci.yml`.
            - Use `# pragma: no cover` sparingly and only with justification.
        """,
        labels=["testing", "ongoing"],
        priority="Medium",
        component="CI-CD",
        phase="Ongoing",
    ),

    IssueSpec(
        title="[Ongoing] Keep README and code comments in sync with implementation",
        body="""
            ## Purpose

            A *standing documentation policy* issue. As the codebase evolves, README sections and
            inline comments must remain accurate. Stale documentation is worse than no documentation.

            ## PR Checklist

            Before merging any feature PR, the author should verify:

            - [ ] README sections referencing changed modules/functions are updated.
            - [ ] Docstrings in modified functions are accurate.
            - [ ] Output examples in README (e.g., EV vs TC table) still match actual output.
            - [ ] Any new configuration options are documented.

            ## Documentation Quality Standards

            1. Every public function/method in `python/src/` must have a docstring explaining:
               - What it does (one-line summary).
               - Parameters and their types.
               - Return value.
               - Side effects or exceptions.

            2. Complex algorithms (Fisher-Yates shuffle in `Shoe`, soft Ace logic in `Hand`) must
               have a comment explaining *why*, not just *what*.

            3. The README *Understanding The Output* section must match the actual output format.

            ## Tooling Options

            - `pydocstyle` or `darglint` can lint docstrings automatically.
            - Consider adding docstring coverage to the CI pipeline.
        """,
        labels=["documentation", "ongoing", "good-first-issue"],
        priority="Low",
        component="Documentation",
        phase="Ongoing",
    ),

    IssueSpec(
        title="[Ongoing] Triage and respond to community issues and pull requests",
        body="""
            ## Purpose

            This is the community engagement policy issue. It tracks SLAs and best practices for
            responding to external contributors.

            ## Response SLA Guidelines

            | Event | Target response time |
            |-------|---------------------|
            | New issue filed | Acknowledge within 7 days |
            | PR opened | Initial review within 14 days |
            | Bug report | Triage and label within 3 days |
            | Question | Answer or redirect within 7 days |

            ## Issue Triage Labels

            When a new issue is filed, apply the appropriate labels:

            | Label | When to use |
            |-------|------------|
            | `bug` | Reproducible defect in the code |
            | `enhancement` | New feature request |
            | `question` | Seeking clarification |
            | `duplicate` | Already reported |
            | `wont-fix` | Out of scope or by design |
            | `good-first-issue` | Suitable for newcomers |

            ## PR Review Checklist

            Before approving any PR:

            - [ ] All CI checks pass.
            - [ ] Test coverage did not decrease.
            - [ ] New functions have docstrings.
            - [ ] Code follows existing style (black + flake8).
            - [ ] C implementation updated if Python logic changed (or vice versa).
            - [ ] CHANGELOG.md updated (if one exists).

            ## Contributing Guide

            A `CONTRIBUTING.md` should be created documenting:
            - How to set up a development environment.
            - How to run tests.
            - The PR process and review criteria.
            - Code style requirements.
        """,
        labels=["documentation", "ongoing", "help-wanted"],
        priority="Low",
        component="CI-CD",
        phase="Ongoing",
    ),
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", default="claudialbombin",
                        help="GitHub username/org that owns the repo (default: claudialbombin)")
    parser.add_argument("--repo", default="beat-the-dealer",
                        help="Repository name (default: beat-the-dealer)")
    args = parser.parse_args()

    owner = args.owner
    repo = args.repo

    print(f"\n🃏  Beat the Dealer — Project Board Setup")
    print(f"   Owner: {owner}   Repo: {repo}")
    print("=" * 60)

    # 1. Labels
    create_labels(owner, repo)

    # 2. Project
    project_number, project_id, project_url = create_project(owner)

    # 3. Link to repo
    link_project_to_repo(owner, repo, project_id)

    # 4. Custom fields
    fields = create_fields(project_number, owner)

    # 5. Issues
    print(f"\n── Creating {len(ISSUES)} issues ───────────────────────────────────────")
    for i, spec in enumerate(ISSUES, 1):
        print(f"\n  [{i}/{len(ISSUES)}] {spec.title[:70]}")
        issue_url = create_issue(owner, repo, spec.title, spec.body, spec.labels)
        print(f"       Issue: {issue_url}")
        add_to_project(owner, project_number, project_id, issue_url, fields,
                       spec.priority, spec.component, spec.phase)
        print(f"       Added to project with Priority={spec.priority}, "
              f"Component={spec.component}, Phase={spec.phase}")

    # 6. Done
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🃏  Beat the Dealer — Project Board Created!               ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║   Project URL:  {project_url:<47}║
║                                                              ║
║   Custom fields:                                             ║
║     • Priority  (Critical / High / Medium / Low)            ║
║     • Component (8 options)                                  ║
║     • Phase     (Phase 1–3 + Ongoing)                       ║
║                                                              ║
║   Issues created:  {len(ISSUES):<42}║
║                                                              ║
║   Next steps:                                                ║
║     1. Visit the project URL above.                         ║
║     2. Set the built-in Status field on each item.          ║
║     3. Create board/table/roadmap views as needed.          ║
║     4. Assign team members to items.                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
