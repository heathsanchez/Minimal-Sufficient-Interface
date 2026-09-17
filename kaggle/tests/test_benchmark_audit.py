"""Evaluator contracts; these synthetic interfaces are NOT benchmark evidence."""
from __future__ import annotations
import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'benchmark_audit.py'
if SCRIPT.exists():
    spec = importlib.util.spec_from_file_location('benchmark_audit', SCRIPT)
    audit = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = audit
    spec.loader.exec_module(audit)
else:
    audit = None

class Action:
    def __init__(self, value=3, data=None, source='explore'):
        self.value = value
        self.name = 'RESET' if value == 0 else f'ACTION{value}'
        self.action_data = SimpleNamespace(model_dump=lambda: data or {})
        self.reasoning = {'source': source}
    def is_complex(self):
        return self.value == 6

def frame(state='NOT_FINISHED', level=0, value=0, legal=(3, 4)):
    return SimpleNamespace(state=state, levels_completed=level, available_actions=list(legal),
        frame=[[[value] * 4 for _ in range(4)]], full_reset=False)

class Policy:
    def __init__(self, actions=None):
        self.actions = iter(actions) if actions else None
        self.frames = []
        memory = SimpleNamespace(forbidden_next=lambda *args: {'refuted'}, refuted_count=0,
                                 capability_count=0, digest=lambda: 'memory')
        self.controller = SimpleNamespace(memory=memory, archived_capabilities=('fixture',),
                                         _next_transfer=lambda *args: 'transfer')
    def _convert_raw_frame_data(self, obs):
        return obs
    def is_done(self, frames, latest):
        return latest.state == 'WIN'
    def choose_action(self, frames, latest):
        return next(self.actions) if self.actions else Action()

class Environment:
    def __init__(self, outcomes=None, error=False):
        self.observation_space = frame()
        self.outcomes = iter(outcomes) if outcomes else None
        self.calls = 0
        self.error = error
    def step(self, action, **kwargs):
        self.calls += 1
        if self.error:
            raise RuntimeError('external boundary failed')
        self.observation_space = next(self.outcomes) if self.outcomes else frame(value=self.calls)
        return self.observation_space

def digest(obs):
    return str((obs.state, obs.levels_completed, obs.frame))

