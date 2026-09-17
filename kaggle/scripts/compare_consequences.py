"""Matched DEVELOPMENT-set comparison. No hidden-score or sealed-holdout claim."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import benchmark_audit as audit

ARMS=('baseline','candidate','no_effect_feedback','no_visual_grounding')
ROOT=audit.ROOT


def load(path,name):
    sys.path.insert(0,str(ROOT/'kaggle/vendor/ARC-AGI-3-Agents'))
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


def cell(args):
    from arc_agi import Arcade,OperationMode
    manifest=json.loads(Path(args.manifest).read_text());audit.validate_manifest(manifest)
    game=next(g for g in manifest['games'] if g['game_id']==args.game)
    if audit.file_hashes(Path(game['local_dir']))!=game['files']:
        raise ValueError('environment hash mismatch')
    baseline=Path(args.baseline);candidate=audit.AGENT
    if audit.sha(candidate.read_bytes())!=manifest['generated_agent_sha256']:
        raise ValueError('candidate hash mismatch')
    expected='871cd5b6092962b098d653875233d26098b84bf22c2ebe82f5750bf427264b5b'
    if audit.sha(baseline.read_bytes())!=expected:
        raise ValueError('baseline is not the qualified frozen artifact')
    module=load(baseline if args.arm=='baseline' else candidate,'comparison_policy')
    audit.block_network()
    arc=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=manifest['environments_dir'],logger=audit.quiet_logger())
    env=arc.make(args.game,seed=0)
    if env is None:raise RuntimeError('exact environment unavailable')
    policy=module.MyAgent(card_id='local-comparison',game_id='source-blind',agent_name='comparison',ROOT_URL='',record=False,arc_env=None)
    policy.controller.archived_capabilities=()
    if args.arm=='no_effect_feedback':policy.controller.consequence_enabled=False
    if args.arm=='no_visual_grounding':policy.controller.visual_grounding=False
    samples=[];seen=set()
    def digest(obs):
        d=module.normalize_frame(obs).evidence_sha256
        if d not in seen and len(samples)<12:
            samples.append(dict(digest=d,frame=obs.frame,level=int(obs.levels_completed),state=audit.state_name(obs)))
            seen.add(d)
        return d
    result=audit.run_session(policy,env,digest,max_actions=manifest['max_actions'],wall_seconds=60)
    # Record an already returned terminal consequence; no new environment action.
    last=policy._convert_raw_frame_data(env.observation_space)
    if audit.state_name(last) in ('WIN','GAME_OVER') and hasattr(policy.controller,'observe_terminal'):
        policy.controller.observe_terminal(last)
    result.update(arm=args.arm,game_id=args.game,seed=0,kind=manifest['kind'],
                  candidate_sha256=audit.sha(candidate.read_bytes()),baseline_sha256=expected)
    if hasattr(policy.controller,'effects'):
        effects=policy.controller.effects
        result.update(effect_records=len(effects.edges),effect_observations=effects.total_observations,
                      conflicting_effect_edges=sum(row['ambiguous'] for row in effects.edges.values()))
        memory=policy.controller.snapshot_memory()
        Path(args.output).with_suffix('.mg').write_text(memory)
        result['consequence_memory_sha256']=audit.sha(memory.encode())
    audit.write_json(Path(args.output),result)
    audit.write_json(Path(args.output).with_suffix('.frames.json'),samples)
    arc.close_scorecard()


def batch(args):
    manifest=json.loads(Path(args.manifest).read_text());audit.validate_manifest(manifest)
    directory=Path(args.output);directory.mkdir(parents=True,exist_ok=True)
    def one(pair):
        game,arm=pair;path=directory/f'{game}-{arm}.json'
        cmd=[sys.executable,str(Path(__file__).resolve()),'cell','--manifest',args.manifest,
             '--baseline',args.baseline,'--game',game,'--arm',arm,'--output',str(path)]
        try:
            done=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
            if done.returncode:raise RuntimeError(done.stderr[-1000:])
            result=json.loads(path.read_text())
        except Exception as exc:
            result=dict(game_id=game,arm=arm,status='ERROR',error=str(exc)[:1000])
            audit.write_json(path,result)
        compact={k:v for k,v in result.items() if k!='trace'}
        print('CONSEQUENCE_CELL='+json.dumps(compact,sort_keys=True),flush=True)
        return compact
    pairs=[(g['game_id'],a) for g in manifest['games'] for a in ARMS]
    with ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(one,pairs))
    valid=len(rows)==len(pairs) and all(r['status'] not in ('ERROR','TIME_BOUND','TIMEOUT') for r in rows)
    for g in manifest['games']:
        group=[r for r in rows if r['game_id']==g['game_id']]
        valid=valid and len(group)==4 and len({r.get('initial_digest') for r in group})==1
    audit.write_json(directory/'summary.json',dict(comparison='MATCHED' if valid else 'INVALID',
        interpretation='public development-set comparison; no sealed holdout or competition score',
        manifest=manifest,results=rows))
    print('CONSEQUENCE_COMPARISON='+('MATCHED' if valid else 'INVALID'))
    if not valid:raise SystemExit(2)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('cell','run'))
    p.add_argument('--manifest',required=True);p.add_argument('--baseline',required=True)
    p.add_argument('--game');p.add_argument('--arm',choices=ARMS);p.add_argument('--output',required=True)
    args=p.parse_args();(cell if args.command=='cell' else batch)(args)
if __name__=='__main__':main()
