from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class Observation:
    levels_completed: int
    state: str
    available_actions: tuple[int, ...]
    frame_digest: str
    height: int
    width: int


@dataclass(frozen=True)
class ActionToken:
    action_id: int
    x: int | None = None
    y: int | None = None
    source: str = "explore"


def _plain(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if hasattr(value, "value") and isinstance(getattr(value, "value"), (int, str)):
        return getattr(value, "value")
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _state_name(value: Any) -> str:
    if hasattr(value, "name"):
        return str(value.name)
    text = str(value)
    return text.rsplit(".", 1)[-1]


def _action_id(value: Any) -> int:
    raw = getattr(value, "value", value)
    return int(raw)


def _field(frame: Any, name: str, default: Any) -> Any:
    if isinstance(frame, dict):
        return frame.get(name, default)
    return getattr(frame, name, default)


def normalize_frame(frame: Any) -> Observation:
    raw_frame = _plain(_field(frame, "frame", []))
    layers = raw_frame if isinstance(raw_frame, list) else []
    first = layers[0] if layers else []
    height = len(first) if isinstance(first, list) else 0
    width = len(first[0]) if height and isinstance(first[0], list) else 0
    actions = tuple(sorted({_action_id(a) for a in _field(frame, "available_actions", [])}))
    payload = {
        "frame": raw_frame,
        "levels_completed": int(_field(frame, "levels_completed", 0)),
        "state": _state_name(_field(frame, "state", "UNKNOWN")),
        "available_actions": actions,
    }
    digest = hashlib.blake2b(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode(),
        digest_size=12,
    ).hexdigest()
    return Observation(
        levels_completed=payload["levels_completed"],
        state=payload["state"],
        available_actions=actions,
        frame_digest=digest,
        height=height,
        width=width,
    )


class OnlineController:
    """Consequence-driven online controller for the Kaggle hot path.

    Exploration starts from the coarsest public task state useful for avoiding
    duplicate probes. Action 6 is grounded by the already-qualified public
    dimensions-only coarse-to-fine grammar from the MSI ARC3 lineage. Each
    coordinate is a distinct experiment token, so future retention preserves
    the exact witnessed intervention rather than only the action ID.

    Retention is stricter than exploration: a witnessed progress program is
    replayed only when the exact public entry observation is seen again. No
    game semantics, object labels, goal labels, solved trajectories, or hidden
    source knowledge are supplied.
    """

    def __init__(
        self,
        action_ids: Iterable[int],
        max_history: int = 8,
        grounding_stride: int = 8,
        max_grounded_actions: int = 256,
    ):
        ids = tuple(dict.fromkeys(int(a) for a in action_ids))
        if not ids:
            raise ValueError("action_ids must be nonempty")
        if max_history < 1:
            raise ValueError("max_history must be positive")
        if grounding_stride < 1 or max_grounded_actions < 1:
            raise ValueError("positive grounding bounds required")
        self.action_ids = ids
        self.max_history = max_history
        self.grounding_stride = grounding_stride
        self.max_grounded_actions = max_grounded_actions
        self._retained: dict[tuple[Any, ...], list[tuple[ActionToken, ...]]] = {}
        self.reset_episode()

    @property
    def retained_option_count(self) -> int:
        return sum(len(items) for items in self._retained.values())

    @property
    def local_history_length(self) -> int:
        return len(self._local_history)

    def reset_episode(self) -> None:
        self._previous: Observation | None = None
        self._last_action: ActionToken | None = None
        self._local_history: list[ActionToken] = []
        self._since_progress: list[ActionToken] = []
        self._level_start_guard: tuple[Any, ...] | None = None
        self._active_option: tuple[ActionToken, ...] = ()
        self._active_index = 0
        self._visits: dict[tuple[tuple[Any, ...], tuple[int, int | None, int | None]], int] = {}

    @staticmethod
    def _retention_guard(obs: Observation) -> tuple[Any, ...]:
        return (
            obs.levels_completed,
            obs.state,
            obs.available_actions,
            obs.frame_digest,
        )

    @staticmethod
    def _exploration_guard(obs: Observation) -> tuple[Any, ...]:
        # Start coarse. Consequence evidence, rather than visual novelty alone,
        # is what should justify a finer live exploration quotient.
        return (
            obs.levels_completed,
            obs.state,
            obs.available_actions,
            obs.height,
            obs.width,
        )

    def _retain_progress(self) -> None:
        if self._level_start_guard is None or not self._since_progress:
            return
        program = tuple(self._since_progress)
        bucket = self._retained.setdefault(self._level_start_guard, [])
        if program not in bucket:
            bucket.append(program)
            bucket.sort(key=lambda p: (len(p), tuple((a.action_id, a.x, a.y) for a in p)))

    def _process_previous_outcome(self, obs: Observation) -> None:
        if self._previous is None or self._last_action is None:
            return
        self._local_history.append(self._last_action)
        if len(self._local_history) > self.max_history:
            del self._local_history[:-self.max_history]
        self._since_progress.append(self._last_action)
        if obs.levels_completed > self._previous.levels_completed:
            self._retain_progress()
            self._since_progress = []
            self._level_start_guard = self._retention_guard(obs)
            self._active_option = ()
            self._active_index = 0

    def _legal_ids(self, obs: Observation) -> tuple[int, ...]:
        if obs.available_actions:
            legal = tuple(a for a in self.action_ids if a in obs.available_actions)
            if legal:
                return legal
        return self.action_ids

    def _coordinate_candidates(self, obs: Observation) -> tuple[tuple[int, int], ...]:
        if obs.height < 1 or obs.width < 1:
            raise ValueError("No public image dimensions")

        seen: set[tuple[int, int]] = set()
        result: list[tuple[int, int]] = []
        for step in (self.grounding_stride, max(1, self.grounding_stride // 2), 1):
            for y in range(step // 2, obs.height, step):
                for x in range(step // 2, obs.width, step):
                    coordinate = (x, y)
                    if coordinate in seen:
                        continue
                    seen.add(coordinate)
                    result.append(coordinate)
        return tuple(result)

    def _action_catalog(self, obs: Observation) -> tuple[ActionToken, ...]:
        """Ground the currently legal public action space deterministically.

        Simple actions remain single tokens. Action 6 receives the donor
        coarse-to-fine coordinate lattice. The total catalog is bounded, so
        this is an experiment grammar rather than a claim of exhaustive useful
        action enumeration.
        """
        legal = self._legal_ids(obs)
        candidates: list[ActionToken] = []

        for action_id in legal:
            if action_id == 6:
                continue
            candidates.append(ActionToken(action_id=action_id, source="explore"))
            if len(candidates) >= self.max_grounded_actions:
                return tuple(candidates)

        if 6 in legal:
            for x, y in self._coordinate_candidates(obs):
                candidates.append(ActionToken(action_id=6, x=x, y=y, source="explore"))
                if len(candidates) >= self.max_grounded_actions:
                    break

        if not candidates:
            raise ValueError("No supported legal action candidates")
        return tuple(candidates)

    @staticmethod
    def _candidate_key(token: ActionToken) -> tuple[int, int | None, int | None]:
        return (token.action_id, token.x, token.y)

    def _next_retained(self, obs: Observation) -> ActionToken | None:
        if self._active_option and self._active_index < len(self._active_option):
            token = self._active_option[self._active_index]
            self._active_index += 1
            return ActionToken(token.action_id, token.x, token.y, "retained")
        self._active_option = ()
        self._active_index = 0
        bucket = self._retained.get(self._retention_guard(obs), ())
        if not bucket:
            return None
        self._active_option = bucket[0]
        self._active_index = 1
        token = self._active_option[0]
        return ActionToken(token.action_id, token.x, token.y, "retained")

    def observe_and_choose(self, frame: Any) -> ActionToken | None:
        obs = normalize_frame(frame)
        self._process_previous_outcome(obs)
        if self._level_start_guard is None:
            self._level_start_guard = self._retention_guard(obs)
        if obs.state == "WIN":
            self._previous = obs
            self._last_action = None
            return None

        retained = self._next_retained(obs)
        if retained is not None:
            token = retained
        else:
            guard = self._exploration_guard(obs)
            catalog = self._action_catalog(obs)
            token = min(
                catalog,
                key=lambda candidate: self._visits.get(
                    (guard, self._candidate_key(candidate)), 0
                ),
            )
            key = (guard, self._candidate_key(token))
            self._visits[key] = self._visits.get(key, 0) + 1

        self._previous = obs
        self._last_action = token
        return token
