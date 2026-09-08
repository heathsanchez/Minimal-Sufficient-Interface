"""Public ARC-AGI-3 adapter for the consequential-development experiment.

No game implementation or hidden state is exposed to the controller. Online
scores are public evaluations, not competition submissions. The model budget
is zero; this is a bounded experimental baseline, not a general ARC solver.
"""
import argparse
import json
import logging
from pathlib import Path
from agent import Development, observation, run_episode


def simple_action_ids(space):
    return tuple(sorted({int(a.value) for a in space if a.is_simple()}))


def decode_action(action_id):
    from arcengine import GameAction
    return GameAction.from_id(int(action_id))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--game', default='ls20')
    p.add_argument('--online', action='store_true')
    p.add_argument('--environments-dir', default='environment_files')
    p.add_argument('--max-actions', type=int, default=300)
    p.add_argument('--controller', choices=('consequence', 'cold'), default='consequence')
    p.add_argument('--output', default='arc3-consequence-result.json')
    p.add_argument('--trace')
    a = p.parse_args()
    from arc_agi import Arcade, OperationMode
    logger = logging.getLogger('arc3-consequence-public')
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.WARNING)
    arcade = Arcade(operation_mode=OperationMode.ONLINE if a.online else OperationMode.OFFLINE,
                    environments_dir=a.environments_dir, logger=logger)
    env = arcade.make(a.game)
    if env is None:
        raise RuntimeError('ARC environment unavailable: ' + a.game)
    actions = simple_action_ids(env.action_space)
    if not actions:
        raise RuntimeError('No supported simple actions')
    trace = [observation(env.observation_space)] if a.trace else None

    class Adapter:
        @property
        def observation_space(self):
            return env.observation_space

        def step(self, action):
            frame = env.step(decode_action(action))
            if trace is not None and frame is not None:
                trace.append(dict(observation(frame), action=action))
            return frame

        def reset(self):
            frame = env.reset()
            if trace is not None and frame is not None:
                trace.append(dict(observation(frame), action='reset'))
            return frame

    development = Development(actions, retain_scripts=a.controller == 'consequence')
    result = run_episode(Adapter(), actions, a.max_actions, development)
    scorecard = arcade.close_scorecard()
    result.update({'game': a.game, 'mode': 'online' if a.online else 'offline',
                   'method': a.controller, 'model_provider': None,
                   'competition_submission': False,
                   'scorecard': scorecard.model_dump(mode='json') if hasattr(scorecard, 'model_dump') else str(scorecard)})
    result['scorecard'].pop('api_key', None) if isinstance(result['scorecard'], dict) else None
    Path(a.output).write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + '\n')
    if trace is not None:
        Path(a.trace).write_text(json.dumps(trace, separators=(',', ':')) + '\n')
    print('ARC3_CONSEQUENCE_RESULT=' + json.dumps(result, sort_keys=True, default=str))


if __name__ == '__main__':
    main()
