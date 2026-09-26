from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Iterable

ActionKey = tuple[int, int | None, int | None]
ContextKey = tuple[Any, ...]


def _freeze(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((str(key), _freeze(item)) for key, item in value.items()))
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


class LawStatus(str, Enum):
    WARRANTED = "WARRANTED"
    EXCLUDED = "EXCLUDED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class VerifiedLaw:
    law_id: str
    kind: str
    statement: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.law_id or not self.kind or not self.statement:
            raise ValueError("law identity, kind and statement are required")
        object.__setattr__(self, "evidence_refs", tuple(sorted(set(self.evidence_refs))))


FINITE_CYCLE_NORMALIZATION = VerifiedLaw(
    law_id="law:finite-cycle-normalization@1",
    kind="finite-cycle-normalization",
    statement=(
        "For a protected deterministic operator with verified period p>0, "
        "n repetitions have the same protected outcome as n mod p repetitions."
    ),
    evidence_refs=("builtin:finite-modular-arithmetic@1",),
)


class VerifiedLawStore:
    def __init__(self, laws: Iterable[VerifiedLaw]) -> None:
        ordered = tuple(sorted(laws, key=lambda law: law.law_id))
        if len({law.law_id for law in ordered}) != len(ordered):
            raise ValueError("duplicate law id")
        self._laws = {law.law_id: law for law in ordered}

    @classmethod
    def default(cls) -> "VerifiedLawStore":
        return cls((FINITE_CYCLE_NORMALIZATION,))

    def get(self, law_id: str) -> VerifiedLaw | None:
        return self._laws.get(law_id)

    @property
    def law_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._laws))


@dataclass(frozen=True)
class ArcLawBinding:
    context: ContextKey
    action: ActionKey
    period: int
    protected_orbit: tuple[str, ...]
    support_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        context = _freeze(self.context)
        action = tuple(self.action)
        if not isinstance(context, tuple) or not context:
            raise ValueError("binding context must be a nonempty tuple")
        if len(action) != 3:
            raise ValueError("action must be (action_id, x, y)")
        if self.period < 1:
            raise ValueError("period must be positive")
        if len(self.protected_orbit) != self.period + 1:
            raise ValueError("orbit must contain exactly period+1 protected states")
        if self.protected_orbit[0] != self.protected_orbit[-1]:
            raise ValueError("orbit must close at the declared period")
        if len(set(self.protected_orbit[:-1])) != self.period:
            raise ValueError("declared period must be the first protected return")
        if not self.support_refs:
            raise ValueError("applicability binding requires live support")
        object.__setattr__(self, "context", context)
        object.__setattr__(
            self, "action",
            (int(action[0]), None if action[1] is None else int(action[1]),
             None if action[2] is None else int(action[2])),
        )
        object.__setattr__(self, "protected_orbit", tuple(str(x) for x in self.protected_orbit))
        object.__setattr__(self, "support_refs", tuple(sorted(set(self.support_refs))))
        object.__setattr__(self, "evidence_refs", tuple(sorted(set(self.evidence_refs))))

    @property
    def binding_id(self) -> str:
        return "arc-binding:" + _digest({
            "context": self.context,
            "action": self.action,
            "period": self.period,
            "protected_orbit": self.protected_orbit,
            "support_refs": self.support_refs,
            "evidence_refs": self.evidence_refs,
        })


@dataclass(frozen=True)
class LawAnswer:
    status: LawStatus
    law_id: str
    original_count: int
    reduced_count: int
    reason: str
    provenance: tuple[str, ...] = ()
    binding_id: str | None = None
    residual: dict[str, Any] | None = None


class ArcCrystalLawBridge:
    """Query verified generic laws under separately earned ARC applicability bindings."""

    CYCLE_LAW_ID = FINITE_CYCLE_NORMALIZATION.law_id

    def __init__(self, laws: VerifiedLawStore) -> None:
        self.laws = laws
        self._bindings: dict[tuple[ContextKey, ActionKey], ArcLawBinding] = {}

    @staticmethod
    def _key(context: ContextKey, action: ActionKey) -> tuple[ContextKey, ActionKey]:
        frozen = _freeze(context)
        if not isinstance(frozen, tuple):
            raise TypeError("context must be tuple-like")
        raw = tuple(action)
        if len(raw) != 3:
            raise ValueError("action must have three fields")
        canonical = (
            int(raw[0]),
            None if raw[1] is None else int(raw[1]),
            None if raw[2] is None else int(raw[2]),
        )
        return frozen, canonical

    def admit_binding(self, binding: ArcLawBinding) -> None:
        self._bindings[self._key(binding.context, binding.action)] = binding

    def normalize_repetition(
        self,
        context: ContextKey,
        action: ActionKey,
        count: int,
        *,
        live_supports: Iterable[str] = (),
    ) -> LawAnswer:
        if count < 0:
            raise ValueError("count must be nonnegative")
        law = self.laws.get(self.CYCLE_LAW_ID)
        if law is None:
            return LawAnswer(
                LawStatus.UNKNOWN, self.CYCLE_LAW_ID, count, count,
                "missing_verified_law",
                residual={"needed": "verified-law", "law_id": self.CYCLE_LAW_ID},
            )

        binding = self._bindings.get(self._key(context, action))
        if binding is None:
            return LawAnswer(
                LawStatus.UNKNOWN, law.law_id, count, count,
                "missing_applicability_binding",
                provenance=law.evidence_refs,
                residual={
                    "needed": "finite-cycle-binding",
                    "law_id": law.law_id,
                    "context": list(_freeze(context)),
                    "action": list(self._key(context, action)[1]),
                },
            )

        live = set(str(x) for x in live_supports)
        missing = tuple(sorted(set(binding.support_refs) - live))
        provenance = tuple(sorted(set(law.evidence_refs + binding.evidence_refs + binding.support_refs)))
        if missing:
            return LawAnswer(
                LawStatus.UNKNOWN, law.law_id, count, count,
                "missing_live_support",
                provenance=provenance,
                binding_id=binding.binding_id,
                residual={
                    "needed": "live-binding-support",
                    "missing_supports": list(missing),
                    "binding_id": binding.binding_id,
                },
            )

        return LawAnswer(
            LawStatus.WARRANTED,
            law.law_id,
            count,
            count % binding.period,
            "verified_cycle_normalization",
            provenance=provenance,
            binding_id=binding.binding_id,
        )
