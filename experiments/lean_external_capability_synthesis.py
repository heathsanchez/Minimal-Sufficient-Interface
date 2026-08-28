#!/usr/bin/env python3
"""Budgeted capability synthesis from a task-only learned Lean interface.

This is the causal follow-up to lean_external_task_only_genesis.py.

A cold/flat search and a warm/interface-guided search use the SAME frozen
lexicographic candidate stream and the SAME external Lean accept/reject oracle.
The only difference is that WARM may reject candidates locally when its
previously learned anonymous interface proves them compositionally impossible.

Success means finding a kernel/elaborator-accepted program for a hidden terminal
context within a strict compiler-query budget.  The exact successful program is
not used during interface learning.
"""

from __future__ import annotations

import itertools
import os
import subprocess
import tempfile
from pathlib import Path

from lean_external_task_only_genesis import (
    PRELUDE,
    BASE_OPS,
    SEEDS,
    recover,
    Counts,
    valid_by_model,
)

# Hidden terminal contexts.  The learner/search policy is not given their Lean
# types; a context is exposed only as an anonymous token and compiler success.
TERMINALS = r'''
namespace ExternalWorld

def h0 : Bool → Unit := fun _ => ()
def h1 : List Nat → Unit := fun _ => ()
def h2 : String → Unit := fun _ => ()
def h3 : Nat → Unit := fun _ => ()
end ExternalWorld
open ExternalWorld
'''

# Frozen challenge.  Chosen before either search runs.
START = "z2"
TERMINAL = "h1"
DEPTH = 5
BUDGET = 32


def lean_accepts_target(chain: tuple[str, ...]) -> bool:
    e = START
    for op in chain:
        e = f"{op} ({e})"
    expr = f"{TERMINAL} ({e})"
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "SynthesisProbe.lean"
        p.write_text(PRELUDE + TERMINALS + f"\n#check ({expr})\n", encoding="utf-8")
        r = subprocess.run(
            ["lean", str(p)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=os.environ.copy(),
            check=False,
        )
        return r.returncode == 0


def all_candidates():
    # Exactly one frozen stream shared by COLD and WARM.
    yield from itertools.product(BASE_OPS, repeat=DEPTH)


def cold_search():
    queries = 0
    for chain in all_candidates():
        if queries >= BUDGET:
            break
        queries += 1
        if lean_accepts_target(chain):
            return chain, queries
    return None, queries


def warm_search(source, dest, seed_class):
    queries = 0
    skipped = 0
    for chain in all_candidates():
        # Only information acquired from the earlier task-only interface is
        # allowed to prune.  Terminal compatibility remains unknown and must be
        # decided externally by Lean.
        if not valid_by_model(chain, START, source, dest, seed_class):
            skipped += 1
            continue
        if queries >= BUDGET:
            break
        queries += 1
        if lean_accepts_target(chain):
            return chain, queries, skipped
    return None, queries, skipped


def verify_exact_witness(chain: tuple[str, ...]) -> None:
    if not lean_accepts_target(chain):
        raise AssertionError(("reported witness does not compile", chain))


def main() -> None:
    if subprocess.run(["lean", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
        raise SystemExit("lean executable not available")

    # Relearn the interface exclusively from binary compiler outcomes.  These
    # queries are acquisition cost and are reported separately from synthesis
    # budget; both COLD and WARM receive the same primitive vocabulary/start.
    counts = Counts()
    ops = BASE_OPS[:]
    seeds = SEEDS[:]
    source, dest = recover(ops, seeds, counts)
    seed_class = {z: i for i, z in enumerate(seeds)}

    cold_chain, cold_queries = cold_search()
    warm_chain, warm_queries, warm_skipped = warm_search(source, dest, seed_class)

    # The preregistered causal gate: flat search must exhaust the budget while
    # the learned-interface search finds a genuinely Lean-accepted program.
    if cold_chain is not None:
        raise AssertionError(("cold unexpectedly succeeded", cold_chain, cold_queries))
    if warm_chain is None:
        raise AssertionError(("warm failed", warm_queries, warm_skipped))
    verify_exact_witness(warm_chain)

    # Ablation is literally the COLD policy: remove source/destination classes
    # and the same candidate order can no longer avoid wasting verifier calls.
    print(
        "LEAN_EXTERNAL_CAPABILITY_SYNTHESIS: "
        f"depth={DEPTH}; budget={BUDGET}; acquisition_queries={counts.compiler_queries}; "
        f"cold=FAIL/{cold_queries}; warm=PASS/{warm_queries}; "
        f"warm_local_prunes={warm_skipped}; witness={'-'.join(warm_chain)}; "
        "diagnostics_exposed=0; verifier=lean"
    )


if __name__ == "__main__":
    main()
