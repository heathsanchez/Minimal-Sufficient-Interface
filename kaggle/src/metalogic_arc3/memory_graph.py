from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

ActionKey = tuple[int, int | None, int | None]
ContextKey = tuple[Any, ...]
ProgramKey = tuple[ActionKey, ...]


def _freeze(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((str(key), _freeze(item)) for key, item in value.items()))
    return value


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    return value


class ArcMemoryGraph:
    """Canonical compressed consequential memory for an ARC session.

    The first admitted facts are deliberately minimal:
    * how often an intervention was already purchased in a context; and
    * complete episode/level prefixes that were refuted by terminal consequence.

    Transient trajectory state does not live here. This object is the retained
    present that survives RESET and can be serialized/restarted exactly.
    """

    VERSION = "MG-ARC1"

    def __init__(self) -> None:
        self._attempts: dict[tuple[ContextKey, ActionKey], int] = {}
        self._refuted: set[tuple[ContextKey, ProgramKey, str]] = set()

    @staticmethod
    def _context(value: Iterable[Any] | ContextKey) -> ContextKey:
        frozen = _freeze(list(value))
        if not isinstance(frozen, tuple):
            raise TypeError("context must be iterable")
        return frozen

    @staticmethod
    def _action(value: Iterable[Any] | ActionKey) -> ActionKey:
        frozen = tuple(value)
        if len(frozen) != 3:
            raise ValueError("action key must be (action_id, x, y)")
        action_id, x, y = frozen
        return (int(action_id), None if x is None else int(x), None if y is None else int(y))

    @classmethod
    def _program(cls, value: Iterable[Iterable[Any] | ActionKey]) -> ProgramKey:
        return tuple(cls._action(action) for action in value)

    @property
    def refuted_count(self) -> int:
        return len(self._refuted)

    @property
    def attempt_fact_count(self) -> int:
        return len(self._attempts)

    def note_attempt(self, context: ContextKey, action: ActionKey) -> None:
        key = (self._context(context), self._action(action))
        self._attempts[key] = self._attempts.get(key, 0) + 1

    def attempt_count(self, context: ContextKey, action: ActionKey) -> int:
        return self._attempts.get((self._context(context), self._action(action)), 0)

    def add_refuted(
        self,
        context: ContextKey,
        program: Iterable[ActionKey],
        consequence: str = "GAME_OVER",
    ) -> None:
        frozen_program = self._program(program)
        if not frozen_program:
            return
        self._refuted.add((self._context(context), frozen_program, str(consequence)))

    def forbidden_next(
        self,
        context: ContextKey,
        prefix: Iterable[ActionKey],
    ) -> set[ActionKey]:
        context_key = self._context(context)
        prefix_key = self._program(prefix)
        result: set[ActionKey] = set()
        for candidate_context, program, _consequence in self._refuted:
            if candidate_context != context_key:
                continue
            if len(prefix_key) >= len(program):
                continue
            if program[: len(prefix_key)] == prefix_key:
                result.add(program[len(prefix_key)])
        return result

    def _payload(self) -> dict[str, Any]:
        attempts = [
            {
                "context": _jsonable(context),
                "action": _jsonable(action),
                "count": count,
            }
            for (context, action), count in sorted(
                self._attempts.items(), key=lambda item: repr(item[0])
            )
        ]
        refuted = [
            {
                "context": _jsonable(context),
                "program": _jsonable(program),
                "consequence": consequence,
            }
            for context, program, consequence in sorted(self._refuted, key=repr)
        ]
        return {"attempts": attempts, "refuted": refuted}

    def text(self) -> str:
        payload = json.dumps(self._payload(), sort_keys=True, separators=(",", ":"))
        return f"{self.VERSION}\n{payload}\n"

    @classmethod
    def parse(cls, text: str) -> "ArcMemoryGraph":
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines or lines[0] != cls.VERSION:
            raise ValueError("unsupported ARC .mg version")
        if len(lines) != 2:
            raise ValueError("malformed ARC .mg")
        payload = json.loads(lines[1])
        out = cls()
        for row in payload.get("attempts", []):
            context = out._context(row["context"])
            action = out._action(row["action"])
            count = int(row["count"])
            if count < 1:
                raise ValueError("attempt counts must be positive")
            out._attempts[(context, action)] = count
        for row in payload.get("refuted", []):
            out.add_refuted(
                out._context(row["context"]),
                out._program(row["program"]),
                str(row.get("consequence", "GAME_OVER")),
            )
        return out

    def digest(self) -> str:
        return hashlib.sha256(self.text().encode()).hexdigest()
