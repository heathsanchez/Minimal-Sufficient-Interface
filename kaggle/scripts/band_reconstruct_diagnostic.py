"""Source-blind reconstructive border-factor diagnostic for frozen MG-ARC5.

For each border band, test whether (outside-world projection, exact band
histogram) uniquely reconstructs every observed full frame. This does not
change the policy and does not claim unobserved-world equivalence.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"kaggle"/"band-reconstruct-results"
AGENT=OUT/"agent.py"


def grid_of(frame):
    raw=frame.frame[-1] if frame.frame else []
    if hasattr(raw,"tolist"):
        raw=raw.tolist()
    return tuple(tuple(int(v) for v in row) for row in raw)


def digest(value):
    return hashlib.sha256(repr(value).encode()).hexdigest()


def points(height,width,side,depth):
    if side=="top":
        return tuple((x,y) for y in range(min(depth,height)) for x in range(width))
    if side=="bottom":
        return tuple((x,y) for y in range(max(0,height-depth),height) for x in range(width))
    if side=="left":
        return tuple((x,y) for x in range(min(depth,width)) for y in range(height))
    if side=="right":
        return tuple((x,y) for x in range(max(0,width-depth),width) for y in range(height))
    raise ValueError(side)


def outside(grid,band):
    b=set(band)
    return tuple(
        tuple(None if (x,y) in b else value for x,value in enumerate(row))
        for y,row in enumerate(grid)
    )


def histogram(grid,band):
    c=Counter(grid[y][x] for x,y in band)
    return tuple(sorted(c.items()))


def pattern(grid,band):
    return tuple(grid[y][x] for x,y in band)


def run_world(game_id,envdir,max_actions):
    from arc_agi import Arcade,OperationMode

    audit.AGENT=AGENT
    module=audit.load_agent()
    audit.block_network()
    arc=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=envdir,logger=audit.quiet_logger())
    env=arc.make(game_id,seed=0)
    if env is None:
        raise RuntimeError("offline world unavailable")
    policy=module.MyAgent(card_id="diag",game_id="source-blind",agent_name="frozen",ROOT_URL="",record=False,arc_env=None)
    policy.controller.archived_capabilities=()
    latest=policy._convert_raw_frame_data(env.observation_space)
    frames=[grid_of(latest)]
    actions=[]
    levels=[int(latest.levels_completed)]
    while len(actions)+1<max_actions and audit.state_name(latest)!="WIN":
        action=policy.choose_action([],latest)
        data=audit.validate_action(action,latest)
        aid=int(action.value)
        raw=env.step(action,data=data,reasoning={"source":"diag"})
        latest=policy._convert_raw_frame_data(raw)
        actions.append((aid,data.get("x"),data.get("y")))
        frames.append(grid_of(latest))
        levels.append(int(latest.levels_completed))
    arc.close_scorecard()

    raw_unique=len({digest(frame) for frame in frames})
    if not frames or not frames[0]:
        return {"game_id":game_id,"candidates":[]}
    h,w=len(frames[0]),len(frames[0][0])
    candidates=[]
    for side in ("top","bottom","left","right"):
        for depth in (1,2,3,4,6,8):
            band=points(h,w,side,depth)
            outside_values=[outside(frame,band) for frame in frames]
            outside_digests=[digest(value) for value in outside_values]
            histograms=[histogram(frame,band) for frame in frames]
            patterns=[pattern(frame,band) for frame in frames]
            full_digests=[digest(frame) for frame in frames]

            hist_to_patterns=defaultdict(set)
            pair_to_full=defaultdict(set)
            for hist,pat,out_d,full_d in zip(histograms,patterns,outside_digests,full_digests):
                hist_to_patterns[hist].add(pat)
                pair_to_full[(out_d,hist)].add(full_d)

            changed_actions=set()
            scalar_changes=0
            for i,(a,b) in enumerate(zip(histograms,histograms[1:])):
                if a!=b:
                    scalar_changes+=1
                    if i<len(actions):
                        changed_actions.add(actions[i][0])

            outside_unique=len(set(outside_digests))
            hist_unique=len(set(histograms))
            joint_unique=len(set(zip(outside_digests,histograms)))
            hist_collisions=sum(1 for values in hist_to_patterns.values() if len(values)>1)
            joint_collisions=sum(1 for values in pair_to_full.values() if len(values)>1)
            candidates.append({
                "side":side,
                "depth":depth,
                "raw_unique":raw_unique,
                "outside_unique":outside_unique,
                "compression":raw_unique/max(1,outside_unique),
                "scalar_states":hist_unique,
                "joint_states":joint_unique,
                "scalar_changes":scalar_changes,
                "scalar_action_classes":len(changed_actions),
                "histogram_pattern_collisions":hist_collisions,
                "joint_reconstruction_collisions":joint_collisions,
                "max_patterns_per_histogram":max((len(v) for v in hist_to_patterns.values()),default=0),
            })
    candidates.sort(key=lambda r:(
        r["joint_reconstruction_collisions"]==0,
        r["scalar_action_classes"]>=2,
        r["compression"],
        -r["outside_unique"],
    ),reverse=True)
    return {
        "game_id":game_id,
        "actions":len(actions)+1,
        "max_level":max(levels,default=0),
        "raw_unique":raw_unique,
        "candidates":candidates[:24],
    }


def main():
    public=json.loads((OUT/"public.json").read_text())
    fixture=json.loads((OUT/"fixture.json").read_text())
    worlds=[]
    for manifest in (fixture,public):
        for row in manifest["games"]:
            worlds.append(run_world(row["game_id"],manifest["environments_dir"],manifest["max_actions"]))
    report={"interpretation":"source-blind bounded reconstructibility diagnostic","worlds":worlds}
    audit.write_json(OUT/"reconstructibility.json",report)
    print("BAND_RECONSTRUCTIBILITY="+json.dumps(report,sort_keys=True),flush=True)


if __name__=="__main__":
    main()
