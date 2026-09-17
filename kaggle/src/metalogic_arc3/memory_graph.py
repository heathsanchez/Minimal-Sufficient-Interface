from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

ActionKey = tuple[int, int | None, int | None]
ContextKey = tuple[Any, ...]
ProgramKey = tuple[ActionKey, ...]
CapabilityKey = tuple[ContextKey, ProgramKey, int, int]


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

    MG-ARC4 retains only facts that have earned future relevance:
    * purchased interventions by public context;
    * exact terminally refuted programs;
    * observed legal branching for exact finite closure; and
    * source-scoped programs that actually caused a level increment; and
    * nonrefundable target-scoped trial allowances for speculative reuse.

    A capability is verified only at its witnessed source context.  Exposing its
    program elsewhere makes it a *hypothesis constructor*, never a universal
    rule.  New contexts must earn their own consequence evidence.
    """

    VERSION = "MG-ARC4"

    def __init__(self) -> None:
        self._attempts: dict[tuple[ContextKey, ActionKey], int] = {}
        self._refuted: set[tuple[ContextKey, ProgramKey, str]] = set()
        self._legal: dict[tuple[ContextKey, ProgramKey], tuple[ActionKey, ...]] = {}
        self._capabilities: set[CapabilityKey] = set()
        # A scheduling scope is NOT a state-equivalence class. Each agent owns
        # one game session; completed-level count names its target obligation.
        # Raster changes and RESET cannot create a fresh action allowance.
        self._transfer_limits: dict[int, int] = {}
        self._transfer_trials: dict[tuple[int, ProgramKey], dict[str, Any]] = {}

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

    @property
    def capability_count(self) -> int:
        return len(self._capabilities)

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
        self._capabilities.add(
            (self._context(source_context), frozen_program, source_level, target_level)
        )

    def capability_programs(self, for_level: int | None = None) -> tuple[ProgramKey, ...]:
        """Return unique witnessed programs ordered by freshest source progress.

        `for_level` is the current completed-level count.  A capability may be
        proposed only after its witnessed target level has been reached, which
        prevents a learned later-stage program from displacing an earlier exact
        retained replay after RESET.
        """
        rows = [
            row for row in self._capabilities
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

    def transfer_remaining(
        self, target_level: int, program: Iterable[ActionKey], max_actions: int,
    ) -> int:
        """Remaining hypothesis allowance, never a semantic success claim.

        The cap is shared by ALL source programs for this target obligation.
        Issued proposals are charged conservatively before the controller's
        final trie filter; rejected proposals are not refunded. Thus actual
        speculative environment calls cannot exceed this issued-action cap.
        """
        level, cap = int(target_level), int(max_actions)
        if level < 0 or cap < 1:
            raise ValueError("nonnegative target and positive trial cap required")
        base = self._program(program)
        if not base or base not in self.capability_programs(for_level=level):
            return 0
        trial = self._transfer_trials.get((level, base))
        if trial and trial["status"] != "OPEN":
            return 0
        cap = min(cap, self._transfer_limits.get(level, cap))
        issued = sum(row["issued"] for (target, _), row in self._transfer_trials.items()
                     if target == level)
        return max(0, cap - issued)

    def issue_transfer(
        self, target_level: int, program: Iterable[ActionKey], max_actions: int,
    ) -> bool:
        """Reserve one proposal slot; RESET and restart never refund it."""
        level, cap = int(target_level), int(max_actions)
        base = self._program(program)
        if not self.transfer_remaining(level, base, cap):
            return False
        self._transfer_limits.setdefault(level, cap)
        row = self._transfer_trials.setdefault(
            (level, base), {"issued": 0, "status": "OPEN"})
        row["issued"] += 1
        return True

    def finish_transfer(
        self, target_level: int, program: Iterable[ActionKey],
        status: str = "EXPIRED_UNCONFIRMED",
    ) -> None:
        if status not in ("EXPIRED_UNCONFIRMED", "WITNESSED_PROGRESS"):
            raise ValueError("invalid transfer disposition")
        row = self._transfer_trials.get((int(target_level), self._program(program)))
        if row is not None:
            row["status"] = status

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
        capabilities = [
            {
                "source_context": _jsonable(context),
                "program": _jsonable(program),
                "source_level": source_level,
                "target_level": target_level,
            }
            for context, program, source_level, target_level in sorted(
                self._capabilities, key=repr
            )
        ]
        transfer_limits = [
            {"target_level": level, "max_actions": cap}
            for level, cap in sorted(self._transfer_limits.items())
        ]
        transfer_trials = [
            {"target_level": level, "program": _jsonable(program),
             "issued": row["issued"], "status": row["status"]}
            for (level, program), row in sorted(self._transfer_trials.items(), key=lambda item: repr(item[0]))
        ]
        return {
            "transfer_limits": transfer_limits,
            "transfer_trials": transfer_trials,
            "attempts": attempts,
            "refuted": refuted,
            "legal": legal,
            "capabilities": capabilities,
        }

    def text(self) -> str:
        payload = json.dumps(self._payload(), sort_keys=True, separators=(",", ":"))
        return f"{self.VERSION}\n{payload}\n"

    @classmethod
    def parse(cls, text: str) -> "ArcMemoryGraph":
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines or lines[0] not in (cls.VERSION, "MG-ARC3"):
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
        for row in payload.get("capabilities", []):
            out.add_capability(
                out._context(row["source_context"]),
                out._program(row["program"]),
                source_level=int(row["source_level"]),
                target_level=int(row["target_level"]),
            )
        for row in payload.get("transfer_limits", []):
            level, cap = int(row["target_level"]), int(row["max_actions"])
            if level < 0 or cap < 1 or level in out._transfer_limits:
                raise ValueError("invalid or duplicate target transfer limit")
            out._transfer_limits[level] = cap
        for row in payload.get("transfer_trials", []):
            level = int(row["target_level"])
            program = out._program(row["program"])
            issued, status = int(row["issued"]), str(row["status"])
            key = (level, program)
            if (level not in out._transfer_limits or issued < 1
                    or key in out._transfer_trials
                    or status not in ("OPEN", "EXPIRED_UNCONFIRMED", "WITNESSED_PROGRESS")
                    or program not in out.capability_programs(for_level=level)):
                raise ValueError("invalid or unsupported transfer trial")
            out._transfer_trials[key] = {"issued": issued, "status": status}
        for level, cap in out._transfer_limits.items():
            issued = sum(row["issued"] for (target, _), row in out._transfer_trials.items()
                         if target == level)
            if issued > cap:
                raise ValueError("transfer trial allowance exceeded")
        return out

    def digest(self) -> str:
        return hashlib.sha256(self.text().encode()).hexdigest()
