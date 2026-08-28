#!/usr/bin/env python3
"""External Lean task-only regime genesis.

The learner never sees Lean types or diagnostics.  Its only oracle is the exit
status of the real `lean` executable on anonymous term-construction tasks.

It reconstructs the minimal operational typing interface, predicts unseen
compositions, survives anonymous presentation changes, attaches a new operator
after a structural intervention, and demonstrates that the flat/untyped
ablation makes systematic errors.
"""

from __future__ import annotations

import itertools
import os
import random
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


PRELUDE = r'''
import Std

namespace ExternalWorld

def q0 : Nat → Nat := fun n => n + 1

def q1 : Nat → Bool := fun n => n == 0

def q2 : Bool → Bool := fun b => !b

def q3 : Bool → Nat := fun b => if b then 1 else 0

def q4 : String → Nat := fun s => s.length

def q5 : Nat → String := fun n => toString n

def q6 : List Nat → Nat := fun xs => xs.length

def q7 : Nat → List Nat := fun n => List.replicate n 0

def q8 : String → String := fun s => s ++ "x"

def q9 : List Nat → List Nat := fun xs => xs.reverse

-- Held back until the intervention phase.
def q10 : String → Bool := fun s => s.isEmpty

def z0 : Nat := 2

def z1 : Bool := true

def z2 : String := "abc"

def z3 : List Nat := [1, 2, 3]

end ExternalWorld
open ExternalWorld
'''

# These signatures are NEVER supplied to the learner.  They are used only for
# post-hoc structural scoring and to enumerate the held-out task universe.
TRUE_SIG = {
    "q0": ("Nat", "Nat"),
    "q1": ("Nat", "Bool"),
    "q2": ("Bool", "Bool"),
    "q3": ("Bool", "Nat"),
    "q4": ("String", "Nat"),
    "q5": ("Nat", "String"),
    "q6": ("ListNat", "Nat"),
    "q7": ("Nat", "ListNat"),
    "q8": ("String", "String"),
    "q9": ("ListNat", "ListNat"),
    "q10": ("String", "Bool"),
}
TRUE_SEED = {"z0": "Nat", "z1": "Bool", "z2": "String", "z3": "ListNat"}
BASE_OPS = [f"q{i}" for i in range(10)]
SEEDS = [f"z{i}" for i in range(4)]


@dataclass
class Counts:
    compiler_queries: int = 0
    heldout: int = 0
    heldout_correct: int = 0
    presentations: int = 0
    exact_structures: int = 0
    intervention_predictions: int = 0
    intervention_correct: int = 0
    ablation_errors: int = 0


