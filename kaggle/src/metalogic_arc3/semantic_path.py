from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Iterable, Sequence


Cell = tuple[int, int]
Point = tuple[int, int]


@dataclass(frozen=True)
class SemanticPathPlan:
    path: str
    probes: tuple[Point, ...]
    probe_directions: tuple[str, ...]
    targets: tuple[tuple[Point, ...], ...]
    submit: Point


def _matrix(value) -> list[list[int]]:
    """Return the visible 2-D integer layer without depending on arcengine."""
    if hasattr(value, "frame"):
        value = value.frame
    if hasattr(value, "tolist"):
        value = value.tolist()
    while (
        isinstance(value, (list, tuple))
        and value
        and isinstance(value[0], (list, tuple))
        and value[0]
        and isinstance(value[0][0], (list, tuple))
    ):
        value = value[0]
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
            if not {4, 5, 6}.issubset(flat) or not flat.issubset({4, 5, 6, 11}):
                continue
            checker = sum(
                dominant[r][c] in (4, 5)
                and dominant[r][c] == (5 if (r + c) % 2 == 0 else 4)
                for r in range(7)
                for c in range(7)
            )
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


def _selector_controls(grid: Sequence[Sequence[int]]) -> tuple[tuple[Point, str], ...]:
    height, width = len(grid), len(grid[0])
    controls: list[tuple[int, Point, str]] = []
    for purple in _components(grid, (11,)):
        top, left, bottom, right = _bbox(purple)
        if top < height - 10 or bottom - top > 2 or right - left > 2:
            continue
        mean_row = sum(row for row, _ in purple) / len(purple)
        mean_col = sum(col for _, col in purple) / len(purple)
        if bottom - top <= 1 and right - left == 2:
            direction = "U" if mean_row < height - 6 else "D"
        elif right - left <= 1 and bottom - top == 2:
            direction = "L" if left < width // 2 else "R"
        else:
            continue
        if direction == "D":
            patch_top, patch_left = bottom - 6, round(mean_col) - 3
        elif direction == "U":
            patch_top, patch_left = top, round(mean_col) - 3
        elif direction == "L":
            patch_top, patch_left = round(mean_row) - 3, left
        else:
            patch_top, patch_left = round(mean_row) - 3, right - 6
        zeros = [
            (row, col)
            for row in range(patch_top, patch_top + 7)
            for col in range(patch_left, patch_left + 7)
            if 0 <= row < height and 0 <= col < width and grid[row][col] == 0
        ]
        if zeros:
            probe_row, probe_col = min(zeros)
            controls.append((patch_left, (probe_col, probe_row), direction))
    controls.sort()
    if len(controls) != 4 or {item[2] for item in controls} != {"U", "D", "L", "R"}:
        raise ValueError("selector_direction_geometry")
    return tuple((point, direction) for _, point, direction in controls)


def _bar_rows(grid: Sequence[Sequence[int]], side: str) -> tuple[tuple[Point, ...], ...]:
    width = len(grid[0])
    bars: list[Point] = []
    for component in _components(grid, (1, 5)):
        top, left, bottom, right = _bbox(component)
        if len(component) != 3 or top != bottom or right - left != 2:
            continue
        center = (left + 1, top)
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


def _source_bits(grid: Sequence[Sequence[int]]) -> tuple[int, ...]:
    bits: list[int] = []
    for row in _bar_rows(grid, "left"):
        colors = {grid[y][x] for x, y in row}
        if len(colors) != 1:
            raise ValueError("source_row_not_monochromatic")
        bits.append(1 if colors.pop() == 5 else 0)
    return tuple(bits)


def _submit(grid: Sequence[Sequence[int]]) -> Point:
    components = _components(grid, (9,))
    if not components:
        raise ValueError("submit_geometry")
    top, left, bottom, right = _bbox(max(components, key=len))
    return ((left + right) // 2, (top + bottom) // 2)


def infer_path_program(grid) -> SemanticPathPlan:
    visible = _matrix(grid)
    board_top, board_left = _find_board(visible)
    mover, _, delta_row, delta_col = _complement_translation(visible, board_top, board_left)
    mover_top, mover_left, _, _ = _bbox(mover)
    start = ((mover_top - board_top) // 4, (mover_left - board_left) // 4)
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
    controls = _selector_controls(visible)
    return SemanticPathPlan(
        path=_shortest_path(start, goal, blocked),
        probes=tuple(point for point, _ in controls),
        probe_directions=tuple(direction for _, direction in controls),
        targets=_bar_rows(visible, "right"),
        submit=_submit(visible),
    )


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
    def start(cls, grid) -> "SemanticPathSession":
        return cls(infer_path_program(grid))

    def _record_pending_probe(self, grid) -> None:
        if self.pending_probe is not None:
            self.codes[self.pending_probe] = _source_bits(_matrix(grid))
            self.pending_probe = None

    def _prepare_writes(self, grid) -> None:
        if set(self.codes) != {"U", "D", "L", "R"}:
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
