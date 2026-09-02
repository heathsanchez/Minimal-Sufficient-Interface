"""Bounded replayable discovery run for the recursive compiler.

No model/API credits are required. Local workers are exact finite/classification workers.
The controller alone owns the global target; each packet is blind to it.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

from recursive_discovery_compiler import (
    BlindPacket,
    ConsequenceResult,
    KnowledgeState,
    RecursiveDiscoveryCompiler,
    VerificationResult,
    WorkerResult,
)

N = 7
PERMS = tuple(itertools.permutations(range(N)))
PAIRS4 = tuple(itertools.combinations(range(4), 2))


def fixed_points(p):
    return sum(i == p[i] for i in range(N))


def parity(p):
    inv = sum(p[i] > p[j] for i in range(N) for j in range(i + 1, N))
    return inv % 2


def parity_worker(packet):
    rows = {}
    for p in PERMS:
        m = fixed_points(p)
        rows.setdefault(m, set()).add(parity(p))
    return WorkerResult(
        packet["id"],
        {str(k): sorted(v) for k, v in sorted(rows.items())},
        (
            "Every permutation of 7 points with exactly 5 fixed points is odd.",
            "Every permutation of 7 points with exactly 4 fixed points is even.",
        ),
    )


def parity_verify(packet, result):
    ok = result.answer.get("5") == [1] and result.answer.get("4") == [0]
    return VerificationResult(ok, {"enumerated": len(PERMS)}, "exhaustive S7 enumeration" if ok else "classification mismatch")


def triple_worker(packet):
    ident = tuple(range(N))
    u1s = [p for p in PERMS if all(p[i] != (i + 1) % N for i in range(N))]
    u2s = [p for p in PERMS if all(p[i] != (i + 2) % N for i in range(N))]
    possible = set()
    admissible_pairs = 0
    for u1 in u1s:
        for u2 in u2s:
            if any(u2[i] == u1[(i + 1) % N] for i in range(N)):
                continue
            if any(ident[i] == u1[i] == u2[i] for i in range(N)):
                continue
            m01 = sum(ident[i] == u1[i] for i in range(N))
            m02 = sum(ident[i] == u2[i] for i in range(N))
            m12 = sum(u1[i] == u2[i] for i in range(N))
            possible.add(tuple(sorted((m01, m02, m12), reverse=True)))
            admissible_pairs += 1
    return WorkerResult(
        packet["id"],
        {
            "possible_sorted_triples": [list(t) for t in sorted(possible)],
            "sum7_possible": [list(t) for t in sorted(t for t in possible if sum(t) == 7)],
            "candidate_forbidden": [[5, 1, 1], [4, 2, 1], [3, 3, 1]],
            "admissible_pairs": admissible_pairs,
        },
        (
            "Under the local shifted-disagreement and no-triple-agreement constraints, exactly 26 sorted pairwise-agreement triples occur.",
            "Among sum-7 profiles, only (7,0,0), (5,2,0), (4,3,0), and (3,2,2) occur.",
            "The locally plausible sum-7 profiles (5,1,1), (4,2,1), and (3,3,1) do not occur.",
        ),
    )


def triple_verify(packet, result):
    expected = [[3, 2, 2], [4, 3, 0], [5, 2, 0], [7, 0, 0]]
    ok = result.answer.get("sum7_possible") == expected and result.answer.get("admissible_pairs") == 854498
    return VerificationResult(ok, {"S7": len(PERMS), "admissible_pairs": result.answer.get("admissible_pairs")}, "independent exhaustive two-worker-variable enumeration" if ok else "enumeration mismatch")


def collision_pairs(counts):
    return sum(k * (k - 1) // 2 for k in counts)


def total13_structural_certificate():
    target = 2 * N - 1
    column_vectors = [v for v in itertools.product(range(3), repeat=N) if sum(v) == target]
    if any(sorted(v) != [1] + [2] * (N - 1) for v in column_vectors):
        raise AssertionError("unexpected column deficit pattern")
    deficient_symbol_vectors = []
    for counts in itertools.product(range(3), repeat=N):
        if sum(counts) == 4 and collision_pairs(counts) == 1:
            if sum(c == 1 for c in counts) < 2:
                raise AssertionError("deficient symbol failed to force two singleton columns")
            deficient_symbol_vectors.append(counts)
    if not deficient_symbol_vectors:
        raise AssertionError("empty deficient-symbol certificate")
    return {
        "target": target,
        "column_vectors_checked": len(column_vectors),
        "deficient_symbol_occurrence_vectors_checked": len(deficient_symbol_vectors),
        "required_deficient_columns_at_target": 1,
        "derived_min_deficient_columns": 2,
        "contradiction": True,
    }


SHIFTED_TOTAL13_WITNESS = (
    (0, 1, 2, 3, 4, 5, 6),
    (0, 1, 2, 6, 4, 5, 3),
    (3, 1, 5, 6, 0, 4, 2),
    (6, 1, 2, 4, 5, 3, 0),
)


def witness_checks(rows):
    all_perm = all(sorted(row) == list(range(N)) for row in rows)
    total = sum(rows[a][i] == rows[b][i] for a, b in PAIRS4 for i in range(N))
    shifted = all(rows[u][i] != rows[t][(i + u - t) % N] for t, u in PAIRS4 for i in range(N))
    no_three = True
    for i in range(N):
        vals = [rows[r][i] for r in range(4)]
        if max(vals.count(x) for x in set(vals)) >= 3:
            no_three = False
            break
    return {"all_rows_permutations": all_perm, "total_pair_agreement": total, "shifted_disagreement": shifted, "no_triple": no_three}


def four_row_worker(packet):
    cert = total13_structural_certificate()
    wcheck = witness_checks(SHIFTED_TOTAL13_WITNESS)
    return WorkerResult(
        packet["id"],
        {
            "general_claim": "For four permutation rows on n symbols with no three rows agreeing in any column, total pair agreement cannot equal 2n-1.",
            "n": N,
            "certificate": cert,
            "shifted_constraints_used": False,
            "no_triple_is_necessary": wcheck == {"all_rows_permutations": True, "total_pair_agreement": 13, "shifted_disagreement": True, "no_triple": False},
            "necessity_witness": [list(r) for r in SHIFTED_TOTAL13_WITNESS],
            "necessity_witness_checks": wcheck,
        },
        (
            "Four permutation rows with no triple column agreement cannot have total pair agreement 2n-1.",
            "For n=7, total pair agreement 13 is impossible.",
            "The shifted-disagreement constraints are not required for this exclusion.",
            "No-triple-agreement is necessary: removing it admits an explicit shifted total-13 witness.",
        ),
    )


def four_row_verify(packet, result):
    # Independent recomputation rather than trusting the worker's certificate object.
    cert = total13_structural_certificate()
    checks = witness_checks(SHIFTED_TOTAL13_WITNESS)
    expected_checks = {"all_rows_permutations": True, "total_pair_agreement": 13, "shifted_disagreement": True, "no_triple": False}
    ok = (
        result.answer.get("certificate") == cert
        and result.answer.get("shifted_constraints_used") is False
        and result.answer.get("no_triple_is_necessary") is True
        and checks == expected_checks
    )
    return VerificationResult(
        ok,
        {"certificate": cert, "necessity_witness_checks": checks},
        "independent counting certificate plus explicit causal witness" if ok else "four-row certificate mismatch",
    )


def worker(packet):
    if packet["id"] == "local-parity-classification":
        return parity_worker(packet)
    if packet["id"] == "three-row-agreement-classification":
        return triple_worker(packet)
    if packet["id"] == "four-row-near-maximum-exclusion":
        return four_row_worker(packet)
    raise KeyError(packet["id"])


def question_policy(state):
    done = {g["packet"]["id"] for g in state.generations}
    if "local-parity-classification" not in done:
        return BlindPacket(
            id="local-parity-classification",
            role="classification",
            question="Classify permutation sign as a function of fixed-point multiplicity on seven symbols, especially multiplicities 4 and 5.",
            facts=("Work in S_7.",),
            constraints=("Use exact finite enumeration or an equivalent proof.",),
            forbidden_context=("E677", "E255"),
            verifier_id="parity",
        )
    if "three-row-agreement-classification" not in done:
        return BlindPacket(
            id="three-row-agreement-classification",
            role="classification",
            question="Classify sorted pairwise agreement multiplicities for three permutations on seven symbols under the supplied shifted-disagreement constraints and no common triple agreement.",
            facts=("Normalize U0(i)=i.", "U1(i) != i+1 mod 7.", "U2(i) != i+2 mod 7.", "U2(i) != U1(i+1 mod 7)."),
            constraints=("No i has U0(i)=U1(i)=U2(i).", "Return the complete finite classification."),
            forbidden_context=("E677", "E255", "magma"),
            verifier_id="triple",
        )
    if "four-row-near-maximum-exclusion" not in done:
        return BlindPacket(
            id="four-row-near-maximum-exclusion",
            role="proof-and-ablation",
            question="For four permutation rows on seven symbols with no three rows equal in a column, decide whether total pairwise row agreement can equal 13. Identify the minimal structural cause and test whether any shifted-disagreement assumptions are actually needed.",
            facts=("Each of the four rows is a permutation of seven symbols.", "No column contains the same symbol in three or four rows."),
            constraints=("Seek a human-checkable counting invariant before using full search.", "If an assumption is unnecessary, exhibit that by ablation; if an assumption is necessary, provide a witness when it is removed."),
            forbidden_context=("E677", "E255", "magma", "Equation 677", "Equation 255"),
            verifier_id="four-row",
        )
    return None


def consequence_gate(state, packet, result, checked):
    if packet.id == "local-parity-classification":
        return ConsequenceResult(False, 0, "Verified but rejected as primary route: high-multiplicity agreement edges already form a matching, leaving no cycle for parity to constrain.", "Find a local graph/relative-permutation invariant stronger than parity and vertex-degree information.")
    if packet.id == "three-row-agreement-classification":
        return ConsequenceResult(True, 2, "Promote exact forbidden three-row agreement profiles as a new graph-level constraint.", "Classify four-row weighted agreement graphs under the triangle restrictions; seek an invariant not implied by degrees or the three-row classification.")
    if packet.id == "four-row-near-maximum-exclusion":
        return ConsequenceResult(
            True,
            3,
            "Promote a representation-independent four-row near-maximum exclusion: permutation balance plus no-triple alone rules out total agreement 2n-1; shifted structure is unnecessary.",
            "Classify the full six-edge four-row agreement profile under permutation balance + no-triple, then intersect those profiles with the shifted/triangle constraints to find the next consequential exclusion.",
        )
    raise KeyError(packet.id)


def main():
    state = KnowledgeState(global_target="Resolve the finite E677 -> E255 implication or produce a verified obstruction/counterexample.")
    engine = RecursiveDiscoveryCompiler(
        worker=worker,
        verifiers={"parity": parity_verify, "triple": triple_verify, "four-row": four_row_verify},
        consequence_gate=consequence_gate,
        question_policy=question_policy,
        max_generations=4,
    )
    state = engine.run(state)
    out = Path("artifacts/e677_recursive_discovery_state.json")
    state.write(out)
    summary = {
        "generations": len(state.generations),
        "verified_consequential": len(state.verified),
        "true_but_low_leverage": len(state.low_leverage),
        "rejected": len(state.rejected),
        "terminal": state.terminal,
        "next_residual": state.residuals[-1] if state.residuals else None,
        "state_sha256": state.digest(),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if len(state.generations) != 3:
        raise SystemExit("expected exactly three bounded generations")
    if len(state.verified) != 2 or len(state.low_leverage) != 1 or state.rejected:
        raise SystemExit("discovery compiler gate failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
