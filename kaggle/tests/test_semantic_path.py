from __future__ import annotations

import unittest

from metalogic_arc3.memory_controller import MemoryGraphController
from metalogic_arc3.semantic_path import (
    SemanticDiscoveryResult,
    SemanticPathPlan,
    SemanticPathSession,
    close_path_capabilities,
    infer_path_program,
)
from metalogic_arc3.protected_future import CompiledCapability, UnknownResidual


class ExplodingDiscovery:
    def __init__(self):
        self.called = False

    def close(self, grid, residual):
        self.called = True
        raise AssertionError("static capability should have won")


class FrozenDiscovery:
    def __init__(self, capability):
        self.capability = capability

    def close(self, grid, residual):
        return SemanticDiscoveryResult.bind(
            self.capability,
            SemanticPathPlan(
                path="".join(self.capability.program),
                probes=(),
                probe_directions=(),
                targets=(),
                submit=(0, 0),
            ),
        )


class MismatchedDiscovery:
    def __init__(self, capability):
        self.capability = capability

    def close(self, grid, residual):
        plan = SemanticPathPlan(
            path="LU",
            probes=(),
            probe_directions=(),
            targets=(),
            submit=(0, 0),
        )
        return SemanticDiscoveryResult.bind(self.capability, plan)


class IncompleteDiscovery:
    def close(self, grid, residual):
        return UnknownResidual("exploration.incomplete@1", "bounded_probe_bank_exhausted")


def fixture_compiled_capability(program):
    return CompiledCapability(
        interface_id="program.protected-future-quotient@1",
        capability_id="fixture-capability",
        quotient_id="fixture-quotient",
        start_class=0,
        accepting_classes=(1,),
        program=tuple(program),
        preserves=("observation.current-frame@1",),
        lineage=("fixture@1",),
    )


def unknown_fixture():
    return [[0 for _ in range(8)] for _ in range(8)]


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


