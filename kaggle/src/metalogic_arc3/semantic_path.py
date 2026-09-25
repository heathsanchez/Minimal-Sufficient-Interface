from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from .protected_future import CompiledCapability, UnknownResidual, canonical_digest


Cell = tuple[int, int]
Point = tuple[int, int]


@dataclass(frozen=True)
class SemanticPathPlan:
    path: str
    probes: tuple[Point, ...]
    probe_directions: tuple[str, ...]
    targets: tuple[tuple[Point, ...], ...]
    submit: Point
    probe_ports: tuple[int | None, ...] = ()


@dataclass(frozen=True)
class SemanticResidual:
    missing_interface: str
    reason: str


@dataclass(frozen=True)
class SemanticCapabilityClosure:
    plan: SemanticPathPlan | None
    closed_interfaces: tuple[str, ...]
    residual: SemanticResidual | None


@dataclass(frozen=True)
class SemanticDiscoveryResult:
    capability: CompiledCapability
    plan: SemanticPathPlan
    binding_id: str

    @classmethod
    def bind(
        cls,
        capability: CompiledCapability,
        plan: SemanticPathPlan,
    ) -> "SemanticDiscoveryResult":
        return cls(
            capability=capability,
            plan=plan,
            binding_id=_discovery_binding_id(capability, plan),
        )


def _discovery_binding_id(
    capability: CompiledCapability,
    plan: SemanticPathPlan,
) -> str:
    return canonical_digest(
        {
            "contract": "arc.semantic-discovery-binding@1",
            "capability": capability.capability_id,
            "plan": plan,
        }
    )


def _matrix(value) -> list[list[int]]:
    """Return the visible 2-D integer layer without depending on arcengine."""
    if hasattr(value, "frame"):
        value = value.frame
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, (list, tuple)):
        value = [item.tolist() if hasattr(item, "tolist") else item for item in value]
    while (
        isinstance(value, (list, tuple))
        and value
        and isinstance(value[0], (list, tuple))
        and value[0]
        and isinstance(value[0][0], (list, tuple))
    ):
        value = value[-1]
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError("missing_visible_grid")
    rows = [list(map(int, row)) for row in value]
    if not rows or not rows[0] or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("non_rectangular_visible_grid")
    return rows


def _components(grid: Sequence[Sequence[int]], colors: Iterable[int]) -> list[set[Cell]]:
    wanted = set(colors)
    height, width = len(grid), len(grid[0])
    unseen = {(r, c) for r in range(height) for c in range(width) if grid[r][c] in wanted}
    result: list[set[Cell]] = []
    while unseen:
        seed = unseen.pop()
        component = {seed}
        queue = [seed]
        while queue:
            row, col = queue.pop()
            for neighbor in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    component.add(neighbor)
                    queue.append(neighbor)
        result.append(component)
    return result


def _bbox(cells: set[Cell]) -> tuple[int, int, int, int]:
    rows = [cell[0] for cell in cells]
    cols = [cell[1] for cell in cells]
    return min(rows), min(cols), max(rows), max(cols)


