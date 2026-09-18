from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
from typing import Iterable

from .memory_graph import ActionKey


Grid = tuple[tuple[int, ...], ...]
ShapeKey = tuple[int, int, int]
CandidateKey = tuple[int, int, int, str, int]
HistoryRow = tuple[bytes, bytes, ActionKey, str]


def _encode(grid: Grid) -> bytes:
    try:
        return bytes(int(value) for row in grid for value in row)
    except ValueError as exc:
        raise ValueError("contextual quotient expects byte-valued public raster") from exc


def _full_digest(data: bytes, height: int, width: int) -> bytes:
    h = hashlib.sha256()
    h.update(height.to_bytes(2, "big"))
    h.update(width.to_bytes(2, "big"))
    h.update(data)
    return h.digest()


def _project_digest(
    data: bytes,
    height: int,
    width: int,
    side: str,
    depth: int,
) -> bytes:
    h = hashlib.sha256()
    h.update(height.to_bytes(2, "big"))
    h.update(width.to_bytes(2, "big"))
    h.update(side.encode())
    h.update(int(depth).to_bytes(2, "big"))
    if side == "top":
        h.update(data[min(depth, height) * width :])
    elif side == "bottom":
        h.update(data[: max(0, height - depth) * width])
    elif side == "left":
        cut = min(depth, width)
        for y in range(height):
            start = y * width + cut
            h.update(data[start : (y + 1) * width])
    elif side == "right":
        keep = max(0, width - depth)
        for y in range(height):
            start = y * width
            h.update(data[start : start + keep])
    else:
        raise ValueError("unknown projection side")
    return h.digest()


