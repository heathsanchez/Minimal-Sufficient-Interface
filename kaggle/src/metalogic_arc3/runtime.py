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
    """Small consequence-driven online controller for the Kaggle hot path.

    It retains only witnessed progress programs and reuses them only when the
    same public guard is seen again. No game semantics or solved trajectories
    are supplied.
    """

    def __init__(self, action_ids: Iterable[int], max_history: int = 8):
        ids = tuple(dict.fromkeys(int(a) for a in action_ids))
        if not ids:
            raise ValueError("action_ids must be nonempty")
        if max_history < 1:
            raise ValueError("max_history must be positive")
        self.action_ids = ids
        self.max_history = max_history
        self._retained: dict[tuple[Any, ...], list[tuple[ActionToken, ...]]] = {}
        self._visits: dict[tuple[tuple[Any, ...], int], int] = {}
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
        self._visits = {}

    @staticmethod
    def _guard(obs: Observation) -> tuple[Any, ...]:
        return (
            obs.levels_completed,
            obs.state,
            obs.available_actions,
            obs.frame_digest,
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
            self._level_start_guard = self._guard(obs)
            self._active_option = ()
            self._active_index = 0

    def _legal_ids(self, obs: Observation) -> tuple[int, ...]:
        if obs.available_actions:
            legal = tuple(a for a in self.action_ids if a in obs.available_actions)
            if legal:
                return legal
        return self.action_ids

    @staticmethod
    def _coordinate(obs: Observation, index: int) -> tuple[int, int]:
        width = max(1, obs.width)
        height = max(1, obs.height)
        candidates = [
            (width // 2, height // 2),
            (width // 4, height // 4),
            ((3 * width) // 4, height // 4),
            (width // 4, (3 * height) // 4),
            ((3 * width) // 4, (3 * height) // 4),
            (0, 0),
            (width - 1, 0),
            (0, height - 1),
            (width - 1, height - 1),
        ]
        x, y = candidates[index % len(candidates)]
        return min(max(0, x), width - 1), min(max(0, y), height - 1)

    def _token_for(self, action_id: int, obs: Observation, source: str) -> ActionToken:
        guard = self._guard(obs)
        count = self._visits.get((guard, action_id), 0)
        self._visits[(guard, action_id)] = count + 1
        if action_id == 6:
            x, y = self._coordinate(obs, count)
            return ActionToken(action_id=6, x=x, y=y, source=source)
        return ActionToken(action_id=action_id, source=source)

    def _next_retained(self, obs: Observation) -> ActionToken | None:
        if self._active_option and self._active_index < len(self._active_option):
            token = self._active_option[self._active_index]
            self._active_index += 1
            return ActionToken(token.action_id, token.x, token.y, "retained")
        self._active_option = ()
        self._active_index = 0
        bucket = self._retained.get(self._guard(obs), ())
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
            self._level_start_guard = self._guard(obs)
        if obs.state == "WIN":
            self._previous = obs
            self._last_action = None
            return None

        retained = self._next_retained(obs)
        if retained is not None:
            token = retained
        else:
            legal = self._legal_ids(obs)
            guard = self._guard(obs)
            action_id = min(
                legal,
                key=lambda a: (self._visits.get((guard, a), 0), self.action_ids.index(a)),
            )
            token = self._token_for(action_id, obs, "explore")

        self._previous = obs
        self._last_action = token
        return token