class BenchmarkAuditContracts(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(audit, 'bounded benchmark evaluator is not implemented')
    def test_fixture_cannot_be_mislabelled_as_public_benchmark(self):
        with self.assertRaises(ValueError):
            audit.validate_manifest({'kind':'public_diagnostic', 'games':[{'game_id':'bt11-fixture'}]})
        with self.assertRaises(ValueError):
            audit.validate_manifest({'kind':'public_diagnostic', 'games':[
                {'game_id':'ls20-test', 'local_dir':'/x/test_environment_files/a'}]})
    def test_exact_versions_and_nonempty_suite_required(self):
        for games in ([], [{'game_id':'ls20'}], [{'game_id':'ls20-a'}, {'game_id':'ls20-b'}]):
            with self.assertRaises(ValueError):
                audit.validate_manifest({'kind':'public_diagnostic', 'games':games})
    def test_no_memory_and_transfer_ablations_are_independent(self):
        full, no_refute, no_transfer, neither = [Policy() for _ in range(4)]
        for policy, arm in zip((full,no_refute,no_transfer,neither), audit.ARMS):
            audit.apply_ablation(policy, arm)
            self.assertEqual(policy.controller.archived_capabilities, ())
        self.assertEqual(full.controller.memory.forbidden_next(), {'refuted'})
        self.assertEqual(no_refute.controller.memory.forbidden_next(), set())
        self.assertEqual(no_refute.controller._next_transfer(), 'transfer')
        self.assertEqual(no_transfer.controller.memory.forbidden_next(), {'refuted'})
        self.assertIsNone(no_transfer.controller._next_transfer())
        self.assertEqual(neither.controller.memory.forbidden_next(), set())
        self.assertIsNone(neither.controller._next_transfer())
    def test_budget_counts_construction_reset_and_every_explicit_reset(self):
        env = Environment([frame(),frame(),frame()])
        p = Policy([Action(3),Action(0),Action(3)])
        result = audit.run_session(p,env,digest,max_actions=4)
        self.assertEqual(result['actions'], 4)
        self.assertEqual(result['environment_step_calls'], 3)
        self.assertEqual(result['reset_actions'], 2)
        self.assertEqual(env.calls, 3)
        self.assertEqual(result['status'], 'ACTION_BOUND')
        self.assertEqual(result['terminal_failures'], 0)
    def test_one_action_budget_performs_no_extra_step(self):
        env = Environment()
        result = audit.run_session(Policy(),env,digest,max_actions=1)
        self.assertEqual(env.calls, 0)
        self.assertEqual(result['actions'], 1)
    def test_terminal_last_action_is_counted_and_stops(self):
        env = Environment([frame('WIN',1)])
        result = audit.run_session(Policy(),env,digest,max_actions=4)
        self.assertEqual(result['status'], 'WIN')
        self.assertEqual(result['actions'], 2)
        self.assertEqual(result['max_levels'], 1)
        self.assertEqual(result['milestones'], [{'level':1,'actions':2}])
        self.assertEqual(env.calls, 1)
    def test_external_exception_is_charged_and_is_not_a_solve(self):
        result = audit.run_session(Policy(),Environment(error=True),digest,max_actions=4)
        self.assertEqual(result['status'], 'ERROR')
        self.assertEqual(result['actions'], 2)
        self.assertEqual(result['environment_step_calls'], 1)
        self.assertEqual(result['max_levels'], 0)
    def test_illegal_action_is_not_sent(self):
        env = Environment()
        result = audit.run_session(Policy([Action(6, {'x':0,'y':0})]),env,digest,max_actions=4)
        self.assertEqual(result['status'], 'ERROR')
        self.assertEqual(env.calls, 0)
        self.assertEqual(result['actions'], 1)
    def test_real_failed_experiment_repeats_are_counted_exactly(self):
        env = Environment([frame('GAME_OVER'),frame(),frame('GAME_OVER')])
        result = audit.run_session(Policy([Action(3),Action(0),Action(3)]),env,digest,max_actions=4)
        self.assertEqual(result['terminal_failures'], 2)
        self.assertEqual(result['duplicate_failed_experiments'], 1)
    def test_time_bound_is_unknown_not_refutation(self):
        result = audit.run_session(Policy(),Environment(),digest,max_actions=100,wall_seconds=0)
        self.assertEqual(result['status'], 'TIME_BOUND')
        self.assertEqual(result['terminal_failures'], 0)
    def test_missing_cells_and_mismatched_starts_prevent_valid_comparison(self):
        rows = [{'game_id':'ls20-a', 'seed':0, 'arm':arm,'initial_digest':'same',
                 'status':'ACTION_BOUND','max_levels':0} for arm in audit.ARMS]
        self.assertEqual(audit.comparison_status(rows), 'MATCHED')
        self.assertEqual(audit.comparison_status(rows[:-1]), 'INCOMPLETE')
        rows[1]['initial_digest'] = 'different'
        self.assertEqual(audit.comparison_status(rows), 'UNMATCHED_START')
    def test_complete_first_game_does_not_hide_missing_remaining_cells(self):
        rows = [{'game_id':'ls20-a', 'seed':0, 'arm':arm,'initial_digest':'same',
                 'status':'ACTION_BOUND','max_levels':0} for arm in audit.ARMS]
        self.assertEqual(audit.comparison_status(rows, expected_count=8), 'INCOMPLETE')
    def test_error_is_not_silently_averaged_as_zero(self):
        rows = [{'game_id':'ls20-a', 'seed':0, 'arm':arm,'initial_digest':'same',
                 'status':'ACTION_BOUND','max_levels':0} for arm in audit.ARMS]
        rows[0]['status'] = 'ERROR'
        self.assertEqual(audit.comparison_status(rows), 'ERROR')

if __name__ == '__main__':
    unittest.main(verbosity=2)
