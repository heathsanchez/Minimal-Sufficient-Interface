from __future__ import annotations

import itertools
import json
import os
import sys
from pathlib import Path
from typing import Any

MSI_ROOT = Path(os.environ["MSI_ROOT"]).resolve()
ENVROOT = Path(os.environ["ENVROOT"]).resolve()
METATRON_ROOT = Path(os.environ["METATRON_ROOT"]).resolve()
OUTDIR = Path(os.environ.get("OUTDIR", MSI_ROOT / "evidence" / "arc3-certified-developmental-atlas-v3"))
OUTDIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(MSI_ROOT / "experiments"))
sys.path.insert(0, str(METATRON_ROOT))

from arc3_certified_capability_slice_v1 import canon, features, grid_hash, make_env  # noqa: E402
from arc3_residual_generated_capability_v2 import execute_click, hist_key  # noqa: E402
from arcengine import GameState  # noqa: E402
from runtime.metatron.nucleus import Node, append, dumps, live_ids  # noqa: E402

ATLAS_PATH = MSI_ROOT / "evidence" / "arc3-residual-generated-capability-v2" / "frozen-atlas.json"

FEATURE_NAMES = [
    "n_colors",
    "color_histogram",
    "nonzero_count",
    "nonzero_bbox",
    "small_component_count",
    "small_component_areas",
    "small_component_boxes",
    "row_transitions",
    "col_transitions",
    "lr_symmetric",
    "tb_symmetric",
    "corner_signature",
    "center_value",
]


def load_atlas() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    raw = json.loads(ATLAS_PATH.read_text())
    atlas = {
        row["guard"]: {
            "coord": list(row["coord"]),
            "max_steps": int(row["max_steps"]),
            "source": row["source"],
            "level_discovered": int(row["level_discovered"]),
        }
        for row in raw["capabilities"]
    }
    return atlas, raw


def collect_states(atlas: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[tuple[int, int], int]]:
    _, env, _ = make_env(ENVROOT)
    rows: list[dict[str, Any]] = []
    cap_ids: dict[tuple[int, int], int] = {}

    while env.observation_space.state != GameState.WIN:
        frame = env.observation_space
        key = hist_key(frame)
        cap = atlas.get(key)
        if cap is None:
            raise AssertionError(f"frozen atlas missing guard at level {frame.levels_completed}: {key}")
        coord = tuple(int(x) for x in cap["coord"])
        if coord not in cap_ids:
            cap_ids[coord] = len(cap_ids)
        feat = features(frame)
        rows.append({
            "level": int(frame.levels_completed),
            "grid_hash": grid_hash(frame),
            "hist_key": key,
            "features": feat,
            "coord": list(coord),
            "cap_class": cap_ids[coord],
            "max_steps": int(cap["max_steps"]),
        })
        res = execute_click(env, coord, int(cap["max_steps"]))
        if not res["progressed"]:
            raise AssertionError(f"frozen capability failed at level {rows[-1]['level']}")
        rows[-1]["actions"] = int(res["actions"])
        rows[-1]["end_level"] = int(res["end_level"])
        rows[-1]["end_state"] = res["end_state"]
    return rows, cap_ids


