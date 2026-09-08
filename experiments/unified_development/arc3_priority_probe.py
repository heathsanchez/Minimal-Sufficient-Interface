"""Bounded diagnostic of the next search decision after a verified checkpoint.

The previous qualification exhausted the primitive and length-two strata before
trying the retained option's repetitions. This experiment changes only ordering.
The frozen grammar, action catalog, verifier, source checkpoint, and budgets stay
unchanged. A prior negative is evidence about the tested schedule, not a proof
that the game or grammar is impossible.
"""
import argparse
import json
import logging
from collections import deque
from pathlib import Path

import arc3_multilevel_transfer as M
import arc3_shared_transfer as T
import closed_feedback_v2 as F


def option_priority(search):
    """Try witnessed operations and their bounded repetitions before expansion.

    No game action or target sequence is supplied. The only distinguished
    programs are those already accepted into the current search's options.
    All other candidates remain in their original relative order, sorted by
    expanded length. The underlying OptionSearch still owns generation/dedup.
    """
    options = tuple(search.options)
    priority = {}
    rank = 0
    for option in reversed(options):
        if option and option not in priority:
            priority[option] = rank
            rank += 1
        for n in F.repetition_counts(search.max_depth // len(option)):
            program = option * n
            if program not in priority:
                priority[program] = rank
                rank += 1
    search.frontier = deque(sorted(search.frontier,
                                   key=lambda p: (0, priority[p]) if p in priority
                                   else (1, len(p))))


def run(factory, actions, source, search_type, execute_stage, output,
        max_training_actions=3000, max_episodes=512, max_depth=32,
        budget=120, max_levels=5, gate=T.run_lean_gate):
    previous = M.order_frontier
    M.order_frontier = option_priority
    try:
        return M.continue_verified(factory, actions, source, search_type,
                                   execute_stage, output,
                                   max_training_actions=max_training_actions,
                                   max_episodes=max_episodes, max_depth=max_depth,
                                   budget=budget, max_levels=max_levels, gate=gate)
    finally:
        M.order_frontier = previous


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source-evidence', required=True)
    p.add_argument('--frozen-dir', required=True)
    p.add_argument('--environments-dir', required=True)
    p.add_argument('--game', default='bt33-a7c3f9d18b4e')
    p.add_argument('--output', default='arc3-priority-probe.json')
    a = p.parse_args()
    _, _, grounding, compositional, multilevel = T.load_frozen(a.frozen_dir)
    from arc_agi import Arcade, OperationMode
    logger = logging.getLogger('arc3-priority-probe')
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.WARNING)
    def factory():
        arcade = Arcade(operation_mode=OperationMode.OFFLINE,
                        environments_dir=a.environments_dir, logger=logger)
        env = arcade.make(a.game)
        if env is None:
            raise RuntimeError('Environment unavailable')
        class Adapter:
            @property
            def observation_space(self): return env.observation_space
            @property
            def action_space(self): return env.action_space
            def reset(self): return env.reset()
            def step(self, action):
                kind, data = grounding.decode(action)
                return env.step(kind, data=data)
            def close(self): return arcade.close_scorecard()
        return Adapter()
    first = factory()
    actions, unsupported = grounding.action_catalog(first.action_space,
                                                     first.observation_space, 8, 256)
    first.close()
    source = json.loads(Path(a.source_evidence).read_text())
    result = run(factory, actions, source, compositional.OptionSearch,
                 multilevel.execute_stage, Path(a.output).parent / 'priority-gate')
    result.update(game=a.game, mode='offline', unsupported_action_ids=unsupported,
                  upstream_commit=T.UPSTREAM, source_blobs=T.SOURCE_BLOBS,
                  scheduling='verified-option-first-v1',
                  comparison_run=34244268321)
    Path(a.output).write_text(json.dumps(result, indent=2, sort_keys=True, default=str)+'\n')
    print('ARC3_PRIORITY_PROBE='+json.dumps({k:result.get(k) for k in
          ('status','training_actions','training_episodes','levels_witnessed',
           'installed_options','terminal_win')},sort_keys=True))


if __name__ == '__main__':
    main()