class ContextualQuotient:
    """Bounded empirical certificate for an observation projection.

    Expensive projection search is deferred until a fixed evidence horizon.
    Before that horizon the controller pays only for compact trace capture.
    Once one projection is admitted, only that projection is monitored. Any
    later transition or protected-outcome contradiction revokes future use.

    This is finite development evidence, not a universal environment theorem.
    """

    SIDES = ("top", "bottom", "left", "right")

    def __init__(
        self,
        *,
        activation_transitions: int = 256,
        min_compression: float = 1.1,
        min_repeated_events: int = 32,
        depths: Iterable[int] = (1, 2, 3, 4, 6, 8),
        reevaluate_every: int = 64,
        max_history: int = 512,
    ) -> None:
        if activation_transitions < 1:
            raise ValueError("positive activation horizon required")
        if min_compression < 1.0:
            raise ValueError("compression threshold must be at least one")
        if min_repeated_events < 1 or reevaluate_every < 1:
            raise ValueError("positive recurrence/evaluation bounds required")
        if max_history < activation_transitions:
            raise ValueError("history must cover the activation horizon")
        cleaned = tuple(sorted({int(value) for value in depths if int(value) > 0}))
        if not cleaned:
            raise ValueError("at least one positive projection depth required")
        self.activation_transitions = int(activation_transitions)
        self.min_compression = float(min_compression)
        self.min_repeated_events = int(min_repeated_events)
        self.depths = cleaned
        self.reevaluate_every = int(reevaluate_every)
        self.max_history = int(max_history)
        self._history: dict[ShapeKey, list[HistoryRow]] = defaultdict(list)
        self._seen_transitions: Counter[ShapeKey] = Counter()
        self._active: dict[ShapeKey, CandidateKey] = {}
        self._candidate_data: dict[CandidateKey, dict] = {}
        self._stats_cache: dict[CandidateKey, dict] = {}
        self._revoked: set[CandidateKey] = set()
        self.evaluation_rounds = 0

    @staticmethod
    def _shape(level: int, grid: Grid) -> ShapeKey | None:
        if not grid:
            return None
        width = len(grid[0])
        if not width or any(len(row) != width for row in grid):
            return None
        return int(level), len(grid), width

    def _candidate_keys(self, shape: ShapeKey) -> tuple[CandidateKey, ...]:
        level, height, width = shape
        rows: list[CandidateKey] = []
        for depth in self.depths:
            for side in self.SIDES:
                if side in ("top", "bottom") and depth >= height:
                    continue
                if side in ("left", "right") and depth >= width:
                    continue
                rows.append((level, height, width, side, depth))
        return tuple(rows)

    @staticmethod
    def _new_data() -> dict:
        return {
            "full": set(),
            "projected": set(),
            "targets": defaultdict(set),
            "key_counts": Counter(),
            "outcomes": defaultdict(set),
            "transitions": 0,
        }

    def _stats(self, key: CandidateKey, row: dict | None = None) -> dict:
        row = row if row is not None else self._candidate_data.get(key, self._new_data())
        level, height, width, side, depth = key
        conflicts = sum(len(values) > 1 for values in row["targets"].values())
        outcome_conflicts = sum(len(values) > 1 for values in row["outcomes"].values())
        repeated_events = sum(
            count for count in row["key_counts"].values() if count > 1
        )
        stats = {
            "level": level,
            "height": height,
            "width": width,
            "side": side,
            "depth": depth,
            "transitions": int(row["transitions"]),
            "full_states": len(row["full"]),
            "projected_states": len(row["projected"]),
            "compression": len(row["full"]) / max(1, len(row["projected"])),
            "repeated_events": int(repeated_events),
            "transition_conflicts": int(conflicts),
            "outcome_conflicts": int(outcome_conflicts),
        }
        self._stats_cache[key] = stats
        return stats

    def _eligible_stats(self, stats: dict) -> bool:
        return (
            stats["transitions"] >= self.activation_transitions
            and stats["compression"] >= self.min_compression
            and stats["repeated_events"] >= self.min_repeated_events
            and stats["transition_conflicts"] == 0
            and stats["outcome_conflicts"] == 0
        )

    def _build_candidate(self, key: CandidateKey, history: list[HistoryRow]) -> dict:
        _level, height, width, side, depth = key
        row = self._new_data()
        for before, after, action, outcome in history:
            full_before = _full_digest(before, height, width)
            full_after = _full_digest(after, height, width)
            projected_before = _project_digest(before, height, width, side, depth)
            projected_after = _project_digest(after, height, width, side, depth)
            row["full"].update((full_before, full_after))
            row["projected"].update((projected_before, projected_after))
            transition_key = (projected_before, tuple(action))
            row["targets"][transition_key].add(projected_after)
            row["key_counts"][transition_key] += 1
            row["outcomes"][projected_before].add(str(outcome))
            row["transitions"] += 1
        return row

    def _evaluate(self, shape: ShapeKey) -> None:
        history = self._history.get(shape, ())
        if len(history) < self.activation_transitions:
            return
        self.evaluation_rounds += 1
        eligible: list[tuple[CandidateKey, dict]] = []
        for key in self._candidate_keys(shape):
            if key in self._revoked:
                continue
            row = self._build_candidate(key, list(history))
            self._candidate_data[key] = row
            stats = self._stats(key, row)
            if self._eligible_stats(stats):
                eligible.append((key, stats))
        if not eligible:
            return
        eligible.sort(
            key=lambda pair: (
                pair[1]["compression"],
                pair[1]["repeated_events"],
                -pair[1]["depth"],
                pair[0][3],
            ),
            reverse=True,
        )
        self._active[shape] = eligible[0][0]

    def _monitor_active(
        self,
        shape: ShapeKey,
        before: bytes,
        after: bytes,
        action: ActionKey,
        outcome: str,
    ) -> None:
        key = self._active.get(shape)
        if key is None:
            return
        _level, height, width, side, depth = key
        row = self._candidate_data[key]
        full_before = _full_digest(before, height, width)
        full_after = _full_digest(after, height, width)
        projected_before = _project_digest(before, height, width, side, depth)
        projected_after = _project_digest(after, height, width, side, depth)
        row["full"].update((full_before, full_after))
        row["projected"].update((projected_before, projected_after))
        transition_key = (projected_before, tuple(action))
        row["targets"][transition_key].add(projected_after)
        row["key_counts"][transition_key] += 1
        row["outcomes"][projected_before].add(str(outcome))
        row["transitions"] += 1
        stats = self._stats(key, row)
        if stats["transition_conflicts"] or stats["outcome_conflicts"]:
            self._revoked.add(key)
            del self._active[shape]

    def observe(
        self,
        level: int,
        before: Grid,
        after: Grid,
        action: ActionKey,
        protected_outcome: str,
    ) -> None:
        before_shape = self._shape(level, before)
        after_shape = self._shape(level, after)
        if before_shape is None or before_shape != after_shape:
            return
        shape = before_shape
        before_bytes = _encode(before)
        after_bytes = _encode(after)
        self._seen_transitions[shape] += 1

        history = self._history[shape]
        history.append((before_bytes, after_bytes, tuple(action), str(protected_outcome)))
        if len(history) > self.max_history:
            del history[: len(history) - self.max_history]

        if shape in self._active:
            self._monitor_active(
                shape, before_bytes, after_bytes, tuple(action), str(protected_outcome)
            )
            return

        n = self._seen_transitions[shape]
        if n >= self.activation_transitions and (
            n == self.activation_transitions
            or (n - self.activation_transitions) % self.reevaluate_every == 0
        ):
            self._evaluate(shape)

    def active_candidate(
        self, level: int, height: int, width: int
    ) -> dict | None:
        key = self._active.get((int(level), int(height), int(width)))
        if key is None:
            return None
        return dict(self._stats_cache.get(key, self._stats(key)))

    def context(self, level: int, grid: Grid, exact_digest: str) -> str:
        shape = self._shape(level, grid)
        if shape is None:
            return str(exact_digest)
        key = self._active.get(shape)
        if key is None:
            return str(exact_digest)
        _level, height, width, side, depth = key
        projected = _project_digest(_encode(grid), height, width, side, depth).hex()
        return f"cq:{level}:{side}:{depth}:{projected}"

    @property
    def active_contexts(self) -> int:
        return len(self._active)

    def active_records(self) -> tuple[dict, ...]:
        return tuple(
            dict(self._stats_cache[key])
            for key in sorted(self._active.values(), key=repr)
        )