def minimal_basis(rows: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    def sig(row: dict[str, Any], subset: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(canon(row["features"][name]) for name in subset)

    def sufficient(subset: tuple[str, ...]) -> bool:
        seen: dict[tuple[str, ...], int] = {}
        for row in rows:
            s = sig(row, subset)
            label = int(row["cap_class"])
            if s in seen and seen[s] != label:
                return False
            seen[s] = label
        return True

    chosen: tuple[str, ...] | None = None
    for k in range(len(FEATURE_NAMES) + 1):
        for subset in itertools.combinations(FEATURE_NAMES, k):
            if sufficient(subset):
                chosen = subset
                break
        if chosen is not None:
            break
    if chosen is None:
        raise AssertionError("no sufficient basis")

    minimality: list[dict[str, Any]] = []
    for drop in chosen:
        sub = tuple(x for x in chosen if x != drop)
        witness = None
        for i, a in enumerate(rows):
            for j, b in enumerate(rows):
                if i >= j:
                    continue
                if sig(a, sub) == sig(b, sub) and a["cap_class"] != b["cap_class"]:
                    witness = {
                        "dropped": drop,
                        "remaining": list(sub),
                        "left_level": a["level"],
                        "right_level": b["level"],
                        "left_class": a["cap_class"],
                        "right_class": b["cap_class"],
                    }
                    break
            if witness:
                break
        if witness is None:
            raise AssertionError(f"basis not inclusion-minimal at {drop}")
        minimality.append(witness)
    return list(chosen), minimality


def signature_table(rows: list[dict[str, Any]], basis: list[str]) -> dict[str, dict[str, Any]]:
    table: dict[str, dict[str, Any]] = {}
    for row in rows:
        s = canon(tuple(canon(row["features"][name]) for name in basis))
        rec = {"cap_class": row["cap_class"], "coord": row["coord"]}
        old = table.get(s)
        if old is not None and old != rec:
            raise AssertionError("same guard signature maps to different capabilities")
        table[s] = rec
    return table


def cold_replay(atlas: dict[str, dict[str, Any]]) -> dict[str, Any]:
    _, env, _ = make_env(ENVROOT)
    trace: list[dict[str, Any]] = []
    while env.observation_space.state != GameState.WIN:
        key = hist_key(env.observation_space)
        cap = atlas.get(key)
        if cap is None:
            return {
                "won": False,
                "levels_completed": int(env.observation_space.levels_completed),
                "state": str(env.observation_space.state),
                "unknown_guard": key,
                "trace": trace,
            }
        start = int(env.observation_space.levels_completed)
        res = execute_click(env, tuple(cap["coord"]), int(cap["max_steps"]))
        trace.append({
            "level": start,
            "guard": key,
            "coord": cap["coord"],
            "budget": cap["max_steps"],
            "actions": res["actions"],
            "progressed": res["progressed"],
            "end_level": res["end_level"],
            "end_state": res["end_state"],
        })
        if not res["progressed"]:
            return {
                "won": False,
                "levels_completed": int(env.observation_space.levels_completed),
                "state": str(env.observation_space.state),
                "failed_guard": key,
                "trace": trace,
            }
    return {
        "won": True,
        "levels_completed": int(env.observation_space.levels_completed),
        "state": str(env.observation_space.state),
        "trace": trace,
        "actions": [x["actions"] for x in trace],
    }


def ablate(atlas: dict[str, dict[str, Any]], coord: tuple[int, int]) -> dict[str, Any]:
    reduced = {k: v for k, v in atlas.items() if tuple(v["coord"]) != coord}
    r = cold_replay(reduced)
    return {
        "removed_coord": list(coord),
        "won": r["won"],
        "levels_completed": r["levels_completed"],
        "state": r["state"],
    }


def emit_lean(path: Path, rows: list[dict[str, Any]], basis: list[str]) -> None:
    n = len(rows)
    cap = [int(r["cap_class"]) for r in rows]
    raw_hash_class = list(range(n))

    encoded: dict[str, list[int]] = {}
    for name in basis:
        classes: dict[str, int] = {}
        arr = []
        for r in rows:
            v = canon(r["features"][name])
            if v not in classes:
                classes[v] = len(classes)
            arr.append(classes[v])
        encoded[name] = arr

    def ln(xs: list[int]) -> str:
        return "[" + ",".join(str(x) for x in xs) + "]"

    lines = [
        "import Std",
        "",
        "namespace Arc3CertifiedDevelopmentalAtlasV3",
        f"def indices : List Nat := List.range {n}",
        f"def capClass : List Nat := {ln(cap)}",
        f"def rawClass : List Nat := {ln(raw_hash_class)}",
        "def cap (i : Nat) : Nat := capClass.getD i 999",
        "def raw (i : Nat) : Nat := rawClass.getD i 999",
    ]
    for idx, name in enumerate(basis):
        lines.append(f"def feat{idx} : List Nat := {ln(encoded[name])}")

    if basis:
        eq_terms = [f"(feat{k}.getD i 999 == feat{k}.getD j 999)" for k in range(len(basis))]
        eq_expr = " && ".join(eq_terms)
    else:
        eq_expr = "true"

    lines += [
        f"def eqGuard (i j : Nat) : Bool := {eq_expr}",
        "def sufficientB : Bool := indices.all (fun i => indices.all (fun j => (! eqGuard i j) || (cap i == cap j)))",
        "theorem selected_basis_sufficient : sufficientB = true := by decide",
    ]

    for drop in range(len(basis)):
        terms = [f"(feat{k}.getD i 999 == feat{k}.getD j 999)" for k in range(len(basis)) if k != drop]
        expr = " && ".join(terms) if terms else "true"
        lines += [
            f"def eqWithout{drop} (i j : Nat) : Bool := {expr}",
            f"def residualWithout{drop}B : Bool := indices.any (fun i => indices.any (fun j => eqWithout{drop} i j && (cap i != cap j)))",
            f"theorem basis_member_{drop}_necessary : residualWithout{drop}B = true := by decide",
        ]

    lines += [
        "def quotientReuseB : Bool := indices.any (fun i => indices.any (fun j => (i != j) && eqGuard i j && (cap i == cap j) && (raw i != raw j)))",
        "theorem quotient_reuse_across_distinct_raw_states : quotientReuseB = true := by decide",
        "end Arc3CertifiedDevelopmentalAtlasV3",
        "",
    ]
    path.write_text("\n".join(lines))


def main() -> None:
    atlas, source = load_atlas()
    rows, cap_ids = collect_states(atlas)
    basis, minimality = minimal_basis(rows)
    table = signature_table(rows, basis)

    cold_runs = [cold_replay(atlas) for _ in range(7)]
    if not all(r["won"] for r in cold_runs):
        raise AssertionError("cold replay failure")
    if not all(r.get("actions") == [4, 8, 16, 20, 24] for r in cold_runs):
        raise AssertionError("cold action trajectory drift")

    coords = sorted(cap_ids, key=lambda x: cap_ids[x])
    ablations = [ablate(atlas, c) for c in coords]
    if any(a["won"] for a in ablations):
        raise AssertionError("capability ablation failed to remove win")

    # Evidence that exact observation identity can be coarser than raw representation.
    reuse_pairs = []
    for i, a in enumerate(rows):
        for j, b in enumerate(rows):
            if i >= j:
                continue
            same_guard = all(canon(a["features"][name]) == canon(b["features"][name]) for name in basis)
            if same_guard and a["cap_class"] == b["cap_class"] and a["grid_hash"] != b["grid_hash"]:
                reuse_pairs.append({
                    "left_level": a["level"],
                    "right_level": b["level"],
                    "cap_class": a["cap_class"],
                    "coord": a["coord"],
                    "left_hash": a["grid_hash"],
                    "right_hash": b["grid_hash"],
                })
    if not reuse_pairs:
        raise AssertionError("no cross-representation quotient reuse pair")

    lean_path = MSI_ROOT / "lean" / "Arc3CertifiedDevelopmentalAtlasV3.lean"
    emit_lean(lean_path, rows, basis)

    # Metatron authority graph: finite guard theorem -> capabilities -> atlas.
    log = ()
    guard_node = Node("guard_theorem", {
        "basis": basis,
        "sample_levels": [r["level"] for r in rows],
        "minimality": minimality,
        "scope": "five bt33 level-start states under frozen winning atlas",
    })
    log = append(log, guard_node)

    cap_nodes = []
    by_coord: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for r in rows:
        by_coord.setdefault(tuple(r["coord"]), []).append(r)
    for coord, group in by_coord.items():
        node = Node("capability", {
            "coord": list(coord),
            "levels": [x["level"] for x in group],
            "guard_signatures": [x["hist_key"] for x in group],
            "max_verified_steps": max(x["max_steps"] for x in group),
            "protected_consequence": "levels_completed increases",
        }, (guard_node.id,))
        log = append(log, node)
        cap_nodes.append(node)

    atlas_node = Node("compiled_atlas", {
        "source_run": source["source_run"],
        "source_artifact": source["source_artifact"],
        "observer_adapter": source["observer_adapter"],
        "model_calls": 0,
        "capability_classes": len(cap_nodes),
        "observation_signatures": len(atlas),
        "cold_replays": len(cold_runs),
        "all_won": True,
    }, tuple(n.id for n in cap_nodes))
    log = append(log, atlas_node)

    # Revocation closure: revoke one capability, atlas must fall out of live closure, history stays.
    target = cap_nodes[-1]
    rev = Node("revoke", {"target": target.id, "reason": "qualification revocation control"})
    log = append(log, rev)
    active = set(live_ids(log))
    if target.id in active or atlas_node.id in active:
        raise AssertionError("revocation failed to remove target-dependent atlas")
    history_ids = {n.id for n in log}
    if target.id not in history_ids or atlas_node.id not in history_ids:
        raise AssertionError("revocation erased lineage")

    result = {
        "status": "WARRANTED_WITHIN_DECLARED_FINITE_BOUNDARY",
        "source": source,
        "observer_adapter": source["observer_adapter"],
        "states": rows,
        "capability_classes": {
            str(i): {"coord": list(coord)}
            for coord, i in cap_ids.items()
        },
        "minimal_guard": {
            "basis": basis,
            "signature_table": table,
            "minimality_residuals": minimality,
        },
        "quotient_reuse_pairs": reuse_pairs,
        "cold_replays": {
            "count": len(cold_runs),
            "all_won": True,
            "action_trajectories": [r["actions"] for r in cold_runs],
            "model_calls": 0,
            "search_calls": 0,
        },
        "ablations": ablations,
        "authority": {
            "atlas_live_before_control_revoke": True,
            "revoked_capability_live_after": target.id in active,
            "dependent_atlas_live_after": atlas_node.id in active,
            "history_retained": target.id in history_ids and atlas_node.id in history_ids,
        },
        "claim_boundary": [
            "finite deterministic bt33 fixture only",
            "minimality only over five level-start states and declared feature language",
            "Lean theorem checks finite atlas classification/reuse, not unrestricted ARC intelligence",
            "cold replays use frozen V2 atlas; no model calls, search, or game-source inspection",
        ],
    }
    (OUTDIR / "result.json").write_text(json.dumps(result, indent=2))
    (OUTDIR / "metatron-log.jsonl").write_text(dumps(log))
    print(json.dumps(result, indent=2))
    print("ARC3_CERTIFIED_DEVELOPMENTAL_ATLAS_V3=PASS")


if __name__ == "__main__":
    main()
