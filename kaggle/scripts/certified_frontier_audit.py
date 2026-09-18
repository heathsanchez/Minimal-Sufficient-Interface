"""Matched MG-ARC9 certified-frontier diagnostic.

Compares the new frontier-priority policy against exact qualified MG-ARC8 and
an ablation that disables graph-frontier routing while keeping the quotient.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import benchmark_audit as audit

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"kaggle"/"certified-frontier-results"
PRIOR="8c84ed5f8fef13d80cf63eef34971646af8e10d4"
PRIOR_AGENT_SHA="6700b43bf5316b882c044a8f4f98e085ccdc0bbdb979053e6a6c6da4f75dea6a"
GAMES={
 "ft09-0d8bbf25":"aa5b54f48a29da9f276c3df0dc04de728002f523384ab868c85d56d819cd0783",
 "ls20-9607627b":"298c810da2850d557c95d92a2cbd846df29a45d7134e20888617bedf5dafcd92",
 "vc33-5430563c":"8afa9f55054b2a2460b6c44ec5c66e120f6d6f4c2289e24d50832a68d1e3fcfd",
}
VARIANTS=("candidate","prior","no_frontier")
audit.BASELINE=PRIOR

def agent_path(v):
    return OUT/("prior.py" if v=="prior" else "candidate.py")

def write(path,value):
    audit.write_json(path,value)

def prepare():
    assert audit.sha(agent_path("prior").read_bytes())==PRIOR_AGENT_SHA
    audit.AGENT=agent_path("candidate")
    for kind in ("fixture","public"):
        path=OUT/f"{kind}.json"
        args=SimpleNamespace(
            fixtures=kind=="fixture",
            games="bt11" if kind=="fixture" else "ls20,ft09,vc33",
            environments_dir=(
                str(ROOT/"upstream-arc-agi"/"test_environment_files")
                if kind=="fixture" else str(OUT/"envs")
            ),
            manifest=str(path),
            max_actions=128 if kind=="fixture" else 400,
        )
        audit.prepare(args)
        m=json.loads(path.read_text())
        assert m["sdk_versions"]=={"arc-agi":"0.9.9","arcengine":"0.9.3"}
        if kind=="public":
            assert {r["game_id"] for r in m["games"]}==set(GAMES)
            for r in m["games"]:
                fn=r["game_id"].split("-")[0]+".py"
                assert r["files"][fn]==GAMES[r["game_id"]]
        m["seeds"]=[0]
        m["baseline_commit"]=PRIOR
        m["interpretation"]="public development diagnostic, not hidden generalization"
        write(path,m)
    print("ARC3_CERTIFIED_FRONTIER_MANIFESTS=PASS",flush=True)

def cell(args):
    m=json.loads((OUT/f"{args.kind}.json").read_text())
    audit.AGENT=agent_path(args.variant)
    m["generated_agent_sha256"]=audit.sha(audit.AGENT.read_bytes())
    path=OUT/f"{args.kind}-{args.variant}-manifest.json"
    write(path,m)
    old=audit.run_session
    def measured(policy,env,digest,**kwargs):
        policy.controller.archived_capabilities=()
        if args.variant=="no_frontier":
            policy.controller.effects.frontier_action=lambda _context: None
        result=old(policy,env,digest,**kwargs)
        q=getattr(policy.controller,"contextual_quotient",None)
        result.update(
            variant=args.variant,
            prior_commit=PRIOR,
            controller=type(policy.controller).__name__,
            quotient_active_contexts=int(getattr(q,"active_contexts",0) if q else 0),
            quotient_records=list(q.active_records()) if q else [],
        )
        return result
    audit.run_session=measured
    audit.cell(SimpleNamespace(
        manifest=str(path),game=args.game,seed=0,arm="full",
        output=str(OUT/f"{args.game}-{args.variant}.json"),
    ))

def compact(row):
    keys=("max_levels","actions","status","milestones","source_counts",
          "capability_records","distinct_observations","terminal_failures",
          "quotient_active_contexts","quotient_records","memory_digest")
    return {k:row[k] for k in keys}

def batch():
    records=[]
    for kind in ("fixture","public"):
        m=json.loads((OUT/f"{kind}.json").read_text())
        for game in m["games"]:
            gid=game["game_id"]
            paired={}
            for variant in VARIANTS:
                done=subprocess.run(
                    [sys.executable,__file__,"cell","--kind",kind,
                     "--game",gid,"--variant",variant],
                    capture_output=True,text=True,timeout=50,
                )
                if done.returncode:
                    raise RuntimeError(done.stderr[-3000:]+"\n"+done.stdout[-3000:])
                row=json.loads((OUT/f"{gid}-{variant}.json").read_text())
                assert row["status"] in ("WIN","ACTION_BOUND"),row
                assert row["actions"]==len(row["trace"])+1
                paired[variant]=row
                print("CERTIFIED_FRONTIER_CELL="+json.dumps(
                    {k:v for k,v in row.items() if k!="trace"},sort_keys=True
                ),flush=True)
            assert len({r["initial_digest"] for r in paired.values()})==1
            records.append({"kind":kind,"game_id":gid,
                            "variants":{v:compact(r) for v,r in paired.items()}})
            write(OUT/"comparison.json",{"prior_commit":PRIOR,
                  "interpretation":"public development diagnostic, not hidden generalization",
                  "complete":False,"comparisons":records})

    fixture=next(r for r in records if r["kind"]=="fixture")["variants"]
    assert fixture["candidate"]["max_levels"]==5
    assert fixture["candidate"]["status"]=="WIN"
    assert fixture["candidate"]["actions"]<=73
    vc33=next(r for r in records if r["game_id"].startswith("vc33-"))["variants"]
    assert vc33["candidate"]["milestones"][:2]==[
        {"level":1,"actions":64},{"level":2,"actions":93}
    ]
    report={"prior_commit":PRIOR,
            "interpretation":"public development diagnostic, not hidden generalization",
            "trial_count":len(records)*len(VARIANTS),
            "complete":True,"comparisons":records}
    write(OUT/"comparison.json",report)
    print("CERTIFIED_FRONTIER_COMPARISON="+json.dumps(report,sort_keys=True),flush=True)
    print("ARC3_CERTIFIED_FRONTIER_QUALIFICATION=PASS",flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("command",choices=("prepare","cell","run"))
    p.add_argument("--kind",choices=("fixture","public"))
    p.add_argument("--game")
    p.add_argument("--variant",choices=VARIANTS)
    a=p.parse_args()
    {"prepare":prepare,"cell":lambda:cell(a),"run":batch}[a.command]()
