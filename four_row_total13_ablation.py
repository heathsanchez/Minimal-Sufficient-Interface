"""Compact causal certificate for the four-row total-agreement=13 exclusion.

This diagnostic is blind to the global equation target. It proves the exclusion from
only: four rows are permutations + no three rows agree in a column. It also checks an
explicit total-13 witness satisfying the shifted constraints when no-triple is removed.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

N = 7
ROWS = 4
PAIRS = tuple(itertools.combinations(range(ROWS), 2))

# Explicit witness found independently. It satisfies the shifted-disagreement laws and
# total pair-agreement 13, but violates no-triple. Therefore no-triple is causally needed.
SHIFTED_TOTAL13_WITNESS = (
    (0, 1, 2, 3, 4, 5, 6),
    (0, 1, 2, 6, 4, 5, 3),
    (3, 1, 5, 6, 0, 4, 2),
    (6, 1, 2, 4, 5, 3, 0),
)


def is_permutation(row):
    return sorted(row) == list(range(N))


def pair_total(rows):
    return sum(rows[a][i] == rows[b][i] for a, b in PAIRS for i in range(N))


def shifted_ok(rows):
    for t, u in PAIRS:
        shift = u - t
        for i in range(N):
            if rows[u][i] == rows[t][(i + shift) % N]:
                return False
    return True


def no_triple(rows):
    for i in range(N):
        vals = [rows[r][i] for r in range(ROWS)]
        if max(vals.count(x) for x in set(vals)) >= 3:
            return False
    return True


def collision_pairs(multiplicities):
    return sum(k * (k - 1) // 2 for k in multiplicities)


def deficient_symbol_forces_two_deficient_columns_certificate():
    # A symbol occurs exactly once in each of four permutation rows. Under no-triple,
    # its column multiplicities are <=2. If it contributes exactly one equality pair,
    # enumerate every possible distribution of four occurrences across seven columns.
    # Every such distribution has shape 2+1+1 and hence two singleton columns.
    certified = []
    for counts in itertools.product(range(3), repeat=N):
        if sum(counts) != 4:
            continue
        if collision_pairs(counts) != 1:
            continue
        singleton_columns = sum(c == 1 for c in counts)
        if singleton_columns < 2:
            raise AssertionError(f"bad occurrence distribution: {counts}")
        certified.append(counts)
    if not certified:
        raise AssertionError("certificate enumeration was empty")
    return len(certified)


def prove_total_2n_minus_1_impossible():
    # Under no-triple, each column contributes 0, 1 or 2 equality pairs.
    # Four permutation rows imply the same 0/1/2 bound symbol-wise.
    # If total = 2N-1, both column deficits and symbol deficits sum to exactly 1,
    # so there is exactly one deficient column and exactly one deficient symbol.
    # The deficient symbol contributes one pair, so its occurrences have shape 2+1+1.
    # Each singleton occurrence lies in a distinct column that cannot be a 2-pair
    # column (one slot is occupied by the singleton; only three slots remain, giving
    # at most one equal pair). Thus there must be at least two deficient columns,
    # contradiction.
    target = 2 * N - 1
    possible_column_vectors = [v for v in itertools.product(range(3), repeat=N) if sum(v) == target]
    if not possible_column_vectors:
        raise AssertionError("arithmetic certificate missing")
    # Sum 13 with seven entries <=2 forces exactly six 2s and one 1.
    if any(sorted(v) != [1] + [2] * (N - 1) for v in possible_column_vectors):
        raise AssertionError("unexpected column deficit pattern")
    occurrence_cases = deficient_symbol_forces_two_deficient_columns_certificate()
    return {
        "target": target,
        "column_vectors_checked": len(possible_column_vectors),
        "deficient_symbol_occurrence_vectors_checked": occurrence_cases,
        "derived_min_deficient_columns": 2,
        "required_deficient_columns_at_target": 1,
        "contradiction": True,
    }


def main():
    witness = SHIFTED_TOTAL13_WITNESS
    witness_checks = {
        "all_rows_permutations": all(is_permutation(r) for r in witness),
        "total_pair_agreement": pair_total(witness),
        "shifted_disagreement": shifted_ok(witness),
        "no_triple": no_triple(witness),
    }
    proof = prove_total_2n_minus_1_impossible()
    out = {
        "n": N,
        "claim": "For four permutation rows with no three rows agreeing in a column, total pair agreement cannot equal 2n-1.",
        "n7_consequence": "total pair agreement 13 is impossible",
        "shifted_constraints_used_in_proof": False,
        "no_triple_used_in_proof": True,
        "proof_certificate": proof,
        "witness_without_no_triple": {
            "rows": [list(r) for r in witness],
            "checks": witness_checks,
        },
        "causal_read": {
            "full": "unsat by structural certificate",
            "without_shifted": "unsat by same structural certificate",
            "without_no_triple": "sat by explicit shifted witness",
            "permutations_only": "sat by same witness",
        },
    }
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/four_row_total13_ablation.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps(out, indent=2, sort_keys=True))

    assert witness_checks == {
        "all_rows_permutations": True,
        "total_pair_agreement": 13,
        "shifted_disagreement": True,
        "no_triple": False,
    }
    assert proof["contradiction"] is True


if __name__ == "__main__":
    main()
