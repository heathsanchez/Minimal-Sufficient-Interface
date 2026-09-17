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

    MG-ARC2 stores only consequences that have earned future relevance:
    * purchased interventions by public context;
    * exact terminally refuted programs; and
    * the legal branching actually observed at each program prefix.

    A terminal program is closed immediately.  An ancestor is closed only when
    every legal child observed from that prefix is itself closed.  This gives an
    exact finite refutation trie rather than treating one failed continuation as
    evidence against an earlier action.
    """

    VERSION = "MG-ARC2"

    def __init__(self) -> None:
        self._attempts: dict[tuple[ContextKey, ActionKey], int] = {}
        self._refuted: set[tuple[ContextKey, ProgramKey, str]] = set()
        self._legal: dict[tuple[ContextKey, ProgramKey], tuple[ActionKey, ...]] = {}

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

    @property
    def branching_fact_count(self) -> int:
        return len(self._legal)

    def note_attempt(self, context: ContextKey, action: ActionKey) -> None:
        key = (self._context(context), self._action(action))
        self._attempts[key] = self._attempts.get(key, 0) + 1

    def attempt_count(self, context: ContextKey, action: ActionKey) -> int:
        return self._attempts.get((self._context(context), self._action(action)), 0)

    def note_legal(
        self,
        context: ContextKey,
        prefix: Iterable[ActionKey],
        legal_actions: Iterable[ActionKey],
    ) -> None:
        context_key = self._context(context)
        prefix_key = self._program(prefix)
        observed = {self._action(action) for action in legal_actions}
        if not observed:
            return
        key = (context_key, prefix_key)
        # Union is conservative if the same action prefix is ever observed with
        # a larger legal set: a newly discovered child re-opens any premature
        # closure instead of silently assuming the action does not exist.
        observed.update(self._legal.get(key, ()))
        self._legal[key] = tuple(sorted(observed, key=repr))

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

    def _terminally_refuted(self, context: ContextKey, program: ProgramKey) -> bool:
        return any(
            candidate_context == context and candidate_program == program
            for candidate_context, candidate_program, _consequence in self._refuted
        )

    def is_closed(
        self,
        context: ContextKey,
        program: Iterable[ActionKey],
    ) -> bool:
        context_key = self._context(context)
        program_key = self._program(program)
        memo: dict[ProgramKey, bool] = {}

        def closed(prefix: ProgramKey) -> bool:
            if prefix in memo:
                return memo[prefix]
            if self._terminally_refuted(context_key, prefix):
                memo[prefix] = True
                return True
            legal = self._legal.get((context_key, prefix), ())
            if not legal:
                memo[prefix] = False
                return False
            value = all(closed(prefix + (action,)) for action in legal)
            memo[prefix] = value
            return value

        return closed(program_key)

    def forbidden_next(
        self,
        context: ContextKey,
        prefix: Iterable[ActionKey],
    ) -> set[ActionKey]:
        context_key = self._context(context)
        prefix_key = self._program(prefix)
        legal = self._legal.get((context_key, prefix_key), ())
        return {
            action
            for action in legal
            if self.is_closed(context_key, prefix_key + (action,))
        }

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
        legal = [
            {
                "context": _jsonable(context),
                "prefix": _jsonable(prefix),
                "actions": _jsonable(actions),
            }
            for (context, prefix), actions in sorted(
                self._legal.items(), key=lambda item: repr(item[0])
            )
        ]
        return {"attempts": attempts, "refuted": refuted, "legal": legal}

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
        for row in payload.get("legal", []):
            out.note_legal(
                out._context(row["context"]),
                out._program(row["prefix"]),
                tuple(out._action(action) for action in row["actions"]),
            )
        for row in payload.get("refuted", []):
            out.add_refuted(
                out._context(row["context"]),
                out._program(row["program"]),
                str(row.get("consequence", "GAME_OVER")),
            )
        return out

    def digest(self) -> str:
        return hashlib.sha256(self.text().encode()).hexdigest()
