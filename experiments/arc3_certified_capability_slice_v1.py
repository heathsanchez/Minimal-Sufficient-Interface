from __future__ import annotations

import hashlib
import itertools
import json
import logging
import os
import sys
from collections import Counter, deque
from pathlib import Path
from typing import Any

from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

WITNESS = (3, 3)
SHAM = (59, 3)
LAW = "repeat same intervention while live; protected progress is authority"
SOURCE_RUN = 35811403514
SOURCE_ARTIFACT = 10730520693
PREFIX = [
    ("ACTION6", 3, 3), ("ACTION6", 55, 3), ("ACTION6", 3, 3), ("ACTION6", 55, 3),
    ("RESET", None, None), ("ACTION6", 32, 4),
    ("ACTION6", 3, 3), ("ACTION6", 3, 3), ("ACTION6", 3, 3), ("ACTION6", 3, 3),
    ("ACTION6", 3, 3), ("ACTION6", 3, 3), ("ACTION6", 3, 3), ("ACTION6", 3, 3),
    ("ACTION6", 3, 3), ("ACTION6", 3, 3), ("ACTION6", 3, 3), ("ACTION6", 3, 3),
]


def grid_of(frame: Any) -> list[list[int]]:
    raw = frame.frame.data if hasattr(frame.frame, "data") else frame.frame
    if hasattr(raw, "tolist"):
        raw = raw.tolist()

    def code(pixel: Any) -> int:
        if isinstance(pixel, (int, float, bool)):
            return int(pixel)
        if hasattr(pixel, "tolist"):
            pixel = pixel.tolist()
        if isinstance(pixel, (list, tuple)):
            vals = []
            stack = list(pixel)
            while stack:
                v = stack.pop(0)
                if isinstance(v, (list, tuple)):
                    stack = list(v) + stack
                else:
                    vals.append(int(v))
            out = 0
            for v in vals:
                out = out * 257 + v
            return out
        return int(pixel)

    return [[code(x) for x in row] for row in raw]


def small_components(grid: list[list[int]]) -> list[dict[str, int]]:
    if not grid:
        return []
    rows, cols = len(grid), len(grid[0])
    total = rows * cols
    seen: set[tuple[int, int]] = set()
    out: list[dict[str, int]] = []
    for r in range(rows):
        for c in range(cols):
            if (r, c) in seen:
                continue
            color = grid[r][c]
            q = deque([(r, c)])
            seen.add((r, c))
            cells: list[tuple[int, int]] = []
            while q:
                rr, cc = q.popleft()
                cells.append((rr, cc))
                for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
                    nr, nc = rr + dr, cc + dc
                    if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in seen and grid[nr][nc] == color:
                        seen.add((nr, nc))
                        q.append((nr, nc))
            if len(cells) > max(16, total // 4):
                continue
            rs = [x[0] for x in cells]
            cs = [x[1] for x in cells]
            out.append({
                "color": color, "area": len(cells),
                "x0": min(cs), "x1": max(cs), "y0": min(rs), "y1": max(rs),
            })
    return out


def features(frame: Any) -> dict[str, Any]:
    g = grid_of(frame)
    rows = len(g)
    cols = len(g[0]) if rows else 0
    flat = [x for row in g for x in row]
    hist = Counter(flat)
    comps = small_components(g)
    nonzero = [(r,c) for r,row in enumerate(g) for c,x in enumerate(row) if x != 0]
    bbox = None
    if nonzero:
        rs = [r for r,_ in nonzero]
        cs = [c for _,c in nonzero]
        bbox = (min(rs), min(cs), max(rs), max(cs))
    row_trans = sum(1 for row in g for a,b in zip(row,row[1:]) if a != b)
    col_trans = sum(
        1 for r in range(max(0,rows-1)) for c in range(cols)
        if g[r][c] != g[r+1][c]
    )
    return {
        "engine_state": str(frame.state),
        "levels_completed": int(frame.levels_completed),
        "n_colors": len(hist),
        "color_histogram": tuple(sorted(hist.items())),
        "nonzero_count": len(nonzero),
        "nonzero_bbox": bbox,
        "small_component_count": len(comps),
        "small_component_areas": tuple(sorted(c["area"] for c in comps)),
        "small_component_boxes": tuple(sorted((c["x1"]-c["x0"]+1,c["y1"]-c["y0"]+1) for c in comps)),
        "row_transitions": row_trans,
        "col_transitions": col_trans,
        "lr_symmetric": bool(g and all(row == list(reversed(row)) for row in g)),
        "tb_symmetric": bool(g and g == list(reversed(g))),
        "corner_signature": (g[0][0],g[0][-1],g[-1][0],g[-1][-1]) if g else (),
        "center_value": g[rows//2][cols//2] if rows and cols else -1,
    }


def canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",",":"), default=list)


