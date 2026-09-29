"""End-to-end contracts for the ARC observed-continuation integration.

These finite fixtures are not ARC score evidence. In particular an observed
pixel self-loop is a shortening proposal, never a certified stutter law.
"""
from __future__ import annotations
import importlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from metalogic_arc3.runtime import ActionToken, TraceCapability, normalize_frame


def frame(value, level=0, state='NOT_FINISHED', actions=(1, 2, 3)):
    return {'frame': [[[value, 0], [0, 0]]], 'levels_completed': level,
            'state': state, 'available_actions': list(actions)}


class DevelopmentalContracts(unittest.TestCase):
    def api(self):
        try:
            return importlib.import_module('metalogic_arc3.developmental_controller')
        except ModuleNotFoundError as exc:
            if exc.name != 'metalogic_arc3.developmental_controller':
                raise
            self.fail('Missing live ARC continuation compiler/controller')

    def memory(self):
        return self.api().ProgressMemory()

    def feed(self, memory, observations, actions):
        memory.begin(normalize_frame(observations[0]))
        for before, action, after in zip(observations, actions, observations[1:]):
            memory.observe(normalize_frame(before), ActionToken(action), normalize_frame(after))

    def test_one_state_two_actions_and_same_encoder_at_both_endpoints(self):
        m = self.memory()
        a, b, goal = frame(1), frame(2), frame(3, 1)
        self.feed(m, [a, b, goal], [2, 3])
        self.feed(m, [a, goal], [1])
        machine = m.machine()
        source = m.state_id(normalize_frame(a), ())
        edges = machine.edges_from(source)
        self.assertEqual(len({e.continuation for e in edges}), 2)
        b_id = m.state_id(normalize_frame(b), ())
        self.assertTrue(any(e.target == b_id for e in edges))
        self.assertTrue(machine.edges_from(b_id))

    def test_no_observed_goal_is_unknown_not_a_wall(self):
        m = self.memory()
        self.feed(m, [frame(1), frame(2)], [1])
        m.begin(normalize_frame(frame(1)))
        self.assertIsNone(m.plan(normalize_frame(frame(1))))
        self.assertEqual(m.last_residual['status'], 'UNKNOWN')
        self.assertEqual(m.last_residual['reason'], 'no_supported_progress_continuation')

    def test_goal_regression_proposes_shorter_composition_then_live_replay_checks_it(self):
        m = self.memory()
        a, b, goal = frame(1), frame(2), frame(3, 1)
        self.feed(m, [a, a, b, goal], [1, 2, 3])
        m.begin(normalize_frame(a))
        decision = m.plan(normalize_frame(a))
        self.assertIsNotNone(decision)
        self.assertEqual(decision.action.action_id, 2)
        self.assertEqual(decision.rank, 2)
        self.assertEqual(decision.status, 'CANDIDATE')
        m.observe(normalize_frame(a), decision.action, normalize_frame(b))
        self.assertEqual(m.plan(normalize_frame(b)).action.action_id, 3)
        m.observe(normalize_frame(b), ActionToken(3), normalize_frame(goal))
        self.assertGreater(m.stats['observed_progress'], 0)
        self.assertGreater(m.stats['matched_predictions'], 0)

    def test_hidden_state_separator_refines_instead_of_certifying_pixel_stutter(self):
        m = self.memory()
        a, goal = frame(1), frame(2, 1)
        self.feed(m, [a, a, goal], [1, 2])
        m.begin(normalize_frame(a))
        proposal = m.plan(normalize_frame(a))
        self.assertEqual(proposal.action.action_id, 2)
        # Same pixels, but action 1 was a necessary hidden arming operation.
        m.observe(normalize_frame(a), proposal.action, normalize_frame(a))
        self.assertGreater(m.history_depth, 0)
        self.assertGreater(m.stats['prediction_mismatches'], 0)
        self.assertTrue(m.residuals)
        self.assertFalse(any(r.get('reason') == 'all_actions_impossible' for r in m.residuals))
        m.begin(normalize_frame(a))
        repaired = m.plan(normalize_frame(a))
        self.assertIsNotNone(repaired)
        self.assertEqual(repaired.action.action_id, 1)

    def test_dead_ends_and_cycles_are_not_goal_progress(self):
        m = self.memory()
        a, b, dead = frame(1), frame(2), frame(3, state='GAME_OVER')
        self.feed(m, [a, b, a, dead], [1, 2, 3])
        m.begin(normalize_frame(a))
        self.assertIsNone(m.plan(normalize_frame(a)))

    def test_legal_actions_and_remaining_budget_gate_execution(self):
        m = self.memory()
        a, b, goal = frame(1), frame(2), frame(3, 1)
        self.feed(m, [a, b, goal], [2, 3])
        m.begin(normalize_frame(a))
        self.assertIsNone(m.plan(normalize_frame(a), remaining_actions=1))
        # A changed legal interface is a different protected state.
        self.assertIsNone(m.plan(normalize_frame(frame(1, actions=(1, 3)))))

    def test_revocation_recloses_and_roundtrip_preserves_evidence(self):
        m = self.memory()
        a, b, goal = frame(1), frame(2), frame(3, 1)
        self.feed(m, [a, b, goal], [2, 3])
        m.begin(normalize_frame(a))
        decision = m.plan(normalize_frame(a))
        first_support = decision.support_refs[0]
        m.revoke(first_support, reason='independent_replay_withdrawn')
        self.assertIsNone(m.plan(normalize_frame(a)))
        restored = self.api().ProgressMemory.from_json(m.to_json())
        self.assertEqual(restored.to_json(), m.to_json())
        self.assertIsNone(restored.plan(normalize_frame(a)))
        self.assertTrue(json.loads(m.to_json())['records'])
        self.assertTrue(json.loads(m.to_json())['revoked'])

    def test_real_controller_consumes_learned_continuations_after_reset(self):
        api = self.api()
        ctl = api.DevelopmentalController((1, 2, 3), archived_capabilities=(), trace_capabilities=())
        a, b, goal = frame(1), frame(2), frame(3, 1, 'WIN')
        # Force neither a hidden oracle nor injected bank entries: ordinary
        # inherited exploration discovers 1 (no-op), then 2, then 3.
        self.assertEqual(ctl.observe_and_choose(a).action_id, 1)
        self.assertEqual(ctl.observe_and_choose(a).action_id, 2)
        self.assertEqual(ctl.observe_and_choose(b).action_id, 3)
        ctl.observe_terminal(goal)
        ctl.reset_episode()
        token = ctl.observe_and_choose(a)
        self.assertEqual(token.action_id, 2)
        self.assertEqual(token.source, 'crystal_candidate')
        self.assertGreater(ctl.crystal.stats['decisions'], 0)
        self.assertEqual(ctl.observe_and_choose(b).action_id, 3)
        ctl.observe_terminal(goal)
        self.assertGreaterEqual(ctl.crystal.stats['observed_progress'], 2)

    def test_empty_bank_ablation_changes_the_delivered_action(self):
        api = self.api()
        kwargs = dict(archived_capabilities=(), trace_capabilities=())
        ctl = api.DevelopmentalController((1, 2, 3), **kwargs)
        a, b, g = frame(1), frame(2), frame(3, 1, 'WIN')
        for f in (a, a, b):
            ctl.observe_and_choose(f)
        ctl.observe_terminal(g)
        ctl.reset_episode()
        empty = api.DevelopmentalController((1, 2, 3), **kwargs)
        self.assertNotEqual(ctl.observe_and_choose(a).action_id,
                            empty.observe_and_choose(a).action_id)


    def test_relative_progress_capability_fires_before_new_context_goal_is_seen(self):
        m = self.memory()
        source_a, source_b, source_goal = frame(10), frame(11), frame(12, 1)
        self.feed(m, [source_a, source_b, source_goal], [2, 3])
        self.assertEqual(m.stats['relative_capabilities_compiled'], 1)

        # New level, new protected observations: the old absolute target states
        # are useless here. Only the relative progress contract can fire.
        target_a, target_b, target_goal = frame(20, 1), frame(21, 1), frame(22, 2)
        m.begin(normalize_frame(target_a))
        first = m.plan(normalize_frame(target_a))
        self.assertIsNotNone(first)
        self.assertEqual(first.action.action_id, 2)
        self.assertEqual(first.action.source, 'crystal_relative')
        m.observe(normalize_frame(target_a), first.action, normalize_frame(target_b))

        second = m.plan(normalize_frame(target_b))
        self.assertIsNotNone(second)
        self.assertEqual(second.action.action_id, 3)
        self.assertEqual(second.action.source, 'crystal_relative')
        m.observe(normalize_frame(target_b), second.action, normalize_frame(target_goal))
        self.assertEqual(m.stats['relative_capability_progress'], 1)
        self.assertEqual(m.stats['relative_capability_mismatches'], 0)

        # Empty-memory ablation cannot make the same first-visit decision.
        empty = self.memory()
        empty.begin(normalize_frame(target_a))
        self.assertIsNone(empty.plan(normalize_frame(target_a)))

    def test_relative_progress_capability_aborts_on_first_effect_separator(self):
        m = self.memory()
        self.feed(m, [frame(10), frame(11), frame(12, 1)], [2, 3])
        target = frame(20, 1)
        m.begin(normalize_frame(target))
        first = m.plan(normalize_frame(target))
        self.assertEqual(first.action.source, 'crystal_relative')

        # Source step changed the protected board; target step does not.
        m.observe(normalize_frame(target), first.action, normalize_frame(target))
        self.assertEqual(m.stats['relative_capability_mismatches'], 1)
        self.assertEqual(m.last_residual['reason'], 'relative_progress_separator')
        self.assertIsNone(m.plan(normalize_frame(target)))

    def test_relative_progress_capability_survives_serialization(self):
        m = self.memory()
        self.feed(m, [frame(10), frame(11), frame(12, 1)], [2, 3])
        restored = self.api().ProgressMemory.from_json(m.to_json())
        target = frame(20, 1)
        restored.begin(normalize_frame(target))
        decision = restored.plan(normalize_frame(target))
        self.assertIsNotNone(decision)
        self.assertEqual(decision.action.source, 'crystal_relative')


    def test_failed_relative_binding_survives_reset(self):
        m = self.memory()
        self.feed(m, [frame(10), frame(11), frame(12, 1)], [2, 3])
        target = frame(20, 1)
        m.begin(normalize_frame(target))
        first = m.plan(normalize_frame(target))
        self.assertEqual(first.action.source, 'crystal_relative')
        m.observe(normalize_frame(target), first.action, normalize_frame(target))
        self.assertEqual(m.stats['relative_capability_mismatches'], 1)
        m.reset_transient()
        m.begin(normalize_frame(target))
        self.assertIsNone(m.plan(normalize_frame(target)))

    def test_terminal_effect_match_earns_bounded_extension_and_progress(self):
        m = self.memory()
        # Source level: 2 then 3 advances after one terminal 3.
        self.feed(m, [frame(10), frame(11), frame(12, 1)], [2, 3])
        target_a, target_b = frame(20, 1), frame(21, 1)
        target_c, target_goal = frame(22, 1), frame(23, 2)
        m.begin(normalize_frame(target_a))

        first = m.plan(normalize_frame(target_a))
        self.assertEqual(first.action.action_id, 2)
        m.observe(normalize_frame(target_a), first.action, normalize_frame(target_b))

        terminal = m.plan(normalize_frame(target_b))
        self.assertEqual(terminal.action.action_id, 3)
        m.observe(normalize_frame(target_b), terminal.action, normalize_frame(target_c))
        self.assertEqual(m.stats['relative_terminal_extensions'], 1)

        extension = m.plan(normalize_frame(target_c))
        self.assertIsNotNone(extension)
        self.assertEqual(extension.action.action_id, 3)
        self.assertEqual(extension.action.source, 'crystal_relative_extension')
        m.observe(normalize_frame(target_c), extension.action, normalize_frame(target_goal))
        self.assertEqual(m.stats['relative_extension_progress'], 1)
        self.assertGreaterEqual(m.stats['relative_capability_progress'], 1)

    def test_complex_terminal_action_does_not_self_extend(self):
        m = self.memory()
        a = frame(10, actions=(6,))
        b = frame(11, 1, actions=(6,))
        m.begin(normalize_frame(a))
        m.observe(normalize_frame(a), ActionToken(6, 0, 0), normalize_frame(b))
        target = frame(20, 1, actions=(6,))
        changed = frame(21, 1, actions=(6,))
        m.begin(normalize_frame(target))
        first = m.plan(normalize_frame(target))
        self.assertEqual(first.action.action_id, 6)
        m.observe(normalize_frame(target), first.action, normalize_frame(changed))
        self.assertEqual(m.stats['relative_terminal_extensions'], 0)
        self.assertEqual(m.stats['relative_capability_mismatches'], 1)
        self.assertIsNone(m.plan(normalize_frame(changed)))


    def test_warranted_trace_outranks_relative_candidate(self):
        api = self.api()
        a, b, g = frame(10), frame(11), frame(12, 1)
        target = frame(20, 1)
        target_next = frame(21, 1)
        target_obs = normalize_frame(target)
        target_next_obs = normalize_frame(target_next)
        trace = TraceCapability(
            board_digests=(target_obs.board_digest, target_next_obs.board_digest),
            program=(ActionToken(1),),
            provenance='unit-test-warranted-trace',
        )
        ctl = api.DevelopmentalController(
            (1, 2, 3), archived_capabilities=(), trace_capabilities=(trace,))
        # Learn a relative capability in the same controller.
        ctl.observe_and_choose(a)
        ctl.observe_and_choose(a)
        ctl.observe_and_choose(b)
        ctl.observe_terminal(g)
        ctl.reset_episode()
        token = ctl.observe_and_choose(target)
        self.assertEqual(token.source, 'trace')
        self.assertEqual(token.action_id, 1)


if __name__ == '__main__':
    unittest.main()
