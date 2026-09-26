"""Frozen whole-controller acquisition/reuse and real-environment A/B gate.

All fitted state stays within one run of one game. Synthetic results are not
ARC results. Public games here are regression/development, not a blind Kaggle
holdout. Every issued step plus the initial reset performed by make is charged.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'kaggle/src'))


def load_bundle(real: bool):
    path = ROOT/'kaggle/agent/my_agent.py'
    text = path.read_text()
    if real:
        sys.path.insert(0, str(ROOT/'kaggle/vendor/ARC-AGI-3-Agents'))
        spec = importlib.util.spec_from_file_location('qualified_arc_agent', path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    else:
        # Execute the actual delivered runtime bytes. Only external framework
        # imports and its thin adapter are omitted in the dependency-free test.
        import types
        module = types.ModuleType('qualified_arc_agent')
        sys.modules[module.__name__] = module
        executable = text.split('from arcengine import FrameData, GameAction, GameState')[0]
        exec(compile(executable, str(path), 'exec'), module.__dict__)
    return module, hashlib.sha256(text.encode()).hexdigest()


def terminal(controller, observation):
    if hasattr(controller, 'observe_terminal'):
        controller.observe_terminal(observation)
    else:
        # Both arms get the same last observation, including budget endings.
        obs = normalize(observation)
        controller._process_previous_outcome(obs)
        controller._previous, controller._last_action = obs, None


def synthetic(module):
    results = []
    # Fixed before evaluation: 128 opaque relabelings, 4 path lengths, 3 lives.
    # No winner selection or excluded failures based on evaluation outcomes.
    for seed in range(128):
        rng = random.Random(20260926 + seed)
        length = 3 + seed % 4
        required = [rng.randint(1, 5) for _ in range(length)]
        labels = rng.sample(range(1, 16), length + 1)
        def observation(index):
            board = [[0]*4 for _ in range(4)]
            board[seed % 4][(seed//4) % 4] = labels[index]
            return dict(frame=[board], levels_completed=int(index == length),
                        state='WIN' if index == length else 'NOT_FINISHED',
                        available_actions=[1,2,3,4,5])
        row = dict(seed=seed, path_length=length, arms={})
        for name, cls in [('baseline', module.MemoryGraphController),
                          ('candidate', module.DevelopmentalController)]:
            ctl = cls((1,2,3,4,5), archived_capabilities=(), trace_capabilities=())
            lives = []
            for life in range(3):
                ctl.reset_episode()
                index, steps = 0, 0
                sources = Counter()
                while index < length and steps < 128:
                    token = ctl.observe_and_choose(observation(index))
                    sources[token.source] += 1
                    if token.action_id == required[index]:
                        index += 1
                    steps += 1
                terminal(ctl, observation(index))
                lives.append(dict(levels=int(index == length), steps=steps,
                                  resets=1, charged=steps+1, sources=dict(sources)))
            row['arms'][name] = lives
        results.append(row)
    totals = {name: sum(life['charged'] for row in results for life in row['arms'][name])
              for name in ('baseline','candidate')}
    successes = {name: sum(life['levels'] for row in results for life in row['arms'][name])
                 for name in totals}
    usages = sum(life['sources'].get('crystal_candidate',0) for row in results
                 for life in row['arms']['candidate'])
    return dict(scope='fixed finite path-world stream; not ARC score or cross-mechanic generalization',
                cases=results, charged=totals, completed=successes, candidate_uses=usages,
                passed=(successes['candidate']==successes['baseline']==384 and
                        totals['candidate']<totals['baseline'] and usages>0))


def real_public(module, environments: Path, output: Path):
    from arc_agi import Arcade, OperationMode
    from arcengine import GameAction
    rows = []
    # The same immutable priors and budget are provided to both arms.
    games = [('bt33-a7c3f9d18b4e',3), ('bt11-fd9df0622a1a',1)]
    for game_id, goal in games:
        row = dict(game_id=game_id, target_levels=goal, arms={})
        for name, cls in [('baseline', module.MemoryGraphController),
                          ('candidate', module.DevelopmentalController)]:
            ids = tuple(int(a.value) for a in GameAction if a is not GameAction.RESET)
            ctl = cls(ids)
            lives = []
            for life in range(3):
                ctl.reset_episode()
                arc = Arcade(operation_mode=OperationMode.OFFLINE,
                             environments_dir=str(environments.resolve()))
                env = arc.make(game_id)
                if env is None:
                    raise RuntimeError(f'Exact public game unavailable: {game_id}')
                current = env.observation_space
                steps, resets, peak = 0, 1, int(current.levels_completed)
                sources = Counter()
                checkpoints = []
                started = time.perf_counter()
                for _ in range(400):
                    obs = normalize(current)
                    if obs.state == 'WIN' or obs.levels_completed >= goal:
                        break
                    if obs.state in ('GAME_OVER','NOT_PLAYED'):
                        terminal(ctl,current)
                        if obs.state == 'GAME_OVER':
                            ctl.record_terminal_failure('GAME_OVER')
                        ctl.reset_episode()
                        current = env.step(GameAction.RESET)
                        resets += 1
                    else:
                        token = ctl.observe_and_choose(current)
                        if token is None:
                            break
                        if token.action_id not in obs.available_actions:
                            raise AssertionError('Controller emitted an unavailable action')
                        action = GameAction.from_id(token.action_id)
                        data = {'x':token.x, 'y':token.y} if token.action_id == 6 else {}
                        current = env.step(action, data=data)
                        sources[token.source] += 1
                        steps += 1
                    if current is None:
                        raise RuntimeError('Environment produced no observation')
                    if int(current.levels_completed) > peak:
                        peak = int(current.levels_completed)
                        checkpoints.append(dict(level=peak,charged=steps+resets))
                terminal(ctl,current)
                lives.append(dict(levels=peak,steps=steps,resets=resets,
                                  charged=steps+resets,sources=dict(sources),
                                  checkpoints=checkpoints,seconds=time.perf_counter()-started))
                arc.close_scorecard()
                print(json.dumps(dict(game=game_id,arm=name,life=life,**lives[-1])),flush=True)
            row['arms'][name] = lives
            if name == 'candidate':
                row['candidate_stats'] = dict(ctl.crystal.stats)
                row['history_depth'] = ctl.crystal.history_depth
                row['unresolved_count'] = len(ctl.crystal.residuals)
                path = output.parent / (game_id + '.continuations.json')
                path.write_text(ctl.crystal.to_json())
                envelope = ctl.crystal.machine().semantic_object()
                (output.parent/(game_id+'.future.bin')).write_bytes(envelope.to_bytes())
                row['memory_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(row)
    improvement = any(
        c['levels'] > b['levels'] or (c['levels'] == b['levels'] and
        c['levels'] >= row['target_levels'] and c['charged'] < b['charged'])
        for row in rows for b,c in zip(row['arms']['baseline'],row['arms']['candidate']))
    regression = any(c['levels'] < b['levels'] for row in rows
                     for b,c in zip(row['arms']['baseline'],row['arms']['candidate']))
    use = sum(row['candidate_stats']['decisions'] for row in rows)
    return dict(scope='two pinned public development/regression games; no Kaggle score',
                results=rows,candidate_uses=use,observed_improvement=improvement,
                observed_regression=regression,
                release_qualified=bool(improvement and not regression and use))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--environments',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    module, digest = load_bundle(bool(args.environments))
    global normalize
    normalize = module.normalize_frame
    result = real_public(module,args.environments,args.output) if args.environments else synthetic(module)
    result.update(schema='arc3.live-continuation-qualification@1',agent_sha256=digest)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('cases','results')},sort_keys=True))
    if not args.environments and not result['passed']:
        raise SystemExit('FINITE_ACQUISITION_REUSE=FAIL')


if __name__ == '__main__':
    main()
