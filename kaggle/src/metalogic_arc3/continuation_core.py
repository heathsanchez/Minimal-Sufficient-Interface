"""Generated dependency slice; edit only through the pinned global source.
metalogiclabs/mathgraph@2efa47b2efc27434ed24dbf6ad6e1f50e463f947
Warranted historical observations do not certify unobserved dynamics.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

JSONScalar = str | int | float | bool | None

JSONValue = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]

def _canonical(value: Any) -> JSONValue:
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, Mapping):
        return {str(k): _canonical(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (set, frozenset)):
        return [_canonical(v) for v in sorted(value, key=repr)]
    if isinstance(value, tuple):
        return [_canonical(v) for v in value]
    if isinstance(value, list):
        return [_canonical(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"not canonically serializable: {type(value)!r}")

def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")

def content_id(value: Any, *, prefix: str = "mg") -> str:
    return f"{prefix}:{hashlib.sha256(canonical_bytes(value)).hexdigest()}"

_SEMANTIC_OBJECT_MAGIC = bytes((77, 71, 83, 79, 0, 1))

def _pack_u32(value: int) -> bytes:
    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError("value does not fit canonical u32")
    return value.to_bytes(4, "big")

def _pack_u64(value: int) -> bytes:
    if not 0 <= value <= 0xFFFFFFFFFFFFFFFF:
        raise ValueError("value does not fit canonical u64")
    return value.to_bytes(8, "big")

def _pack_text(value: str) -> bytes:
    data = value.encode("utf-8")
    return _pack_u32(len(data)) + data

@dataclass(frozen=True)
class SemanticObject:
    """Opaque, content-addressed semantic object envelope.

    The microkernel owns only this envelope. Payload is meaning-bearing
    canonical bytes defined by type_id + contract_version; an older runtime
    must preserve those bytes without interpreting or normalising them.
    Interfaces are stable semantic contracts advertised by the object and are
    canonicalised as a sorted set.

    Envelope encoding v1 is deterministic:
    MAGIC | type-id | u32 version | interface-set | u64 payload-len | payload.

    Unknown semantic types are valid objects. Unsupported interpretation
    returns UnknownSemantics rather than degrading the payload.
    """

    type_id: str
    contract_version: int
    payload: bytes
    interfaces: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.type_id:
            raise ValueError("semantic object type_id must be non-empty")
        if not 0 <= self.contract_version <= 0xFFFFFFFF:
            raise ValueError("contract_version must fit canonical u32")
        if not isinstance(self.payload, bytes):
            raise TypeError("semantic object payload must be bytes")
        if any(not interface for interface in self.interfaces):
            raise ValueError("interface ids must be non-empty")
        canonical_interfaces = tuple(sorted(set(self.interfaces)))
        object.__setattr__(self, "interfaces", canonical_interfaces)

    @property
    def id(self) -> str:
        return f"semantic:{hashlib.sha256(self.to_bytes()).hexdigest()}"

    def to_bytes(self) -> bytes:
        type_bytes = self.type_id.encode("utf-8")
        out = bytearray(_SEMANTIC_OBJECT_MAGIC)
        out += _pack_u32(len(type_bytes))
        out += type_bytes
        out += _pack_u32(self.contract_version)
        out += _pack_u32(len(self.interfaces))
        for interface in self.interfaces:
            out += _pack_text(interface)
        out += _pack_u64(len(self.payload))
        out += self.payload
        return bytes(out)

    @classmethod
    def from_bytes(cls, data: bytes) -> "SemanticObject":
        """Decode only the stable envelope; never interpret opaque payload."""

        if not isinstance(data, bytes):
            raise TypeError("semantic object transport must be bytes")
        if not data.startswith(_SEMANTIC_OBJECT_MAGIC):
            raise ValueError("unknown semantic object envelope")
        offset = len(_SEMANTIC_OBJECT_MAGIC)

        def take(count: int) -> bytes:
            nonlocal offset
            end = offset + count
            if count < 0 or end > len(data):
                raise ValueError("truncated semantic object")
            chunk = data[offset:end]
            offset = end
            return chunk

        def take_u32() -> int:
            return int.from_bytes(take(4), "big")

        def take_u64() -> int:
            return int.from_bytes(take(8), "big")

        type_id = take(take_u32()).decode("utf-8")
        contract_version = take_u32()
        interfaces = []
        for _ in range(take_u32()):
            interfaces.append(take(take_u32()).decode("utf-8"))
        payload = take(take_u64())
        if offset != len(data):
            raise ValueError("trailing bytes in semantic object")

        obj = cls(type_id, contract_version, payload, tuple(interfaces))
        if obj.to_bytes() != data:
            raise ValueError("non-canonical semantic object encoding")
        return obj

class ContinuationStatus(str, Enum):
    WARRANTED = "WARRANTED"
    EXCLUDED = "EXCLUDED"
    UNKNOWN = "UNKNOWN"

@dataclass(frozen=True)
class ProtectedContinuation:
    source: str
    continuation: str
    outcome: tuple[str, ...]
    status: ContinuationStatus
    target: str | None = None
    support_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source or not self.continuation:
            raise ValueError("source and continuation must be non-empty")
        if not self.outcome:
            raise ValueError("protected outcome must be non-empty")
        object.__setattr__(self, "support_refs", tuple(sorted(set(self.support_refs))))
        object.__setattr__(self, "evidence_refs", tuple(sorted(set(self.evidence_refs))))

    @property
    def id(self) -> str:
        return content_id(self, prefix="continuation")

    def is_live(self, live_supports: set[str] | frozenset[str]) -> bool:
        return self.status is ContinuationStatus.WARRANTED and set(self.support_refs).issubset(live_supports)

@dataclass(frozen=True)
class ProtectedContinuationMachine:
    boundary_ref: str
    states: tuple[str, ...]
    continuations: tuple[ProtectedContinuation, ...]

    def __post_init__(self) -> None:
        if not self.boundary_ref:
            raise ValueError("boundary_ref must be non-empty")
        canonical_states = tuple(sorted(set(self.states)))
        object.__setattr__(self, "states", canonical_states)
        known = set(canonical_states)
        for edge in self.continuations:
            if edge.source not in known:
                raise ValueError(f"unknown continuation source: {edge.source}")
            if edge.target is not None and edge.target not in known:
                raise ValueError(f"unknown continuation target: {edge.target}")
        ordered = tuple(sorted(
            self.continuations,
            key=lambda e: (e.source,e.continuation,e.outcome,e.status.value,e.target or "",e.support_refs,e.evidence_refs),
        ))
        if len({edge.id for edge in ordered}) != len(ordered):
            raise ValueError("duplicate protected continuation")
        object.__setattr__(self, "continuations", ordered)

    @property
    def id(self) -> str:
        return content_id(self, prefix="future-machine")

    def semantic_object(self) -> SemanticObject:
        payload = json.dumps({
            "boundary_ref": self.boundary_ref,
            "states": list(self.states),
            "continuations": [{
                "source": e.source, "continuation": e.continuation,
                "outcome": list(e.outcome), "status": e.status.value,
                "target": e.target, "support_refs": list(e.support_refs),
                "evidence_refs": list(e.evidence_refs),
            } for e in self.continuations],
        }, sort_keys=True, separators=(",", ":")).encode()
        return SemanticObject(
            type_id="future.protected.partial@1",
            contract_version=1,
            payload=payload,
            interfaces=("future.bracket@1","future.quotient@1","future.residual@1","future.support@1"),
        )

    def edges_from(self, state: str) -> tuple[ProtectedContinuation, ...]:
        if state not in self.states:
            raise KeyError(state)
        return tuple(e for e in self.continuations if e.source == state)

    def lower_signature(self, state: str):
        return tuple((e.continuation,e.outcome,e.target) for e in self.edges_from(state)
                     if e.status is ContinuationStatus.WARRANTED)

    def upper_signature(self, state: str):
        return tuple((e.continuation,e.outcome,e.target) for e in self.edges_from(state)
                     if e.status is not ContinuationStatus.EXCLUDED)

    def unresolved(self, state: str | None = None):
        edges = self.continuations if state is None else self.edges_from(state)
        return tuple(e for e in edges if e.status is ContinuationStatus.UNKNOWN)

    def live_signature(self, state: str, live_supports: set[str] | frozenset[str]):
        return tuple((e.continuation,e.outcome,e.target) for e in self.edges_from(state)
                     if e.is_live(live_supports))

    def future_classes(self, *, use_upper: bool = False):
        groups = {}
        for state in self.states:
            sig = self.upper_signature(state) if use_upper else self.lower_signature(state)
            groups.setdefault(sig, []).append(state)
        return {sig: tuple(sorted(items)) for sig,items in groups.items()}

def relation_machine(states: Iterable[str], relations: Iterable[tuple[str,str,str,tuple[str,...]]], *, boundary_ref: str):
    edges=[]
    for left,right,relation,evidence_refs in relations:
        if relation not in {"equivalent","implies","separated"}:
            raise ValueError(relation)
        edges.append(ProtectedContinuation(left,f"relation:{relation}",(right,),ContinuationStatus.WARRANTED,evidence_refs=evidence_refs))
    return ProtectedContinuationMachine(boundary_ref,tuple(states),tuple(edges))

def equivalence_classes_from_relations(machine: ProtectedContinuationMachine):
    parent={s:s for s in machine.states}
    def find(x):
        while parent[x] != x:
            parent[x]=parent[parent[x]]
            x=parent[x]
        return x
    def union(a,b):
        ra,rb=find(a),find(b)
        if ra != rb:
            if ra < rb: parent[rb]=ra
            else: parent[ra]=rb
    for e in machine.continuations:
        if e.status is ContinuationStatus.WARRANTED and e.continuation=="relation:equivalent":
            union(e.source,e.outcome[0])
    groups={}
    for s in machine.states:
        groups.setdefault(find(s),[]).append(s)
    return tuple(sorted(tuple(sorted(g)) for g in groups.values()))
