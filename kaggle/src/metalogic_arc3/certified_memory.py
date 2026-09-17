from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from .memory_graph import (
    ActionKey,
    ArcMemoryGraph,
    CapabilityKey,
    ContextKey,
    ProgramKey,
    _jsonable,
)

Checkpoint = tuple[int, ActionKey, str, tuple[int, int, int, int, int, int]]


class CertifiedArcMemoryGraph(ArcMemoryGraph):
    """MG-ARC5: source capability + finite consequence contract + target trial state."""

    VERSION = "MG-ARC5"
    STATUSES = {
        "OPEN_PROBE",
        "PREFIX_REQUALIFIED",
        "CONTRACT_MISMATCH",
        "EXPIRED_UNCONFIRMED",
        "WITNESSED_PROGRESS",
    }

    def __init__(self) -> None:
        super().__init__()
        self._capability_contracts: dict[CapabilityKey, dict[str, Any]] = {}

    def _capability_key(
        self,
        source_context: ContextKey,
        program: Iterable[ActionKey],
        source_level: int,
        target_level: int,
    ) -> CapabilityKey:
        return (
            self._context(source_context),
            self._program(program),
            int(source_level),
            int(target_level),
        )

    def _normalize_checkpoints(
        self,
        program: ProgramKey,
        checkpoints: Iterable[Iterable[Any]],
    ) -> tuple[Checkpoint, ...]:
        out: list[Checkpoint] = []
        for position, raw in enumerate(checkpoints):
            row = tuple(raw)
            if len(row) != 4:
                raise ValueError("checkpoint must be (index, action, descriptor, signature)")
            index, action_raw, descriptor, signature_raw = row
            index = int(index)
            action = self._action(action_raw)
            signature = tuple(int(value) for value in signature_raw)
            if len(signature) != 6:
                raise ValueError("structural effect signature must contain six integers")
            if index != position or index >= len(program):
                raise ValueError("checkpoint indices must be consecutive program positions")
            if action != program[index]:
                raise ValueError("checkpoint action must match source program")
            descriptor = str(descriptor)
            if not descriptor:
                raise ValueError("checkpoint descriptor must be nonempty")
            out.append((index, action, descriptor, signature))
            if len(out) > 8:
                raise ValueError("MG-ARC5 retains at most eight requalification checkpoints")
        if not out:
            raise ValueError("capability contract requires at least one checkpoint")
        return tuple(out)

    @staticmethod
    def _contract_digest(
        key: CapabilityKey,
        checkpoints: tuple[Checkpoint, ...],
        protected_outcome: str,
    ) -> str:
        payload = {
            "source_context": _jsonable(key[0]),
            "program": _jsonable(key[1]),
            "source_level": key[2],
            "target_level": key[3],
            "checkpoints": _jsonable(checkpoints),
            "protected_outcome": protected_outcome,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def add_capability_contract(
        self,
        source_context: ContextKey,
        program: Iterable[ActionKey],
        *,
        source_level: int,
        target_level: int,
        checkpoints: Iterable[Iterable[Any]],
        protected_outcome: str = "LEVEL_INCREMENT",
    ) -> str:
        key = self._capability_key(source_context, program, source_level, target_level)
        if key not in self._capabilities:
            raise ValueError("contract must attach to an existing witnessed capability")
        if protected_outcome != "LEVEL_INCREMENT":
            raise ValueError("unsupported protected outcome")
        normalized = self._normalize_checkpoints(key[1], checkpoints)
        digest = self._contract_digest(key, normalized, protected_outcome)
        self._capability_contracts[key] = {
            "checkpoints": normalized,
            "protected_outcome": protected_outcome,
            "digest": digest,
        }
        return digest

    def certified_capability_candidates(
        self, for_level: int | None = None
    ) -> tuple[dict[str, Any], ...]:
        rows = [
            key for key in self._capabilities
            if key in self._capability_contracts
            and (for_level is None or key[3] <= int(for_level))
        ]
        rows.sort(key=lambda key: (-key[3], len(key[1]), repr(key[1]), repr(key[0])))
        out: list[dict[str, Any]] = []
        seen: set[ProgramKey] = set()
        for key in rows:
            if key[1] in seen:
                continue
            seen.add(key[1])
            contract = self._capability_contracts[key]
            out.append({
                "source_context": key[0],
                "program": key[1],
                "source_level": key[2],
                "target_level": key[3],
                "checkpoints": contract["checkpoints"],
                "protected_outcome": contract["protected_outcome"],
                "digest": contract["digest"],
            })
        return tuple(out)

    def _certified_program(self, level: int, program: ProgramKey) -> dict[str, Any] | None:
        return next(
            (row for row in self.certified_capability_candidates(level)
             if row["program"] == program),
            None,
        )

    def transfer_trial(
        self, target_level: int, program: Iterable[ActionKey] | None = None
    ) -> dict[str, Any] | None:
        level = int(target_level)
        if program is not None:
            frozen = self._program(program)
            row = self._transfer_trials.get((level, frozen))
            return None if row is None else {"program": frozen, **row}
        matches = [
            (candidate, row)
            for (target, candidate), row in self._transfer_trials.items()
            if target == level
        ]
        if not matches:
            return None
        candidate, row = sorted(matches, key=lambda item: repr(item[0]))[0]
        return {"program": candidate, **row}

    def transfer_remaining(
        self, target_level: int, program: Iterable[ActionKey], max_actions: int,
    ) -> int:
        level, cap = int(target_level), int(max_actions)
        if level < 0 or cap < 1:
            raise ValueError("nonnegative target and positive trial cap required")
        base = self._program(program)
        candidate = self._certified_program(level, base)
        if candidate is None:
            return 0
        row = self._transfer_trials.get((level, base))
        if row and row["status"] in {
            "CONTRACT_MISMATCH", "EXPIRED_UNCONFIRMED", "WITNESSED_PROGRESS"
        }:
            return 0
        cap = min(cap, self._transfer_limits.get(level, cap))
        issued = sum(
            int(value["issued"])
            for (target, _), value in self._transfer_trials.items()
            if target == level
        )
        return max(0, cap - issued)

    def issue_transfer(
        self, target_level: int, program: Iterable[ActionKey], max_actions: int,
    ) -> bool:
        level, cap = int(target_level), int(max_actions)
        base = self._program(program)
        candidate = self._certified_program(level, base)
        if candidate is None or not self.transfer_remaining(level, base, cap):
            return False
        self._transfer_limits.setdefault(level, cap)
        row = self._transfer_trials.setdefault(
            (level, base),
            {
                "issued": 0,
                "status": "OPEN_PROBE",
                "matched": 0,
                "contract_digest": candidate["digest"],
            },
        )
        if row["contract_digest"] != candidate["digest"]:
            raise ValueError("target trial contract changed after admission")
        row["issued"] += 1
        return True

    def mark_probe_match(
        self,
        target_level: int,
        program: Iterable[ActionKey],
        *,
        contract_digest: str,
        checkpoint_count: int,
    ) -> str:
        key = (int(target_level), self._program(program))
        row = self._transfer_trials.get(key)
        if row is None or row["status"] != "OPEN_PROBE":
            raise ValueError("no open probe to advance")
        if row["contract_digest"] != str(contract_digest):
            raise ValueError("probe evidence belongs to a different contract")
        row["matched"] += 1
        if row["matched"] >= int(checkpoint_count):
            row["status"] = "PREFIX_REQUALIFIED"
        return row["status"]

    def mark_contract_mismatch(
        self, target_level: int, program: Iterable[ActionKey]
    ) -> None:
        row = self._transfer_trials.get((int(target_level), self._program(program)))
        if row is not None and row["status"] == "OPEN_PROBE":
            row["status"] = "CONTRACT_MISMATCH"

    def finish_transfer(
        self,
        target_level: int,
        program: Iterable[ActionKey],
        status: str = "EXPIRED_UNCONFIRMED",
    ) -> None:
        if status not in ("EXPIRED_UNCONFIRMED", "WITNESSED_PROGRESS"):
            raise ValueError("invalid transfer disposition")
        row = self._transfer_trials.get((int(target_level), self._program(program)))
        if row is None:
            return
        if status == "WITNESSED_PROGRESS":
            row["status"] = status
        elif row["status"] in ("OPEN_PROBE", "PREFIX_REQUALIFIED"):
            row["status"] = status

    def _payload(self) -> dict[str, Any]:
        payload = super()._payload()
        payload["capability_contracts"] = [
            {
                "source_context": _jsonable(key[0]),
                "program": _jsonable(key[1]),
                "source_level": key[2],
                "target_level": key[3],
                "checkpoints": _jsonable(contract["checkpoints"]),
                "protected_outcome": contract["protected_outcome"],
                "digest": contract["digest"],
            }
            for key, contract in sorted(self._capability_contracts.items(), key=lambda item: repr(item[0]))
        ]
        payload["transfer_trials"] = [
            {
                "target_level": level,
                "program": _jsonable(program),
                "issued": int(row["issued"]),
                "status": row["status"],
                "matched": int(row.get("matched", 0)),
                "contract_digest": str(row.get("contract_digest", "")),
            }
            for (level, program), row in sorted(self._transfer_trials.items(), key=lambda item: repr(item[0]))
        ]
        return payload

    @classmethod
    def parse(cls, text: str) -> "CertifiedArcMemoryGraph":
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) != 2 or lines[0] not in ("MG-ARC3", "MG-ARC4", cls.VERSION):
            raise ValueError("unsupported ARC .mg version")
        version = lines[0]
        payload = json.loads(lines[1])

        sanitized = dict(payload)
        sanitized["transfer_limits"] = []
        sanitized["transfer_trials"] = []
        sanitized.pop("capability_contracts", None)
        legacy_header = "MG-ARC3" if version == "MG-ARC3" else "MG-ARC4"
        base = ArcMemoryGraph.parse(
            legacy_header + "\n" + json.dumps(sanitized, sort_keys=True, separators=(",", ":")) + "\n"
        )
        out = cls()
        out._attempts = dict(base._attempts)
        out._refuted = set(base._refuted)
        out._legal = dict(base._legal)
        out._capabilities = set(base._capabilities)

        for row in payload.get("capability_contracts", []):
            digest = out.add_capability_contract(
                out._context(row["source_context"]),
                out._program(row["program"]),
                source_level=int(row["source_level"]),
                target_level=int(row["target_level"]),
                checkpoints=row["checkpoints"],
                protected_outcome=str(row.get("protected_outcome", "LEVEL_INCREMENT")),
            )
            if row.get("digest") not in (None, digest):
                raise ValueError("capability contract digest mismatch")

        for row in payload.get("transfer_limits", []):
            level, cap = int(row["target_level"]), int(row["max_actions"])
            if level < 0 or cap < 1 or level in out._transfer_limits:
                raise ValueError("invalid or duplicate target transfer limit")
            out._transfer_limits[level] = cap

        for raw in payload.get("transfer_trials", []):
            level = int(raw["target_level"])
            program = out._program(raw["program"])
            issued = int(raw["issued"])
            key = (level, program)
            if issued < 1 or key in out._transfer_trials:
                raise ValueError("invalid or duplicate transfer trial")
            if version == cls.VERSION:
                status = str(raw["status"])
                matched = int(raw.get("matched", 0))
                contract_digest = str(raw.get("contract_digest", ""))
                if status not in cls.STATUSES or matched < 0:
                    raise ValueError("invalid transfer trial status")
                candidate = out._certified_program(level, program)
                if candidate is None:
                    raise ValueError("MG-ARC5 transfer trial lacks certified source capability")
                if contract_digest != candidate["digest"]:
                    raise ValueError("transfer trial contract digest mismatch")
                if matched > len(candidate["checkpoints"]):
                    raise ValueError("transfer trial matched count exceeds contract")
            else:
                old_status = str(raw.get("status", "EXPIRED_UNCONFIRMED"))
                status = "WITNESSED_PROGRESS" if old_status == "WITNESSED_PROGRESS" else "EXPIRED_UNCONFIRMED"
                matched = 0
                contract_digest = ""
            out._transfer_trials[key] = {
                "issued": issued,
                "status": status,
                "matched": matched,
                "contract_digest": contract_digest,
            }

        for level, cap in out._transfer_limits.items():
            issued = sum(
                int(row["issued"])
                for (target, _), row in out._transfer_trials.items()
                if target == level
            )
            if issued > cap:
                raise ValueError("transfer trial allowance exceeded")
        return out
