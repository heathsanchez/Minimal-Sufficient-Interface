from __future__ import annotations
from dataclasses import dataclass
from typing import Hashable, Iterable

@dataclass(frozen=True)
class RoleExample:
    hypothesis: str
    action: tuple[int,int|None,int|None]
    role: tuple[Hashable,...]
    outcome: str

@dataclass(frozen=True)
class CausalRolePredictor:
    mapping: dict[tuple[Hashable,...],str]
    conflicted_roles: frozenset[tuple[Hashable,...]]

    @classmethod
    def fit(cls, examples: Iterable[RoleExample]) -> "CausalRolePredictor":
        seen: dict[tuple[Hashable,...],set[str]]={}
        for row in examples:
            seen.setdefault(tuple(row.role),set()).add(str(row.outcome))
        conflicts=frozenset(role for role,vals in seen.items() if len(vals)!=1)
        mapping={role:next(iter(vals)) for role,vals in seen.items() if len(vals)==1}
        return cls(mapping,conflicts)

    def predict(self, role: tuple[Hashable,...]) -> str|None:
        return self.mapping.get(tuple(role))