def grid_hash(frame: Any) -> str:
    return hashlib.sha256(canon(grid_of(frame)).encode()).hexdigest()


def make_env(envroot: Path):
    logger = logging.getLogger("arc3-certified-slice")
    logger.setLevel(logging.WARNING)
    arcade = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=str(envroot), logger=logger)
    card = arcade.create_scorecard()
    env = arcade.make(game_id="bt33-a7c3f9d18b4e", scorecard_id=card)
    if env is None:
        raise RuntimeError("bt33 unavailable")
    return arcade, env, card


def apply_action(env: Any, item: tuple[str,int|None,int|None]):
    kind,x,y = item
    if kind == "RESET":
        return env.step(GameAction.RESET)
    return env.step(GameAction.ACTION6, data={"x":int(x),"y":int(y)})


def replay(envroot: Path, n: int):
    arcade, env, card = make_env(envroot)
    for item in PREFIX[:n]:
        f = apply_action(env, item)
        if f is None:
            raise RuntimeError("prefix action returned None")
    return arcade, env, card


def trial_from_prefix(envroot: Path, n: int, witness: tuple[int,int], max_steps: int) -> dict[str,Any]:
    arcade, env, card = replay(envroot, n)
    start = int(env.observation_space.levels_completed)
    state0 = env.observation_space
    if state0.state in (GameState.GAME_OVER, GameState.WIN):
        return {
            "prefix": n, "start_levels": start, "start_state": str(state0.state),
            "start_hash": grid_hash(state0), "features": features(state0),
            "progressed": False, "won": state0.state == GameState.WIN,
            "actions": 0, "board_changed_steps": 0,
        }
    prev_hash = grid_hash(state0)
    changed = 0
    actions = 0
    progressed = False
    won = False
    for _ in range(max_steps):
        f = env.step(GameAction.ACTION6, data={"x":witness[0],"y":witness[1]})
        actions += 1
        if f is None:
            break
        h = grid_hash(f)
        changed += int(h != prev_hash)
        prev_hash = h
        now = int(f.levels_completed)
        if now > start:
            progressed = True
            won = f.state == GameState.WIN
            break
        if f.state in (GameState.GAME_OVER, GameState.WIN):
            won = f.state == GameState.WIN
            break
    return {
        "prefix": n, "start_levels": start, "start_state": str(state0.state),
        "start_hash": grid_hash(state0), "features": features(state0),
        "progressed": progressed, "won": won, "actions": actions,
        "board_changed_steps": changed,
    }


