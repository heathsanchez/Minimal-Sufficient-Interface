"""Frontier-driven exact test of the next nonlinear D-curvature layer.

This experiment is intentionally self-routing: it refuses to run unless
program_frontier.json is authoritative and its single live residual asks for
the next D-curvature layer followed by the four-row T6 PAIR-KERNEL gate.

No unproved scalar/gauge quotient is used for the new layer.  We exhaust all
7! D permutations, derive the curvature spectrum, identify the first nonlinear
layer above kappa=18, and use only the exact output-translation symmetry
D -> D+c.  PAIR-KERNEL compares two expressions containing D with the same
additive output offset, so this symmetry cancels identically.  Each orbit has
a unique representative with D(0)=0.

For every normalized D in that next layer, every one of the 141 shifted phase
states is tested against all 720 normalized A fixing zero under the same
source-backed four-row T6 PAIR-KERNEL used by the preceding attachment probe.
"""
from __future__ import annotations

import collections
import itertools
import json
from pathlib import Path

from partition_derangement_probe import enumerate_states, shifted_ok
from phase_T6_four_row_attachment_probe import A_FIX0, pair_kernel_ok

N = 7
FRONTIER = Path("program_frontier.json")
OUT = Path("artifacts/phase_T6_next_curvature_probe.json")


def derivative_counts(p: tuple[int, ...], shift: int) -> tuple[int, ...]:
    c = collections.Counter((p[(x + shift) % N] - p[x]) % N for x in range(N))
    return tuple(sorted(c.values(), reverse=True))


def curvature(p: tuple[int, ...]) -> int:
    return sum(N - derivative_counts(p, t)[0] for t in range(1, N))


def is_affine(p: tuple[int, ...]) -> bool:
    return any(
        all(p[x] == (a * x + b) % N for x in range(N))
        for a in range(1, N)
        for b in range(N)
    )


def output_translate(p: tuple[int, ...], c: int) -> tuple[int, ...]:
    return tuple((v + c) % N for v in p)


def normalize_output(p: tuple[int, ...]) -> tuple[int, ...]:
    return output_translate(p, (-p[0]) % N)


def load_and_check_frontier() -> dict:
    x = json.loads(FRONTIER.read_text())
    assert x["authoritative"] is True
    assert x["branch"] == "recursive-discovery-compiler-v1"
    r = x["live_residual"]
    assert r["type"] == "DERIVATION"
    text = r["text"].lower()
    assert "next attainable nonlinear d-curvature" in text
    assert "four-row t6 pair-kernel" in text
    assert any(v.get("id") == "kappa18_excluded" for v in x["promoted"])
    return x


def classify_curvature() -> tuple[dict[int, int], int, list[tuple[int, ...]], list[tuple[int, ...]]]:
    by_kappa: collections.Counter[int] = collections.Counter()
    layer: dict[int, list[tuple[int, ...]]] = collections.defaultdict(list)
    affine_count = 0
    for p in itertools.permutations(range(N)):
        if is_affine(p):
            affine_count += 1
            continue
        k = curvature(p)
        by_kappa[k] += 1
        layer[k].append(p)
    assert affine_count == 42
    assert sum(by_kappa.values()) == 4998
    assert by_kappa[18] == 294
    ks = sorted(by_kappa)
    assert ks[0] == 18
    next_kappa = ks[1]
    labelled = layer[next_kappa]
    normalized = sorted({normalize_output(p) for p in labelled})

    # Exact quotient audit for the only symmetry used here.
    assert all(p[0] == 0 for p in normalized)
    assert len(labelled) == N * len(normalized)
    labelled_set = set(labelled)
    for q in normalized:
        orbit = {output_translate(q, c) for c in range(N)}
        assert len(orbit) == N
        assert orbit <= labelled_set
    assert {normalize_output(p) for p in labelled} == set(normalized)
    return dict(sorted(by_kappa.items())), next_kappa, labelled, normalized


def shifted_states():
    states = []
    for blocks, sigmas, rows in enumerate_states():
        if shifted_ok(rows):
            states.append(rows)
    assert len(states) == 141
    return states