def g4_fixture():
    grid = g3_fixture(alternating_bars=True)

    # Restore the board and install the observed G4 wall, enlarged mover, and
    # primitive-scale complementary dock.
    for row in range(4, 32):
        for col in range(33, 61):
            grid[row][col] = 5 if ((row - 4) // 4 + (col - 33) // 4) % 2 == 0 else 4
    for col_index in (0, 1, 3, 4, 5, 6):
        paint(
            grid,
            ((20 + dr, 33 + 4 * col_index + dc) for dr in range(4) for dc in range(4)),
            6,
        )
    large = {
        (row, col)
        for row in range(8, 16)
        for col in range(45, 53)
        if not (row >= 14 and 47 <= col <= 50)
    }
    small = {
        (row, col)
        for row, line in enumerate(("X....X", "X....X", "X....X", "X.XX.X", "XXXXXX"), 24)
        for col, value in enumerate(line, 40)
        if value == "X"
    }
    paint(grid, large | small, 11)

    # Four visible controls: left, grow, down, shrink.  The first is selected
    # initially; the submit object remains the far-right color-9 component.
    for row in range(54, 63):
        for col in range(0, 45):
            grid[row][col] = 5
    paint(grid, ((row, col) for row in range(57, 60) for col in range(2, 4)), 11)
    paint(grid, ((row, col) for row in range(56, 61) for col in range(13, 18)), 11)
    paint(grid, ((row, col) for row in range(60, 62) for col in range(24, 27)), 11)
    grid[58][35] = 11
    return grid


def g5_fixture():
    grid = g3_fixture(alternating_bars=True)

    for row in range(4, 32):
        for col in range(33, 61):
            grid[row][col] = 5 if ((row - 4) // 4 + (col - 33) // 4) % 2 == 0 else 4
    for col_index in (0, 1, 2, 3, 5, 6):
        paint(
            grid,
            ((16 + dr, 33 + 4 * col_index + dc) for dr in range(4) for dc in range(4)),
            6,
        )

    mover = {
        (row, col)
        for row, line in enumerate(("XXXX", "XXX.", "XXX.", "XXXX"), 8)
        for col, value in enumerate(line, 49)
        if value == "X"
    }
    endpoint_primitive = {
        (row, col)
        for row, line in enumerate(("X....X", "X....X", "X....X", "X.XX.X", "XXXXXX"), 20)
        for col, value in enumerate(line, 47)
        if value == "X"
    }
    endpoint = {
        (20 + 2 * (row - 20) + dr, 47 + 2 * (col - 47) + dc)
        for row, col in endpoint_primitive
        for dr in range(2)
        for dc in range(2)
    }
    paint(grid, mover, 11)
    paint(grid, endpoint, 15)

    for row in range(54, 63):
        for col in range(0, 52):
            grid[row][col] = 5
    grid[58][5] = 11
    paint(grid, ((row, col) for row in range(56, 61) for col in range(13, 18)), 11)
    paint(grid, ((row, col) for row in range(60, 62) for col in range(24, 27)), 11)
    paint(
        grid,
        ((row, col) for row, width in ((56, 1), (57, 3), (58, 5), (59, 3), (60, 1))
         for col in range(35 - width // 2, 36 + width // 2)),
        11,
    )
    paint(grid, ((row, col) for row in range(57, 60) for col in range(44, 47)), 15)

    # G5 has three source ports; ordinary controls broadcast, while the color
    # transition exposes only the active middle port.
    for row in (33, 36, 39, 42, 45, 48):
        for col in (10, 15, 20, 25):
            paint(grid, ((row, col - 1), (row, col), (row, col + 1)), 2)
        for col in (10, 15, 20):
            paint(grid, ((row, col - 1), (row, col), (row, col + 1)), 1)
    return grid


def set_source_bits(grid, bits):
    for bit, row in zip(bits, (33, 36, 39, 42, 45, 48)):
        color = 5 if bit else 1
        for col in (10, 15, 20, 25):
            paint(grid, ((row, col - 1), (row, col), (row, col + 1)), color)


def g6_control_fixture():
    grid = g3_fixture()
    for row in range(54, 63):
        for col in range(0, 42):
            grid[row][col] = 5
    # Controls remain U/D/L/R, but the horizontal pair straddles the global
    # screen midpoint.  Their role is carried by position inside each box.
    paint(grid, ((row, col) for row in range(60, 62) for col in range(4, 7)), 11)
    paint(grid, ((row, col) for row in range(55, 57) for col in range(14, 17)), 11)
    paint(grid, ((row, col) for row in range(57, 60) for col in range(27, 29)), 11)
    paint(grid, ((row, col) for row in range(57, 60) for col in range(32, 34)), 11)
    grid[56][5] = grid[58][5] = 0
    grid[58][15] = grid[60][15] = 0
    grid[58][23] = grid[58][25] = 0
    grid[58][35] = grid[58][37] = 0
    return grid


class SemanticPathContracts(unittest.TestCase):
    def test_static_g3_capability_does_not_invoke_discovery(self):
        discovery = ExplodingDiscovery()

        closure = close_path_capabilities(
            g3_fixture(alternating_bars=True),
            discovery=discovery,
        )

        self.assertEqual(closure.plan.path, "URRRUR")
        self.assertFalse(discovery.called)

    def test_named_residual_can_be_closed_by_compiled_capability(self):
        capability = fixture_compiled_capability(program=("R", "U"))

        closure = close_path_capabilities(
            unknown_fixture(),
            discovery=FrozenDiscovery(capability),
        )

        self.assertEqual(closure.plan.path, "RU")
        self.assertIn(
            "program.protected-future-quotient@1",
            closure.closed_interfaces,
        )

    def test_incomplete_discovery_preserves_unknown(self):
        closure = close_path_capabilities(
            unknown_fixture(),
            discovery=IncompleteDiscovery(),
        )

        self.assertEqual(
            closure.residual.missing_interface,
            "exploration.incomplete@1",
        )

    def test_compiled_capability_cannot_authorize_unrelated_plan(self):
        closure = close_path_capabilities(
            unknown_fixture(),
            discovery=MismatchedDiscovery(
                fixture_compiled_capability(program=("R", "U"))
            ),
        )

        self.assertIsNone(closure.plan)
        self.assertEqual(
            closure.residual.missing_interface,
            "adapter.semantic-binding@1",
        )

    def test_session_can_reach_injected_discovery(self):
        capability = fixture_compiled_capability(program=("R", "U"))

        session = SemanticPathSession.start(
            unknown_fixture(),
            discovery=FrozenDiscovery(capability),
        )

        self.assertEqual(session.plan.path, "RU")

    def test_direction_roles_are_local_to_each_control_box(self):
        plan = infer_path_program(g6_control_fixture())

        self.assertEqual(plan.path, "URRRUR")
        self.assertEqual(plan.probe_directions, ("D", "U", "R", "L"))
        self.assertEqual(plan.probes, ((5, 56), (15, 58), (23, 58), (35, 58)))

    def test_recognizer_compiles_multicolor_endpoint_transform_g5(self):
        closure = close_path_capabilities(g5_fixture())

        self.assertIsNone(closure.residual)
        self.assertEqual(closure.plan.path, "XDDDTS")
        self.assertEqual(set(closure.plan.probe_directions), {"I", "S", "D", "X", "T"})
        self.assertEqual(closure.plan.probe_ports[closure.plan.probe_directions.index("T")], 1)
        self.assertIn("shape.multicolor-endpoint-transform@1", closure.closed_interfaces)
        self.assertIn("port.active-source-projection@1", closure.closed_interfaces)

    def test_g5_endpoint_transform_fails_closed_on_nonuniform_scale_block(self):
        grid = g5_fixture()
        grid[20][47] = 5

        closure = close_path_capabilities(grid)

        self.assertIsNone(closure.plan)
        self.assertEqual(
            closure.residual.missing_interface,
            "shape.subcell-docking-pose@1",
        )

    def test_recognizer_compiles_scale_normalized_g4_docking(self):
        closure = close_path_capabilities(g4_fixture())

        self.assertIsNone(closure.residual)
        self.assertEqual(closure.plan.path, "ILDDDD")
        self.assertEqual(set(closure.plan.probe_directions), {"L", "S", "D", "I"})
        self.assertIn("shape.scale-normalized-docking@1", closure.closed_interfaces)

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
        self.assertEqual(closure.residual.reason, "scale_normalized_docking_geometry")

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
        with self.assertRaisesRegex(ValueError, "scale_normalized_docking_geometry"):
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
