"""Matched quotient-frontier diagnostic against qualified typed-factor baseline.

Public worlds are development diagnostics. This isolates scheduling: candidate
and no_frontier share the exact typed representation; the prior is the exact
qualified typed-factor agent.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "quotient-frontier-results"
PRIOR = "7ddb1288ff09c931af50011639b918d08f3407dc"
PRIOR_AGENT_SHA = "77bd6648e6a6c9973aea3fd3a92f805e4ecce4d055b9d847e2322b30a6f066a7"
GAMES = {
    "ft09-0d8bbf25": "aa5b54f48a29da9f276c3df0dc04de728002f523384ab868c85d56d819cd0783",
    "ls20-9607627b": "298c810da2850d557c95d92a2cbd846df29a45d7134e20888617bedf5dafcd92",
    "vc33-5430563c": "8afa9f55054b2a2460b6c44ec5c66e120f6d6f4c2289e24d50832a68d1e3fcfd",
}
VARIANTS = ("candidate", "prior", "no_frontier")
audit.BASELINE = PRIOR


def agent_path(variant):
    return OUT / ("prior.py" if variant == "prior" else "candidate.py")


def prepare():
    assert audit.sha(agent_path("prior").read_bytes()) == PRIOR_AGENT_SHA
    audit.AGENT = agent_path("candidate")
    for kind in ("fixture", "public"):
        path = OUT / f"{kind}.json"
        args = SimpleNamespace(
            fixtures=kind == "fixture",
            games="bt11" if kind == "fixture" else "ft09,ls20,vc33",
            environments_dir=(
                str(ROOT / "upstream-arc-agi" / "test_environment_files")
                if kind == "fixture"
                else str(OUT / "envs")
            ),
            manifest=str(path),
            max_actions=128 if kind == "fixture" else 400,
        )
        audit.prepare(args)
        manifest=json.loads(path.read_text())
        manifest["seeds"]=[0]
        manifest["baseline_commit"]=PRIOR
        manifest["interpretation"]="public development diagnostic, not hidden generalization"
        if kind=="public":
            assert {row["game_id"] for row in manifest["games"]}==set(GAMES)
            for row in manifest["games"]:
                filename=row["game_id"].split("-")[0]+".py"
                assert row["files"][filename]==GAMES[row["game_id"]]
        audit.write_json(path,manifest)
    print("ARC3_QUOTIENT_FRONTIER_MANIFESTS=PASS",flush=True)


def graph_stats(controller):
    effects=controller.effects
    world_contexts=set()
    deterministic=0
    ambiguous=0
    self_loops=0
    for (source, _action), row in effects.edges.items():
        if not str(source).startswith("w:"):
            continue
        world_contexts.add(str(source))
        if row["ambiguous"] or len(row["outcomes"]) != 1:
            ambiguous += 1
            continue
        target=next(iter(row["outcomes"]))
        if str(target).startswith("w:"):
            world_contexts.add(str(target))
        if target == source:
            self_loops += 1
        else:
            deterministic += 1
    frontier_states=0
    for state,catalog in effects.catalogs.items():
        if not str(state).startswith("w:"):
            continue
        if any(effects.attempts(state,action)==0 for action in catalog):
            frontier_states += 1
    return {
        "world_contexts":len(world_contexts),
        "deterministic_world_edges":deterministic,
        "ambiguous_world_edges":ambiguous,
        "world_self_loops":self_loops,
        "world_frontier_states":frontier_states,
    }


def cell(args):
    manifest=json.loads((OUT/f"{args.kind}.json").read_text())
    audit.AGENT=agent_path(args.variant)
    manifest["generated_agent_sha256"]=audit.sha(audit.AGENT.read_bytes())
    path=OUT/f"{args.kind}-{args.variant}-manifest.json"
    audit.write_json(path,manifest)
    old=audit.run_session

    def measured(policy,env,digest,**kwargs):
        policy.controller.archived_capabilities=()
        if args.variant=="no_frontier":
            policy.controller.quotient_frontier_enabled=False
        result=old(policy,env,digest,**kwargs)
        controller=policy.controller
        factor=controller.typed_factor
        factors=[]
        for (level,height,width),row in sorted(factor._factors.items()):
            factors.append({
                "level":level,"height":height,"width":width,
                "side":row["side"],"depth":row["depth"],
                "palette":list(row["palette"]),
                "compression":row["compression"],
            })
        result.update(
            variant=args.variant,
            prior_commit=PRIOR,
            quotient_frontier_enabled=bool(
                getattr(controller,"quotient_frontier_enabled",False)
            ),
            typed_active_contexts=factor.active_contexts,
            typed_factors=factors,
            typed_scalar_transitions=len(factor.transitions()),
            **graph_stats(controller),
        )
        return result

    audit.run_session=measured
    audit.cell(SimpleNamespace(
        manifest=str(path),game=args.game,seed=0,arm="full",
        output=str(OUT/f"{args.game}-{args.variant}.json"),
    ))


def compact(row):
    keys=(
        "max_levels","actions","status","milestones","source_counts",
        "capability_records","distinct_observations","terminal_failures",
        "quotient_frontier_enabled","typed_active_contexts","typed_factors",
        "typed_scalar_transitions","world_contexts","deterministic_world_edges",
        "ambiguous_world_edges","world_self_loops","world_frontier_states",
        "memory_digest",
    )
    return {k:row[k] for k in keys}


def batch():
    records=[]
    for kind in ("fixture","public"):
        manifest=json.loads((OUT/f"{kind}.json").read_text())
        for game in manifest["games"]:
            gid=game["game_id"]
            paired={}
            for variant in VARIANTS:
                done=subprocess.run([
                    sys.executable,__file__,"cell","--kind",kind,
                    "--game",gid,"--variant",variant,
                ],capture_output=True,text=True,timeout=50)
                if done.returncode:
                    raise RuntimeError(done.stderr[-3000:]+"\n"+done.stdout[-3000:])
                row=json.loads((OUT/f"{gid}-{variant}.json").read_text())
                assert row["status"] in ("WIN","ACTION_BOUND"),row
                paired[variant]=row
                print(
                    "QUOTIENT_FRONTIER_CELL="
                    +json.dumps({k:v for k,v in row.items() if k!="trace"},sort_keys=True),
                    flush=True,
                )
            assert len({row["initial_digest"] for row in paired.values()})==1
            records.append({
                "kind":kind,"game_id":gid,
                "variants":{name:compact(row) for name,row in paired.items()},
            })
            audit.write_json(OUT/"comparison.json",{
                "prior_commit":PRIOR,
                "interpretation":"public development diagnostic, not hidden generalization",
                "complete":False,"comparisons":records,
            })

    fixture=next(r for r in records if r["kind"]=="fixture")["variants"]
    assert fixture["candidate"]["max_levels"]==5
    assert fixture["candidate"]["status"]=="WIN"
    assert fixture["candidate"]["actions"]<=73

    vc33=next(r for r in records if r["game_id"].startswith("vc33-"))["variants"]
    assert vc33["candidate"]["milestones"][:2]==[
        {"level":1,"actions":64},{"level":2,"actions":93}
    ]

    report={
        "prior_commit":PRIOR,
        "interpretation":"public development diagnostic, not hidden generalization",
        "trial_count":len(records)*len(VARIANTS),
        "complete":True,
        "comparisons":records,
    }
    audit.write_json(OUT/"comparison.json",report)
    print("QUOTIENT_FRONTIER_COMPARISON="+json.dumps(report,sort_keys=True),flush=True)
    print("ARC3_QUOTIENT_FRONTIER_QUALIFICATION=PASS",flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("prepare","cell","run"))
    p.add_argument("--kind",choices=("fixture","public"))
    p.add_argument("--game")
    p.add_argument("--variant",choices=VARIANTS)
    args=p.parse_args()
    {"prepare":prepare,"cell":lambda:cell(args),"run":batch}[args.command]()
