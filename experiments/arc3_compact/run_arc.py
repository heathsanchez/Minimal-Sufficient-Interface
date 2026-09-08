"""Run the compact controller through the official ARC-AGI Toolkit.

The public SDK is the only game interface. No game source or hidden state is
passed to the controller. Offline fixtures are integration tests, not scores
on the ARC-AGI-3 competition. Online mode uses the official server scorecard.
"""
import argparse
import json
import os
from pathlib import Path
from compact_agent import Controller, run_episode


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--game', default='ls20')
    p.add_argument('--online', action='store_true')
    p.add_argument('--environments-dir', default='environment_files')
    p.add_argument('--max-actions', type=int, default=120)
    p.add_argument('--probe-limit', type=int, default=32)
    p.add_argument('--output', default='arc3-result.json')
    args = p.parse_args()
    from arc_agi import Arcade, OperationMode
    from arcengine import GameAction
    mode = OperationMode.ONLINE if args.online else OperationMode.OFFLINE
    arcade = Arcade(operation_mode=mode, environments_dir=args.environments_dir)
    env = arcade.make(args.game)
    if env is None:
        raise RuntimeError('ARC environment unavailable: ' + args.game)
    actions = tuple(int(getattr(a, 'value', a)) for a in env.action_space
                    if not (a.is_complex() if hasattr(a, 'is_complex') else int(a) == 6))
    class Adapter:
        @property
        def observation_space(self): return env.observation_space
        def step(self, action): return env.step(GameAction(action))
        def reset(self): return env.reset()
    controller = Controller(actions, args.probe_limit)
    result = run_episode(Adapter(), controller, args.max_actions)
    scorecard = arcade.close_scorecard()
    result.update({'game': args.game, 'mode': 'online' if args.online else 'offline',
                   'official_score': getattr(scorecard, 'score', None),
                   'scorecard_id': getattr(scorecard, 'card_id', None),
                   'method': 'bounded-repeat-macro-v1', 'model_provider': None})
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + '\n')
    print('ARC3_COMPACT_RESULT=' + json.dumps(result, sort_keys=True, default=str))


if __name__ == '__main__': main()
