from __future__ import annotations

import unittest

from metalogic_arc3.memory_controller import MemoryGraphController
from metalogic_arc3.semantic_path import (
    SemanticPathSession,
    close_path_capabilities,
    infer_path_program,
)


def paint(grid, cells, color):
    for row, col in cells:
        grid[row][col] = color


def g3_fixture(alternating_bars=False):
    grid = [[0 for _ in range(64)] for _ in range(64)]

    # Observed 7x7 checkerboard and the one-cell wall gap.
    for row in range(7):
        for col in range(7):
            color = 5 if (row + col) % 2 == 0 else 4
            paint(
                grid,
                ((4 + 4 * row + dr, 33 + 4 * col + dc)
                 for dr in range(4) for dc in range(4)),
                color,
            )
    for row in (0, 1, 2, 4, 5, 6):
        paint(
            grid,
            ((4 + 4 * row + dr, 45 + dc) for dr in range(4) for dc in range(4)),
            6,
        )

    # Small moving U and its complementary docking glyph.  Their unique
    # cell-aligned translation is (-2, +4), yielding URRRUR on the board.
    mover = {(20, 37), (20, 40)} | {
        (row, col) for row in range(21, 24) for col in range(37, 41)
    }
    dock = {(11, col) for col in range(52, 58)}
    dock |= {(12, 52), (12, 54), (12, 55), (12, 57)}
    dock |= {(row, col) for row in range(13, 16) for col in (52, 57)}
    paint(grid, mover, 11)
    paint(grid, dock, 11)

    patches = (
        (2, (".......", "...o...", ".......", "...o...", ".......", "..PPP..", "..PPP..")),
        (12, ("..PPP..", "..PPP..", ".......", "...o...", ".......", "...o...", ".......")),
        (22, (".......", ".......", "PP.....", "PP.o.o.", "PP.....", ".......", ".......")),
        (32, (".......", ".......", ".....PP", ".o.o.PP", ".....PP", ".......", ".......")),
    )
    for col0, patch in patches:
        for dr, line in enumerate(patch):
            for dc, value in enumerate(line):
                grid[55 + dr][col0 + dc] = {".": 5, "o": 0, "P": 11}[value]

    # Six source rows and six writable target columns.
    for row_index, row in enumerate((33, 36, 39, 42, 45, 48)):
        source_color = 5 if row_index in (0, 1) else 1
        for col in (10, 15, 20, 25):
            cells = (
                ((row - 1, col), (row, col), (row + 1, col))
                if alternating_bars and row_index % 2
                else ((row, col - 1), (row, col), (row, col + 1))
            )
            paint(grid, cells, source_color)
        for col in (34, 39, 44, 49, 54, 59):
            cells = (
                ((row - 1, col), (row, col), (row + 1, col))
                if alternating_bars and row_index % 2
                else ((row, col - 1), (row, col), (row, col + 1))
            )
            paint(grid, cells, 1)

    paint(grid, ((row, col) for row in range(54, 63) for col in range(53, 62)), 9)
    return grid


def set_source_bits(grid, bits):
    for bit, row in zip(bits, (33, 36, 39, 42, 45, 48)):
        color = 5 if bit else 1
        for col in (10, 15, 20, 25):
            paint(grid, ((row, col - 1), (row, col), (row, col + 1)), color)


