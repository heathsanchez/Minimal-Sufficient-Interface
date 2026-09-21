from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

ActionKey = tuple[int, int | None, int | None]
ContextKey = tuple[Any, ...]
ProgramKey = tuple[ActionKey, ...]
CapabilityKey = tuple[ContextKey, ProgramKey, int, int]
Node = tuple[str, tuple[Any, ...]]
Log = tuple[Node, ...]


def _freeze(value: Any) -> Any:
    """Recursively canonicalize values into immutable tuples."""
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((str(key), _freeze(item)) for key, item in value.items()))
    if isinstance(value, set):
        return tuple(sorted((_freeze(item) for item in value), key=repr))
    return value


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    return value


def _node(kind: str, *payload: Any) -> Node:
    return (str(kind), tuple(_freeze(item) for item in payload))


class ArcMemoryGraph:
    """DuckTape: immutable warranted history plus a derived live ARC view.

    The authoritative state is only L = (e_1, ..., e_n), where every event is
    a canonical immutable Node. All attempts, refutations, branching facts and
    reusable capabilities are derived by replaying that tuple. There are no
    authoritative mutable side stores.

    The public API intentionally remains compatible with the earlier MG-ARC3
    controller so the Kaggle runtime can adopt pure-log semantics without
    changing its action policy at the same time.
    """

    VERSION = "DUCKTAPE-ARC3"

    def __init__(self, log: Log = ()) -> None:
        frozen = tuple(_node(kind, *payload) for kind, payload in log)
        self._log: Log = frozen

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
    def log(self) -> Log:
        return self._log

    @property
    def log_size(self) -> int:
        return len(self._log)

    def _append(self, kind: str, *payload: Any) -> None:
        self._log = self._log + (_node(kind, *payload),)

    def _live(
        self,
    ) -> tuple[
        dict[tuple[ContextKey, ActionKey], int],
        set[tuple[ContextKey, ProgramKey, str]],
        dict[tuple[ContextKey, ProgramKey], tuple[ActionKey, ...]],
        set[CapabilityKey],
    ]:
        attempts: dict[tuple[ContextKey, ActionKey], int] = {}
        refuted: set[tuple[ContextKey, ProgramKey, str]] = set()
        legal_sets: dict[tuple[ContextKey, ProgramKey], set[ActionKey]] = {}
        capabilities: set[CapabilityKey] = set()

        for kind, payload in self._log:
            if kind == "ATTEMPT":
                context, action = payload
                key = (context, action)
                attempts[key] = attempts.get(key, 0) + 1
            elif kind == "LEGAL":
                context, prefix, actions = payload
                key = (context, prefix)
                legal_sets.setdefault(key, set()).update(actions)
            elif kind == "REFUTE":
                context, program, consequence = payload
                refuted.add((context, program, str(consequence)))
            elif kind == "CAPABILITY":
                context, program, source_level, target_level = payload
                capabilities.add(
                    (context, program, int(source_level), int(target_level))
                )
            else:
                raise ValueError(f"unsupported DuckTape node kind: {kind}")

        legal = {
            key: tuple(sorted(actions, key=repr))
            for key, actions in legal_sets.items()
        }
        return attempts, refuted, legal, capabilities

    @property
    def refuted_count(self) -> int:
        _attempts, refuted, _legal, _capabilities = self._live()
        return len(refuted)

    @property
    def attempt_fact_count(self) -> int:
        attempts, _refuted, _legal, _capabilities = self._live()
        return len(attempts)

    @property
    def branching_fact_count(self) -> int:
        _attempts, _refuted, legal, _capabilities = self._live()
        return len(legal)

    @property
    def capability_count(self) -> int:
        _attempts, _refuted, _legal, capabilities = self._live()
        return len(capabilities)

    def note_attempt(self, context: ContextKey, action: ActionKey) -> None:
        self._append("ATTEMPT", self._context(context), self._action(action))

    def attempt_count(self, context: ContextKey, action: ActionKey) -> int:
        attempts, _refuted, _legal, _capabilities = self._live()
        return attempts.get((self._context(context), self._action(action)), 0)

    def note_legal(
        self,
        context: ContextKey,
        prefix: Iterable[ActionKey],
        legal_actions: Iterable[ActionKey],
    ) -> None:
        actions = tuple(
            sorted({self._action(action) for action in legal_actions}, key=repr)
        )
        if not actions:
            return
        self._append(
            "LEGAL",
            self._context(context),
            self._program(prefix),
            actions,
        )

    def add_refuted(
        self,
        context: ContextKey,
        program: Iterable[ActionKey],
        consequence: str = "GAME_OVER",
    ) -> None:
        frozen_program = self._program(program)
        if not frozen_program:
            return
        candidate = (
            self._context(context),
            frozen_program,
            str(consequence),
        )
        _attempts, refuted, _legal, _capabilities = self._live()
        if candidate not in refuted:
            self._append("REFUTE", *candidate)

    def add_capability(
        self,
        source_context: ContextKey,
        program: Iterable[ActionKey],
        *,
        source_level: int,
        target_level: int,
    ) -> None:
        frozen_program = self._program(program)
        if not frozen_program:
            return
        source_level = int(source_level)
        target_level = int(target_level)
        if target_level <= source_level:
            raise ValueError("capability must witness positive level progress")
        candidate: CapabilityKey = (
            self._context(source_context),
            frozen_program,
            source_level,
            target_level,
        )
        _attempts, _refuted, _legal, capabilities = self._live()
        if candidate not in capabilities:
            self._append("CAPABILITY", *candidate)

    def capability_programs(self, for_level: int | None = None) -> tuple[ProgramKey, ...]:
        """Return unique witnessed programs ordered by freshest source progress."""
        _attempts, _refuted, _legal, capabilities = self._live()
        rows = [
            row for row in capabilities
            if for_level is None or row[3] <= int(for_level)
        ]
        rows.sort(key=lambda row: (-row[3], len(row[1]), repr(row[1]), repr(row[0])))
        seen: set[ProgramKey] = set()
        out: list[ProgramKey] = []
        for _context, program, _source_level, _target_level in rows:
            if program not in seen:
                seen.add(program)
                out.append(program)
        return tuple(out)

    def capability_programs_for_source(
        self, source_context: ContextKey
    ) -> tuple[ProgramKey, ...]:
        """Return programs actually witnessed from this exact public context."""
        context_key = self._context(source_context)
        _attempts, _refuted, _legal, capabilities = self._live()
        rows = [row for row in capabilities if row[0] == context_key]
        rows.sort(key=lambda row: (-row[3], len(row[1]), repr(row[1])))
        seen: set[ProgramKey] = set()
        out: list[ProgramKey] = []
        for _context, program, _source_level, _target_level in rows:
            if program not in seen:
                seen.add(program)
                out.append(program)
        return tuple(out)

    @staticmethod
    def _terminally_refuted(
        refuted: set[tuple[ContextKey, ProgramKey, str]],
        context: ContextKey,
        program: ProgramKey,
    ) -> bool:
        return any(
            candidate_context == context and candidate_program == program
            for candidate_context, candidate_program, _consequence in refuted
        )

    def is_closed(
        self,
        context: ContextKey,
        program: Iterable[ActionKey],
    ) -> bool:
        context_key = self._context(context)
        program_key = self._program(program)
        _attempts, refuted, legal, _capabilities = self._live()
        memo: dict[ProgramKey, bool] = {}

        def closed(prefix: ProgramKey) -> bool:
            if prefix in memo:
                return memo[prefix]
            if self._terminally_refuted(refuted, context_key, prefix):
                memo[prefix] = True
                return True
            next_actions = legal.get((context_key, prefix), ())
            if not next_actions:
                memo[prefix] = False
                return False
            value = all(closed(prefix + (action,)) for action in next_actions)
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
        _attempts, _refuted, legal, _capabilities = self._live()
        next_actions = legal.get((context_key, prefix_key), ())
        return {
            action
            for action in next_actions
            if self.is_closed(context_key, prefix_key + (action,))
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "events": [
                {"kind": kind, "payload": _jsonable(payload)}
                for kind, payload in self._log
            ]
        }

    def text(self) -> str:
        payload = json.dumps(self._payload(), sort_keys=True, separators=(",", ":"))
        return f"{self.VERSION}\n{payload}\n"

    @classmethod
    def parse(cls, text: str) -> "ArcMemoryGraph":
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines or lines[0] != cls.VERSION:
            raise ValueError("unsupported DuckTape ARC version")
        if len(lines) != 2:
            raise ValueError("malformed DuckTape ARC log")
        payload = json.loads(lines[1])
        rows = payload.get("events")
        if not isinstance(rows, list):
            raise ValueError("DuckTape events must be a list")

        events: list[Node] = []
        allowed = {"ATTEMPT", "LEGAL", "REFUTE", "CAPABILITY"}
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("malformed DuckTape event")
            kind = str(row.get("kind", ""))
            if kind not in allowed:
                raise ValueError(f"unsupported DuckTape node kind: {kind}")
            raw_payload = row.get("payload", [])
            frozen_payload = _freeze(raw_payload)
            if not isinstance(frozen_payload, tuple):
                raise ValueError("DuckTape event payload must be a sequence")
            events.append((kind, frozen_payload))

        out = cls(tuple(events))
        out._live()
        return out

    def digest(self) -> str:
        return hashlib.sha256(self.text().encode()).hexdigest()
