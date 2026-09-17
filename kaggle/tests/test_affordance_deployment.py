"""Execute the generated policy, not just a source-string wiring check.

Only the third-party SDK boundary is substituted here. The generated memory,
probe selection and adapter code all execute unchanged; real SDK/game tests
remain a separate qualification stage.
"""
from __future__ import annotations

import ast
from enum import Enum
import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'kaggle/src'))


class BoundaryState(Enum):
    NOT_PLAYED = 0
    NOT_FINISHED = 1
    GAME_OVER = 2
    WIN = 3


class BoundaryAction(Enum):
    RESET = 0
    ACTION1 = 1
    ACTION2 = 2
    ACTION3 = 3
    ACTION4 = 4
    ACTION5 = 5
    ACTION6 = 6

    @classmethod
    def from_id(cls, action_id):
        return cls(action_id)

    def is_complex(self):
        return self.value == 6

    def set_data(self, data):
        self.data = dict(data)


class BoundaryAgent:
    def __init__(self, *args, **kwargs):
        pass

    @property
    def name(self):
        return 'boundary-test'


def observation(value=0, *, level=0, state=BoundaryState.NOT_FINISHED,
                full_reset=False, actions=(3, 4)):
    return types.SimpleNamespace(
        frame=[[[value, 0, 0], [0, 1, 1], [0, 1, 1]]],
        levels_completed=level, state=state,
        full_reset=full_reset, available_actions=list(actions),
    )


def load_generated():
    spec = importlib.util.spec_from_file_location(
        '_affordance_deployment_builder', ROOT / 'kaggle/scripts/build_agent.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    tree = ast.parse(builder.render())
    tree.body = [node for node in tree.body if not (
        isinstance(node, ast.ImportFrom)
        and node.level == 0 and node.module in ('arcengine', 'agents.agent'))]
    module = types.ModuleType('_generated_affordance_deployment')
    module.Agent = BoundaryAgent
    module.FrameData = types.SimpleNamespace
    module.GameAction = BoundaryAction
    module.GameState = BoundaryState
    sys.modules[module.__name__] = module
    exec(compile(tree, '<generated-agent>', 'exec'), module.__dict__)
    return module


class AffordanceDeploymentContracts(unittest.TestCase):
    def setUp(self):
        self.generated = load_generated()
        self.policy = self.generated.MyAgent()
        self.policy.controller.archived_capabilities = ()

    def require_consequence_controller(self):
        self.assertEqual(type(self.policy.controller).__name__, 'CertifiedConsequenceController')
        return self.policy.controller

    def test_standalone_contains_both_new_modules(self):
        self.assertTrue(hasattr(self.generated, 'AffordanceMemory'))
        self.assertTrue(hasattr(self.generated, 'ConsequenceController'))
        self.assertTrue(hasattr(self.generated, 'CertifiedArcMemoryGraph'))
        self.assertTrue(hasattr(self.generated, 'CertifiedConsequenceController'))

    def test_adapter_instantiates_the_consequence_controller(self):
        self.require_consequence_controller()

    def test_generated_adapter_records_nonterminal_effect(self):
        c = self.require_consequence_controller()
        start = observation(full_reset=True)
        self.policy.choose_action([start], start)
        changed = observation(2)
        self.policy.choose_action([start, changed], changed)
        self.assertEqual(c.effects.total_observations, 1)
        self.assertTrue(c.affordances._rows)
        self.assertTrue(any(row['changed'] == 1 for row in c.effects.edges.values()))

    def test_game_over_effect_is_committed_before_reset(self):
        c = self.require_consequence_controller()
        start = observation(full_reset=True)
        self.policy.choose_action([start], start)
        failed = observation(2, state=BoundaryState.GAME_OVER)
        action = self.policy.choose_action([start, failed], failed)
        self.assertIs(action, BoundaryAction.RESET)
        self.assertEqual(c.effects.total_observations, 1)
        self.assertTrue(any(row['terminal'] for row in c.effects.edges.values()))
        self.assertEqual(c.memory.refuted_count, 1)
        self.assertIsNone(c._pending_effect)

    def test_final_win_is_observed_once_without_buying_another_action(self):
        c = self.require_consequence_controller()
        start = observation(full_reset=True)
        self.policy.choose_action([start], start)
        won = observation(2, level=1, state=BoundaryState.WIN)
        self.assertTrue(self.policy.is_done([start, won], won))
        self.assertEqual(c.effects.total_observations, 1)
        self.assertEqual(c.memory.capability_count, 1)
        # A one-action endpoint success contains no pre-boundary process effect.
        # Retain the witnessed capability, but do not fabricate portability.
        self.assertEqual(c.memory.certified_capability_candidates(1), ())
        self.assertIsNone(c._pending_effect)
        self.assertTrue(self.policy.is_done([start, won], won))
        self.assertEqual(c.effects.total_observations, 1)
        self.assertEqual(c.memory.capability_count, 1)

    def test_reset_preserves_memory_without_fabricating_a_transition(self):
        c = self.require_consequence_controller()
        first = observation(full_reset=True)
        self.policy.choose_action([first], first)
        second = observation(2)
        self.policy.choose_action([first, second], second)
        restarted = observation(4, full_reset=True)
        self.policy.choose_action([restarted], restarted)
        self.assertEqual(c.effects.total_observations, 1)
        self.policy.choose_action([restarted, second], second)
        self.assertEqual(c.effects.total_observations, 2)

    def test_generated_and_modular_controllers_make_identical_decisions(self):
        from metalogic_arc3.requalification_controller import CertifiedConsequenceController
        c = self.require_consequence_controller()
        modular = CertifiedConsequenceController(tuple(range(1, 7)), archived_capabilities=())
        for i in range(24):
            frame = observation(i % 4, actions=(3, 4, 6), full_reset=(i in (0, 12)))
            if frame.full_reset:
                modular.reset_episode()
            expected = modular.observe_and_choose(frame)
            actual = self.policy.choose_action([frame], frame)
            coordinates = getattr(actual, 'data', {}) if actual.is_complex() else {}
            self.assertEqual(
                (actual.value, coordinates.get('x'), coordinates.get('y'), actual.reasoning['source']),
                (expected.action_id, expected.x, expected.y, expected.source),
            )
        self.assertEqual(c.effects.total_observations, modular.effects.total_observations)
        self.assertEqual(c.memory.digest(), modular.memory.digest())


if __name__ == '__main__':
    unittest.main(verbosity=2)
