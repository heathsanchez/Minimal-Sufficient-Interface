"""A source witness buys a bounded target hypothesis, not unlimited control.

These tests exercise the actual MG-ARC4 controller. Raster/goal observations are
a controlled interface, not an ARC benchmark or a world-equivalence certificate.
The generated policy has advanced to MG-ARC5, so its compatibility check asserts
that a legacy bare capability cannot silently gain certified transfer authority.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'kaggle/src'))
from metalogic_arc3.consequence_controller import ConsequenceController
from metalogic_arc3.memory_graph import ArcMemoryGraph
from metalogic_arc3.runtime import normalize_frame


def frame(value=0, level=1, width=4):
    return dict(frame=[[[value]*width for _ in range(4)]],
                levels_completed=level, state='NOT_FINISHED',
                available_actions=[3, 4])


def controller(depth=8):
    c = ConsequenceController((3, 4), archived_capabilities=(), max_transfer_depth=depth)
    source = c._memory_context(normalize_frame(frame(level=0)))
    c.memory.add_capability(source, ((3, None, None),), source_level=0, target_level=1)
    return c


class TransferContractTests(unittest.TestCase):
    def test_exhausted_hypothesis_does_not_relaunch(self):
        c = controller()
        tokens = [c.observe_and_choose(frame(i % 5)) for i in range(40)]
        self.assertEqual(sum(t.source == 'transfer' for t in tokens), 8)
        self.assertTrue(all(t.source != 'transfer' for t in tokens[8:]))

    def test_reset_does_not_refund_the_target_budget(self):
        c = controller()
        tokens = []
        for episode in range(10):
            c.reset_episode()
            tokens.extend(c.observe_and_choose(frame(i+episode)) for i in range(3))
        self.assertEqual(sum(t.source == 'transfer' for t in tokens), 8)

    def test_serialized_restart_preserves_the_spent_budget(self):
        c = controller()
        before = [c.observe_and_choose(frame(i)) for i in range(5)]
        saved = c.memory.text()
        replacement = controller()
        replacement.memory = ArcMemoryGraph.parse(saved)
        after = [replacement.observe_and_choose(frame(i)) for i in range(24)]
        self.assertEqual(sum(t.source == 'transfer' for t in before+after), 8)
        self.assertEqual(ArcMemoryGraph.parse(saved).text(), saved)

    def test_visual_change_cannot_mint_a_fresh_transfer_allowance(self):
        c = controller()
        tokens = [c.observe_and_choose(frame(i, width=4+i%3)) for i in range(40)]
        self.assertEqual(sum(t.source == 'transfer' for t in tokens), 8)

    def test_another_source_program_cannot_evade_aggregate_target_cap(self):
        c = controller()
        tokens = [c.observe_and_choose(frame(i)) for i in range(10)]
        source = c._memory_context(normalize_frame(frame(level=0)))
        c.memory.add_capability(source, ((4, None, None),), source_level=0, target_level=1)
        tokens.extend(c.observe_and_choose(frame(i+30)) for i in range(20))
        self.assertEqual(sum(t.source == 'transfer' for t in tokens), 8)

    def test_expiry_neither_refutes_source_nor_fabricates_target_success(self):
        c = controller()
        for i in range(20):
            c.observe_and_choose(frame(i))
        self.assertEqual(c.memory.refuted_count, 0)
        self.assertEqual(c.memory.capability_count, 1)
        payload = json.loads(c.memory.text().splitlines()[1])
        trials = payload.get('transfer_trials', [])
        self.assertEqual(len(trials), 1)
        self.assertEqual(trials[0]['status'], 'EXPIRED_UNCONFIRMED')
        self.assertEqual(trials[0]['issued'], 8)

    def test_observed_level_progress_opens_a_distinct_target_budget(self):
        c = controller()
        first = [c.observe_and_choose(frame(i)) for i in range(10)]
        second = [c.observe_and_choose(frame(30+i, level=2)) for i in range(12)]
        self.assertEqual(sum(t.source == 'transfer' for t in first), 8)
        self.assertEqual(sum(t.source == 'transfer' for t in second), 8)
        self.assertEqual(c.memory.capability_count, 2)

    def test_generated_agent_requires_certificate_before_transfer(self):
        from test_affordance_deployment import load_generated, observation
        module = load_generated()
        policy = module.MyAgent()
        c = policy.controller
        c.archived_capabilities = ()
        c.max_transfer_depth = 8
        source = c._memory_context(module.normalize_frame(observation(level=0)))
        c.memory.add_capability(source, ((3,None,None),), source_level=0,target_level=1)
        sources = []
        for i in range(16):
            actual = policy.choose_action([], observation(i,level=1,full_reset=(i%5==0)))
            sources.append(actual.reasoning['source'])
        self.assertEqual(c.memory.capability_count, 1)
        self.assertEqual(c.memory.certified_capability_candidates(1), ())
        self.assertFalse(any(source in ('transfer_probe', 'transfer') for source in sources))

    def test_increasing_runtime_limit_does_not_refund_a_started_contract(self):
        c = controller()
        for i in range(3):
            c.observe_and_choose(frame(i))
        c.reset_episode()
        c.max_transfer_depth = 64
        tokens = [c.observe_and_choose(frame(i+10)) for i in range(80)]
        self.assertEqual(sum(t.source == 'transfer' for t in tokens), 5)

    def test_serialized_overspend_and_unsupported_trial_are_rejected(self):
        c = controller()
        c.observe_and_choose(frame())
        payload = json.loads(c.memory.text().splitlines()[1])
        payload['transfer_trials'][0]['issued'] = 9
        with self.assertRaises(ValueError):
            ArcMemoryGraph.parse('MG-ARC4\n'+json.dumps(payload)+'\n')
        payload['transfer_trials'][0]['issued'] = 1
        payload['transfer_trials'][0]['program'] = [[4,None,None]]
        with self.assertRaises(ValueError):
            ArcMemoryGraph.parse('MG-ARC4\n'+json.dumps(payload)+'\n')

    def test_legacy_memory_loads_without_claiming_target_evidence(self):
        c = controller()
        legacy = json.loads(c.memory.text().splitlines()[1])
        legacy.pop('transfer_trials', None)
        legacy.pop('transfer_limits', None)
        restored = ArcMemoryGraph.parse('MG-ARC3\n'+json.dumps(legacy)+'\n')
        self.assertEqual(restored.capability_count, 1)
        self.assertEqual(json.loads(restored.text().splitlines()[1]).get('transfer_trials'), [])


if __name__ == '__main__':
    unittest.main()
