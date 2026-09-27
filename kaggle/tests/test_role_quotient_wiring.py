"""Regressions for live role decoding and CLI causal-bank transport.

The CLI fixtures replace the external environment runner, not the parsing or
handoff under test. They are wiring evidence, never ARC performance evidence.
"""
from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'kaggle/src'))
from metalogic_arc3.residual_exploration import ResidualController
from metalogic_arc3.protected_future_kernel import ProtectedFutureKernel, context as future_context
from metalogic_arc3.runtime import ActionToken, normalize_frame


def observation(actions, level=3):
    return normalize_frame(dict(frame=[[[1]]], levels_completed=level,
                                state='NOT_FINISHED', available_actions=actions))


class RoleActionDecodingContracts(unittest.TestCase):
    def check_action(self, expected, split=False):
        ctl = ResidualController((expected.action_id,),
                                 archived_capabilities=(), trace_capabilities=())
        ctl._action_catalog = lambda obs: (expected,)
        kind = 'CLICK' if expected.action_id == 6 else 'ACTION'
        coarse = ('procedure-effect-v3', kind, 3)
        if split:
            ctl._role_splits.add(coarse)
        token = ctl._crystal_acquisition_next(observation([expected.action_id]))
        self.assertIsNotNone(token, 'An unknown legal role must issue its action')
        self.assertEqual((token.action_id, token.x, token.y),
                         (expected.action_id, expected.x, expected.y))
        self.assertEqual(token.source, 'crystal_acquire')
        self.assertEqual(ctl.crystal.stats['crystal_acquisitions'], 1)
        self.assertEqual(ctl._pending_acquisition_coarse, coarse)
        self.assertGreaterEqual(len(ctl._pending_acquisition_role), 3)

    def test_coarse_directional_role_preserves_execution_action(self):
        self.check_action(ActionToken(1))

    def test_coarse_click_role_preserves_execution_coordinates(self):
        self.check_action(ActionToken(6, 17, 29))

    def test_legacy_split_marker_no_longer_changes_role_identity(self):
        # SUPERSEDED: hypothesis identity was an over-specific repair. A bare
        # split marker is not an earned capability and must not change the
        # protected-future quotient.
        self.check_action(ActionToken(6, 17, 29), split=False)

    def test_future_separator_preserves_action_id_and_coordinates(self):
        expected=ActionToken(6,17,29)
        ctl=ResidualController((6,),archived_capabilities=(),trace_capabilities=())
        ctl._action_catalog=lambda obs:(expected,)
        coarse=('procedure-effect-v3','CLICK',3)
        k=ProtectedFutureKernel()
        k.observe('A','p',future_context(kind='CLICK',distinct_cells=1))
        k.observe('B','n',future_context(kind='CLICK',distinct_cells=2))
        self.assertEqual(k.refine(('distinct_cells','kind')),'distinct_cells')
        ctl._future_kernels[coarse]=k
        token=ctl._crystal_acquisition_next(observation([6]))
        self.assertEqual((token.action_id,token.x,token.y),(6,17,29))
        self.assertEqual(ctl._pending_acquisition_coarse,coarse)


class CausalBankCliContracts(unittest.TestCase):
    def run_cli(self, bank, public_catalog):
        spec = importlib.util.spec_from_file_location(
            'role_wiring_qualifier', ROOT / 'kaggle/scripts/qualify_developmental_controller.py')
        qualifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(qualifier)
        bundle = SimpleNamespace(normalize_frame=normalize_frame)

        def environment_boundary(module, environments, output, games=None,
                                 lives_count=3, causal_bank=None):
            # Persist the value the real runner would receive. Dropping the
            # CLI argument changes this observable result to None.
            return dict(scope='wiring fixture only', received_bank=causal_bank,
                        received_lives=lives_count)

        arc_module = ModuleType('arc_agi')
        arc_module.OperationMode = SimpleNamespace(NORMAL='NORMAL')
        arc_module.Arcade = lambda **kwargs: SimpleNamespace(
            get_environments=lambda: [SimpleNamespace(game_id='fixture-0000')],
            make=lambda game_id: object(), close_scorecard=lambda: None)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'result.json'
            argv = ['qualify', '--environments', str(root / 'environments'),
                    '--output', str(output)]
            if bank is not None:
                path = root / 'bank.json'
                path.write_text(json.dumps(bank))
                argv += ['--causal-bank', str(path)]
            if public_catalog:
                argv += ['--public-catalog']
            with patch.object(sys, 'argv', argv), \
                 patch.object(qualifier, 'load_bundle', return_value=(bundle, 'fixture')), \
                 patch.object(qualifier, 'real_public', environment_boundary), \
                 patch.dict(sys.modules, {'arc_agi': arc_module}), \
                 patch('importlib.metadata.version', return_value='fixture'), \
                 redirect_stdout(io.StringIO()):
                qualifier.main()
            return json.loads(output.read_text())

    def test_explicit_environments_receive_requested_bank(self):
        bank = {'schema': 'test-only', 'templates': [{'game': 'source'}]}
        result = self.run_cli(bank, public_catalog=False)
        self.assertEqual(result['received_bank'], bank)
        self.assertEqual(result['received_lives'], 3)

    def test_public_catalog_replay_receives_requested_bank(self):
        bank = {'schema': 'test-only', 'templates': [{'game': 'source'}]}
        result = self.run_cli(bank, public_catalog=True)
        self.assertEqual(result['received_bank'], bank)
        self.assertEqual(result['received_lives'], 1)

    def test_no_bank_ablation_stays_empty(self):
        result = self.run_cli(None, public_catalog=True)
        self.assertIsNone(result['received_bank'])


if __name__ == '__main__':
    unittest.main()
