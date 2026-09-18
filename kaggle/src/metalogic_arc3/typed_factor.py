from __future__ import annotations

from collections import Counter
import hashlib
from typing import Any

from .memory_graph import ActionKey


Grid = tuple[tuple[int, ...], ...]
ShapeKey = tuple[int, int, int]
ScalarSignature = tuple[tuple[int, int], ...]


class BorderCompositionFactor:
    """Learn a typed border composition factor from transition evidence.

    The factor does not erase a band. It identifies a small palette whose
    *counts* evolve monotonically across multiple interventions, then canonicalizes
    only palette identity inside that band. Non-palette pixels and support
    geometry remain in the world state, while the exact palette histogram is
    retained separately as a scalar/resource ledger.
    """

    def __init__(
        self,
        activation_transitions: int = 24,
        history_limit: int = 128,
        min_changes: int = 8,
        min_action_classes: int = 2,
        min_sign_consistency: float = 0.9,
        min_projection_compression: float = 2.0,
        ledger_limit: int = 2048,
    ) -> None:
        if activation_transitions < 1 or history_limit < activation_transitions:
            raise ValueError("invalid evidence bounds")
        if min_changes < 1 or min_action_classes < 1 or ledger_limit < 1:
            raise ValueError("positive factor bounds required")
        if not 0.0 <= min_sign_consistency <= 1.0:
            raise ValueError("sign consistency must lie in [0,1]")
        if min_projection_compression < 1.0:
            raise ValueError("compression threshold must be >= 1")
        self.activation_transitions = int(activation_transitions)
        self.history_limit = int(history_limit)
        self.min_changes = int(min_changes)
        self.min_action_classes = int(min_action_classes)
        self.min_sign_consistency = float(min_sign_consistency)
        self.min_projection_compression = float(min_projection_compression)
        self.ledger_limit = int(ledger_limit)

        self._frames: dict[ShapeKey, list[Grid]] = {}
        self._actions: dict[ShapeKey, list[ActionKey]] = {}
        self._factors: dict[ShapeKey, dict[str, Any]] = {}
        self._closed: set[ShapeKey] = set()
        self._ledger: list[dict[str, Any]] = []

    @staticmethod
    def _shape(level: int, grid: Grid) -> ShapeKey | None:
        if not grid:
            return None
        width = len(grid[0])
        if not width or any(len(row) != width for row in grid):
            return None
        return int(level), len(grid), width

    @staticmethod
    def _band_points(height: int, width: int, side: str, depth: int) -> tuple[tuple[int, int], ...]:
        depth = max(1, int(depth))
        if side == "top":
            return tuple((x, y) for y in range(min(depth, height)) for x in range(width))
        if side == "bottom":
            return tuple((x, y) for y in range(max(0, height-depth), height) for x in range(width))
        if side == "left":
            return tuple((x, y) for x in range(min(depth, width)) for y in range(height))
        if side == "right":
            return tuple((x, y) for x in range(max(0, width-depth), width) for y in range(height))
        raise ValueError("unknown side")

    @staticmethod
    def _digest(grid: Grid) -> str:
        return hashlib.sha256(repr(grid).encode()).hexdigest()

    @staticmethod
    def _project(grid: Grid, points: set[tuple[int, int]], palette: set[int]) -> tuple[tuple[Any, ...], ...]:
        return tuple(
            tuple(
                ("factor",) if (x, y) in points and int(value) in palette else int(value)
                for x, value in enumerate(row)
            )
            for y, row in enumerate(grid)
        )

    def _evaluate(self, key: ShapeKey) -> None:
        level, height, width = key
        frames = self._frames.get(key, [])
        actions = self._actions.get(key, [])
        if len(actions) < self.activation_transitions or len(frames) != len(actions) + 1:
            return

        raw_unique = len({self._digest(frame) for frame in frames})
        if raw_unique < 2:
            return

        best: tuple[float, int, str, tuple[int, ...], tuple[tuple[int, int], ...]] | None = None
        max_depth = max(height, width)
        depths = sorted({d for d in (1, 2, 3, 4, 6, 8) if d <= max_depth})

        for side in ("top", "bottom", "left", "right"):
            for depth in depths:
                points_tuple = self._band_points(height, width, side, depth)
                if not points_tuple:
                    continue
                points = set(points_tuple)
                colors = sorted({frame[y][x] for frame in frames for x, y in points})
                palette: list[int] = []

                for color in colors:
                    values = [
                        sum(1 for x, y in points_tuple if frame[y][x] == color)
                        for frame in frames
                    ]
                    changed = [(i, b-a) for i, (a, b) in enumerate(zip(values, values[1:])) if b != a]
                    if len(changed) < self.min_changes:
                        continue
                    signs = Counter(1 if delta > 0 else -1 for _, delta in changed)
                    if max(signs.values()) / len(changed) < self.min_sign_consistency:
                        continue
                    action_classes = {actions[i][0] for i, _delta in changed}
                    if len(action_classes) < self.min_action_classes:
                        continue
                    palette.append(int(color))

                if len(palette) < 2:
                    continue

                palette_set = set(palette)
                projected = {
                    hashlib.sha256(repr(self._project(frame, points, palette_set)).encode()).hexdigest()
                    for frame in frames
                }
                compression = raw_unique / max(1, len(projected))
                if compression < self.min_projection_compression:
                    continue

                candidate = (
                    compression,
                    -len(points_tuple),
                    side,
                    tuple(sorted(palette)),
                    points_tuple,
                )
                if best is None or candidate[:2] > best[:2]:
                    best = candidate

        if best is not None:
            compression, _negative_size, side, palette, points = best
            # Recover the selected depth from the point geometry.
            if side in ("top", "bottom"):
                depth = len(points) // width
            else:
                depth = len(points) // height
            self._factors[key] = {
                "side": side,
                "depth": int(depth),
                "palette": tuple(palette),
                "points": tuple(points),
                "compression": float(compression),
            }
            return

        if len(actions) >= self.history_limit:
            self._closed.add(key)

    def observe(self, level: int, before: Grid, after: Grid, action: ActionKey) -> None:
        before_key = self._shape(level, before)
        after_key = self._shape(level, after)
        if before_key is None or before_key != after_key:
            return
        key = before_key
        if key in self._factors or key in self._closed:
            return

        frames = self._frames.setdefault(key, [before])
        actions = self._actions.setdefault(key, [])
        if frames[-1] != before:
            # Discontinuities (RESET/camera replacement) do not fabricate a
            # continuous factor history. Start a fresh bounded window.
            frames[:] = [before]
            actions[:] = []
        frames.append(after)
        actions.append(tuple(action))
        if len(actions) > self.history_limit:
            frames.pop(0)
            actions.pop(0)
        self._evaluate(key)

    def active(self, level: int, height: int, width: int) -> bool:
        return (int(level), int(height), int(width)) in self._factors

    def factor(self, level: int, height: int, width: int) -> dict[str, Any] | None:
        row = self._factors.get((int(level), int(height), int(width)))
        return None if row is None else dict(row)

    def side(self, level: int, height: int, width: int) -> str | None:
        row = self._factors.get((int(level), int(height), int(width)))
        return None if row is None else str(row["side"])

    def palette(self, level: int, height: int, width: int) -> tuple[int, ...]:
        row = self._factors.get((int(level), int(height), int(width)))
        return () if row is None else tuple(row["palette"])

    def world_digest(self, level: int, grid: Grid) -> str:
        key = self._shape(level, grid)
        row = self._factors.get(key) if key is not None else None
        if row is None:
            return self._digest(grid)
        projected = self._project(grid, set(row["points"]), set(row["palette"]))
        return hashlib.sha256(repr(projected).encode()).hexdigest()

    def scalar_signature(self, level: int, grid: Grid) -> ScalarSignature:
        key = self._shape(level, grid)
        row = self._factors.get(key) if key is not None else None
        if row is None:
            return ()
        points = tuple(row["points"])
        palette = set(row["palette"])
        counts = Counter(
            int(grid[y][x])
            for x, y in points
            if int(grid[y][x]) in palette
        )
        return tuple(sorted((color, counts.get(color, 0)) for color in palette))

    def note_transition(
        self,
        source: str,
        action: ActionKey,
        target: str,
        before: ScalarSignature,
        after: ScalarSignature,
    ) -> None:
        if not before and not after:
            return
        self._ledger.append({
            "source": str(source),
            "action": tuple(action),
            "target": str(target),
            "before": tuple(before),
            "after": tuple(after),
        })
        if len(self._ledger) > self.ledger_limit:
            del self._ledger[: len(self._ledger)-self.ledger_limit]

    def transitions(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(row) for row in self._ledger)

    @property
    def active_contexts(self) -> int:
        return len(self._factors)

    @property
    def projection_compressions(self) -> tuple[float, ...]:
        return tuple(float(row["compression"]) for row in self._factors.values())
