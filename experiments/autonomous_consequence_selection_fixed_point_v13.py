#!/usr/bin/env python3
"""V13: autonomous consequence selection -> minimal sufficient fixed point.

Question
--------
If no single future consequence is privileged, can a controller choose WHICH
consequences to verify from the unresolved aliases of its current representation,
and reach the same coarsest sufficient quotient as an exhaustive oracle under a
minimal query budget?

Protocol
--------
* Finite world X: 16 anonymous states.
* Initial representation: the indiscrete/constant quotient (all states aliased).
* Future: 60 anonymous verifier-valid Boolean continuations.  They are deliberately
  distractor-rich/redundant: many surface continuations induce the same structural
  distinction, while three independent distinctions are jointly necessary.
* No continuation is marked as a target, important, or structurally privileged.
* The controller may choose only 3 verifier queries.
* At step t it scores each unqueried continuation by how many pairs that are STILL
  aliased by R_t the continuation would separate.  This is the residual-coverage
  criterion.  After external verification, the consequence is retained and R_t is
  refined by intersecting with its kernel.
* Oracle: exhaustively compute the quotient induced by ALL future consequences and
  the minimum number of consequences needed to induce that quotient.
* Controls under the identical budget:
    1. exhaustive random 3-subsets of the 60 consequences;
    2. a no-residual-update sham that keeps scoring against R_0.
* Transfer: repeat in three source-distinct sealed worlds with different latent bit
  choices, state permutations, and axis-to-surface multiplicity assignments.

Success is NOT workflow green.  The scientific gate is the explicit PASS block at
bottom.  Boundary: the finite world, candidate consequence pool, verifier and
residual-coverage selection law are supplied.  This tests autonomous SELECTION of
what is consequential, not unrestricted invention of new consequence types.
"""
from __future__ import annotations

from itertools import combinations, product
from math import comb

STATES = tuple(product((0, 1), repeat=4))
BUDGET = 3


def parity_bit(x, bit):
    return x[bit]


def complement(v):
    return tuple(1 - z for z in v)


def canonical_partition(vectors, n_states=16):
    """Partition state indices by their signatures under retained consequences."""
    buckets = {}
    for i in range(n_states):
        sig = tuple(v[i] for v in vectors)
        buckets.setdefault(sig, []).append(i)
    return tuple(sorted((tuple(g) for g in buckets.values()), key=lambda g: g[0]))


def unresolved_pairs(partition):
    return tuple((i, j) for g in partition for i, j in combinations(g, 2))


def residual_gain(partition, vector):
    """How many currently aliased pairs this prospective consequence separates."""
    return sum(vector[i] != vector[j] for i, j in unresolved_pairs(partition))


def permute_vector(v, permutation):
    # New anonymous state index i denotes old state permutation[i].
    return tuple(v[permutation[i]] for i in range(len(permutation)))


def make_world(name, latent_bits, multiplicities, permutation):
    assert len(latent_bits) == 3
    assert sorted(multiplicities) == [1, 4, 55]
    assert sorted(permutation) == list(range(16))

    candidates = []
    # Surface IDs deliberately reveal neither latent bit nor structural family.
    serial = 0
    for axis, (bit, count) in enumerate(zip(latent_bits, multiplicities)):
        base = tuple(parity_bit(x, bit) for x in STATES)
        for k in range(count):
            # Complementing half the spellings changes values but not the induced
            # equivalence relation, creating genuine surface redundancy.
            raw = complement(base) if (k % 2) else base
            vector = permute_vector(raw, permutation)
            candidates.append({
                "name": f"c{serial:02d}",
                "vector": vector,
                "sealed_axis": axis,   # verifier/audit only; controller never reads
            })
            serial += 1
    assert len(candidates) == 60
    return {"name": name, "candidates": tuple(candidates)}


WORLDS = (
    make_world(
        "W_A",
        latent_bits=(0, 1, 2),
        multiplicities=(55, 4, 1),
        permutation=(7, 0, 12, 3, 15, 8, 5, 10, 2, 13, 6, 1, 14, 9, 4, 11),
    ),
    make_world(
        "W_B",
        latent_bits=(3, 0, 2),
        multiplicities=(4, 1, 55),
        permutation=(11, 4, 1, 14, 9, 2, 13, 6, 0, 15, 8, 5, 10, 3, 12, 7),
    ),
    make_world(
        "W_C",
        latent_bits=(1, 3, 0),
        multiplicities=(1, 55, 4),
        permutation=(5, 10, 3, 12, 7, 0, 15, 8, 13, 6, 1, 14, 9, 2, 11, 4),
    ),
)