def minimal_basis(samples: list[dict[str,Any]], names: list[str]) -> tuple[list[str], dict[str,bool], list[dict[str,Any]]]:
    def signature(s: dict[str,Any], subset: tuple[str,...]) -> tuple[str,...]:
        return tuple(canon(s["features"][name]) for name in subset)

    def sufficient(subset: tuple[str,...]) -> bool:
        seen: dict[tuple[str,...],bool] = {}
        for s in samples:
            sig = signature(s,subset)
            y = bool(s["progressed"])
            if sig in seen and seen[sig] != y:
                return False
            seen[sig] = y
        return True

    chosen: tuple[str,...] | None = None
    for k in range(len(names)+1):
        for subset in itertools.combinations(names,k):
            if sufficient(subset):
                chosen = subset
                break
        if chosen is not None:
            break
    if chosen is None:
        raise RuntimeError("no sufficient feature basis")

    table: dict[str,bool] = {}
    for s in samples:
        key = canon(signature(s,chosen))
        table[key] = bool(s["progressed"])

    residuals = []
    for drop in chosen:
        sub = tuple(x for x in chosen if x != drop)
        witness_pair = None
        for i,a in enumerate(samples):
            for j,b in enumerate(samples):
                if i >= j:
                    continue
                if signature(a,sub) == signature(b,sub) and bool(a["progressed"]) != bool(b["progressed"]):
                    witness_pair = {
                        "dropped":drop,"remaining":list(sub),
                        "left_prefix":a["prefix"],"right_prefix":b["prefix"],
                        "left_label":bool(a["progressed"]),"right_label":bool(b["progressed"]),
                    }
                    break
            if witness_pair:
                break
        if witness_pair is None:
            raise RuntimeError(f"chosen basis was not inclusion-minimal at {drop}")
        residuals.append(witness_pair)
    return list(chosen), table, residuals


def emit_lean(path: Path, samples: list[dict[str,Any]], basis: list[str]) -> None:
    n = len(samples)
    labels = ["true" if s["progressed"] else "false" for s in samples]
    encoded: dict[str,list[int]] = {}
    for name in basis:
        vals = [canon(s["features"][name]) for s in samples]
        classes: dict[str,int] = {}
        arr=[]
        for v in vals:
            if v not in classes:
                classes[v]=len(classes)
            arr.append(classes[v])
        encoded[name]=arr

    def list_nat(xs): return "["+",".join(str(x) for x in xs)+"]"
    lines = [
        "import Std",
        "",
        "namespace Arc3CertifiedCapabilitySliceV1",
        f"def labels : List Bool := [{','.join(labels)}]",
    ]
    for idx,name in enumerate(basis):
        lines.append(f"def feat{idx} : List Nat := {list_nat(encoded[name])}")
    lines += [
        f"abbrev Ix := Fin {n}",
        "def label (i : Ix) : Bool := labels.getD i.val false",
    ]
    if basis:
        terms=[f"(feat{k}.getD i.val 0 == feat{k}.getD j.val 0)" for k in range(len(basis))]
        expr=" && ".join(terms)
    else:
        expr="true"
    lines += [
        f"def eqSelected (i j : Ix) : Bool := {expr}",
        "def Sufficient : Prop := ∀ i j : Ix, eqSelected i j = true → label i = label j",
        "theorem selected_basis_sufficient : Sufficient := by decide",
    ]
    for drop in range(len(basis)):
        terms=[f"(feat{k}.getD i.val 0 == feat{k}.getD j.val 0)" for k in range(len(basis)) if k != drop]
        expr=" && ".join(terms) if terms else "true"
        lines += [
            f"def eqWithout{drop} (i j : Ix) : Bool := {expr}",
            f"def ResidualWithout{drop} : Prop := ∃ i j : Ix, eqWithout{drop} i j = true ∧ label i ≠ label j",
            f"theorem basis_member_{drop}_necessary : ResidualWithout{drop} := by decide",
        ]
    lines += ["end Arc3CertifiedCapabilitySliceV1",""]
    path.write_text("\n".join(lines))


def incremental_live_after_revoke(log, target: str):
    # Exact for the append-only conjunctive-premise Nucleus: remove target and
    # transitively remove every node whose premise loses liveness.
    from runtime.metatron.nucleus import ids
    alive = set(ids(log))
    revoked = {target}
    changed = True
    while changed:
        changed=False
        for node in log:
            if node.kind == "revoke":
                continue
            if node.id in revoked:
                continue
            if any(p in revoked for p in node.premises):
                revoked.add(node.id)
                changed=True
    return tuple(node.id for node in log if node.kind != "revoke" and node.id in alive and node.id not in revoked)


