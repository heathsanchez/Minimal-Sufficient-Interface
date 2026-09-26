from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "kaggle" / "scripts" / "compile_trace_capabilities.py"


def load_compiler():
    spec = importlib.util.spec_from_file_location("trace_compiler", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load trace compiler")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def event(board, **extra):
    row = {
        "board": board,
        "type": "initial",
        "state": "NOT_FINISHED",
        "level": 1,
        "action_num": 0,
    }
    row.update(extra)
    return row


class TraceCompilerContracts(unittest.TestCase):
    def test_compiles_shortest_progress_segment_for_each_exact_start_board(self):
        compiler = load_compiler()
        board0 = [[0, 0], [0, 0]]
        board1 = [[1, 0], [0, 0]]
        board2 = [[1, 1], [0, 0]]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            long_rows = [
                event(board0),
                event(
                    board1,
                    type="action",
                    action_num=1,
                    action_name="ACTION1",
                    action_display="UP",
                    level_completed=False,
                ),
                event(
                    board2,
                    type="action",
                    action_num=2,
                    action_name="ACTION6",
                    action_display="MOUSE(row=1, col=0)",
                    level_completed=True,
                    level=2,
                ),
            ]
            short_rows = [
                event(board0),
                event(
                    board2,
                    type="action",
                    action_num=1,
                    action_name="ACTION6",
                    action_display="MOUSE(row=1, col=1)",
                    level_completed=True,
                    level=2,
                ),
            ]
            for name, rows in (("game_p0_events.jsonl", long_rows), ("game_p1_events.jsonl", short_rows)):
                (root / name).write_text(
                    "".join(json.dumps(row) + "\n" for row in rows),
                    encoding="utf-8",
                )

            compiled = compiler.compile_event_directory(root)

        self.assertEqual(len(compiled), 1)
        capability = compiled[0]
        self.assertEqual(capability["program"], ((6, 1, 1),))
        self.assertEqual(len(capability["board_digests"]), 2)
        self.assertEqual(capability["source"], "game_p1_events.jsonl")

    def test_reset_discards_failed_prefix_before_a_later_progress_witness(self):
        compiler = load_compiler()
        board0 = [[0]]
        dead = [[9]]
        solved = [[1]]
        rows = [
            event(board0),
            event(
                dead,
                type="action",
                action_num=1,
                action_name="ACTION1",
                action_display="UP",
                game_over=True,
                level_completed=False,
            ),
            event(
                board0,
                type="action",
                action_num=2,
                action_name="RESET",
                action_display="RESET",
                level_completed=False,
            ),
            event(
                solved,
                type="action",
                action_num=3,
                action_name="ACTION2",
                action_display="DOWN",
                level_completed=True,
                level=2,
            ),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "game_p0_events.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            compiled = compiler.compile_event_directory(root)

        self.assertEqual(len(compiled), 1)
        self.assertEqual(compiled[0]["program"], ((2, None, None),))


if __name__ == "__main__":
    unittest.main(verbosity=2)
