from __future__ import annotations

from collections import Counter
import hashlib
from typing import Any

from .memory_graph import ActionKey


Grid = tuple[tuple[int, ...], ...]
ShapeKey = tuple[int, int, int]


class BorderScalarFactor:
    """Evidence-admitted border scalar with reconstructive transition buffer.

    A factor is admitted only when:
    * a border-band color count moves with high directional consistency;
    * those changes occur under multiple intervention classes; and
    * removing that border band measurably increases observed-state recurrence.

    The border scalar is retained separately; only the learned consequence graph
    may use the projected world identity. Exact .mg contexts remain untouched.
    """

    def __init__(
        self,
        activation_transitions: int = 96,
        min_changes: int = 8,
        min_action_classes: int = 2,
        min_sign_consistency: float = 0.9,
        min_projection_compression: float = 2.0,
        max_depth: int = 8,
        buffer_limit: int = 512,
    ) -> None:
        if min(activation_transitions, min_changes, min_action_classes, max_depth, buffer_limit) < 1:
            raise ValueError("positive factor bounds required")
        if not 0.0 <= min_sign_consistency <= 1.0:
            raise ValueError("sign consistency must lie in [0,1]")
        if min_projection_compression < 1.0:
            raise ValueError("compression threshold must be >= 1")
        self.activation_transitions = int(activation_transitions)
        self.min_changes = int(min_changes)
        self.min_action_classes = int(min_action_classes)
        self.min_sign_consistency = float(min_sign_consistency)
        self.min_projection_compression = float(min_projection_compression)
        self.max_depth = int(max_depth)
        self.buffer_limit = int(buffer_limit)
        self._buffers: dict[ShapeKey, list[dict[str, Any]]] = {}
        self._candidates: dict[ShapeKey, dict[str, Any] | None] = {}

    @staticmethod
    def _shape(level: int, grid: Grid) -> ShapeKey | None:
        if not grid:
            return None
        width = len(grid[0])
        if width < 1 or any(len(row) != width for row in grid):
            return None
        return int(level), len(grid), width

    @staticmethod
    def _digest(grid: Grid, mask: set[tuple[int, int]] | None = None) -> str:
        mask = mask or set()
        canonical = tuple(
            tuple(None if (x, y) in mask else int(value) for x, value in enumerate(row))
            for y, row in enumerate(grid)
        )
        return hashlib.sha256(repr(canonical).encode()).hexdigest()

    @staticmethod
    def _band(height: int, width: int, side: str, depth: int) -> tuple[tuple[int, int], ...]:
        depth = max(1, int(depth))
        if side == "top":
            return tuple((x, y) for y in range(min(depth, height)) for x in range(width))
        if side == "bottom":
            return tuple((x, y) for y in range(max(0, height - depth), height) for x in range(width))
        if side == "left":
            return tuple((x, y) for x in range(min(depth, width)) for y in range(height))
        if side == "right":
            return tuple((x, y) for x in range(max(0, width - depth), width) for y in range(height))
        raise ValueError("unknown border side")

    def observe(
        self,
        level: int,
        before: Grid,
        after: Grid,
        action: ActionKey,
        *,
        descriptor: str,
        history: str,
        terminal: bool,
    ) -> None:
        before_key = self._shape(level, before)
        after_key = self._shape(level, after)
        if before_key is None or before_key != after_key:
            return
        key = before_key
        rows = self._buffers.setdefault(key, [])
        rows.append(
            {
                "before": before,
                "after": after,
                "action": tuple(action),
                "descriptor": str(descriptor),
                "history": str(history),
                "terminal": bool(terminal),
            }
        )
        if len(rows) > self.buffer_limit:
            del rows[: len(rows) - self.buffer_limit]
        if key not in self._candidates and len(rows) >= self.activation_transitions:
            self._candidates[key] = self._infer(key, rows)

    def _infer(
        self, key: ShapeKey, rows: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        _level, height, width = key
        frames = [rows[0]["before"]] + [row["after"] for row in rows]
        raw_unique = len({self._digest(grid) for grid in frames})
        colors = sorted({value for grid in frames for row in grid for value in row})
        best: tuple[tuple[Any, ...], dict[str, Any]] | None = None

        for side in ("top", "bottom", "left", "right"):
            max_depth = min(self.max_depth, height if side in ("top", "bottom") else width)
            for depth in range(1, max_depth + 1):
                band = self._band(height, width, side, depth)
                mask = set(band)
                projected_unique = len({self._digest(grid, mask) for grid in frames})
                compression = raw_unique / max(1, projected_unique)
                if compression < self.min_projection_compression:
                    continue

                for color in colors:
                    values = [
                        sum(int(grid[y][x] == color) for x, y in band)
                        for grid in frames
                    ]
                    deltas = [b - a for a, b in zip(values, values[1:])]
                    changed = [(i, delta) for i, delta in enumerate(deltas) if delta]
                    if len(changed) < self.min_changes:
                        continue
                    action_ids = {
                        int(rows[i]["action"][0])
                        for i, _delta in changed
                        if int(rows[i]["action"][0]) != 0
                    }
                    if len(action_ids) < self.min_action_classes:
                        continue
                    signs = Counter(1 if delta > 0 else -1 for _i, delta in changed)
                    direction, sign_n = signs.most_common(1)[0]
                    consistency = sign_n / len(changed)
                    if consistency < self.min_sign_consistency:
                        continue
                    magnitudes = Counter(abs(delta) for _i, delta in changed)
                    modal_delta, modal_n = magnitudes.most_common(1)[0]
                    modal_fraction = modal_n / len(changed)

                    candidate = {
                        "side": side,
                        "depth": int(depth),
                        "color": int(color),
                        "direction": int(direction),
                        "changes": len(changed),
                        "action_classes": len(action_ids),
                        "sign_consistency": consistency,
                        "modal_abs_delta": int(modal_delta),
                        "modal_fraction": modal_fraction,
                        "compression": compression,
                        "raw_unique": raw_unique,
                        "projected_unique": projected_unique,
                        "mask": band,
                    }
                    # Prefer the smallest admitted interface first; then
                    # stronger recurrence and stronger directional evidence.
                    score = (
                        -depth,
                        compression,
                        consistency,
                        len(changed),
                        int(direction < 0),
                        modal_fraction,
                    )
                    if best is None or score > best[0]:
                        best = (score, candidate)
        return None if best is None else best[1]

    def frozen(self, level: int, height: int, width: int) -> bool:
        return (int(level), int(height), int(width)) in self._candidates

    def active(self, level: int, height: int, width: int) -> bool:
        return bool(self._candidates.get((int(level), int(height), int(width))))

    def candidate(self, level: int, height: int, width: int) -> dict[str, Any] | None:
        row = self._candidates.get((int(level), int(height), int(width)))
        if row is None:
            return None
        return dict(row)

    def world_digest(self, level: int, grid: Grid) -> str:
        key = self._shape(level, grid)
        row = self._candidates.get(key) if key is not None else None
        mask = set(row["mask"]) if row else set()
        return self._digest(grid, mask)

    def projected_grid(self, level: int, grid: Grid) -> Grid:
        key = self._shape(level, grid)
        row = self._candidates.get(key) if key is not None else None
        if not row:
            return grid
        mask = set(row["mask"])
        return tuple(
            tuple(-1_000_000 if (x, y) in mask else int(value) for x, value in enumerate(line))
            for y, line in enumerate(grid)
        )

    def scalar_signature(self, level: int, grid: Grid) -> tuple[int, int, int] | tuple[()]:
        key = self._shape(level, grid)
        row = self._candidates.get(key) if key is not None else None
        if not row:
            return ()
        color = int(row["color"])
        value = sum(int(grid[y][x] == color) for x, y in row["mask"])
        return (color, int(value), int(row["direction"]))

    def buffered_transitions(
        self, level: int, height: int, width: int
    ) -> tuple[dict[str, Any], ...]:
        rows = self._buffers.get((int(level), int(height), int(width)), ())
        return tuple(dict(row) for row in rows)
