"""Verified JOIN -> REIFY -> TEST -> PROMOTE layer.

This module deliberately does not decide truth. It organizes already-grounded dots,
asks heterogeneous join generators for candidate relations, turns those relations into
operational reifications, and promotes only candidates accepted by an external test plus
an ablation check.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class Dot:
    id: str
    kind: str
    statement: str
    evidence: dict[str, Any]
    tags: tuple[str, ...] = ()
    parents: tuple[str, ...] = ()
    consequential: bool = True


@dataclass(frozen=True)
class JoinCandidate:
    id: str
    strategy: str
    dot_ids: tuple[str, ...]
    relation: str
    proposed_object: str
    prediction: str
    falsifier: str
    novelty: str = ""


@dataclass(frozen=True)
class Reification:
    id: str
    candidate_id: str
    object_type: str
    name: str
    definition: dict[str, Any]
    prediction: str
    verifier_id: str


@dataclass(frozen=True)
class TestResult:
    accepted: bool
    consequential: bool
    evidence: dict[str, Any]
    reason: str
    residual_after: str


@dataclass(frozen=True)
class AblationResult:
    causal: bool
    evidence: dict[str, Any]
    reason: str


@dataclass
class JoinState:
    residual: str
    dots: list[Dot] = field(default_factory=list)
    candidates: list[JoinCandidate] = field(default_factory=list)
    reifications: list[Reification] = field(default_factory=list)
    promoted: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)
    process_residuals: list[str] = field(default_factory=list)

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


JoinGenerator = Callable[[str, tuple[Dot, ...]], Iterable[JoinCandidate]]
Reifier = Callable[[JoinCandidate], Reification]
ExternalTest = Callable[[Reification, JoinState], TestResult]
Ablator = Callable[[Reification, JoinState, TestResult], AblationResult]


class VerifiedJoinReifyEngine:
    """Loose proposal boundary, hard promotion boundary."""

    def __init__(
        self,
        join_generators: dict[str, JoinGenerator],
        reifier: Reifier,
        tests: dict[str, ExternalTest],
        ablator: Ablator,
        max_candidates: int = 100,
    ) -> None:
        self.join_generators = join_generators
        self.reifier = reifier
        self.tests = tests
        self.ablator = ablator
        self.max_candidates = max_candidates

    @staticmethod
    def retrieve(state: JoinState, limit: int = 24) -> tuple[Dot, ...]:
        """Residual-directed retrieval without pretending lexical score is semantic truth."""
        words = {w.lower().strip('.,:;()[]') for w in state.residual.split() if len(w) > 3}
        ranked = []
        for dot in state.dots:
            hay = (dot.statement + ' ' + ' '.join(dot.tags)).lower()
            score = sum(1 for w in words if w in hay) + 2 * int(dot.consequential)
            ranked.append((score, dot.id, dot))
        ranked.sort(key=lambda x: (-x[0], x[1]))
        return tuple(x[2] for x in ranked[:limit])

    @staticmethod
    def _semantic_key(c: JoinCandidate) -> str:
        text = ' '.join((c.relation, c.proposed_object, c.prediction)).lower()
        return ' '.join(text.split())

    def generate(self, state: JoinState) -> list[JoinCandidate]:
        dots = self.retrieve(state)
        seen: set[str] = set()
        out: list[JoinCandidate] = []
        for strategy, generator in self.join_generators.items():
            for c in generator(state.residual, dots):
                if c.strategy != strategy:
                    raise RuntimeError(f'JOIN strategy mismatch: {c.strategy} != {strategy}')
                if not set(c.dot_ids).issubset({d.id for d in dots}):
                    raise RuntimeError(f'JOIN used unavailable dot: {c.id}')
                key = self._semantic_key(c)
                if key in seen:
                    continue
                seen.add(key)
                out.append(c)
                if len(out) >= self.max_candidates:
                    state.candidates.extend(out)
                    return out
        state.candidates.extend(out)
        return out

    def test_and_promote(self, state: JoinState, candidates: Iterable[JoinCandidate]) -> JoinState:
        for candidate in candidates:
            r = self.reifier(candidate)
            state.reifications.append(r)
            if r.verifier_id not in self.tests:
                state.rejected.append({'candidate': asdict(candidate), 'reason': 'no verifier'})
                continue
            tested = self.tests[r.verifier_id](r, state)
            record = {'candidate': asdict(candidate), 'reification': asdict(r), 'test': asdict(tested)}
            if not (tested.accepted and tested.consequential):
                state.rejected.append(record)
                continue
            ablated = self.ablator(r, state, tested)
            record['ablation'] = asdict(ablated)
            if not ablated.causal:
                state.rejected.append(record)
                continue
            state.promoted.append(record)
            state.dots.append(Dot(
                id=f'promoted:{r.id}',
                kind='promoted-concept',
                statement=f'{r.name}: {candidate.relation}',
                evidence={'test': asdict(tested), 'ablation': asdict(ablated)},
                tags=(r.object_type, candidate.strategy, 'reified'),
                parents=candidate.dot_ids,
                consequential=True,
            ))
            state.residual = tested.residual_after
        if not state.promoted and state.candidates:
            state.process_residuals.append(
                'JOIN produced candidates but none survived truth + consequence + ablation; diagnose retrieval, join diversity, reification, or verifier coverage.'
            )
        elif not state.candidates:
            state.process_residuals.append(
                'No nonduplicate JOIN candidates were generated; expand retrieval or generator diversity before changing the object-level representation.'
            )
        return state

    def run(self, state: JoinState) -> JoinState:
        return self.test_and_promote(state, self.generate(state))
