from __future__ import annotations

from collections import Counter
import hashlib
from typing import Any

from .memory_graph import ActionKey


Grid = tuple[tuple[int, ...], ...]
Projection = tuple[tuple[int | None, ...], ...]
ShapeKey = tuple[int, int, int]


class RecurrenceFactor:
    """Admit a removable observation factor only when recurrence proves useful.

    Candidate edge bands are evaluated from black-box transitions. A factor earns
    use only if projecting it out creates a large increase in observed state
    recurrence and at least one retained scalar evolves monotonically under
    multiple intervention classes. Removed cells remain reconstructively
    available through factor_signature.
    """

    def __init__(
        self,
        activation_frames: int = 64,
        min_compression: float = 8.0,
        min_scalar_changes: int = 16,
        min_sign_consistency: float = 0.9,
        min_action_classes: int = 2,
        min_modal_fraction: float = 0.8,
        candidate_depths: tuple[int, ...] = (1, 2, 3, 4, 6, 8),
        history_limit: int = 512,
    ) -> None:
        if activation_frames < 1 or min_scalar_changes < 1:
            raise ValueError("positive evidence bounds required")
        if min_compression <= 1.0:
            raise ValueError("compression threshold must exceed one")
        if not 0.5 <= float(min_sign_consistency) <= 1.0:
            raise ValueError("sign consistency must lie in [0.5,1]")
        if min_action_classes < 1:
            raise ValueError("positive intervention diversity required")
        if not 0.0 <= float(min_modal_fraction) <= 1.0:
            raise ValueError("modal fraction must lie in [0,1]")
        depths = tuple(sorted({int(depth) for depth in candidate_depths if int(depth) > 0}))
        if not depths:
            raise ValueError("at least one positive candidate depth required")
        if history_limit < activation_frames:
            raise ValueError("history limit must cover the activation horizon")

        self.activation_frames = int(activation_frames)
        self.min_compression = float(min_compression)
        self.min_scalar_changes = int(min_scalar_changes)
        self.min_sign_consistency = float(min_sign_consistency)
        self.min_action_classes = int(min_action_classes)
        self.min_modal_fraction = float(min_modal_fraction)
        self.candidate_depths = depths
        self.history_limit = int(history_limit)

        self._records: dict[
            ShapeKey, list[tuple[Grid, Grid, ActionKey]]
        ] = {}
        self._transition_counts: dict[ShapeKey, int] = {}
        self._evaluated: set[ShapeKey] = set()
        self._specs: dict[ShapeKey, dict[str, Any]] = {}

    @staticmethod
    def _shape(level: int, grid: Grid) -> ShapeKey | None:
        if not grid:
            return None
        width = len(grid[0])
        if not width or any(len(row) != width for row in grid):
            return None
        return int(level), len(grid), width

    @staticmethod
    def _mask(
        height: int, width: int, side: str, depth: int
    ) -> tuple[tuple[int, int], ...]:
        depth = max(0, int(depth))
        if side == "top":
            points = ((x, y) for y in range(min(depth, height)) for x in range(width))
        elif side == "bottom":
            points = (
                (x, y)
                for y in range(max(0, height - depth), height)
                for x in range(width)
            )
        elif side == "left":
            points = ((x, y) for x in range(min(depth, width)) for y in range(height))
        elif side == "right":
            points = (
                (x, y)
                for x in range(max(0, width - depth), width)
                for y in range(height)
            )
        else:
            raise ValueError("unknown candidate side")
        return tuple(sorted(set(points), key=lambda point: (point[1], point[0])))

    @staticmethod
    def _projection(grid: Grid, mask: tuple[tuple[int, int], ...]) -> Projection:
        hidden = set(mask)
        return tuple(
            tuple(None if (x, y) in hidden else int(value)
                  for x, value in enumerate(row))
            for y, row in enumerate(grid)
        )

    @staticmethod
    def _digest(value: Any) -> str:
        return hashlib.sha256(repr(value).encode()).hexdigest()

    @staticmethod
    def _frames(
        records: list[tuple[Grid, Grid, ActionKey]]
    ) -> tuple[Grid, ...]:
        if not records:
            return ()
        out: list[Grid] = [records[0][0]]
        out.extend(after for _before, after, _action in records)
        return tuple(out)

    def _scalar_witness(
        self,
        mask: tuple[tuple[int, int], ...],
        records: list[tuple[Grid, Grid, ActionKey]],
    ) -> dict[str, Any] | None:
        colors = sorted(
            {
                int(grid[y][x])
                for before, after, _action in records
                for grid in (before, after)
                for x, y in mask
            }
        )
        best: dict[str, Any] | None = None
        for color in colors:
            deltas: list[int] = []
            action_ids: set[int] = set()
            for before, after, action in records:
                left = sum(before[y][x] == color for x, y in mask)
                right = sum(after[y][x] == color for x, y in mask)
                delta = int(right - left)
                if not delta:
                    continue
                deltas.append(delta)
                action_ids.add(int(action[0]))
            if len(deltas) < self.min_scalar_changes:
                continue
            if len(action_ids) < self.min_action_classes:
                continue
            signs = Counter(1 if delta > 0 else -1 for delta in deltas)
            sign_consistency = max(signs.values()) / len(deltas)
            if sign_consistency < self.min_sign_consistency:
                continue
            magnitudes = Counter(abs(delta) for delta in deltas)
            modal_magnitude, modal_count = magnitudes.most_common(1)[0]
            modal_fraction = modal_count / len(deltas)
            if modal_fraction < self.min_modal_fraction:
                continue
            row = {
                "color": int(color),
                "changes": len(deltas),
                "action_classes": len(action_ids),
                "sign_consistency": float(sign_consistency),
                "modal_abs_delta": int(modal_magnitude),
                "modal_fraction": float(modal_fraction),
            }
            if best is None or (
                row["changes"],
                row["sign_consistency"],
                row["modal_fraction"],
            ) > (
                best["changes"],
                best["sign_consistency"],
                best["modal_fraction"],
            ):
                best = row
        return best

    def _evaluate(self, key: ShapeKey) -> None:
        records = self._records.get(key, [])
        if len(records) < self.activation_frames:
            return
        self._evaluated.add(key)
        if key in self._specs:
            return

        _level, height, width = key
        frames = self._frames(records)
        raw_unique = len({self._digest(frame) for frame in frames})
        qualified: list[dict[str, Any]] = []
        seen_masks: set[tuple[tuple[int, int], ...]] = set()

        for depth in self.candidate_depths:
            for side in ("top", "bottom", "left", "right"):
                mask = self._mask(height, width, side, depth)
                if not mask or mask in seen_masks:
                    continue
                seen_masks.add(mask)
                projected_unique = len(
                    {self._digest(self._projection(frame, mask)) for frame in frames}
                )
                compression = raw_unique / max(1, projected_unique)
                if compression < self.min_compression:
                    continue
                scalar = self._scalar_witness(mask, records)
                if scalar is None:
                    continue
                qualified.append(
                    {
                        "side": side,
                        "depth": int(depth),
                        "compression": float(compression),
                        "raw_unique": int(raw_unique),
                        "projected_unique": int(projected_unique),
                        "mask": mask,
                        "mask_size": len(mask),
                        "scalar": scalar,
                    }
                )

        if not qualified:
            return

        winner = min(
            qualified,
            key=lambda row: (
                row["mask_size"],
                -row["compression"],
                row["side"],
                row["depth"],
            ),
        )
        self._specs[key] = winner

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
        if key in self._specs:
            return
        records = self._records.setdefault(key, [])
        records.append((before, after, tuple(action)))
        if len(records) > self.history_limit:
            del records[: len(records) - self.history_limit]
        count = self._transition_counts.get(key, 0) + 1
        self._transition_counts[key] = count
        if count >= self.activation_frames:
            multiple = count // self.activation_frames
            geometric_checkpoint = (
                count % self.activation_frames == 0
                and multiple > 0
                and (multiple & (multiple - 1)) == 0
            )
            if geometric_checkpoint:
                self._evaluate(key)

    def frozen(self, level: int, height: int, width: int) -> bool:
        return (int(level), int(height), int(width)) in self._evaluated

    def active(self, level: int, height: int, width: int) -> bool:
        return (int(level), int(height), int(width)) in self._specs

    def factor_spec(self, level: int, height: int, width: int) -> dict[str, Any]:
        row = self._specs.get((int(level), int(height), int(width)))
        if row is None:
            return {}
        return {key: value for key, value in row.items() if key != "mask"}

    def _active_mask(self, level: int, grid: Grid) -> tuple[tuple[int, int], ...]:
        key = self._shape(level, grid)
        if key is None:
            return ()
        row = self._specs.get(key)
        return () if row is None else row["mask"]

    def world_projection(self, level: int, grid: Grid) -> Projection:
        return self._projection(grid, self._active_mask(level, grid))

    def world_digest(self, level: int, grid: Grid) -> str:
        return self._digest(self.world_projection(level, grid))

    def factor_signature(self, level: int, grid: Grid) -> tuple[int, ...]:
        mask = self._active_mask(level, grid)
        return tuple(int(grid[y][x]) for x, y in mask)

    def restore(
        self,
        level: int,
        projection: Projection,
        signature: tuple[int, ...],
    ) -> Grid:
        height = len(projection)
        width = len(projection[0]) if height else 0
        key = (int(level), height, width)
        row = self._specs.get(key)
        if row is None:
            if signature:
                raise ValueError("factor signature supplied without active factor")
            return tuple(tuple(int(value) for value in line) for line in projection)
        mask = row["mask"]
        if len(signature) != len(mask):
            raise ValueError("factor signature does not match admitted mask")
        values = [list(line) for line in projection]
        for (x, y), value in zip(mask, signature):
            values[y][x] = int(value)
        if any(value is None for line in values for value in line):
            raise ValueError("projection contains unreconstructed cells")
        return tuple(tuple(int(value) for value in line) for line in values)

    @property
    def active_contexts(self) -> int:
        return len(self._specs)

    @property
    def removed_cell_count(self) -> int:
        return sum(int(row["mask_size"]) for row in self._specs.values())
