from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
from typing import Iterable

from .memory_graph import ActionKey


Grid = tuple[tuple[int, ...], ...]
ShapeKey = tuple[int, int, int]
CandidateKey = tuple[int, int, int, str, int]


def _digest_grid(grid: Grid, ignored: set[tuple[int, int]] | None = None) -> str:
    ignored = ignored or set()
    canonical = tuple(
        tuple(None if (x, y) in ignored else int(value) for x, value in enumerate(row))
        for y, row in enumerate(grid)
    )
    return hashlib.sha256(repr(canonical).encode()).hexdigest()


class ContextualQuotient:
    """Finite empirical certificate for an observation projection.

    A projection becomes active only after a fixed evidence horizon when it:
    compresses observed states, creates genuine recurrence, preserves a
    deterministic projected transition for every repeated (state, action) key,
    and never merges source states with different protected successor outcomes.

    This is a bounded development certificate, not a universal environment law.
    """

    SIDES = ("top", "bottom", "left", "right")

    def __init__(
        self,
        *,
        activation_transitions: int = 256,
        min_compression: float = 1.1,
        min_repeated_events: int = 32,
        depths: Iterable[int] = (1, 2, 3, 4, 6, 8),
    ) -> None:
        if activation_transitions < 1:
            raise ValueError("positive activation horizon required")
        if min_compression < 1.0:
            raise ValueError("compression threshold must be at least one")
        if min_repeated_events < 1:
            raise ValueError("positive recurrence threshold required")
        cleaned = tuple(sorted({int(value) for value in depths if int(value) > 0}))
        if not cleaned:
            raise ValueError("at least one positive projection depth required")
        self.activation_transitions = int(activation_transitions)
        self.min_compression = float(min_compression)
        self.min_repeated_events = int(min_repeated_events)
        self.depths = cleaned
        self._rows: dict[CandidateKey, dict] = {}
        self._active: dict[ShapeKey, CandidateKey] = {}

    @staticmethod
    def _shape(level: int, grid: Grid) -> ShapeKey | None:
        if not grid:
            return None
        width = len(grid[0])
        if not width or any(len(row) != width for row in grid):
            return None
        return int(level), len(grid), width

    @staticmethod
    def _ignored(height: int, width: int, side: str, depth: int) -> set[tuple[int, int]]:
        depth = int(depth)
        if side == "top":
            return {(x, y) for y in range(min(depth, height)) for x in range(width)}
        if side == "bottom":
            return {
                (x, y)
                for y in range(max(0, height - depth), height)
                for x in range(width)
            }
        if side == "left":
            return {(x, y) for x in range(min(depth, width)) for y in range(height)}
        if side == "right":
            return {
                (x, y)
                for x in range(max(0, width - depth), width)
                for y in range(height)
            }
        raise ValueError("unknown projection side")

    def _row(self, key: CandidateKey) -> dict:
        return self._rows.setdefault(
            key,
            {
                "n": 0,
                "full": set(),
                "projected": set(),
                "targets": defaultdict(set),
                "key_counts": Counter(),
                "outcomes": defaultdict(set),
            },
        )

    def _stats(self, key: CandidateKey) -> dict:
        level, height, width, side, depth = key
        row = self._row(key)
        full = len(row["full"])
        projected = len(row["projected"])
        conflicts = sum(len(values) > 1 for values in row["targets"].values())
        outcome_conflicts = sum(len(values) > 1 for values in row["outcomes"].values())
        repeated_events = sum(
            count for count in row["key_counts"].values() if count > 1
        )
        return {
            "level": level,
            "height": height,
            "width": width,
            "side": side,
            "depth": depth,
            "transitions": int(row["n"]),
            "full_states": full,
            "projected_states": projected,
            "compression": full / max(1, projected),
            "repeated_events": int(repeated_events),
            "transition_conflicts": int(conflicts),
            "outcome_conflicts": int(outcome_conflicts),
        }

    def _eligible(self, key: CandidateKey) -> bool:
        stats = self._stats(key)
        return (
            stats["transitions"] >= self.activation_transitions
            and stats["compression"] >= self.min_compression
            and stats["repeated_events"] >= self.min_repeated_events
            and stats["transition_conflicts"] == 0
            and stats["outcome_conflicts"] == 0
        )

    def _maybe_activate(self, shape: ShapeKey) -> None:
        if shape in self._active:
            # A later contradiction revokes future quotient use.
            key = self._active[shape]
            if not self._eligible(key):
                del self._active[shape]
            return
        level, height, width = shape
        candidates = [
            key
            for key in self._rows
            if key[:3] == shape and self._eligible(key)
        ]
        if not candidates:
            return
        candidates.sort(
            key=lambda key: (
                self._stats(key)["compression"],
                self._stats(key)["repeated_events"],
                -self._stats(key)["depth"],
                key[3],
            ),
            reverse=True,
        )
        self._active[shape] = candidates[0]

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
        _, height, width = shape
        full_before = _digest_grid(before)
        full_after = _digest_grid(after)
        action_key = tuple(action)

        for depth in self.depths:
            for side in self.SIDES:
                ignored = self._ignored(height, width, side, depth)
                projected_before = _digest_grid(before, ignored)
                projected_after = _digest_grid(after, ignored)
                key: CandidateKey = (*shape, side, depth)
                row = self._row(key)
                row["n"] += 1
                row["full"].update((full_before, full_after))
                row["projected"].update((projected_before, projected_after))
                transition_key = (projected_before, action_key)
                row["targets"][transition_key].add(projected_after)
                row["key_counts"][transition_key] += 1
                row["outcomes"][projected_before].add(str(protected_outcome))

        self._maybe_activate(shape)

    def active_candidate(
        self, level: int, height: int, width: int
    ) -> dict | None:
        shape = (int(level), int(height), int(width))
        self._maybe_activate(shape)
        key = self._active.get(shape)
        return None if key is None else self._stats(key)

    def context(self, level: int, grid: Grid, exact_digest: str) -> str:
        shape = self._shape(level, grid)
        if shape is None:
            return str(exact_digest)
        self._maybe_activate(shape)
        key = self._active.get(shape)
        if key is None:
            return str(exact_digest)
        _level, height, width, side, depth = key
        projected = _digest_grid(grid, self._ignored(height, width, side, depth))
        return f"cq:{level}:{side}:{depth}:{projected}"

    @property
    def active_contexts(self) -> int:
        return len(self._active)

    def active_records(self) -> tuple[dict, ...]:
        return tuple(self._stats(key) for key in sorted(self._active.values(), key=repr))