def lean_accepts(expr: str) -> bool:
    """Return only the Lean process bit; diagnostics are deliberately hidden."""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "Probe.lean"
        p.write_text(PRELUDE + f"\n#check ({expr})\n", encoding="utf-8")
        r = subprocess.run(
            ["lean", str(p)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=os.environ.copy(),
            check=False,
        )
        return r.returncode == 0


def seed_expr(seed: str, op: str) -> str:
    return f"{op} {seed}"


def pair_expr(a: str, b: str, seed: str) -> str:
    # b after a
    return f"{b} ({a} {seed})"


def chain_expr(chain: tuple[str, ...], seed: str) -> str:
    e = seed
    for op in chain:
        e = f"{op} ({e})"
    return e


def canonical_signature(src_class: dict[str, int], dst_class: dict[str, int], ops: list[str]):
    edges = sorted((src_class[o], dst_class[o]) for o in ops)
    indeg = {}
    outdeg = {}
    for s, d in edges:
        outdeg[s] = outdeg.get(s, 0) + 1
        indeg[d] = indeg.get(d, 0) + 1
    nodes = sorted(set(src_class.values()) | set(dst_class.values()))
    profile = sorted((outdeg.get(x, 0), indeg.get(x, 0)) for x in nodes)
    return (len(nodes), tuple(edges), tuple(profile))


def recover(ops: list[str], seeds: list[str], counts: Counts):
    # Phase A: anonymous seed -> operation success gives each op's source class.
    seed_ok: dict[tuple[str, str], bool] = {}
    for z in seeds:
        for op in ops:
            seed_ok[z, op] = lean_accepts(seed_expr(z, op))
            counts.compiler_queries += 1

    source = {}
    for op in ops:
        compatible = [i for i, z in enumerate(seeds) if seed_ok[z, op]]
        if len(compatible) != 1:
            raise AssertionError((op, "source ambiguity", compatible))
        source[op] = compatible[0]

    # One representative operation for each discovered source class.
    reps = {}
    for op in ops:
        reps.setdefault(source[op], op)

    # Phase B: ask only one continuation representative per discovered class.
    # This identifies each destination by future success behaviour.
    dest = {}
    for a in ops:
        # choose the unique seed accepted by a, solely from observed behaviour
        z = seeds[source[a]]
        hits = []
        for cls, b in sorted(reps.items()):
            ok = lean_accepts(pair_expr(a, b, z))
            counts.compiler_queries += 1
            if ok:
                hits.append(cls)
        if len(hits) != 1:
            raise AssertionError((a, "destination ambiguity", hits))
        dest[a] = hits[0]

    return source, dest


def valid_by_model(chain: tuple[str, ...], seed: str, source, dest, seed_class) -> bool:
    cur = seed_class[seed]
    for op in chain:
        if source[op] != cur:
            return False
        cur = dest[op]
    return True


def valid_truth(chain: tuple[str, ...], seed: str) -> bool:
    cur = TRUE_SEED[seed]
    for op in chain:
        s, d = TRUE_SIG[op]
        if s != cur:
            return False
        cur = d
    return True


def run_presentation(seed_value: int, counts: Counts):
    rng = random.Random(seed_value)
    ops = BASE_OPS[:]
    seeds = SEEDS[:]
    rng.shuffle(ops)
    rng.shuffle(seeds)

    source, dest = recover(ops, seeds, counts)
    seed_class = {z: i for i, z in enumerate(seeds)}

    # Exact structure is scored only now, after learning.  Canonicalize learned
    # classes against which anonymous seed they correspond to, not Lean names.
    learned_pairs = sorted((source[o], dest[o]) for o in ops)
    true_pairs = []
    type_to_cls = {TRUE_SEED[z]: seed_class[z] for z in seeds}
    for o in ops:
        s, d = TRUE_SIG[o]
        true_pairs.append((type_to_cls[s], type_to_cls[d]))
    true_pairs.sort()
    if learned_pairs != true_pairs:
        raise AssertionError("post-hoc structural mismatch")
    counts.exact_structures += 1
    counts.presentations += 1

    # Huge task space was never queried: all length-3 anonymous programs from
    # every seed.  Predict from the recovered interface only.
    for z in seeds:
        for chain in itertools.product(ops, repeat=3):
            pred = valid_by_model(chain, z, source, dest, seed_class)
            truth = valid_truth(chain, z)
            counts.heldout += 1
            counts.heldout_correct += int(pred == truth)

            # Flat/untyped ablation predicts every syntactic chain admissible.
            if not truth:
                counts.ablation_errors += 1

    # Structural intervention: reveal one previously unavailable anonymous op.
    # Attach it using the ALREADY recovered interface, with only |objects|+|seeds|
    # binary Lean probes, then predict every pair involving it.
    newop = "q10"
    src_hits = []
    for z in seeds:
        ok = lean_accepts(seed_expr(z, newop))
        counts.compiler_queries += 1
        if ok:
            src_hits.append(seed_class[z])
    if len(src_hits) != 1:
        raise AssertionError(("intervention source", src_hits))
    new_src = src_hits[0]

    reps = {}
    for o in ops:
        reps.setdefault(source[o], o)
    z_for_new = next(z for z in seeds if seed_class[z] == new_src)
    dst_hits = []
    for cls, b in sorted(reps.items()):
        ok = lean_accepts(pair_expr(newop, b, z_for_new))
        counts.compiler_queries += 1
        if ok:
            dst_hits.append(cls)
    if len(dst_hits) != 1:
        raise AssertionError(("intervention destination", dst_hits))
    new_dst = dst_hits[0]

    source2 = dict(source, **{newop: new_src})
    dest2 = dict(dest, **{newop: new_dst})
    ops2 = ops + [newop]
    for z in seeds:
        for a in ops2:
            for b in ops2:
                if newop not in (a, b):
                    continue
                pred = valid_by_model((a, b), z, source2, dest2, seed_class)
                truth = valid_truth((a, b), z)
                counts.intervention_predictions += 1
                counts.intervention_correct += int(pred == truth)

    return canonical_signature(source, dest, ops)


def external_compile_witnesses() -> None:
    # Final external capability gate: independently compile a collection of
    # novel valid programs and independently reject invalid ones.  None of these
    # exact expressions were used during interface recovery.
    valid = [
        "q8 (q5 (q0 z0))",
        "q2 (q1 (q3 z1))",
        "q9 (q7 (q6 z3))",
        "q3 (q2 (q1 z0))",
        "q0 (q4 (q8 z2))",
        "q10 (q8 (q5 z0))",
    ]
    invalid = [
        "q2 (q0 z0)",
        "q9 (q5 z0)",
        "q8 (q7 z0)",
        "q4 (q3 z1)",
        "q10 (q7 z0)",
        "q6 (q8 z2)",
    ]
    for e in valid:
        if not lean_accepts(e):
            raise AssertionError(("Lean rejected predicted-valid witness", e))
    for e in invalid:
        if lean_accepts(e):
            raise AssertionError(("Lean accepted predicted-invalid witness", e))


def main() -> None:
    if subprocess.run(["lean", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
        raise SystemExit("lean executable not available")

    counts = Counts()
    signatures = [run_presentation(s, counts) for s in (11, 29, 47, 83)]
    external_compile_witnesses()

    if counts.heldout_correct != counts.heldout:
        raise AssertionError((counts.heldout_correct, counts.heldout))
    if counts.intervention_correct != counts.intervention_predictions:
        raise AssertionError((counts.intervention_correct, counts.intervention_predictions))
    # Presentation order may relabel latent classes, so compare invariant profile
    # rather than raw class ids.
    invariant_profiles = {(sig[0], sig[2]) for sig in signatures}
    if len(invariant_profiles) != 1:
        raise AssertionError(("presentation invariance", invariant_profiles))
    if counts.ablation_errors == 0:
        raise AssertionError("flat ablation unexpectedly sufficient")

    print(
        "LEAN_EXTERNAL_TASK_ONLY_GENESIS: "
        f"presentations={counts.presentations}; "
        f"exact_structures={counts.exact_structures}/{counts.presentations}; "
        f"compiler_queries={counts.compiler_queries}; "
        f"heldout={counts.heldout_correct}/{counts.heldout}; "
        f"intervention={counts.intervention_correct}/{counts.intervention_predictions}; "
        f"flat_ablation_errors={counts.ablation_errors}; "
        "diagnostics_exposed=0; external_witness_gate=12/12"
    )


if __name__ == "__main__":
    main()
