"""Frozen-agent, source-blind PUBLIC DIAGNOSTIC, not a hidden Kaggle score.

Preparation downloads public games via the official SDK, records exact versions
and hashes, and is separate from evaluation. Each cell has a fresh process,
agent, environment and scorecard. The generated MyAgent receives public frames,
never an environment object. Source code is hashed by the evaluator, not read
by the policy. Python-level outbound socket guards are defense-in-depth, not an
OS sandbox. Same-level retained replay is held fixed in all four ablation arms.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.metadata
import importlib.util
import json
import logging
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

BASELINE = '846b3919f4b8cdf8e2ca414b41c7239c255419e7'
ARMS = ('full', 'no_refutation', 'no_transfer', 'neither')
FIXTURES = {'bt11', 'bt33'}
ROOT = Path(__file__).resolve().parents[2]
AGENT = ROOT / 'kaggle/agent/my_agent.py'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')


def validate_manifest(manifest: dict) -> None:
    kind = manifest.get('kind')
    if kind not in ('public_diagnostic', 'sdk_fixture'):
        raise ValueError('explicit dataset class required')
    games = manifest.get('games', [])
    if not games:
        raise ValueError('empty evaluation suite')
    seen = set()
    for row in games:
        gid = row['game_id']
        short, sep, version = gid.partition('-')
        if not sep or not version or short in seen:
            raise ValueError('one exact version per game required')
        seen.add(short)
        fixture = short in FIXTURES or 'test_environment_files' in Path(row.get('local_dir', '')).parts
        if kind == 'public_diagnostic' and fixture:
            raise ValueError('SDK fixture cannot count as benchmark evidence')
        if kind == 'sdk_fixture' and short not in FIXTURES:
            raise ValueError('unexpected fixture')


def apply_ablation(policy: Any, arm: str) -> None:
    if arm not in ARMS:
        raise ValueError('unknown ablation')
    controller = policy.controller
    # No archived game-specific prefixes in any generalization measurement.
    controller.archived_capabilities = ()
    if arm in ('no_refutation', 'neither'):
        controller.memory.forbidden_next = lambda *args, **kwargs: set()
    if arm in ('no_transfer', 'neither'):
        controller._next_transfer = lambda *args, **kwargs: None


def state_name(frame: Any) -> str:
    return str(getattr(frame.state, 'name', frame.state)).rsplit('.', 1)[-1]


def validate_action(action: Any, frame: Any) -> dict:
    aid = int(action.value)
    legal = {int(getattr(a, 'value', a)) for a in frame.available_actions}
    if aid != 0 and legal and aid not in legal:
        raise ValueError('policy selected an unavailable action')
    data = action.action_data.model_dump()
    if action.is_complex():
        grid = frame.frame[-1] if frame.frame else []
        height, width = len(grid), len(grid[0]) if len(grid) else 0
        x, y = data.get('x'), data.get('y')
        if type(x) is not int or type(y) is not int or not (0 <= x < width and 0 <= y < height):
            raise ValueError('invalid public coordinate action')
    return data


def run_session(policy: Any, env: Any, digest: Any, *, max_actions: int = 400,
                wall_seconds: float = 30.0) -> dict:
    """Charge arc.make's construction RESET plus every attempted env.step.

    Artificial stopping bounds are NEVER passed to the policy as GAME_OVER.
    The final external consequence is included even at the exact action limit.
    """
    if max_actions < 1:
        raise ValueError('positive action bound required')
    start = time.perf_counter()
    latest = policy._convert_raw_frame_data(env.observation_space)
    initial = digest(latest)
    out = dict(status='ACTION_BOUND', initial_digest=initial, actions=1,
               construction_resets=1, reset_actions=1, environment_step_calls=0,
               max_levels=int(latest.levels_completed), final_state=state_name(latest),
               milestones=[], terminal_failures=0, duplicate_failed_experiments=0,
               zero_observation_change=0, trace=[])
    frames = [latest]
    distinct = {initial}
    failed = set()
    context, program = initial, []
    source_counts = Counter()
    while out['actions'] < max_actions:
        if state_name(latest) == 'WIN':
            out['status'] = 'WIN'
            break
        if time.perf_counter() - start >= wall_seconds:
            out['status'] = 'TIME_BOUND'
            break
        try:
            if policy.is_done(frames, latest):
                out['status'] = 'POLICY_STOP'
                break
            action = policy.choose_action(frames, latest)
            data = validate_action(action, latest)
            aid = int(action.value)
            before = digest(latest)
            reasoning = getattr(action, 'reasoning', {})
            source = str(reasoning.get('source', 'reset' if aid == 0 else 'unspecified')) if isinstance(reasoning, dict) else 'unspecified'
            key = (aid, data.get('x'), data.get('y'))
            # A failed external call still consumes its attempted interaction.
            out['actions'] += 1
            out['environment_step_calls'] += 1
            out['reset_actions'] += int(aid == 0)
            raw = env.step(action, data=data, reasoning={'source': source})
            latest = policy._convert_raw_frame_data(raw)
            after = digest(latest)
            distinct.add(after)
            source_counts[source] += 1
            out['zero_observation_change'] += int(before == after)
            out['trace'].append(dict(action=list(key), source=source, before=before,
                                     after=after, state=state_name(latest), level=int(latest.levels_completed)))
            if aid == 0:
                context, program = after, []
            else:
                program.append(key)
            if int(latest.levels_completed) > out['max_levels']:
                out['milestones'].append(dict(level=int(latest.levels_completed), actions=out['actions']))
                out['max_levels'] = int(latest.levels_completed)
            if int(latest.levels_completed) > int(frames[-1].levels_completed):
                context, program = after, []
            if state_name(latest) == 'GAME_OVER':
                signature = (context, tuple(program))
                out['terminal_failures'] += 1
                out['duplicate_failed_experiments'] += int(signature in failed)
                failed.add(signature)
            frames.append(latest)
        except Exception as exc:
            out['status'] = 'ERROR'
            out['error'] = type(exc).__name__ + ': ' + str(exc)[:240]
            break
    if state_name(latest) == 'WIN':
        out['status'] = 'WIN'
    out.update(final_state=state_name(latest), final_levels=int(latest.levels_completed),
               distinct_observations=len(distinct), source_counts=dict(source_counts),
               wall_seconds=time.perf_counter() - start,
               memory_digest=policy.controller.memory.digest(),
               refuted_programs=policy.controller.memory.refuted_count,
               capability_records=policy.controller.memory.capability_count)
    return out


def comparison_status(rows: list[dict], expected_count: int | None = None) -> str:
    if not rows or (expected_count is not None and len(rows) != expected_count):
        return 'INCOMPLETE'
    groups = defaultdict(list)
    for row in rows:
        groups[(row['game_id'], row['seed'])].append(row)
    for group in groups.values():
        if len(group) != len(ARMS) or {r['arm'] for r in group} != set(ARMS):
            return 'INCOMPLETE'
        if any(r['status'] in ('ERROR', 'TIMEOUT') for r in group):
            return 'ERROR'
        if len({r['initial_digest'] for r in group}) != 1:
            return 'UNMATCHED_START'
    return 'MATCHED'


def quiet_logger() -> logging.Logger:
    logger = logging.getLogger('arc3-audit-sdk')
    logger.handlers = [logging.NullHandler()]
    logger.propagate = False
    logger.setLevel(logging.CRITICAL)
    return logger


def file_hashes(directory: Path) -> dict[str, str]:
    return {str(p.relative_to(directory)): sha(p.read_bytes()) for p in sorted(directory.rglob('*'))
            if p.is_file() and p.suffix in ('.py', '.json')}


def prepare(args: Any) -> None:
    from arc_agi import Arcade, OperationMode
    envdir = Path(args.environments_dir).resolve()
    requested = [s.strip() for s in args.games.split(',') if s.strip()]
    kind = 'sdk_fixture' if args.fixtures else 'public_diagnostic'
    prep_resets = 0
    if not args.fixtures:
        # This is the only network-using stage. Suppress SDK token logging.
        cloud = Arcade(operation_mode=OperationMode.NORMAL,
                       environments_dir=str(envdir), logger=quiet_logger())
        available = {e.game_id.split('-')[0]: e.game_id for e in cloud.get_environments()}
        for short in requested:
            if short in FIXTURES or short not in available:
                raise RuntimeError('requested benchmark absent from official accessible catalog: ' + short)
            if cloud.make(available[short]) is None:
                raise RuntimeError('official benchmark download unavailable: ' + short)
            prep_resets += 1
        cloud.close_scorecard()
    offline = Arcade(operation_mode=OperationMode.OFFLINE,
                     environments_dir=str(envdir), logger=quiet_logger())
    games = []
    for info in sorted(offline.get_environments(), key=lambda e: e.game_id):
        if info.game_id.split('-')[0] in requested:
            games.append(dict(game_id=info.game_id, local_dir=str(Path(info.local_dir).resolve()),
                              files=file_hashes(Path(info.local_dir))))
    manifest = dict(kind=kind, games=games, baseline_commit=BASELINE,
                    generated_agent_sha256=sha(AGENT.read_bytes()),
                    environments_dir=str(envdir), arms=list(ARMS), seeds=[0,1] if not args.fixtures else [0],
                    max_actions=args.max_actions, wall_seconds=30,
                    preparation_resets_excluded_from_agent_trials=prep_resets,
                    interpretation='public diagnostic, not sealed holdout or competition score',
                    discovery_source='official arc-agi SDK' if not args.fixtures else 'pinned SDK fixture repository',
                    sdk_versions={p: importlib.metadata.version(p) for p in ('arc-agi','arcengine')})
    validate_manifest(manifest)
    if len(games) != len(requested):
        raise RuntimeError('incomplete or ambiguous environment download')
    write_json(Path(args.manifest), manifest)
    print('MANIFEST_LOCKED=' + json.dumps({k:manifest[k] for k in ('kind','baseline_commit','generated_agent_sha256')},sort_keys=True))
    print('EXACT_GAMES=' + ','.join(row['game_id'] for row in games))


def load_agent() -> Any:
    sys.path.insert(0, str(ROOT / 'kaggle/vendor/ARC-AGI-3-Agents'))
    spec = importlib.util.spec_from_file_location('frozen_audit_agent', AGENT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def block_network() -> None:
    import socket
    def denied(*args, **kwargs):
        raise RuntimeError('network disabled during offline evaluation')
    socket.create_connection = denied
    socket.socket.connect = denied
    socket.socket.connect_ex = denied


def cell(args: Any) -> None:
    from arc_agi import Arcade, OperationMode
    manifest = json.loads(Path(args.manifest).read_text())
    validate_manifest(manifest)
    if sha(AGENT.read_bytes()) != manifest['generated_agent_sha256']:
        raise ValueError('frozen generated agent mismatch')
    row = next(r for r in manifest['games'] if r['game_id'] == args.game)
    if file_hashes(Path(row['local_dir'])) != row['files']:
        raise ValueError('frozen environment source mismatch')
    module = load_agent()
    block_network()
    arc = Arcade(operation_mode=OperationMode.OFFLINE,
                 environments_dir=manifest['environments_dir'], logger=quiet_logger())
    env = arc.make(args.game, seed=args.seed)
    if env is None:
        raise RuntimeError('pinned offline environment unavailable')
    # The policy has NO reference to the world. Only public frames cross in.
    policy = module.MyAgent(card_id='local-audit',game_id='public-diagnostic',
                            agent_name='frozen',ROOT_URL='',record=False,arc_env=None)
    apply_ablation(policy,args.arm)
    result = run_session(policy,env,lambda obs: module.normalize_frame(obs).evidence_sha256,
                         max_actions=manifest['max_actions'],wall_seconds=manifest['wall_seconds'])
    result.update(game_id=args.game,seed=args.seed,arm=args.arm,kind=manifest['kind'],
                  generated_agent_sha256=manifest['generated_agent_sha256'],baseline_commit=BASELINE)
    arc.close_scorecard()
    write_json(Path(args.output),result)


def batch(args: Any) -> None:
    manifest = json.loads(Path(args.manifest).read_text())
    validate_manifest(manifest)
    target = Path(args.output)
    target.mkdir(parents=True,exist_ok=True)
    rows = []
    expected_count = len(manifest['games']) * len(manifest['seeds']) * len(ARMS)
    for game in manifest['games']:
        for seed in manifest['seeds']:
            for arm in ARMS:
                path = target / f"{game['game_id']}-{seed}-{arm}.json"
                cmd = [sys.executable,str(Path(__file__).resolve()),'cell','--manifest',args.manifest,
                       '--game',game['game_id'],'--seed',str(seed),'--arm',arm,'--output',str(path)]
                try:
                    done = subprocess.run(cmd,capture_output=True,text=True,timeout=45)
                    if done.returncode != 0:
                        raise RuntimeError(done.stderr[-600:])
                    result = json.loads(path.read_text())
                except (RuntimeError,subprocess.TimeoutExpired) as exc:
                    result = dict(game_id=game['game_id'],seed=seed,arm=arm,initial_digest=None,
                                  status='TIMEOUT' if isinstance(exc,subprocess.TimeoutExpired) else 'ERROR',
                                  error=str(exc)[:600])
                    write_json(path,result)
                rows.append(result)
                compact = {k:v for k,v in result.items() if k != 'trace'}
                print('AUDIT_CELL=' + json.dumps(compact,sort_keys=True),flush=True)
                write_json(target/'summary.json',dict(manifest=manifest,comparison=comparison_status(rows, expected_count),
                    results=[{k:v for k,v in r.items() if k != 'trace'} for r in rows]))
    status = comparison_status(rows, expected_count)
    print('ARC3_DIAGNOSTIC_COMPARISON=' + status)
    if status != 'MATCHED':
        raise SystemExit(2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','run','cell'))
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--environments-dir',default='kaggle/.benchmark_envs')
    parser.add_argument('--games',default='ls20,ft09,vc33')
    parser.add_argument('--fixtures',action='store_true')
    parser.add_argument('--max-actions',type=int,default=400)
    parser.add_argument('--game')
    parser.add_argument('--seed',type=int,default=0)
    parser.add_argument('--arm',choices=ARMS,default='full')
    parser.add_argument('--output',default='kaggle/benchmark-results')
    args = parser.parse_args()
    {'prepare':prepare,'run':batch,'cell':cell}[args.command](args)

if __name__ == '__main__':
    main()