def main() -> None:
    frontier = load_and_check_frontier()
    spectrum, next_kappa, labelled, normalized = classify_curvature()
    assert next_kappa > 18

    states = shifted_states()
    survivors_by_D: dict[str, int] = {}
    witness_by_D: dict[str, dict] = {}
    total_pairs = 0
    surviving_pairs = 0

    for D in normalized:
        dkey = "".join(map(str, D))
        d_survivors = 0
        for state_index, rows in enumerate(states):
            total_pairs += 1
            witness = None
            for A in A_FIX0:
                if pair_kernel_ok(rows, A, D):
                    witness = A
                    break
            if witness is not None:
                surviving_pairs += 1
                d_survivors += 1
                witness_by_D.setdefault(dkey, {
                    "phase_state_index": state_index,
                    "rows": [list(r) for r in rows],
                    "A": list(witness),
                })
        survivors_by_D[dkey] = d_survivors

    ds_with_survivor = sum(v > 0 for v in survivors_by_D.values())
    rejected_pairs = total_pairs - surviving_pairs
    full_layer_excluded_by_projection = surviving_pairs == 0

    if full_layer_excluded_by_projection:
        classification = "PROMOTE"
        residual = (
            f"The exact next nonlinear curvature layer kappa={next_kappa} is also excluded "
            "by the source-backed four-row T6 PAIR-KERNEL projection after exhaustive "
            "output-translation normalization. Update the authoritative frontier, then "
            "derive and test the next attainable nonlinear curvature layer before any "
            "higher-arity escalation."
        )
    else:
        classification = "REQUIRE_ATTACHMENT"
        residual = (
            f"At kappa={next_kappa}, the four-row T6 PAIR-KERNEL projection leaves "
            f"{surviving_pairs} normalized D/phase-state pairs across {ds_with_survivor} D maps. "
            "Compile exactly those survivors and attach the first genuinely multi-row "
            "relative-pair TRIANGLE-COCYCLE constraint; do not widen to raw seven-row search."
        )

    out = {
        "consumed_frontier": {
            "schema_version": frontier["schema_version"],
            "live_state_parent_sha": frontier["live_state_parent_sha"],
            "live_residual": frontier["live_residual"],
        },
        "curvature_definition": "sum_{t!=0}(7-max_v |{x:D(x+t)-D(x)=v}|)",
        "nonlinear_curvature_spectrum": {str(k): v for k, v in spectrum.items()},
        "previous_excluded_kappa": 18,
        "next_attainable_nonlinear_kappa": next_kappa,
        "labelled_maps_in_next_layer": len(labelled),
        "normalization": "output translation D -> D+c, unique representative D(0)=0",
        "normalized_D_count": len(normalized),
        "normalization_coverage_exact": len(labelled) == N * len(normalized),
        "phase_states": len(states),
        "A_domain": "all 720 permutations of Z7 fixing 0",
        "rows_tested": [0, 1, 2, 3],
        "normalized_D_phase_pairs": total_pairs,
        "surviving_pairs": surviving_pairs,
        "rejected_pairs": rejected_pairs,
        "D_maps_with_survivor": ds_with_survivor,
        "survivors_by_D": survivors_by_D,
        "witness_by_surviving_D": witness_by_D,
        "full_layer_excluded_by_four_row_projection": full_layer_excluded_by_projection,
        "full_seven_row_core_claimed": False,
        "e677_implication_solved_claimed": False,
        "proposed_transition": {
            "classification": classification,
            "scope": f"n=7 next nonlinear D-curvature layer kappa={next_kappa}; necessary four-row T6 projection",
            "residual": residual,
        },
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "spectrum": out["nonlinear_curvature_spectrum"],
        "next_kappa": next_kappa,
        "labelled": len(labelled),
        "normalized_D": len(normalized),
        "phase_states": len(states),
        "pairs": total_pairs,
        "survivors": surviving_pairs,
        "D_with_survivor": ds_with_survivor,
        "classification": classification,
        "residual": residual,
    }, indent=2, sort_keys=True))
    print("FRONTIER_CONSUMED_WITHOUT_CHAT_STATE")
    print("T6_NEXT_CURVATURE_PROBE_PASS")


if __name__ == "__main__":
    main()
