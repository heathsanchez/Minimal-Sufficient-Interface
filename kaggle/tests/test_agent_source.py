from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "kaggle" / "src" / "metalogic_arc3" / "agent_template.py"


class AgentSourceContracts(unittest.TestCase):
    def test_adapter_exposes_official_agent_contract(self):
        source = SRC.read_text()
        tree = ast.parse(source)
        classes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
        self.assertIn("MyAgent", classes)
        methods = {n.name for n in classes["MyAgent"].body if isinstance(n, ast.FunctionDef)}
        self.assertIn("is_done", methods)
        self.assertIn("choose_action", methods)

    def test_adapter_has_no_forbidden_runtime_dependencies(self):
        source = SRC.read_text().lower()
        for forbidden in (
            "requests", "openai", "anthropic", "subprocess", "socket",
            "urllib", "github", "realitygraph", "mathgraph",
        ):
            self.assertNotIn(forbidden, source)

    def test_adapter_handles_reset_win_and_complex_data(self):
        source = SRC.read_text()
        self.assertIn("full_reset", source)
        self.assertIn("GameState.NOT_PLAYED", source)
        self.assertIn("GameState.GAME_OVER", source)
        self.assertIn("GameState.WIN", source)
        self.assertIn("set_data", source)
        self.assertIn("OnlineController", source)

    def test_full_reset_clears_local_state_but_does_not_send_reset_again(self):
        tree = ast.parse(SRC.read_text())
        my_agent = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "MyAgent")
        choose = next(n for n in my_agent.body if isinstance(n, ast.FunctionDef) and n.name == "choose_action")
        full_reset_if = next(
            n for n in choose.body
            if isinstance(n, ast.If)
            and isinstance(n.test, ast.Attribute)
            and n.test.attr == "full_reset"
        )
        self.assertTrue(
            any(
                isinstance(n, ast.Expr)
                and isinstance(n.value, ast.Call)
                and isinstance(n.value.func, ast.Attribute)
                and n.value.func.attr == "reset_episode"
                for n in full_reset_if.body
            )
        )
        self.assertFalse(any(isinstance(n, ast.Return) for n in full_reset_if.body))


if __name__ == "__main__":
    unittest.main(verbosity=2)