def main() -> None:
    msi_root=Path(os.environ["MSI_ROOT"]).resolve()
    envroot=Path(os.environ["ENVROOT"]).resolve()
    metatron_root=Path(os.environ["METATRON_ROOT"]).resolve()
    outdir=Path(os.environ.get("OUTDIR",msi_root/"evidence"/"arc3-certified-capability-slice-v1"))
    outdir.mkdir(parents=True,exist_ok=True)

    # Import the exact pinned Metatron Nucleus checkout.
    sys.path.insert(0,str(metatron_root))
    from runtime.metatron.nucleus import Node, append, live_ids, dumps

    # Build the finite observer bank strictly from the sealed V3 replay prefix.
    samples=[trial_from_prefix(envroot,n,WITNESS,16) for n in range(len(PREFIX)+1)]
    feature_names=[
        "engine_state","levels_completed","n_colors","color_histogram","nonzero_count","nonzero_bbox",
        "small_component_count","small_component_areas","small_component_boxes","row_transitions",
        "col_transitions","lr_symmetric","tb_symmetric","corner_signature","center_value",
    ]
    basis,guard_table,minimality = minimal_basis(samples,feature_names)

    def sig_for(feat: dict[str,Any]) -> str:
        return canon(tuple(canon(feat[x]) for x in basis))
    def guard(feat: dict[str,Any]) -> bool|None:
        return guard_table.get(sig_for(feat))

    source=samples[10]  # immediately after V3 first protected progress
    target=samples[18]  # immediately after V3 second protected progress
    if not source["progressed"] or not target["progressed"]:
        raise AssertionError("sealed source/target witness no longer progresses")
    if source["start_hash"] == target["start_hash"]:
        raise AssertionError("source and target representations unexpectedly identical")

    sham=trial_from_prefix(envroot,18,SHAM,16)
    if sham["progressed"]:
        raise AssertionError("matched sham unexpectedly progressed")

    # Formal/warrant lineage: residual -> learned guard -> candidate -> verification -> capability -> transport.
    log=()
    residual=Node("residual",{
        "domain":"ARC3/bt33","source_run":SOURCE_RUN,"source_artifact":SOURCE_ARTIFACT,
        "question":"what minimal observable guard recognizes applicability of the compiled consequence law?"
    })
    log=append(log,residual)
    guard_node=Node("guard_basis",{
        "basis":basis,"sample_count":len(samples),"guard_table":guard_table,
        "minimality_residuals":minimality,"authority":"finite sealed replay bank"
    },(residual.id,))
    log=append(log,guard_node)
    candidate=Node("candidate_capability",{
        "law":LAW,"witness":{"action":"ACTION6","x":WITNESS[0],"y":WITNESS[1]},
        "source_prefix":10,"target_prefix":18,"max_verified_steps":16
    },(guard_node.id,))
    log=append(log,candidate)
    verification=Node("verification",{
        "guard_sufficient_on_finite_bank":True,
        "guard_inclusion_minimal":True,
        "source_progressed":True,"source_actions":source["actions"],
        "target_progressed":True,"target_actions":target["actions"],
        "raw_representation_changed":True,
        "sham_progressed":False,"sham_actions":sham["actions"],
    },(candidate.id,))
    log=append(log,verification)
    capability=Node("capability",{
        "guard_basis":basis,"law":LAW,
        "witness":{"action":"ACTION6","x":WITNESS[0],"y":WITNESS[1]},
        "protected_consequence":"levels_completed increases",
        "boundary":"sealed finite bt33 replay bank + source/target transport",
    },(verification.id,))
    log=append(log,capability)
    transport=Node("transport",{
        "source_hash":source["start_hash"],"target_hash":target["start_hash"],
        "source_signature":sig_for(source["features"]),
        "target_signature":sig_for(target["features"]),
        "protected_consequence_preserved":True,
        "note":"finite cross-form behavioral transport; not generic CLC theorem",
    },(capability.id,))
    log=append(log,transport)

    if capability.id not in set(live_ids(log)):
        raise AssertionError("verified capability failed to become live")

    # Zero-model exact target execution under learned guard.
    arcade,env,card=replay(envroot,18)
    target_feat=features(env.observation_space)
    if guard(target_feat) is not True:
        raise AssertionError("learned guard did not recognize sealed target")
    start=int(env.observation_space.levels_completed)
    target_exec=0
    for _ in range(16):
        f=env.step(GameAction.ACTION6,data={"x":WITNESS[0],"y":WITNESS[1]})
        target_exec+=1
        if int(f.levels_completed)>start:
            break
        if f.state==GameState.GAME_OVER:
            break
    target_ok=int(env.observation_space.levels_completed)>start
    if not target_ok:
        raise AssertionError("guarded zero-model target execution failed")
    exec_node=Node("execute",{"model_calls":0,"actions":target_exec,"progressed":True},(transport.id,))
    log=append(log,exec_node)

    # Matched implementation control is rejected, while the valid capability remains live.
    sham_candidate=Node("candidate_capability",{
        "law":LAW,"witness":{"action":"ACTION6","x":SHAM[0],"y":SHAM[1]},
        "guard_basis":basis,"max_test_steps":16,
    },(guard_node.id,))
    log=append(log,sham_candidate)
    obstruction=Node("obstruction",{
        "candidate":sham_candidate.id,"reason":"matched target-side witness failed and reached GAME_OVER",
        "progressed":False,"actions":sham["actions"],
    },(sham_candidate.id,))
    log=append(log,obstruction)
    if capability.id not in set(live_ids(log)):
        raise AssertionError("control candidate incorrectly revoked valid capability")

    # Fresh zero-model developmental rollout. Known signatures execute immediately.
    # Unknown forms create a residual; the same semantic witness is requalified with
    # a bounded 32-step test and the guard table is extended only after protected progress.
    arcade2,env2,card2=make_env(envroot)
    rollout=[]
    model_calls=0
    total_actions=0
    extension_nodes=[]
    while total_actions < 120 and env2.observation_space.state not in (GameState.WIN,GameState.GAME_OVER):
        before=env2.observation_space
        feat=features(before)
        decision=guard(feat)
        start_level=int(before.levels_completed)
        if decision is True:
            budget=16
            phase="compiled"
        else:
            res=Node("residual",{
                "reason":"unrecognized or non-applicable guard signature",
                "levels_completed":start_level,"signature":sig_for(feat),
            },(capability.id,))
            log=append(log,res)
            budget=32
            phase="bounded_requalification"
        used=0
        progressed=False
        for _ in range(budget):
            f=env2.step(GameAction.ACTION6,data={"x":WITNESS[0],"y":WITNESS[1]})
            used+=1; total_actions+=1
            if int(f.levels_completed)>start_level or f.state==GameState.WIN:
                progressed=True
                break
            if f.state==GameState.GAME_OVER:
                break
        rollout.append({
            "phase":phase,"start_level":start_level,"guard_decision":decision,
            "actions":used,"progressed":progressed,"end_level":int(env2.observation_space.levels_completed),
            "end_state":str(env2.observation_space.state),
        })
        if not progressed:
            # A true-guard failure is a real counterexample to the currently live capability.
            if decision is True:
                counter=Node("counterexample",{
                    "levels_completed":start_level,"signature":sig_for(feat),
                    "reason":"guard true but protected progress absent within verified budget",
                },(capability.id,))
                log=append(log,counter)
                revoke=Node("revoke",{"target":capability.id,"reason":"live guarded prediction falsified"},(counter.id,))
                log=append(log,revoke)
            break
        if decision is not True:
            new_key=sig_for(feat)
            guard_table[new_key]=True
            ext_verify=Node("verification",{
                "kind":"guard_extension","signature":new_key,"levels_completed":start_level,
                "witness_progressed":True,"actions":used,"model_calls":0,
            },(capability.id,))
            log=append(log,ext_verify)
            ext=Node("capability_extension",{
                "parent":capability.id,"guard_signature":new_key,
                "same_law":LAW,"same_witness":WITNESS,
            },(ext_verify.id,capability.id))
            log=append(log,ext)
            extension_nodes.append(ext.id)

    full_win=env2.observation_space.state==GameState.WIN
    final_levels=int(env2.observation_space.levels_completed)

    # Authority/reclosure control: explicit policy revocation must remove the capability
    # and all dependent extensions from current live closure without erasing history.
    live_before=tuple(live_ids(log))
    policy=Node("policy_change",{"reason":"test-only authority revocation control"})
    log=append(log,policy)
    revoke=Node("revoke",{"target":capability.id,"reason":"test-only policy withdrawal"},(policy.id,))
    log=append(log,revoke)
    batch_after=tuple(live_ids(log))
    incremental_after=incremental_live_after_revoke(log,capability.id)
    # incremental helper ignores revoke nodes just as live_ids does.
    flash_equal=set(batch_after)==set(incremental_after)
    if not flash_equal:
        raise AssertionError("incremental reclosure disagrees with batch Nucleus closure")
    if capability.id in set(batch_after):
        raise AssertionError("revoked capability remained live")
    if capability.id not in set(x.id for x in log):
        raise AssertionError("revocation erased historical evidence")

    lean_path=msi_root/"lean"/"Arc3CertifiedCapabilitySliceV1.lean"
    emit_lean(lean_path,samples,basis)

    evidence={
        "status":"WARRANTED_WITHIN_DECLARED_FINITE_BOUNDARY",
        "source":{"run":SOURCE_RUN,"artifact":SOURCE_ARTIFACT,"base_head":"b45fb19d272d28c060de34c48e95ffe31ece7173"},
        "objective":"compile recognition + execution + warrant into one minimal live capability",
        "sample_bank":{"n":len(samples),"max_test_steps":16},
        "minimal_guard":{"basis":basis,"table":guard_table,"minimality_residuals":minimality},
        "transport":{
            "source_prefix":10,"target_prefix":18,
            "source_hash":source["start_hash"],"target_hash":target["start_hash"],
            "representations_differ":source["start_hash"]!=target["start_hash"],
            "source_actions":source["actions"],"target_actions":target["actions"],
            "sham_progressed":sham["progressed"],
        },
        "zero_model_target_execute":{"actions":target_exec,"progressed":target_ok,"model_calls":0},
        "developmental_rollout":{
            "model_calls":model_calls,"actions":total_actions,"trace":rollout,
            "extensions_promoted":len(extension_nodes),"won":full_win,"levels_completed":final_levels,
        },
        "authority":{
            "capability_live_before_revoke":capability.id in set(live_before),
            "capability_live_after_revoke":capability.id in set(batch_after),
            "history_retained_after_revoke":capability.id in set(x.id for x in log),
            "incremental_equals_batch_reclosure":flash_equal,
        },
        "claim_boundary":[
            "finite bt33 fixture only",
            "guard minimality only over sealed replay-reachable sample bank and declared feature language",
            "finite transport evidence is CLC-inspired, not the generic CLC theorem",
            "zero-model rollout does not establish unrestricted ARC transfer or invention",
        ],
    }
    (outdir/"result.json").write_text(json.dumps(evidence,indent=2))
    (outdir/"metatron-log.jsonl").write_text(dumps(log))
    print(json.dumps(evidence,indent=2))
    print("ARC3_CERTIFIED_CAPABILITY_SLICE_V1=PASS")
    if full_win:
        print("ARC3_CERTIFIED_CAPABILITY_SLICE_V1_ZERO_MODEL_ROLLOUT=WIN")
    else:
        print("ARC3_CERTIFIED_CAPABILITY_SLICE_V1_ZERO_MODEL_ROLLOUT=RESIDUAL")


if __name__ == "__main__":
    main()
