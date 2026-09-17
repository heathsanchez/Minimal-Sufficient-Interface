from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from .memory_graph import ActionKey

Grid = tuple[tuple[int, ...], ...]
Shape = tuple[tuple[int, int], ...]
ComponentKey = tuple[int, Shape]


@dataclass(frozen=True)
class Transport:
    component_key: ComponentKey
    origin_before: tuple[int, int]
    origin_after: tuple[int, int]
    dx: int
    dy: int
    area: int


def _components(grid: Grid) -> dict[ComponentKey, list[tuple[int, int]]]:
    if not grid:
        return {}
    height, width = len(grid), len(grid[0])
    if not width or any(len(row) != width for row in grid):
        return {}
    seen: set[tuple[int, int]] = set()
    groups: dict[ComponentKey, list[tuple[int, int]]] = {}
    for y in range(height):
        for x in range(width):
            if (x, y) in seen:
                continue
            value = int(grid[y][x])
            stack = [(x, y)]
            seen.add((x, y))
            cells: list[tuple[int, int]] = []
            while stack:
                px, py = stack.pop()
                cells.append((px, py))
                for nx, ny in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    if (
                        0 <= nx < width
                        and 0 <= ny < height
                        and (nx, ny) not in seen
                        and int(grid[ny][nx]) == value
                    ):
                        seen.add((nx, ny))
                        stack.append((nx, ny))
            ox = min(px for px, _ in cells)
            oy = min(py for _, py in cells)
            shape: Shape = tuple(sorted((px - ox, py - oy) for px, py in cells))
            groups.setdefault((value, shape), []).append((ox, oy))
    return groups


def extract_transports(before: Grid, after: Grid) -> tuple[Transport, ...]:
    """Return exact, unambiguous translated connected components.

    Matching is intentionally conservative: a component key must occur exactly
    once before and once after. Multiple identical components stay UNKNOWN
    rather than choosing a pairing.
    """
    if len(before) != len(after):
        return ()
    if before and after and len(before[0]) != len(after[0]):
        return ()
    left = _components(before)
    right = _components(after)
    out: list[Transport] = []
    for key, before_origins in left.items():
        after_origins = right.get(key, ())
        if len(before_origins) != 1 or len(after_origins) != 1:
            continue
        origin_before = before_origins[0]
        origin_after = after_origins[0]
        dx = origin_after[0] - origin_before[0]
        dy = origin_after[1] - origin_before[1]
        if dx == 0 and dy == 0:
            continue
        out.append(
            Transport(
                component_key=key,
                origin_before=origin_before,
                origin_after=origin_after,
                dx=dx,
                dy=dy,
                area=len(key[1]),
            )
        )
    return tuple(sorted(out, key=repr))


class MotionMemory:
    """Bounded exact evidence for action-conditioned component transport."""

    def __init__(self, min_support: int = 2, min_dominance: float = 0.8) -> None:
        if min_support < 1:
            raise ValueError("positive motion support required")
        if not 0.0 < float(min_dominance) <= 1.0:
            raise ValueError("motion dominance must lie in (0,1]")
        self.min_support = int(min_support)
        self.min_dominance = float(min_dominance)
        self._vectors: dict[tuple[ComponentKey, ActionKey], Counter[tuple[int, int]]] = {}
        self._positions: dict[ComponentKey, Counter[tuple[int, int]]] = {}

    @staticmethod
    def _action(value: ActionKey | Iterable[int | None]) -> ActionKey:
        action_id, x, y = tuple(value)
        return (
            int(action_id),
            None if x is None else int(x),
            None if y is None else int(y),
        )

    def record(self, action: ActionKey, before: Grid, after: Grid) -> None:
        action_key = self._action(action)
        for row in extract_transports(before, after):
            counts = self._vectors.setdefault((row.component_key, action_key), Counter())
            counts[(row.dx, row.dy)] += 1
            positions = self._positions.setdefault(row.component_key, Counter())
            positions[row.origin_before] += 1
            positions[row.origin_after] += 1

    def _reliable_vector(
        self, component_key: ComponentKey, action: ActionKey
    ) -> tuple[int, int] | None:
        counts = self._vectors.get((component_key, self._action(action)))
        if not counts:
            return None
        vector, support = counts.most_common(1)[0]
        total = sum(counts.values())
        if support < self.min_support or support / total < self.min_dominance:
            return None
        return vector

    @property
    def reliable_control_count(self) -> int:
        return sum(
            self._reliable_vector(component_key, action) is not None
            for component_key, action in self._vectors
        )

    def recommend(
        self,
        grid: Grid,
        legal_actions: Iterable[ActionKey],
    ) -> ActionKey | None:
        if not grid:
            return None
        height, width = len(grid), len(grid[0])
        components = _components(grid)
        actions = tuple(self._action(action) for action in legal_actions)
        candidates: list[tuple[int, int, tuple[int, int, int], ActionKey]] = []

        for component_key, origins in components.items():
            if len(origins) != 1:
                continue
            origin = origins[0]
            controls: list[tuple[ActionKey, tuple[int, int]]] = []
            for action in actions:
                vector = self._reliable_vector(component_key, action)
                if vector is not None:
                    controls.append((action, vector))
            # A controllable coordinate needs alternatives. One repeated action
            # is evidence of transport, not yet a frontier-control system.
            if len(controls) < 2:
                continue
            shape = component_key[1]
            seen = self._positions.get(component_key, Counter())
            for action, (dx, dy) in controls:
                predicted = (origin[0] + dx, origin[1] + dy)
                if any(
                    not (0 <= predicted[0] + sx < width and 0 <= predicted[1] + sy < height)
                    for sx, sy in shape
                ):
                    continue
                visits = int(seen.get(predicted, 0))
                action_sort = tuple(-1 if value is None else int(value) for value in action)
                candidates.append((visits, abs(dx) + abs(dy), action_sort, action))

        if not candidates:
            return None
        candidates.sort(key=lambda row: row[:3])
        # Do not displace generic acquisition unless a modeled control reaches
        # a component position not yet witnessed for this transport class.
        if candidates[0][0] > 0:
            return None
        return candidates[0][3]
