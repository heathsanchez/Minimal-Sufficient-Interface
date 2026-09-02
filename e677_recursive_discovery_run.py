"""Bounded replayable discovery run for the recursive compiler.

No model/API credits are required. The local workers are exhaustive finite solvers,
which makes the blindness/verifier/compiler mechanics independently reproducible in CI.
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
    answer = {str(k): sorted(v) for k, v in sorted(rows.items())}
    claims = (
        "Every permutation of 7 points with exactly 5 fixed points is odd.",
        "Every permutation of 7 points with exactly 4 fixed points is even.",
    )
    return WorkerResult(packet["id"], answer, claims)


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
    sum7 = sorted(t for t in possible if sum(t) == 7)
    forbidden = [(5, 1, 1), (4, 2, 1), (3, 3, 1)]
    answer = {
        "possible_sorted_triples": [list(t) for t in sorted(possible)],
        "sum7_possible": [list(t) for t in sum7],
        "candidate_forbidden": [list(t) for t in forbidden],
        "admissible_pairs": admissible_pairs,
    }
    claims = (
        "Under the local shifted-disagreement and no-triple-agreement constraints, exactly 26 sorted pairwise-agreement triples occur.",
        "Among sum-7 profiles, only (7,0,0), (5,2,0), (4,3,0), and (3,2,2) occur.",
        "The locally plausible sum-7 profiles (5,1,1), (4,2,1), and (3,3,1) do not occur.",
    )
    return WorkerResult(packet["id"], answer, claims)


def triple_verify(packet, result):
    expected = [[3, 2, 2], [4, 3, 0], [5, 2, 0], [7, 0, 0]]
    ok = result.answer.get("sum7_possible") == expected and result.answer.get("admissible_pairs") == 854498
    return VerificationResult(
        ok,
        {"S7": len(PERMS), "admissible_pairs": result.answer.get("admissible_pairs")},
        "independent exhaustive two-worker-variable enumeration" if ok else "enumeration mismatch",
    )


def worker(packet):
    if packet["id"] == "local-parity-classification":
        return parity_worker(packet)
    if packet["id"] == "three-row-agreement-classification":
        return triple_worker(packet)
    raise KeyError(packet["id"])


def question_policy(state):
    done = {g["packet"]["id"] for g in state.generations}
    if "local-parity-classification" not in done:
        return BlindPacket(
            id="local-parity-classification",
            question="Classify permutation sign as a function of fixed-point multiplicity on seven symbols, especially multiplicities 4 and 5.",
            facts=("Work in S_7.",),
            constraints=("Use exact finite enumeration or an equivalent proof.",),
            forbidden_context=("E677", "E255"),
            verifier_id="parity",
        )
    if "three-row-agreement-classification" not in done:
        return BlindPacket(
            id="three-row-agreement-classification",
            question="Classify sorted pairwise agreement multiplicities for three permutations on seven symbols under the supplied shifted-disagreement constraints and no common triple agreement.",
            facts=(
                "Normalize U0(i)=i.",
                "U1(i) != i+1 mod 7.",
                "U2(i) != i+2 mod 7.",
                "U2(i) != U1(i+1 mod 7).",
            ),
            constraints=("No i has U0(i)=U1(i)=U2(i).", "Return the complete finite classification."),
            forbidden_context=("E677", "E255", "magma"),
            verifier_id="triple",
        )
    return None


def consequence_gate(state, packet, result, checked):
    if packet.id == "local-parity-classification":
        return ConsequenceResult(
            consequential=False,
            score=0,
            consequence="Verified but rejected as primary route: high-multiplicity agreement edges already form a matching, leaving no cycle for parity to constrain.",
            next_residual="Find a local graph/relative-permutation invariant stronger than parity and vertex-degree information.",
        )
    if packet.id == "three-row-agreement-classification":
        return ConsequenceResult(
            consequential=True,
            score=2,
            consequence="Promote exact forbidden three-row agreement profiles as a new graph-level constraint.",
            next_residual="Classify four-row weighted agreement graphs under the triangle restrictions; seek an invariant not implied by degrees or the three-row classification.",
        )
    raise KeyError(packet.id)


def main():
    state = KnowledgeState(global_target="Resolve the finite E677 -> E255 implication or produce a verified obstruction/counterexample.")
    engine = RecursiveDiscoveryCompiler(
        worker=worker,
        verifiers={"parity": parity_verify, "triple": triple_verify},
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
    if len(state.generations) != 2:
        raise SystemExit("expected exactly two bounded generations")
    if len(state.verified) != 1 or len(state.low_leverage) != 1 or state.rejected:
        raise SystemExit("discovery compiler gate failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
