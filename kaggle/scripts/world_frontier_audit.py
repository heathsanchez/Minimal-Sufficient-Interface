"""Matched MG-ARC9 world-frontier diagnostic against exact MG-ARC8."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "world-frontier-results"
PRIOR = "dddd50ff2da147f8584352f7d1775cf8e8f8a2e7"
PRIOR_AGENT_SHA = "acfabd929580a9ac2a9b4cf5b6e5344c86ae964dbc63c16c613a861e64b7955c"
GAMES = {
    "ft09-0d8bbf25": "aa5b54f48a29da9f276c3df0dc04de728002f523384ab868c85d56d819cd0783",
    "ls20-9607627b": "298c810da2850d557c95d92a2cbd846df29a45d7134e20888617bedf5dafcd92",
    "vc33-5430563c": "8afa9f55054b2a2460b6c44ec5c66e120f6d6f4c2289e24d50832a68d1e3fcfd",
}
VARIANTS = ("candidate","prior","no_frontier")
audit.BASELINE = PRIOR


def agent_path(v):
    return OUT / ("prior.py" if v=="prior" else "candidate.py")


def prepare():
    assert audit.sha(agent_path("prior").read_bytes()) == PRIOR_AGENT_SHA
    audit.AGENT=agent_path("candidate")
    for kind in ("fixture","public"):
        path=OUT/f"{kind}.json"
        args=SimpleNamespace(
            fixtures=kind=="fixture",
            games="bt11" if kind=="fixture" else "ft09,ls20,vc33",
            environments_dir=(
                str(ROOT/"upstream-arc-agi"/"test_environment_files")
                if kind=="fixture" else str(OUT/"envs")
            ),
            manifest=str(path),
            max_actions=128 if kind=="fixture" else 400,
        )
        audit.prepare(args)
        m=json.loads(path.read_text())
        m["seeds"]=[0]
        m["baseline_commit"]=PRIOR
        if kind=="public":
            assert {r["game_id"] for r in m["games"]}==set(GAMES)
            for row in m["games"]:
                name=row["game_id"].split("-")[0]+".py"
                assert row["files"][name]==GAMES[row["game_id"]]
        audit.write_json(path,m)
    print("ARC3_WORLD_FRONTIER_MANIFESTS=PASS",flush=True)


def cell(args):
    m=json.loads((OUT/f"{args.kind}.json").read_text())
    audit.AGENT=agent_path(args.variant)
    m["generated_agent_sha256"]=audit.sha(audit.AGENT.read_bytes())
    mp=OUT/f"{args.kind}-{args.variant}.json"
    audit.write_json(mp,m)

    old=audit.run_session
    def measured(policy,env,digest,**kwargs):
        policy.controller.archived_capabilities=()
        if args.variant=="no_frontier":
            policy.controller.world_effects.frontier_action=lambda _context: None
        result=old(policy,env,digest,**kwargs)
        c=policy.controller
        factor=getattr(c,"border_factor",None)
        candidates=[]
        if factor is not None:
            for key,row in sorted(factor._candidates.items()):
                if row:
                    candidates.append({
                        "level":key[0],"height":key[1],"width":key[2],
                        "side":row["side"],"depth":row["depth"],
                        "color":row["color"],"direction":row["direction"],
                        "compression":row["compression"],
                        "raw_unique":row["raw_unique"],
                        "projected_unique":row["projected_unique"],
                    })
        world=getattr(c,"world_effects",None)
        contexts=set()
        if world:
            for (source,_a),row in world.edges.items():
                contexts.add(source)
                contexts.update(row.get("outcomes",{}))
        result.update(
            variant=args.variant,
            prior_commit=PRIOR,
            factor_candidates=candidates,
            factor_active_contexts=len(candidates),
            world_effect_contexts=len(contexts),
            world_effect_observations=int(getattr(world,"total_observations",0) if world else 0),
        )
        return result

    audit.run_session=measured
    audit.cell(SimpleNamespace(
        manifest=str(mp),game=args.game,seed=0,arm="full",
        output=str(OUT/f"{args.game}-{args.variant}-result.json"),
    ))


def compact(r):
    keys=("max_levels","actions","status","milestones","source_counts",
          "capability_records","distinct_observations","memory_digest",
          "factor_candidates","factor_active_contexts",
          "world_effect_contexts","world_effect_observations")
    return {k:r[k] for k in keys}


def run():
    records=[]
    for kind in ("fixture","public"):
        m=json.loads((OUT/f"{kind}.json").read_text())
        for game in m["games"]:
            gid=game["game_id"]
            paired={}
            for variant in VARIANTS:
                done=subprocess.run(
                    [sys.executable,__file__,"cell","--kind",kind,"--game",gid,"--variant",variant],
                    capture_output=True,text=True,timeout=55,
                )
                if done.returncode:
                    raise RuntimeError(done.stderr[-3000:]+"\n"+done.stdout[-3000:])
                row=json.loads((OUT/f"{gid}-{variant}-result.json").read_text())
                assert row["status"] in ("WIN","ACTION_BOUND"),row
                paired[variant]=row
                print("WORLD_FRONTIER_CELL="+json.dumps(
                    {k:v for k,v in row.items() if k!="trace"},sort_keys=True),flush=True)
            assert len({r["initial_digest"] for r in paired.values()})==1
            records.append({"kind":kind,"game_id":gid,
                            "variants":{v:compact(r) for v,r in paired.items()}})

    fixture=next(r for r in records if r["kind"]=="fixture")["variants"]
    assert fixture["candidate"]["status"]=="WIN"
    assert fixture["candidate"]["max_levels"]==5
    assert fixture["candidate"]["actions"]<=73

    vc=next(r for r in records if r["game_id"].startswith("vc33-"))["variants"]
    assert vc["candidate"]["milestones"][:2]==[
        {"level":1,"actions":64},{"level":2,"actions":93}
    ]

    report={"prior_commit":PRIOR,
            "interpretation":"public development diagnostic, not hidden generalization",
            "trial_count":len(records)*len(VARIANTS),
            "comparisons":records,"complete":True}
    audit.write_json(OUT/"comparison.json",report)
    print("WORLD_FRONTIER_COMPARISON="+json.dumps(report,sort_keys=True),flush=True)
    print("ARC3_WORLD_FRONTIER_QUALIFICATION=PASS",flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("prepare","cell","run"))
    p.add_argument("--kind",choices=("fixture","public"))
    p.add_argument("--game")
    p.add_argument("--variant",choices=VARIANTS)
    a=p.parse_args()
    {"prepare":prepare,"cell":lambda:cell(a),"run":run}[a.command]()
