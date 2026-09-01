"""Residual-driven synthesis of realization coordinates.

This module is deliberately domain-agnostic.  It receives a finite carrier,
primitive observations and a fixed constructor grammar.  It enumerates semantic
expressions, then keeps exactly those coordinates whose addition to the current
interface realizes the canonical consequence-sufficient quotient.

Protected-consequence names and known successful realizer names are never used
by the search procedure.  They are consulted only by the existing consequence
compiler when it computes the required quotient and by tests after synthesis to
interpret what was rediscovered.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Hashable, Mapping, Sequence, Tuple

from consequence_compiler import CompilerReport, CompilerSpec, compile_consequences, kernel

Observation = Callable[[Hashable], Hashable]
UnaryConstructor = Callable[[Hashable], Hashable]
BinaryConstructor = Callable[[Hashable, Hashable], Hashable]


@dataclass(frozen=True)
class Expression:
    text: str
    size: int
    values: Tuple[Hashable, ...]

    def observation(self, carrier: Tuple[Hashable, ...]) -> Observation:
        table = dict(zip(carrier, self.values))
        return lambda x, table=table: table[x]


@dataclass(frozen=True)
class SynthesisGrammar:
    primitives: Mapping[str, Observation]
    unary: Mapping[str, UnaryConstructor]
    binary: Mapping[str, BinaryConstructor]
    max_size: int = 3

    def __post_init__(self):
        if not self.primitives:
            raise ValueError("synthesis grammar requires at least one primitive")
        if self.max_size < 1:
            raise ValueError("max_size must be positive")


@dataclass(frozen=True)
class SynthesizedCompilerReport:
    base: CompilerReport
    expressions: Tuple[Expression, ...]
    lawful_expressions: Tuple[Expression, ...]
    minimal_lawful_size: int | None


def _safe_unary(fn: UnaryConstructor, values: Tuple[Hashable, ...]):
    try:
        return tuple(fn(v) for v in values)
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        return None


def _safe_binary(fn: BinaryConstructor, left: Tuple[Hashable, ...], right: Tuple[Hashable, ...]):
    try:
        return tuple(fn(a, b) for a, b in zip(left, right))
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        return None


def enumerate_expressions(
    carrier: Tuple[Hashable, ...],
    grammar: SynthesisGrammar,
) -> Tuple[Expression, ...]:
    """Enumerate one cheapest representative per extensional observation."""
    by_values: Dict[Tuple[Hashable, ...], Expression] = {}
    frontier: Dict[int, list[Expression]] = {}

    for name, primitive in grammar.primitives.items():
        values = tuple(primitive(x) for x in carrier)
        expr = Expression(name, 1, values)
        old = by_values.get(values)
        if old is None or (expr.size, expr.text) < (old.size, old.text):
            by_values[values] = expr

    frontier[1] = sorted(by_values.values(), key=lambda e: e.text)

    for size in range(2, grammar.max_size + 1):
        new: list[Expression] = []

        for op_name, op in grammar.unary.items():
            for child in tuple(by_values.values()):
                if child.size + 1 != size:
                    continue
                values = _safe_unary(op, child.values)
                if values is None:
                    continue
                expr = Expression(f"{op_name}({child.text})", size, values)
                old = by_values.get(values)
                if old is None or (expr.size, expr.text) < (old.size, old.text):
                    by_values[values] = expr
                    new.append(expr)

        existing = tuple(by_values.values())
        for op_name, op in grammar.binary.items():
            for left in existing:
                for right in existing:
                    if left.size + right.size + 1 != size:
                        continue
                    values = _safe_binary(op, left.values, right.values)
                    if values is None:
                        continue
                    expr = Expression(f"{op_name}({left.text},{right.text})", size, values)
                    old = by_values.get(values)
                    if old is None or (expr.size, expr.text) < (old.size, old.text):
                        by_values[values] = expr
                        new.append(expr)
        frontier[size] = new

    return tuple(sorted(by_values.values(), key=lambda e: (e.size, e.text)))


def synthesize_realizers(
    spec: CompilerSpec,
    grammar: SynthesisGrammar,
) -> SynthesizedCompilerReport:
    """Derive the target quotient, synthesize coordinates, then compile it.

    The supplied CompilerSpec must not contain candidate realizers.  This makes
    accidental leakage of known solutions into the search an explicit error.
    """
    if spec.realizers:
        raise ValueError("residual-driven synthesis requires an empty realizer list")

    target_report = compile_consequences(spec)
    expressions = enumerate_expressions(spec.carrier, grammar)

    lawful = []
    synthesized = {}
    for expr in expressions:
        obs = expr.observation(spec.carrier)
        realized = kernel(spec.carrier, {**dict(spec.interface), "__synthesized__": obs})
        if realized == target_report.required:
            lawful.append(expr)
            synthesized[expr.text] = obs

    min_size = min((e.size for e in lawful), default=None)
    minimal = tuple(e for e in lawful if e.size == min_size)

    compiled = compile_consequences(
        CompilerSpec(
            name=spec.name,
            carrier=spec.carrier,
            interface=spec.interface,
            protected=spec.protected,
            realizers={e.text: e.observation(spec.carrier) for e in minimal},
            future_queries=spec.future_queries,
            realization_costs={},
        )
    )
    return SynthesizedCompilerReport(compiled, expressions, tuple(lawful), min_size)


def extensionally_matches(
    expr: Expression,
    carrier: Sequence[Hashable],
    observation: Observation,
) -> bool:
    return expr.values == tuple(observation(x) for x in carrier)