def _find_board(grid: Sequence[Sequence[int]], cell_size: int = 4) -> tuple[int, int]:
    """Locate the 7x7 tiled playfield by its palette and four-pixel cadence."""
    height, width = len(grid), len(grid[0])
    span = 7 * cell_size
    candidates: list[tuple[float, int, int]] = []
    for top in range(0, height - span + 1):
        for left in range(width // 3, width - span + 1):
            dominant: list[list[int]] = []
            purity = 0.0
            for board_row in range(7):
                line = []
                for board_col in range(7):
                    counts: dict[int, int] = {}
                    for dr in range(cell_size):
                        for dc in range(cell_size):
                            value = grid[top + cell_size * board_row + dr][left + cell_size * board_col + dc]
                            counts[value] = counts.get(value, 0) + 1
                    color, count = max(counts.items(), key=lambda item: item[1])
                    line.append(color)
                    purity += count / (cell_size * cell_size)
                dominant.append(line)
            flat = {value for line in dominant for value in line}
            if not {4, 5, 6}.issubset(flat) or not flat.issubset({4, 5, 6, 11, 15}):
                continue
            checker = sum(
                dominant[r][c] in (4, 5)
                and dominant[r][c] == (5 if (r + c) % 2 == 0 else 4)
                for r in range(7)
                for c in range(7)
            )
            if checker < 20:
                continue
            candidates.append((purity + 2.0 * checker, top, left))
    if not candidates:
        raise ValueError("board_geometry")
    _, top, left = max(candidates)
    return top, left


def _complement_translation(
    grid: Sequence[Sequence[int]], board_top: int, board_left: int, cell_size: int = 4
) -> tuple[set[Cell], set[Cell], int, int]:
    board_bottom = board_top + 7 * cell_size
    board_right = board_left + 7 * cell_size
    glyphs = [
        component
        for component in _components(grid, (11,))
        if any(board_top <= row < board_bottom and board_left <= col < board_right for row, col in component)
    ]
    solutions: list[tuple[set[Cell], set[Cell], int, int]] = []
    for mover in glyphs:
        for dock in glyphs:
            if mover is dock:
                continue
            dtop, dleft, dbottom, dright = _bbox(dock)
            rectangle = {(r, c) for r in range(dtop, dbottom + 1) for c in range(dleft, dright + 1)}
            for delta_row in range(-7 * cell_size, 7 * cell_size + 1, cell_size):
                for delta_col in range(-7 * cell_size, 7 * cell_size + 1, cell_size):
                    shifted = {(row + delta_row, col + delta_col) for row, col in mover}
                    if shifted.isdisjoint(dock) and shifted | dock == rectangle:
                        solutions.append((mover, dock, delta_row, delta_col))
    if len(solutions) != 1:
        raise ValueError("subcell_docking_geometry")
    return solutions[0]


def _scale_normalized_translation(
    grid: Sequence[Sequence[int]], board_top: int, board_left: int, cell_size: int = 4
) -> tuple[set[Cell], set[Cell], int, int]:
    """Recover complement docking when the transported mover is enlarged 2x."""
    board_bottom = board_top + 7 * cell_size
    board_right = board_left + 7 * cell_size
    glyphs = [
        component
        for component in _components(grid, (11,))
        if any(board_top <= row < board_bottom and board_left <= col < board_right for row, col in component)
    ]
    solutions: list[tuple[set[Cell], set[Cell], int, int]] = []
    for enlarged in glyphs:
        top, left, bottom, right = _bbox(enlarged)
        height, width = bottom - top + 1, right - left + 1
        if height % 2 or width % 2:
            continue
        primitive: set[Cell] = set()
        valid = True
        for block_row in range(height // 2):
            for block_col in range(width // 2):
                block = {
                    (top + 2 * block_row + dr, left + 2 * block_col + dc)
                    for dr in range(2) for dc in range(2)
                }
                occupied = len(block & enlarged)
                if occupied not in (0, 4):
                    valid = False
                    break
                if occupied == 4:
                    primitive.add((top + block_row, left + block_col))
            if not valid:
                break
        if not valid or len(primitive) * 4 != len(enlarged):
            continue
        for dock in glyphs:
            if dock is enlarged:
                continue
            dtop, dleft, dbottom, dright = _bbox(dock)
            rectangle = {(r, c) for r in range(dtop, dbottom + 1) for c in range(dleft, dright + 1)}
            for delta_row in range(-7 * cell_size, 7 * cell_size + 1, cell_size):
                for delta_col in range(-7 * cell_size, 7 * cell_size + 1, cell_size):
                    shifted = {(row + delta_row, col + delta_col) for row, col in primitive}
                    if shifted.isdisjoint(dock) and shifted | dock == rectangle:
                        solutions.append((enlarged, dock, delta_row, delta_col))
    if len(solutions) != 1:
        raise ValueError("scale_normalized_docking_geometry")
    return solutions[0]


def _downsample_exact(component: set[Cell], scale: int = 2) -> set[Cell]:
    top, left, bottom, right = _bbox(component)
    height, width = bottom - top + 1, right - left + 1
    if height % scale or width % scale:
        raise ValueError("nonuniform_scale_block")
    primitive: set[Cell] = set()
    for block_row in range(height // scale):
        for block_col in range(width // scale):
            block = {
                (top + scale * block_row + dr, left + scale * block_col + dc)
                for dr in range(scale)
                for dc in range(scale)
            }
            occupied = len(block & component)
            if occupied not in (0, scale * scale):
                raise ValueError("nonuniform_scale_block")
            if occupied:
                primitive.add((top + block_row, left + block_col))
    if len(primitive) * scale * scale != len(component):
        raise ValueError("nonuniform_scale_block")
    return primitive


def _rotate_clockwise(cells: set[Cell]) -> set[Cell]:
    top, left, _, _ = _bbox(cells)
    relative = {(row - top, col - left) for row, col in cells}
    rotated = {(col, -row) for row, col in relative}
    min_row = min(row for row, _ in rotated)
    min_col = min(col for _, col in rotated)
    return {(row - min_row, col - min_col) for row, col in rotated}


def _multicolor_endpoint_transform(
    grid: Sequence[Sequence[int]], board_top: int, board_left: int, cell_size: int = 4
) -> tuple[set[Cell], str]:
    """Compile a mover-to-endpoint transformation across rotation, color and scale."""
    board_bottom = board_top + 7 * cell_size
    board_right = board_left + 7 * cell_size
    movers = [
        component for component in _components(grid, (11,))
        if len(component) == 14
        and all(board_top <= row < board_bottom and board_left <= col < board_right for row, col in component)
    ]
    endpoints = [
        component for component in _components(grid, (15,))
        if len(component) > 9
        and all(board_top <= row < board_bottom and board_left <= col < board_right for row, col in component)
    ]
    if len(movers) != 1 or len(endpoints) != 1:
        raise ValueError("multicolor_endpoint_geometry")
    mover, endpoint = movers[0], endpoints[0]
    primitive = _downsample_exact(endpoint)
    rotated = _rotate_clockwise(mover)
    solutions: list[tuple[int, int]] = []
    for anchor_row in range(board_top, board_bottom):
        for anchor_col in range(board_left, board_right):
            shifted = {(anchor_row + row, anchor_col + col) for row, col in rotated}
            union = shifted | primitive
            top, left, bottom, right = _bbox(union)
            rectangle = {(row, col) for row in range(top, bottom + 1) for col in range(left, right + 1)}
            if shifted.isdisjoint(primitive) and union == rectangle:
                solutions.append((anchor_row, anchor_col))
    if len(solutions) != 1:
        raise ValueError("multicolor_endpoint_geometry")
    mover_top, _, _, _ = _bbox(mover)
    goal_top, _ = solutions[0]
    delta_rows = (goal_top - mover_top) // cell_size
    if goal_top - mover_top != delta_rows * cell_size or delta_rows == 0:
        raise ValueError("multicolor_endpoint_translation")
    direction = "D" if delta_rows > 0 else "U"
    return mover, "X" + direction * abs(delta_rows) + "TS"


def _shortest_path(start: Cell, goal: Cell, blocked: set[Cell], size: int = 7) -> str:
    queue = deque([(start, "")])
    visited = {start}
    directions = ((-1, 0, "U"), (1, 0, "D"), (0, -1, "L"), (0, 1, "R"))
    while queue:
        cell, path = queue.popleft()
        if cell == goal:
            return path
        for dr, dc, direction in directions:
            candidate = cell[0] + dr, cell[1] + dc
            if (
                0 <= candidate[0] < size
                and 0 <= candidate[1] < size
                and candidate not in blocked
                and candidate not in visited
            ):
                visited.add(candidate)
                queue.append((candidate, path + direction))
    raise ValueError("unreachable_docking_translation")


def _aligned_path(start: Cell, goal: Cell, blocked: set[Cell], size: int = 7) -> str:
    """Align the subcell docking column before changing rows."""
    path = ""
    row, col = start
    horizontal = "L" if goal[1] < col else "R"
    while col != goal[1]:
        col += -1 if horizontal == "L" else 1
        if not (0 <= row < size and 0 <= col < size) or (row, col) in blocked:
            raise ValueError("unreachable_docking_translation")
        path += horizontal
    vertical = "U" if goal[0] < row else "D"
    while row != goal[0]:
        row += -1 if vertical == "U" else 1
        if not (0 <= row < size and 0 <= col < size) or (row, col) in blocked:
            raise ValueError("unreachable_docking_translation")
        path += vertical
    return path


def _selector_controls(grid: Sequence[Sequence[int]]) -> tuple[tuple[Point, str], ...]:
    height, width = len(grid), len(grid[0])
    controls: list[tuple[int, Point, str]] = []
    for purple in _components(grid, (11,)):
        top, left, bottom, right = _bbox(purple)
        if top < height - 10 or bottom - top > 2 or right - left > 2:
            continue
        mean_row = sum(row for row, _ in purple) / len(purple)
        mean_col = sum(col for _, col in purple) / len(purple)
        box_center_x = (int(mean_col) // 10) * 10 + 5
        box_center_y = height - 6
        if bottom - top <= 1 and right - left == 2:
            direction = "U" if mean_row < box_center_y else "D"
        elif right - left <= 1 and bottom - top == 2:
            direction = "L" if mean_col < box_center_x else "R"
        else:
            continue
        patch_top, patch_left = box_center_y - 3, box_center_x - 3
        zeros = [
            (row, col)
            for row in range(patch_top, patch_top + 7)
            for col in range(patch_left, patch_left + 7)
            if 0 <= row < height and 0 <= col < width and grid[row][col] == 0
        ]
        if zeros:
            probe_row, probe_col = min(zeros)
            controls.append((box_center_x, (probe_col, probe_row), direction))
    controls.sort()
    if len(controls) != 4 or {item[2] for item in controls} != {"U", "D", "L", "R"}:
        raise ValueError("selector_direction_geometry")
    return tuple((point, direction) for _, point, direction in controls)


def _multiscale_controls(grid: Sequence[Sequence[int]]) -> tuple[tuple[Point, str], ...]:
    """Decode left, grow, down, and shrink from their visible control glyphs."""
    height = len(grid)
    controls: list[tuple[int, Point, str]] = []
    for purple in _components(grid, (11,)):
        top, left, bottom, right = _bbox(purple)
        if top < height - 10:
            continue
        box_height, box_width = bottom - top + 1, right - left + 1
        if len(purple) == 1:
            label = "I"
        elif len(purple) == 25 and box_height == box_width == 5:
            label = "S"
        elif len(purple) == 6 and (box_height, box_width) == (2, 3):
            label = "D"
        elif len(purple) == 6 and (box_height, box_width) == (3, 2):
            label = "L"
        else:
            continue
        mean_col = sum(col for _, col in purple) / len(purple)
        box_center_x = (int(mean_col) // 10) * 10 + 5
        controls.append((box_center_x, (box_center_x, height - 6), label))
    controls.sort()
    if len(controls) != 4 or {item[2] for item in controls} != {"L", "S", "D", "I"}:
        raise ValueError("multiscale_control_geometry")
    return tuple((point, label) for _, point, label in controls)


def _endpoint_controls(
    grid: Sequence[Sequence[int]],
) -> tuple[tuple[Point, str, int | None], ...]:
    height = len(grid)
    controls: list[tuple[int, Point, str, int | None]] = []
    for color, label_specs in (
        (11, {(1, 1, 1): "I", (25, 5, 5): "S", (6, 2, 3): "D", (13, 5, 5): "X"}),
        (15, {(9, 3, 3): "T"}),
    ):
        for component in _components(grid, (color,)):
            top, left, bottom, right = _bbox(component)
            if top < height - 10:
                continue
            key = (len(component), bottom - top + 1, right - left + 1)
            label = label_specs.get(key)
            if label is None:
                continue
            mean_col = sum(col for _, col in component) / len(component)
            box_center_x = (int(mean_col) // 10) * 10 + 5
            controls.append((box_center_x, (box_center_x, height - 6), label, 1 if label == "T" else None))
    controls.sort()
    if len(controls) != 5 or {item[2] for item in controls} != {"I", "S", "D", "X", "T"}:
        raise ValueError("endpoint_control_geometry")
    return tuple((point, label, port) for _, point, label, port in controls)


def _bar_rows(grid: Sequence[Sequence[int]], side: str) -> tuple[tuple[Point, ...], ...]:
    width = len(grid[0])
    bars: list[Point] = []
    for component in _components(grid, (1, 5)):
        top, left, bottom, right = _bbox(component)
        horizontal = top == bottom and right - left == 2
        vertical = left == right and bottom - top == 2
        if len(component) != 3 or not (horizontal or vertical):
            continue
        center = ((left + right) // 2, (top + bottom) // 2)
        if (side == "left" and center[0] < width // 2) or (side == "right" and center[0] >= width // 2):
            bars.append(center)
    grouped: dict[int, list[Point]] = {}
    for point in bars:
        grouped.setdefault(point[1], []).append(point)
    minimum = 6 if side == "right" else 3
    rows = [tuple(sorted(points)) for _, points in sorted(grouped.items()) if len(points) >= minimum]
    if len(rows) != 6 or (side == "right" and any(len(row) != 6 for row in rows)):
        raise ValueError(f"{side}_panel_geometry")
    return tuple(rows)


def _source_bits(grid: Sequence[Sequence[int]], port: int | None = None) -> tuple[int, ...]:
    bits: list[int] = []
    for row in _bar_rows(grid, "left"):
        values = [grid[y][x] for x, y in row]
        if len(set(values)) == 1:
            value = values[0]
        elif port is not None and 0 <= port < len(values):
            value = values[port]
        else:
            raise ValueError("source_row_not_monochromatic")
        bits.append(1 if value == 5 else 0)
    return tuple(bits)


def _submit(grid: Sequence[Sequence[int]]) -> Point:
    components = _components(grid, (9,))
    if not components:
        raise ValueError("submit_geometry")
    top, left, bottom, right = _bbox(max(components, key=len))
    return ((left + right) // 2, (top + bottom) // 2)


def _close_static_path_capabilities(grid) -> SemanticCapabilityClosure:
    closed: list[str] = []

    def missing(interface: str, reason: str) -> SemanticCapabilityClosure:
        return SemanticCapabilityClosure(
            plan=None,
            closed_interfaces=tuple(closed),
            residual=SemanticResidual(interface, reason),
        )

    try:
        visible = _matrix(grid)
    except ValueError as error:
        return missing("observation.current-frame@1", str(error))
    closed.append("observation.current-frame@1")

    try:
        board_top, board_left = _find_board(visible)
    except ValueError as error:
        return missing("board.tiled-grid@1", str(error))
    closed.append("board.tiled-grid@1")

    multiscale = False
    endpoint = False
    endpoint_path = ""
    try:
        mover, _, delta_row, delta_col = _complement_translation(visible, board_top, board_left)
        closed.append("shape.docking-translation@1")
    except ValueError:
        try:
            mover, _, delta_row, delta_col = _scale_normalized_translation(
                visible, board_top, board_left
            )
            multiscale = True
            closed.append("shape.scale-normalized-docking@1")
        except ValueError as scale_error:
            board_has_endpoint_color = any(
                board_top <= row < board_top + 28 and board_left <= col < board_left + 28
                for component in _components(visible, (15,))
                for row, col in component
            )
            if not board_has_endpoint_color:
                return missing("shape.subcell-docking-pose@1", str(scale_error))
            try:
                mover, endpoint_path = _multicolor_endpoint_transform(
                    visible, board_top, board_left
                )
                endpoint = True
                closed.append("shape.multicolor-endpoint-transform@1")
            except ValueError as error:
                return missing("shape.subcell-docking-pose@1", str(error))

    mover_top, mover_left, _, _ = _bbox(mover)
    start = ((mover_top - board_top) // 4, (mover_left - board_left) // 4)
    if endpoint:
        goal = (start[0] + endpoint_path.count("D") - endpoint_path.count("U"), start[1])
    else:
        goal = (start[0] + delta_row // 4, start[1] + delta_col // 4)
    blocked: set[Cell] = set()
    for row in range(7):
        for col in range(7):
            values = [
                visible[board_top + 4 * row + dr][board_left + 4 * col + dc]
                for dr in range(4)
                for dc in range(4)
            ]
            if values.count(6) >= 8:
                blocked.add((row, col))
    blocked.discard(start)
    blocked.discard(goal)
    closed.append("board.route-problem@1")

    try:
        if endpoint:
            endpoint_controls = _endpoint_controls(visible)
            controls = tuple((point, label) for point, label, _ in endpoint_controls)
            probe_ports = tuple(port for _, _, port in endpoint_controls)
            closed.append("port.active-source-projection@1")
        else:
            controls = _multiscale_controls(visible) if multiscale else _selector_controls(visible)
            probe_ports = tuple(None for _ in controls)
    except ValueError as error:
        return missing("control.direction-role@1", str(error))
    closed.append("control.direction-role@1")

    try:
        targets = _bar_rows(visible, "right")
    except ValueError as error:
        return missing("panel.target-grid@1", str(error))
    closed.append("panel.target-grid@1")

    try:
        submit = _submit(visible)
    except ValueError as error:
        return missing("control.submit@1", str(error))
    closed.append("control.submit@1")

    try:
        path = endpoint_path if endpoint else (
            "I" + _aligned_path(start, goal, blocked)
            if multiscale
            else _shortest_path(start, goal, blocked)
        )
    except ValueError as error:
        return missing("board.valid-route@1", str(error))
    if not targets or len(path) != len(targets[0]):
        return missing("program.temporal-columns@1", "path_target_arity")

    plan = SemanticPathPlan(
        path=path,
        probes=tuple(point for point, _ in controls),
        probe_directions=tuple(direction for _, direction in controls),
        targets=targets,
        submit=submit,
        probe_ports=probe_ports,
    )
    closed.append("program.temporal-columns@1")
    return SemanticCapabilityClosure(
        plan=plan,
        closed_interfaces=tuple(closed),
        residual=None,
    )


def close_path_capabilities(grid, discovery=None) -> SemanticCapabilityClosure:
    static = _close_static_path_capabilities(grid)
    if static.plan is not None or discovery is None:
        return static
    result = discovery.close(grid, static.residual)
    if isinstance(result, UnknownResidual):
        return SemanticCapabilityClosure(
            plan=None,
            closed_interfaces=static.closed_interfaces,
            residual=SemanticResidual(result.missing_interface, result.reason),
        )
    if not isinstance(result, SemanticDiscoveryResult):
        raise TypeError("discovery_must_return_semantic_result_or_unknown")
    if result.capability.interface_id != "program.protected-future-quotient@1":
        return SemanticCapabilityClosure(
            plan=None,
            closed_interfaces=static.closed_interfaces,
            residual=SemanticResidual(
                "target.projection@1",
                "unsupported_compiled_interface",
            ),
        )
    if result.binding_id != _discovery_binding_id(result.capability, result.plan):
        return SemanticCapabilityClosure(
            plan=None,
            closed_interfaces=static.closed_interfaces,
            residual=SemanticResidual(
                "adapter.semantic-binding@1",
                "compiled_capability_plan_binding_mismatch",
            ),
        )
    if tuple(result.plan.path) != result.capability.program:
        return SemanticCapabilityClosure(
            plan=None,
            closed_interfaces=static.closed_interfaces,
            residual=SemanticResidual(
                "adapter.semantic-binding@1",
                "compiled_program_plan_path_mismatch",
            ),
        )
    return SemanticCapabilityClosure(
        plan=result.plan,
        closed_interfaces=static.closed_interfaces + (result.capability.interface_id,),
        residual=None,
    )


def infer_path_program(grid) -> SemanticPathPlan:
    closure = close_path_capabilities(grid)
    if closure.plan is None:
        raise ValueError(closure.residual.reason)
    return closure.plan


@dataclass
class SemanticPathSession:
    plan: SemanticPathPlan
    phase: str = "probe"
    probe_index: int = 0
    pending_probe: str | None = None
    codes: dict[str, tuple[int, ...]] = field(default_factory=dict)
    writes: list[tuple[Point, int]] = field(default_factory=list)
    last_action_kind: str | None = None
    last_write_value: int | None = None

    @classmethod
    def start(cls, grid, discovery=None) -> "SemanticPathSession":
        closure = close_path_capabilities(grid, discovery=discovery)
        if closure.plan is None:
            raise ValueError(closure.residual.reason)
        return cls(closure.plan)

    def _record_pending_probe(self, grid) -> None:
        if self.pending_probe is not None:
            index = self.plan.probe_directions.index(self.pending_probe)
            port = self.plan.probe_ports[index] if self.plan.probe_ports else None
            self.codes[self.pending_probe] = _source_bits(_matrix(grid), port=port)
            self.pending_probe = None

    def _prepare_writes(self, grid) -> None:
        if set(self.codes) != set(self.plan.probe_directions):
            raise ValueError("incomplete_direction_codebook")
        columns = [self.codes[direction] for direction in self.plan.path]
        if len(columns) != len(self.plan.targets[0]):
            raise ValueError("path_target_arity")
        visible = _matrix(grid)
        for row_index, target_row in enumerate(self.plan.targets):
            for col_index, point in enumerate(target_row):
                desired = columns[col_index][row_index]
                current = 1 if visible[point[1]][point[0]] == 5 else 0
                if current != desired:
                    self.writes.append((point, desired))

    def next_action(self, grid) -> Point:
        if self.phase == "done":
            raise StopIteration("semantic path session is complete")
        if self.phase == "probe":
            self._record_pending_probe(grid)
            if self.probe_index < len(self.plan.probes):
                point = self.plan.probes[self.probe_index]
                self.pending_probe = self.plan.probe_directions[self.probe_index]
                self.probe_index += 1
                self.last_action_kind = "probe"
                return point
            self._prepare_writes(grid)
            self.phase = "write" if self.writes else "submit"
        if self.phase == "write":
            point, value = self.writes.pop(0)
            self.last_action_kind = "write"
            self.last_write_value = value
            if not self.writes:
                self.phase = "submit"
            return point
        self.phase = "done"
        self.last_action_kind = "submit"
        return self.plan.submit
