"""Paired public DEVELOPMENT diagnostic for target-scoped transfer budgets.

Reuses the source-blind evaluator. No hidden-game, equivalence, or goal-law
certificate is inferred from these runs. Each variant gets a fresh process.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'kaggle/contract-results'
PRIOR = '90b88081f8bd7c6c58dcd891b4654fc7f6d0169c'
PRIOR_AGENT_SHA = '37933991340b02c74d297545587c23e5d12f2a7f2ba20edfb35370072617a8c8'
GAMES = {
    'ft09-0d8bbf25': 'aa5b54f48a29da9f276c3df0dc04de728002f523384ab868c85d56d819cd0783',
    'ls20-9607627b': '298c810da2850d557c95d92a2cbd846df29a45d7134e20888617bedf5dafcd92',
    'vc33-5430563c': '8afa9f55054b2a2460b6c44ec5c66e120f6d6f4c2289e24d50832a68d1e3fcfd',
}
VARIANTS = ('candidate', 'prior', 'no_transfer', 'no_affordance')
audit.BASELINE = PRIOR


def agent_path(variant):
    return OUT / ('prior.py' if variant == 'prior' else 'candidate.py')


def write(path, value):
    audit.write_json(path, value)


def prepare():
    assert audit.sha(agent_path('prior').read_bytes()) == PRIOR_AGENT_SHA
    audit.AGENT = agent_path('candidate')
    for kind in ('fixture', 'public'):
        path = OUT / (kind + '.json')
        args = SimpleNamespace(fixtures=kind=='fixture',
            games='bt11' if kind=='fixture' else 'ls20,ft09,vc33',
            environments_dir=str(ROOT/'upstream-arc-agi/test_environment_files') if kind=='fixture' else str(OUT/'envs'),
            manifest=str(path), max_actions=128 if kind=='fixture' else 400)
        audit.prepare(args)
        manifest = json.loads(path.read_text())
        # Inspect and validate the manifest schema before changing its metadata.
        assert {'kind','games','sdk_versions','max_actions','generated_agent_sha256'} <= set(manifest)
        assert manifest['sdk_versions'] == {'arc-agi':'0.9.9','arcengine':'0.9.3'}
        if kind == 'public':
            assert {r['game_id'] for r in manifest['games']} == set(GAMES)
            for row in manifest['games']:
                filename = row['game_id'].split('-')[0]+'.py'
                assert row['files'][filename] == GAMES[row['game_id']]
        manifest['seeds'] = [0]
        manifest['baseline_commit'] = PRIOR
        manifest['interpretation'] = 'paired development diagnostic, not hidden generalization'
        write(path, manifest)
    print('ARC3_TRANSFER_CONTRACT_MANIFESTS=PASS', flush=True)


def cell(args):
    manifest = json.loads((OUT/(args.kind+'.json')).read_text())
    audit.AGENT = agent_path(args.variant)
    manifest['generated_agent_sha256'] = audit.sha(audit.AGENT.read_bytes())
    path = OUT/(args.kind+'-'+args.variant+'-manifest.json')
    write(path, manifest)
    original = audit.apply_ablation
    def configure(policy, arm):
        original(policy, arm)
        if args.variant == 'no_affordance':
            policy.controller.affordances.affordance_score = lambda descriptor: 0.0
    audit.apply_ablation = configure
    old_session = audit.run_session
    def measured(policy, env, digest, **kwargs):
        result = old_session(policy, env, digest, **kwargs)
        snapshot = json.loads(policy.controller.memory.text().splitlines()[1])
        trials = snapshot.get('transfer_trials', [])
        totals = {}
        for trial in trials:
            level = str(trial['target_level'])
            totals[level] = totals.get(level,0)+trial['issued']
        result['transfer_issued_by_target'] = totals
        result['transfer_trial_records'] = trials
        result['memory_format'] = policy.controller.memory.VERSION
        result['variant'] = args.variant
        result['controller'] = type(policy.controller).__name__
        result['prior_commit'] = PRIOR
        if args.variant != 'prior':
            assert all(n <= policy.controller.max_transfer_depth for n in totals.values())
            assert result['source_counts'].get('transfer',0) <= sum(totals.values())
        return result
    audit.run_session = measured
    audit.cell(SimpleNamespace(manifest=str(path), game=args.game,seed=0,
        arm='no_transfer' if args.variant=='no_transfer' else 'full',
        output=str(OUT/(args.game+'-'+args.variant+'.json'))))


def batch():
    records=[]
    for kind in ('fixture','public'):
        manifest=json.loads((OUT/(kind+'.json')).read_text())
        for game in manifest['games']:
            gid=game['game_id']
            paired={}
            for variant in VARIANTS:
                command=[sys.executable,__file__,'cell','--kind',kind,'--game',gid,'--variant',variant]
                done=subprocess.run(command,capture_output=True,text=True,timeout=45)
                if done.returncode:
                    raise RuntimeError(done.stderr[-2000:])
                row=json.loads((OUT/(gid+'-'+variant+'.json')).read_text())
                assert row['status'] in ('WIN','ACTION_BOUND'),row
                assert row['actions']==len(row['trace'])+1
                paired[variant]=row
                print('CONTRACT_CELL='+json.dumps({k:v for k,v in row.items() if k not in ('trace','transfer_trial_records')},sort_keys=True),flush=True)
            assert len({r['initial_digest'] for r in paired.values()})==1
            record={'kind':kind,'game_id':gid,'variants':{
                variant:{k:row[k] for k in ('max_levels','actions','status','milestones','source_counts','transfer_issued_by_target','capability_records')}
                for variant,row in paired.items()}}
            records.append(record)
            write(OUT/'comparison.json',{'prior_commit':PRIOR,'interpretation':'development diagnostic, not hidden generalization','complete':False,'comparisons':records})
    # Preservation of the narrow positive control; no requirement to solve a
    # new level just to turn the measurement workflow green.
    fixture=records[0]['variants']
    assert fixture['candidate']['max_levels']==fixture['prior']['max_levels']==5
    assert fixture['candidate']['actions']<=fixture['prior']['actions']
    report={'prior_commit':PRIOR,'interpretation':'development diagnostic, not hidden generalization',
            'trial_count':len(records)*len(VARIANTS),'complete':True,'comparisons':records}
    write(OUT/'comparison.json',report)
    print('CONTRACT_COMPARISON='+json.dumps(report,sort_keys=True),flush=True)
    print('ARC3_TRANSFER_CONTRACT_QUALIFICATION=PASS',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','cell','run'))
    parser.add_argument('--kind',choices=('fixture','public'))
    parser.add_argument('--game')
    parser.add_argument('--variant',choices=VARIANTS)
    args=parser.parse_args()
    {'prepare':prepare,'cell':lambda:cell(args),'run':batch}[args.command]()
