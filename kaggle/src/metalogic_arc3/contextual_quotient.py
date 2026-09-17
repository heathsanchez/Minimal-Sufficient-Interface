from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
from typing import Any, Iterable

from .memory_graph import ActionKey


Grid = tuple[tuple[int, ...], ...]
Protected = tuple[Any, ...]
ShapeKey = tuple[int, int]


class ContextualQuotient:
    """Bounded empirical substitution for the learned consequence graph.

    Candidate projections are not trusted because of geometry. They are admitted
    only when a fixed observed transition set shows:
      * measurable compression,
      * repeated projected state/action use,
      * no observed protected-outcome merge, and
      * no observed projected successor conflict.

    The certificate is therefore bounded evidence, not universal equivalence.
    """

    SIDES = ("top", "bottom", "left", "right")

    def __init__(
        self,
        activation_transitions: int = 128,
        evaluation_interval: int = 64,
        min_compression: float = 1.1,
        min_repeated_events: int = 32,
        candidate_depths: Iterable[int] = (1, 2, 3, 4, 6, 8),
        history_limit: int = 512,
    ) -> None:
        if activation_transitions < 1 or evaluation_interval < 1:
            raise ValueError("positive quotient horizons required")
        if min_compression < 1.0:
            raise ValueError("compression threshold must be at least one")
        if min_repeated_events < 1 or history_limit < activation_transitions:
            raise ValueError("invalid quotient evidence bounds")
        depths = tuple(sorted({int(d) for d in candidate_depths if int(d) > 0}))
        if not depths:
            raise ValueError("at least one positive candidate depth required")
        self.activation_transitions = int(activation_transitions)
        self.evaluation_interval = int(evaluation_interval)
        self.min_compression = float(min_compression)
        self.min_repeated_events = int(min_repeated_events)
        self.candidate_depths = depths
        self.history_limit = int(history_limit)
        self._history: dict[ShapeKey, list[dict[str, Any]]] = defaultdict(list)
        self._certificates: dict[ShapeKey, dict[str, Any]] = {}

    @staticmethod
    def _shape(grid: Grid) -> ShapeKey | None:
        if not grid:
            return None
        width = len(grid[0])
        if not width or any(len(row) != width for row in grid):
            return None
        return len(grid), width

    @staticmethod
    def _points(shape: ShapeKey, side: str, depth: int) -> set[tuple[int, int]]:
        height, width = shape
        if side == "top":
            depth = min(depth, max(0, height - 1))
            return {(x, y) for y in range(depth) for x in range(width)}
        if side == "bottom":
            depth = min(depth, max(0, height - 1))
            return {(x, y) for y in range(height - depth, height) for x in range(width)}
        if side == "left":
            depth = min(depth, max(0, width - 1))
            return {(x, y) for x in range(depth) for y in range(height)}
        if side == "right":
            depth = min(depth, max(0, width - 1))
            return {(x, y) for x in range(width - depth, width) for y in range(height)}
        raise ValueError("unknown projection side")

    @staticmethod
    def _digest(grid: Grid, ignored: set[tuple[int, int]]) -> str:
        canonical = tuple(
            tuple(None if (x, y) in ignored else int(value)
                  for x, value in enumerate(row))
            for y, row in enumerate(grid)
        )
        return hashlib.sha256(repr(canonical).encode()).hexdigest()

    @staticmethod
    def _raw_digest(grid: Grid) -> str:
        return hashlib.sha256(repr(grid).encode()).hexdigest()

    def _evaluate(
        self,
        shape: ShapeKey,
        side: str,
        depth: int,
        rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        ignored = self._points(shape, side, depth)
        if not ignored:
            return {}
        q_states: set[str] = set()
        raw_states: set[str] = set()
        protected: dict[str, set[Protected]] = defaultdict(set)
        transitions: dict[tuple[str, ActionKey], Counter[tuple[str, Protected]]] = defaultdict(Counter)
        key_counts: Counter[tuple[str, ActionKey]] = Counter()

        for row in rows:
            before = row["before"]
            after = row["after"]
            q_before = self._digest(before, ignored)
            q_after = self._digest(after, ignored)
            raw_states.add(self._raw_digest(before))
            raw_states.add(self._raw_digest(after))
            q_states.add(q_before)
            q_states.add(q_after)
            protected[q_before].add(row["source_protected"])
            protected[q_after].add(row["target_protected"])
            key = (q_before, row["action"])
            transitions[key][(q_after, row["target_protected"])] += 1
            key_counts[key] += 1

        outcome_conflicts = sum(len(values) > 1 for values in protected.values())
        ambiguous_keys = sum(len(counter) > 1 for counter in transitions.values())
        conflicting_events = sum(
            sum(counter.values()) - max(counter.values())
            for counter in transitions.values()
        )
        repeated_events = sum(count for count in key_counts.values() if count > 1)
        repeated_keys = sum(count > 1 for count in key_counts.values())
        compression = len(raw_states) / max(1, len(q_states))
        return {
            "side": side,
            "depth": int(depth),
            "sample_transitions": len(rows),
            "raw_states": len(raw_states),
            "projected_states": len(q_states),
            "compression": compression,
            "repeated_events": int(repeated_events),
            "repeated_keys": int(repeated_keys),
            "ambiguous_keys": int(ambiguous_keys),
            "conflicting_events": int(conflicting_events),
            "outcome_conflicts": int(outcome_conflicts),
            "ignored_cells": len(ignored),
            "status": "BOUNDED_EMPIRICAL_SUBSTITUTION",
        }

    def _try_admit(self, shape: ShapeKey) -> None:
        rows = self._history.get(shape, ())
        if len(rows) < self.activation_transitions or shape in self._certificates:
            return
        eligible: list[dict[str, Any]] = []
        for depth in self.candidate_depths:
            for side in self.SIDES:
                candidate = self._evaluate(shape, side, depth, list(rows))
                if not candidate:
                    continue
                if (
                    candidate["compression"] >= self.min_compression
                    and candidate["repeated_events"] >= self.min_repeated_events
                    and candidate["outcome_conflicts"] == 0
                    and candidate["conflicting_events"] == 0
                ):
                    eligible.append(candidate)
        if not eligible:
            return
        eligible.sort(
            key=lambda row: (
                row["repeated_events"],
                row["compression"],
                -row["ignored_cells"],
                row["side"],
            ),
            reverse=True,
        )
        self._certificates[shape] = dict(eligible[0])

    def observe(
        self,
        before: Grid,
        action: ActionKey,
        after: Grid,
        source_protected: Protected,
        target_protected: Protected,
    ) -> None:
        shape = self._shape(before)
        if shape is None or shape != self._shape(after):
            return
        if shape in self._certificates:
            return
        rows = self._history[shape]
        rows.append(
            {
                "before": before,
                "action": tuple(action),
                "after": after,
                "source_protected": tuple(source_protected),
                "target_protected": tuple(target_protected),
            }
        )
        if len(rows) > self.history_limit:
            del rows[: len(rows) - self.history_limit]
        n = len(rows)
        if n >= self.activation_transitions and (
            n == self.activation_transitions
            or (n - self.activation_transitions) % self.evaluation_interval == 0
        ):
            self._try_admit(shape)

    def active(self, height: int, width: int) -> bool:
        return (int(height), int(width)) in self._certificates

    def certificate(self, height: int, width: int) -> dict[str, Any] | None:
        row = self._certificates.get((int(height), int(width)))
        return None if row is None else dict(row)

    def project(self, grid: Grid) -> str:
        shape = self._shape(grid)
        if shape is None:
            return self._raw_digest(grid)
        cert = self._certificates.get(shape)
        if cert is None:
            return self._raw_digest(grid)
        ignored = self._points(shape, str(cert["side"]), int(cert["depth"]))
        return self._digest(grid, ignored)

    @property
    def active_contexts(self) -> int:
        return len(self._certificates)