def verifier(world, candidate):
    """External semantic gate.  Candidate identity alone never grants retention."""
    # In this sealed experiment every member of the future-continuation pool is a
    # legitimate consequence.  Verification re-evaluates membership AND exact bits.
    for sealed in world["candidates"]:
        if sealed["name"] == candidate["name"]:
            return sealed["vector"] == candidate["vector"]
    return False


def oracle(world):
    vectors = [c["vector"] for c in world["candidates"]]
    target = canonical_partition(vectors)
    minimum = None
    witnesses = []
    for k in range(BUDGET + 1):
        for idxs in combinations(range(len(vectors)), k):
            if canonical_partition([vectors[i] for i in idxs]) == target:
                minimum = k
                witnesses.append(idxs)
        if minimum is not None:
            break
    assert minimum is not None
    return target, minimum, tuple(witnesses)


def residual_controller(world, budget=BUDGET):
    retained = []
    queried = set()
    trace = []
    for step in range(1, budget + 1):
        current = canonical_partition([c["vector"] for c in retained])
        scored = []
        for c in world["candidates"]:
            if c["name"] in queried:
                continue
            scored.append((residual_gain(current, c["vector"]), c["name"], c))
        scored.sort(key=lambda row: (-row[0], row[1]))
        gain, _, chosen = scored[0]
        queried.add(chosen["name"])
        ok = verifier(world, chosen)
        trace.append((step, chosen["name"], gain, ok, len(current)))
        if ok:
            retained.append(chosen)
    final = canonical_partition([c["vector"] for c in retained])
    return final, tuple(trace), tuple(c["name"] for c in retained)


def no_residual_update_sham(world, budget=BUDGET):
    """Ablation: rank every query against R_0 instead of the evolving residual."""
    r0 = canonical_partition([])
    ranked = sorted(
        world["candidates"],
        key=lambda c: (-residual_gain(r0, c["vector"]), c["name"]),
    )
    picked = ranked[:budget]
    assert all(verifier(world, c) for c in picked)
    return canonical_partition([c["vector"] for c in picked]), tuple(c["name"] for c in picked)


def exhaustive_random_control(world, target, budget=BUDGET):
    """Exact random-subset baseline: enumerate every matched-budget subset."""
    vectors = [c["vector"] for c in world["candidates"]]
    successes = 0
    total = 0
    for idxs in combinations(range(len(vectors)), budget):
        total += 1
        if canonical_partition([vectors[i] for i in idxs]) == target:
            successes += 1
    assert total == comb(len(vectors), budget)
    return successes, total


def main():
    rows = []
    for world in WORLDS:
        target, oracle_min, witnesses = oracle(world)
        got, trace, retained = residual_controller(world)
        sham, sham_names = no_residual_update_sham(world)
        rand_success, rand_total = exhaustive_random_control(world, target)

        print("V13_WORLD", world["name"])
        print("V13_ORACLE_CLASSES", len(target), "MIN_QUERIES", oracle_min,
              "MIN_WITNESSES", len(witnesses))
        print("V13_RESIDUAL_TRACE", trace)
        print("V13_RESIDUAL_RETAINED", retained, "CLASSES", len(got),
              "EXACT_ORACLE", got == target)
        print("V13_SHAM", sham_names, "CLASSES", len(sham),
              "EXACT_ORACLE", sham == target)
        print("V13_RANDOM_EXACT", rand_success, "/", rand_total,
              "RATE", rand_success / rand_total)

        assert oracle_min == BUDGET
        assert len(target) == 8
        assert got == target
        assert sham != target
        # Exact matched-budget random baseline must be below 1%.
        assert rand_success / rand_total < 0.01
        rows.append((world["name"], trace, rand_success, rand_total))

    # Transfer gate: the same consequence-selection law must close every independently
    # permuted world without inspecting latent bit IDs or sealed structural families.
    assert len(rows) == 3
    print("NO_PRIVILEGED_TARGET_CONSEQUENCE=PASS")
    print("RESIDUAL_DRIVEN_CONSEQUENCE_SELECTION_MATCHES_ORACLE_MINIMUM=PASS")
    print("EXACT_MINIMAL_SUFFICIENT_QUOTIENT_REACHED_IN_ALL_SOURCE_DISTINCT_WORLDS=PASS")
    print("NO_RESIDUAL_UPDATE_ABLATION_FAILS_ALL_WORLDS=PASS")
    print("EXHAUSTIVE_MATCHED_BUDGET_RANDOM_SUCCESS_BELOW_1_PERCENT=PASS")
    print("AUTONOMOUS_CONSEQUENCE_SELECTION_FIXED_POINT_V13=PASS")
    print("BOUNDARY=finite future-consequence pool and residual-coverage law supplied; consequence selection is autonomous, consequence-type invention is not")


if __name__ == "__main__":
    main()
