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
        self._local: dict[tuple[ComponentKey, tuple[int, int], ActionKey], Counter[tuple[int, int]]] = {}

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
        before_components = _components(before)
        after_components = _components(after)

        # Local applicability evidence is kept even for a no-move outcome.
        # Ambiguous component multiplicity stays UNKNOWN.
        for component_key, origins in before_components.items():
            targets = after_components.get(component_key, ())
            if len(origins) != 1 or len(targets) != 1:
                continue
            origin = origins[0]
            target = targets[0]
            local = self._local.setdefault(
                (component_key, origin, action_key), Counter()
            )
            local[target] += 1

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

    @property
    def blocked_local_count(self) -> int:
        count = 0
        for (component_key, origin, action), outcomes in self._local.items():
            vector = self._reliable_vector(component_key, action)
            if vector is None or not outcomes:
                continue
            target, support = outcomes.most_common(1)[0]
            if target == origin and support == sum(outcomes.values()):
                count += 1
        return count

    def _local_target(
        self,
        component_key: ComponentKey,
        origin: tuple[int, int],
        action: ActionKey,
    ) -> tuple[int, int] | None:
        outcomes = self._local.get((component_key, origin, self._action(action)))
        if not outcomes:
            return None
        target, support = outcomes.most_common(1)[0]
        if support != sum(outcomes.values()):
            return None
        return target

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

        def in_bounds(component_key: ComponentKey, origin: tuple[int, int]) -> bool:
            return all(
                0 <= origin[0] + sx < width and 0 <= origin[1] + sy < height
                for sx, sy in component_key[1]
            )

        for component_key, origins in sorted(components.items(), key=repr):
            if len(origins) != 1:
                continue
            start = origins[0]
            controls = [
                (action, vector)
                for action in actions
                if (vector := self._reliable_vector(component_key, action)) is not None
            ]
            if len(controls) < 2:
                continue
            controls.sort(
                key=lambda row: tuple(-1 if value is None else int(value) for value in row[0])
            )

            # Search the actually observed local transition graph for the
            # nearest position that still has an untried modeled control.
            queue: list[tuple[tuple[int, int], ActionKey | None]] = [(start, None)]
            seen_positions = {start}
            index = 0
            while index < len(queue) and len(seen_positions) <= 256:
                origin, first_action = queue[index]
                index += 1

                frontier: list[tuple[int, tuple[int, int, int], ActionKey]] = []
                for action, (dx, dy) in controls:
                    predicted = (origin[0] + dx, origin[1] + dy)
                    if not in_bounds(component_key, predicted):
                        continue
                    local = self._local_target(component_key, origin, action)
                    if local is None:
                        visits = int(self._positions.get(component_key, Counter()).get(predicted, 0))
                        action_sort = tuple(
                            -1 if value is None else int(value) for value in action
                        )
                        frontier.append((visits, action_sort, action))
                        continue
                    if local == origin:
                        # Position-scoped obstruction: preserve the global
                        # action->motion law but do not retry it here.
                        continue
                    if local not in seen_positions:
                        seen_positions.add(local)
                        queue.append((local, action if first_action is None else first_action))

                if frontier:
                    frontier.sort(key=lambda row: row[:2])
                    chosen = frontier[0][2]
                    return chosen if first_action is None else first_action

        return None
