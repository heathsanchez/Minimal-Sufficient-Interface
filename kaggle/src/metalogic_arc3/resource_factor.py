from __future__ import annotations

from collections import Counter
import hashlib
from typing import Any

from .memory_graph import ActionKey


Grid = tuple[tuple[int, ...], ...]
ShapeKey = tuple[int, int, int]
ResourceSignature = tuple[tuple[int, int], ...]


class ResourceFactor:
    """Learn a bounded edge-mounted monotone resource display.

    The world projection and resource observation remain separate. A candidate
    region is admitted only after a fixed horizon and must be a long, contiguous
    near-edge strip dominated by one directed color transition with very low
    per-pixel revisit. This targets counters/bars whose boundary moves across
    different pixels; it does not treat interior object motion as disposable.
    """

    def __init__(
        self,
        activation_transitions: int = 12,
        min_positions: int = 8,
        edge_band: int = 3,
        min_pair_fraction: float = 0.8,
        min_span_density: float = 0.7,
        max_changes_per_position: int = 2,
        ledger_limit: int = 2048,
    ) -> None:
        if activation_transitions < 1 or min_positions < 1 or edge_band < 1:
            raise ValueError("positive resource-factor bounds required")
        if not 0.0 <= min_pair_fraction <= 1.0:
            raise ValueError("pair fraction must lie in [0,1]")
        if not 0.0 <= min_span_density <= 1.0:
            raise ValueError("span density must lie in [0,1]")
        if max_changes_per_position < 1 or ledger_limit < 1:
            raise ValueError("positive revisit and ledger bounds required")
        self.activation_transitions = int(activation_transitions)
        self.min_positions = int(min_positions)
        self.edge_band = int(edge_band)
        self.min_pair_fraction = float(min_pair_fraction)
        self.min_span_density = float(min_span_density)
        self.max_changes_per_position = int(max_changes_per_position)
        self.ledger_limit = int(ledger_limit)
        self._n: dict[ShapeKey, int] = {}
        self._events: dict[
            ShapeKey, dict[tuple[int, int], Counter[tuple[int, int]]]
        ] = {}
        self._masks: dict[ShapeKey, tuple[tuple[int, int], ...]] = {}
        self._ledger: list[dict[str, Any]] = []

    @staticmethod
    def _shape(level: int, grid: Grid) -> ShapeKey | None:
        if not grid:
            return None
        width = len(grid[0])
        if not width or any(len(row) != width for row in grid):
            return None
        return int(level), len(grid), width

    def frozen(self, level: int, height: int, width: int) -> bool:
        return (int(level), int(height), int(width)) in self._masks

    def active(self, level: int, height: int, width: int) -> bool:
        key = (int(level), int(height), int(width))
        return bool(self._masks.get(key, ()))

    def masked_positions(
        self, level: int, height: int, width: int
    ) -> tuple[tuple[int, int], ...]:
        return self._masks.get((int(level), int(height), int(width)), ())

    @staticmethod
    def _dominant_pair(
        points: list[tuple[int, int]],
        events: dict[tuple[int, int], Counter[tuple[int, int]]],
    ) -> tuple[tuple[int, int] | None, int, int]:
        counts: Counter[tuple[int, int]] = Counter()
        total = 0
        for point in points:
            point_counts = events.get(point, Counter())
            counts.update(point_counts)
            total += sum(point_counts.values())
        if not counts:
            return None, 0, total
        pair, count = counts.most_common(1)[0]
        return pair, count, total

    def _row_candidate(
        self,
        y: int,
        grid: Grid,
        events: dict[tuple[int, int], Counter[tuple[int, int]]],
    ) -> set[tuple[int, int]]:
        width = len(grid[0])
        changed = [(x, y) for x in range(width) if events.get((x, y))]
        if len(changed) < self.min_positions:
            return set()
        xs = [x for x, _ in changed]
        span = max(xs) - min(xs) + 1
        if len(changed) / span < self.min_span_density:
            return set()
        if any(sum(events[p].values()) > self.max_changes_per_position for p in changed):
            return set()
        pair, dominant, total = self._dominant_pair(changed, events)
        if pair is None or not total or dominant / total < self.min_pair_fraction:
            return set()
        values = set(pair)
        left, right = min(xs), max(xs)
        while left > 0 and grid[y][left - 1] in values:
            left -= 1
        while right + 1 < width and grid[y][right + 1] in values:
            right += 1
        return {(x, y) for x in range(left, right + 1)}

    def _col_candidate(
        self,
        x: int,
        grid: Grid,
        events: dict[tuple[int, int], Counter[tuple[int, int]]],
    ) -> set[tuple[int, int]]:
        height = len(grid)
        changed = [(x, y) for y in range(height) if events.get((x, y))]
        if len(changed) < self.min_positions:
            return set()
        ys = [y for _, y in changed]
        span = max(ys) - min(ys) + 1
        if len(changed) / span < self.min_span_density:
            return set()
        if any(sum(events[p].values()) > self.max_changes_per_position for p in changed):
            return set()
        pair, dominant, total = self._dominant_pair(changed, events)
        if pair is None or not total or dominant / total < self.min_pair_fraction:
            return set()
        values = set(pair)
        top, bottom = min(ys), max(ys)
        while top > 0 and grid[top - 1][x] in values:
            top -= 1
        while bottom + 1 < height and grid[bottom + 1][x] in values:
            bottom += 1
        return {(x, y) for y in range(top, bottom + 1)}

    def _freeze(self, key: ShapeKey, grid: Grid) -> None:
        _level, height, width = key
        events = self._events.get(key, {})
        mask: set[tuple[int, int]] = set()
        row_ids = sorted(
            set(range(min(self.edge_band, height)))
            | set(range(max(0, height - self.edge_band), height))
        )
        col_ids = sorted(
            set(range(min(self.edge_band, width)))
            | set(range(max(0, width - self.edge_band), width))
        )
        for y in row_ids:
            mask.update(self._row_candidate(y, grid, events))
        for x in col_ids:
            mask.update(self._col_candidate(x, grid, events))
        self._masks[key] = tuple(sorted(mask, key=lambda p: (p[1], p[0])))

    def observe(self, level: int, before: Grid, after: Grid) -> None:
        before_key = self._shape(level, before)
        after_key = self._shape(level, after)
        if before_key is None or before_key != after_key:
            return
        key = before_key
        if key in self._masks:
            return
        self._n[key] = self._n.get(key, 0) + 1
        events = self._events.setdefault(key, {})
        for y, (left_row, right_row) in enumerate(zip(before, after)):
            for x, (left, right) in enumerate(zip(left_row, right_row)):
                if left == right:
                    continue
                events.setdefault((x, y), Counter())[(int(left), int(right))] += 1
        if self._n[key] >= self.activation_transitions:
            self._freeze(key, after)

    def world_digest(self, level: int, grid: Grid) -> str:
        key = self._shape(level, grid)
        mask = set(self._masks.get(key, ())) if key is not None else set()
        canonical = tuple(
            tuple(None if (x, y) in mask else int(value) for x, value in enumerate(row))
            for y, row in enumerate(grid)
        )
        return hashlib.sha256(repr(canonical).encode()).hexdigest()

    def resource_signature(self, level: int, grid: Grid) -> ResourceSignature:
        key = self._shape(level, grid)
        mask = self._masks.get(key, ()) if key is not None else ()
        if not mask:
            return ()
        counts = Counter(int(grid[y][x]) for x, y in mask)
        return tuple(sorted((value, count) for value, count in counts.items()))

    def note_transition(
        self,
        source: str,
        action: ActionKey,
        target: str,
        before: ResourceSignature,
        after: ResourceSignature,
    ) -> None:
        if not before and not after:
            return
        self._ledger.append(
            {
                "source": str(source),
                "action": tuple(action),
                "target": str(target),
                "before": tuple(before),
                "after": tuple(after),
            }
        )
        if len(self._ledger) > self.ledger_limit:
            del self._ledger[: len(self._ledger) - self.ledger_limit]

    def resource_transitions(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(row) for row in self._ledger)

    @property
    def active_contexts(self) -> int:
        return sum(bool(mask) for mask in self._masks.values())

    @property
    def masked_pixel_count(self) -> int:
        return sum(len(mask) for mask in self._masks.values())
