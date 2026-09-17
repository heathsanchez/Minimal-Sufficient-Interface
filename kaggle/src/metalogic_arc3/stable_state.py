from __future__ import annotations

import hashlib
from typing import Iterable

from .memory_graph import ActionKey


Grid = tuple[tuple[int, ...], ...]
ShapeKey = tuple[int, int, int]


class StableStateQuotient:
    """A bounded, frozen quotient for recurrent same-level raster volatility.

    The quotient is deliberately conservative. A pixel becomes ignorable only
    after a fixed evidence horizon, when it changed frequently and under more
    than one distinct intervention. Once a shape/level mask is frozen it never
    changes, so learned state identities remain stable.
    """

    def __init__(
        self,
        activation_transitions: int = 64,
        min_change_rate: float = 0.75,
        min_action_classes: int = 2,
    ) -> None:
        if activation_transitions < 1:
            raise ValueError("positive activation transition bound required")
        if not 0.0 <= float(min_change_rate) <= 1.0:
            raise ValueError("change rate must lie in [0,1]")
        if min_action_classes < 1:
            raise ValueError("positive intervention diversity required")
        self.activation_transitions = int(activation_transitions)
        self.min_change_rate = float(min_change_rate)
        self.min_action_classes = int(min_action_classes)
        self._transitions: dict[ShapeKey, int] = {}
        self._changes: dict[ShapeKey, dict[tuple[int, int], int]] = {}
        self._actions: dict[
            ShapeKey, dict[tuple[int, int], set[ActionKey]]
        ] = {}
        self._masks: dict[ShapeKey, tuple[tuple[int, int], ...]] = {}

    @staticmethod
    def _shape(level: int, grid: Grid) -> ShapeKey | None:
        if not grid:
            return None
        width = len(grid[0])
        if not width or any(len(row) != width for row in grid):
            return None
        return int(level), len(grid), width

    def observe(
        self,
        level: int,
        before: Grid,
        after: Grid,
        action: ActionKey,
    ) -> None:
        before_key = self._shape(level, before)
        after_key = self._shape(level, after)
        if before_key is None or before_key != after_key:
            return
        key = before_key
        if key in self._masks:
            return

        self._transitions[key] = self._transitions.get(key, 0) + 1
        changes = self._changes.setdefault(key, {})
        actions = self._actions.setdefault(key, {})
        action_key = tuple(action)

        for y, (left_row, right_row) in enumerate(zip(before, after)):
            for x, (left, right) in enumerate(zip(left_row, right_row)):
                if left == right:
                    continue
                point = (x, y)
                changes[point] = changes.get(point, 0) + 1
                actions.setdefault(point, set()).add(action_key)

        n = self._transitions[key]
        if n < self.activation_transitions:
            return

        mask = tuple(
            sorted(
                point
                for point, count in changes.items()
                if count / n >= self.min_change_rate
                and len(actions.get(point, ())) >= self.min_action_classes
            )
        )
        self._masks[key] = mask

    def active(self, level: int, height: int, width: int) -> bool:
        return (int(level), int(height), int(width)) in self._masks

    def masked_positions(
        self, level: int, height: int, width: int
    ) -> tuple[tuple[int, int], ...]:
        return self._masks.get((int(level), int(height), int(width)), ())

    def digest(self, level: int, grid: Grid) -> str:
        key = self._shape(level, grid)
        mask = set(self._masks.get(key, ())) if key is not None else set()
        canonical = tuple(
            tuple(None if (x, y) in mask else int(value) for x, value in enumerate(row))
            for y, row in enumerate(grid)
        )
        return hashlib.sha256(repr(canonical).encode()).hexdigest()

    @property
    def active_contexts(self) -> int:
        return len(self._masks)

    @property
    def masked_pixel_count(self) -> int:
        return sum(len(mask) for mask in self._masks.values())
