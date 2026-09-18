"""Typed downstream outcomes aligned with frozen `QCK.API`.

These Python records carry developmental evidence.  They mirror the names of
the frozen Lean boundary without pretending to re-prove its theorems.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

E = TypeVar("E")
S = TypeVar("S")


@dataclass(frozen=True)
class ReserveRequired:
    snapshot_rank: int
    maintained_rank: int

    def __post_init__(self) -> None:
        if self.snapshot_rank < 0 or self.maintained_rank < 0:
            raise ValueError("reserve ranks must be nonnegative")


@dataclass(frozen=True)
class RecoveryUnavailable(Generic[E]):
    evidence: E


@dataclass(frozen=True)
class ImplementationMismatch(Generic[E]):
    evidence: E


@dataclass(frozen=True)
class CertificateInvalid(Generic[E]):
    evidence: E


@dataclass(frozen=True)
class OutOfScope(Generic[S]):
    scope: S


@dataclass(frozen=True)
class Unknown(Generic[E]):
    evidence: E
