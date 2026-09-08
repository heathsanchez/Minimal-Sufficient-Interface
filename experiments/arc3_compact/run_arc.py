"""Run the compact controller through the official ARC-AGI Toolkit.

The public SDK is the only game interface. No game source or hidden state is
passed to the controller. Offline fixtures are integration tests, not scores
on the ARC-AGI-3 competition. Online mode is not competition mode.
"""
import argparse
import json
from pathlib import Path
from compact_agent import Controller, run_episode


def simple_action_ids(action_space):
    return tuple(sorted(set(int(a.value) for a in action_space if a.is_simple())))


def decode_action(action_id):
    from arcengine import GameAction
    return GameAction.from_id(int(action_id))


def observation_record(frame, action=None):
    """Only public frame and progress data; never inspect game internals."""
    return {'action': action, 'state': getattr(frame.state, 'name', str(frame.state)),
            'levels_completed': int(frame.levels_completed),
            'available_actions': list(frame.available_actions),
            'frame': [layer.tolist() if hasattr(layer, 'tolist') else layer
                      for layer in frame.frame]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--game', default='ls20')
    p.add_argument('--online', action='store_true')
    p.add_argument('--environments-dir', default='environment_files')
    p.add_argument('--max-actions', type=int, default=120)
    p.add_argument('--probe-limit', type=int, default=32)
    p.add_argument('--output', default='arc3-result.json')
    p.add_argument('--trace', default=None)
    args = p.parse_args()
    from arc_agi import Arcade, OperationMode
    mode = OperationMode.ONLINE if args.online else OperationMode.OFFLINE
    arcade = Arcade(operation_mode=mode, environments_dir=args.environments_dir)
    env = arcade.make(args.game)
    if env is None:
        raise RuntimeError('ARC environment unavailable: ' + args.game)
    actions = simple_action_ids(env.action_space)
    trace = [observation_record(env.observation_space)] if args.trace else None
    class Adapter:
        @property
        def observation_space(self): return env.observation_space
        def step(self, action):
            frame = env.step(decode_action(action))
            if trace is not None and frame is not None:
                trace.append(observation_record(frame, action))
            return frame
        def reset(self):
            frame = env.reset()
            if trace is not None and frame is not None:
                trace.append(observation_record(frame, 'reset'))
            return frame
    controller = Controller(actions, args.probe_limit)
    result = run_episode(Adapter(), controller, args.max_actions)
    scorecard = arcade.close_scorecard()
    result.update({'game': args.game, 'mode': 'online' if args.online else 'offline',
                   'scorecard': scorecard.model_dump(mode='json') if hasattr(scorecard, 'model_dump') else str(scorecard),
                   'method': 'bounded-repeat-macro-v1', 'model_provider': None})
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + '\n')
    if trace is not None:
        Path(args.trace).write_text(json.dumps(trace, separators=(',', ':')) + '\n')
    print('ARC3_COMPACT_RESULT=' + json.dumps(result, sort_keys=True, default=str))


if __name__ == '__main__': main()
