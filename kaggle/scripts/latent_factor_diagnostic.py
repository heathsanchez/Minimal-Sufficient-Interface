"""Source-blind latent-factor diagnostic for frozen MG-ARC5.

Measures low-dimensional transition features and projection recurrence without
changing the policy. Public worlds are development diagnostics only.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "latent-factor-results"
AGENT = OUT / "agent.py"


def grid_of(frame):
    raw = frame.frame[-1] if frame.frame else []
    if hasattr(raw, "tolist"):
        raw = raw.tolist()
    return tuple(tuple(int(v) for v in row) for row in raw)


def digest_grid(grid, ignored=()):
    ignore = set(ignored)
    canonical = tuple(
        tuple(None if (x, y) in ignore else value for x, value in enumerate(row))
        for y, row in enumerate(grid)
    )
    return hashlib.sha256(repr(canonical).encode()).hexdigest()


def border_points(height, width, side, depth):
    if side == "top":
        return {(x, y) for y in range(min(depth, height)) for x in range(width)}
    if side == "bottom":
        return {(x, y) for y in range(max(0, height-depth), height) for x in range(width)}
    if side == "left":
        return {(x, y) for x in range(min(depth, width)) for y in range(height)}
    if side == "right":
        return {(x, y) for x in range(max(0, width-depth), width) for y in range(height)}
    raise ValueError(side)


def feature_values(grid):
    height = len(grid)
    width = len(grid[0]) if height else 0
    colors = sorted({v for row in grid for v in row})
    values = {}
    global_counts = Counter(v for row in grid for v in row)
    for color in colors:
        values[f"global:c{color}"] = global_counts[color]
    for depth in (1, 2, 3, 4):
        for side in ("top", "bottom", "left", "right"):
            points = border_points(height, width, side, depth)
            counts = Counter(grid[y][x] for x, y in points)
            for color in colors:
                values[f"{side}{depth}:c{color}"] = counts[color]
    return values


def run_world(game_id, envdir, max_actions):
    from arc_agi import Arcade, OperationMode

    audit.AGENT = AGENT
    module = audit.load_agent()
    audit.block_network()
    arc = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=envdir,
        logger=audit.quiet_logger(),
    )
    env = arc.make(game_id, seed=0)
    if env is None:
        raise RuntimeError("offline world unavailable")
    policy = module.MyAgent(
        card_id="latent-diagnostic",
        game_id="source-blind",
        agent_name="frozen",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    policy.controller.archived_capabilities = ()

    latest = policy._convert_raw_frame_data(env.observation_space)
    frames = [grid_of(latest)]
    actions = []
    sources = []
    states = []
    levels = []
    while len(actions) + 1 < max_actions and audit.state_name(latest) != "WIN":
        action = policy.choose_action([], latest)
        data = audit.validate_action(action, latest)
        aid = int(action.value)
        reasoning = getattr(action, "reasoning", {})
        source = str(reasoning.get("source", "unknown")) if isinstance(reasoning, dict) else "unknown"
        raw = env.step(action, data=data, reasoning={"source": source})
        latest = policy._convert_raw_frame_data(raw)
        actions.append((aid, data.get("x"), data.get("y")))
        sources.append(source)
        states.append(audit.state_name(latest))
        levels.append(int(latest.levels_completed))
        frames.append(grid_of(latest))
    arc.close_scorecard()

    transitions = []
    feature_series = [feature_values(g) for g in frames]
    all_names = sorted(set().union(*(f.keys() for f in feature_series)))
    feature_stats = {}
    for name in all_names:
        vals = [f.get(name, 0) for f in feature_series]
        deltas = [b-a for a,b in zip(vals, vals[1:])]
        changed = [(i,d) for i,d in enumerate(deltas) if d]
        if not changed:
            continue
        action_ids = [actions[i][0] for i,_ in changed if i < len(actions)]
        signs = Counter(1 if d>0 else -1 for _,d in changed)
        magnitudes = Counter(abs(d) for _,d in changed)
        feature_stats[name] = {
            "changes": len(changed),
            "distinct_actions": len(set(action_ids)),
            "sign_consistency": max(signs.values())/len(changed),
            "modal_abs_delta": magnitudes.most_common(1)[0][0],
            "modal_delta_fraction": magnitudes.most_common(1)[0][1]/len(changed),
            "start": vals[0],
            "end": vals[-1],
        }

    ranked = sorted(
        feature_stats.items(),
        key=lambda kv: (
            kv[1]["distinct_actions"] >= 2,
            kv[1]["sign_consistency"],
            kv[1]["modal_delta_fraction"],
            kv[1]["changes"],
        ),
        reverse=True,
    )[:30]

    raw_unique = len({digest_grid(g) for g in frames})
    projections = []
    if frames and frames[0]:
        h,w = len(frames[0]),len(frames[0][0])
        for depth in (1,2,3,4,6,8):
            for side in ("top","bottom","left","right"):
                pts=border_points(h,w,side,depth)
                unique=len({digest_grid(g,pts) for g in frames})
                projections.append({
                    "side":side,"depth":depth,"unique":unique,
                    "compression": raw_unique/max(1,unique),
                })
    projections.sort(key=lambda x:(x["compression"],-x["unique"]),reverse=True)

    pair_actions=defaultdict(set)
    pair_positions=defaultdict(set)
    pair_count=Counter()
    for i,(before,after) in enumerate(zip(frames,frames[1:])):
        if not before or len(before)!=len(after) or len(before[0])!=len(after[0]):
            continue
        for y,(ra,rb) in enumerate(zip(before,after)):
            for x,(a,b) in enumerate(zip(ra,rb)):
                if a!=b:
                    pair=(a,b)
                    pair_count[pair]+=1
                    pair_actions[pair].add(actions[i][0])
                    pair_positions[pair].add((x,y))
    pairs=[
        {
            "pair":list(pair),
            "events":count,
            "distinct_actions":len(pair_actions[pair]),
            "positions":len(pair_positions[pair]),
        }
        for pair,count in pair_count.most_common(20)
    ]

    return {
        "game_id":game_id,
        "actions":len(actions)+1,
        "max_level":max(levels,default=0),
        "final_state":audit.state_name(latest),
        "raw_unique_frames":raw_unique,
        "top_scalar_features":[{"name":name,**stats} for name,stats in ranked],
        "top_border_projections":projections[:20],
        "top_color_transitions":pairs,
        "source_counts":dict(Counter(sources)),
    }


def main():
    manifests={}
    for kind in ("fixture","public"):
        manifests[kind]=json.loads((OUT/f"{kind}.json").read_text())
    worlds=[]
    for kind,manifest in manifests.items():
        for row in manifest["games"]:
            worlds.append(run_world(
                row["game_id"],
                manifest["environments_dir"],
                manifest["max_actions"],
            ))
    report={"interpretation":"source-blind development diagnostic","worlds":worlds}
    audit.write_json(OUT/"latent-diagnostic.json",report)
    print("LATENT_FACTOR_DIAGNOSTIC="+json.dumps(report,sort_keys=True),flush=True)


if __name__=="__main__":
    main()