class SemanticPathContracts(unittest.TestCase):
    def test_capability_closure_records_complete_g3_interface_chain(self):
        closure = close_path_capabilities(g3_fixture(alternating_bars=True))

        self.assertIsNone(closure.residual)
        self.assertEqual(closure.plan.path, "URRRUR")
        self.assertEqual(closure.closed_interfaces, (
            "observation.current-frame@1",
            "board.tiled-grid@1",
            "shape.docking-translation@1",
            "board.route-problem@1",
            "control.direction-role@1",
            "panel.target-grid@1",
            "control.submit@1",
            "program.temporal-columns@1",
        ))

    def test_capability_closure_preserves_g4_docking_residual(self):
        grid = g3_fixture(alternating_bars=True)
        for row in range(8, 16):
            for col in range(45, 53):
                grid[row][col] = 11
        for row in (14, 15):
            for col in range(47, 51):
                grid[row][col] = 4

        closure = close_path_capabilities(grid)

        self.assertIsNone(closure.plan)
        self.assertEqual(closure.closed_interfaces, (
            "observation.current-frame@1",
            "board.tiled-grid@1",
        ))
        self.assertEqual(
            closure.residual.missing_interface,
            "shape.subcell-docking-pose@1",
        )
        self.assertEqual(closure.residual.reason, "subcell_docking_geometry")

    def test_recognizer_uses_bar_centres_across_orientation(self):
        plan = infer_path_program(g3_fixture(alternating_bars=True))
        self.assertEqual(plan.path, "URRRUR")
        self.assertEqual(len(plan.targets), 6)
        self.assertTrue(all(len(row) == 6 for row in plan.targets))

    def test_recognizer_uses_latest_frame_from_visible_history(self):
        class Frame:
            frame = [[[0 for _ in range(64)] for _ in range(64)], g3_fixture()]

        self.assertEqual(infer_path_program(Frame()).path, "URRRUR")

    def test_recognizer_accepts_frame_with_array_like_visible_layer(self):
        class Layer:
            def tolist(self):
                return g3_fixture()

        class Frame:
            frame = [Layer()]

        self.assertEqual(infer_path_program(Frame()).path, "URRRUR")

    def test_recognizer_derives_observed_g3_path_and_controls(self):
        plan = infer_path_program(g3_fixture())
        self.assertEqual(plan.path, "URRRUR")
        self.assertEqual(plan.probes, ((5, 56), (15, 58), (25, 58), (33, 58)))
        self.assertEqual(plan.probe_directions, ("D", "U", "L", "R"))
        self.assertEqual(plan.submit, (57, 58))
        self.assertEqual(len(plan.targets), 6)
        self.assertTrue(all(len(row) == 6 for row in plan.targets))

    def test_recognizer_rejects_noncomplementary_multiscale_dock(self):
        grid = g3_fixture()
        # Replace the exact 5x6 dock with the G4 8x8 Pi glyph.  The semantic
        # capability must preserve UNKNOWN instead of guessing a subcell anchor.
        for row in range(8, 16):
            for col in range(45, 53):
                grid[row][col] = 11
        for row in (14, 15):
            for col in range(47, 51):
                grid[row][col] = 4
        with self.assertRaisesRegex(ValueError, "subcell_docking_geometry"):
            infer_path_program(grid)

    def test_session_probes_then_writes_then_submits(self):
        grid = g3_fixture()
        session = SemanticPathSession.start(grid)
        codes = {
            "D": (1, 1, 0, 0, 0, 0),
            "U": (1, 0, 0, 0, 0, 1),
            "L": (0, 1, 0, 0, 0, 1),
            "R": (0, 1, 0, 0, 0, 0),
        }

        actions = []
        while session.phase != "done":
            action = session.next_action(grid)
            actions.append(action)
            if session.last_action_kind == "probe":
                set_source_bits(grid, codes[session.pending_probe])
            elif session.last_action_kind == "write":
                x, y = action
                grid[y][x] = 5 if session.last_write_value else 1

        self.assertEqual(actions[:4], [(5, 56), (15, 58), (25, 58), (33, 58)])
        self.assertEqual(actions[-1], (57, 58))
        self.assertEqual(session.phase, "done")

    def test_memory_controller_prefers_qualified_semantic_session(self):
        grid = g3_fixture()
        controller = MemoryGraphController((6,), archived_capabilities=())
        codes = {
            "D": (1, 1, 0, 0, 0, 0),
            "U": (1, 0, 0, 0, 0, 1),
            "L": (0, 1, 0, 0, 0, 1),
            "R": (0, 1, 0, 0, 0, 0),
        }
        actions = []
        for _ in range(32):
            frame = {
                "frame": [grid],
                "levels_completed": 2,
                "state": "NOT_FINISHED",
                "available_actions": [6],
            }
            token = controller.observe_and_choose(frame)
            self.assertIsNotNone(token)
            actions.append((token.x, token.y, token.source))
            session = controller._semantic_path
            if token.source == "semantic_path" and session.last_action_kind == "probe":
                set_source_bits(grid, codes[session.pending_probe])
            elif token.source == "semantic_path" and session.last_action_kind == "write":
                grid[token.y][token.x] = 5 if session.last_write_value else 1
            if token.source == "semantic_path" and session.phase == "done":
                break

        self.assertEqual(actions[:4], [
            (5, 56, "semantic_path"),
            (15, 58, "semantic_path"),
            (25, 58, "semantic_path"),
            (33, 58, "semantic_path"),
        ])
        self.assertEqual(actions[-1], (57, 58, "semantic_path"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
