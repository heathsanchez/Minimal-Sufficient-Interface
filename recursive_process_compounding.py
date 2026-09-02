"""Recursive COMPOUND test over the promoted sequential macro library.

The first-order tournament promoted three transparent motifs from seven frozen
cross-domain developmental traces.  This experiment feeds those earned macros
back into the proposal language and asks two distinct questions:

1. does a second-order macro earn promotion after paying its definition cost?;
2. even if no second-order macro is earned, do the first-order macros causally
   enlarge reach on a new resource-bounded developmental task?

The two questions are deliberately separated.  Failure to earn a second-order
abstraction is a valid scientific result and must not block a capability test.
All macros remain transparent and expand exactly to primitive events.

Scope: bounded, synthetic process capability.  The held-out task is a new exact
composition of already-supported primitive developmental events; it is not a
natural-domain benchmark and does not establish open-ended self-improvement.
"""

from dataclasses import dataclass
from itertools import combinations
from typing import Dict, Mapping, Sequence, Tuple

from sequential_motif_tournament import TRACES, discover_library, shortest_encoding

PrimitiveTrace = Tuple[str, ...]
SymbolTrace = Tuple[str, ...]
Motif = Tuple[str, ...]


@dataclass(frozen=True)
class RecursiveCompoundingReport:
    first_order_macros: Tuple[PrimitiveTrace, ...]
    symbol_traces: Mapping[str, SymbolTrace]
    second_order_candidates: int
    second_order_champion: Tuple[Motif, ...]
    second_order_baseline: int
    second_order_total: int
    second_order_decision: str
    held_out_primitive_cost: int
    held_out_warm_cost: int
    held_out_budget: int
    cold_reaches: bool
    warm_reaches: bool
    sham_reaches: bool
    ablation_reaches: Mapping[str, bool]
    exact_warm_expansion: bool
    capability_decision: str


def _macro_names(macros: Sequence[PrimitiveTrace]) -> Dict[PrimitiveTrace, str]:
    return {macro: f"M{i + 1}" for i, macro in enumerate(macros)}


def encode_as_symbols(trace: PrimitiveTrace, macros: Sequence[PrimitiveTrace]) -> SymbolTrace:
    """Exact shortest first-order encoding, with deterministic macro symbols."""
    names = _macro_names(macros)
    n = len(trace)
    best = [10**9] * (n + 1)
    path: list[SymbolTrace | None] = [None] * (n + 1)
    best[0], path[0] = 0, tuple()
    for i in range(n):
        if path[i] is None:
            continue
        if best[i] + 1 < best[i + 1]:
            best[i + 1] = best[i] + 1
            path[i + 1] = path[i] + (trace[i],)
        for macro in macros:
            w = len(macro)
            if trace[i : i + w] == macro and best[i] + 1 < best[i + w]:
                best[i + w] = best[i] + 1
                path[i + w] = path[i] + (names[macro],)
    assert path[n] is not None
    return path[n]


def expand_symbols(trace: SymbolTrace, macros: Sequence[PrimitiveTrace]) -> PrimitiveTrace:
    expansions = {f"M{i + 1}": macro for i, macro in enumerate(macros)}
    out = []
    for token in trace:
        out.extend(expansions.get(token, (token,)))
    return tuple(out)


def enumerate_second_order_motifs(traces: Mapping[str, SymbolTrace]) -> Tuple[Motif, ...]:
    domains: Dict[Motif, set[str]] = {}
    for domain, trace in traces.items():
        for width in range(2, 5):
            for i in range(len(trace) - width + 1):
                motif = trace[i : i + width]
                if any(tok.startswith("M") for tok in motif):
                    domains.setdefault(motif, set()).add(domain)
    return tuple(sorted(m for m, ds in domains.items() if len(ds) >= 2))


def symbol_encoding_cost(trace: SymbolTrace, macros: Sequence[Motif]) -> int:
    n = len(trace)
    best = [10**9] * (n + 1)
    best[0] = 0
    for i in range(n):
        if best[i] == 10**9:
            continue
        best[i + 1] = min(best[i + 1], best[i] + 1)
        for macro in macros:
            w = len(macro)
            if trace[i : i + w] == macro:
                best[i + w] = min(best[i + w], best[i] + 1)
    return best[n]


def second_order_score(traces: Mapping[str, SymbolTrace], macros: Sequence[Motif]) -> int:
    encoded = sum(symbol_encoding_cost(t, macros) for t in traces.values())
    definitions = sum(len(m) + 1 for m in macros)
    return encoded + definitions


def discover_second_order_library(traces: Mapping[str, SymbolTrace]) -> Tuple[Motif, ...]:
    candidates = enumerate_second_order_motifs(traces)
    baseline = sum(len(t) for t in traces.values())
    best_key = (baseline, 0, tuple())
    best: Tuple[Motif, ...] = tuple()
    for width in range(1, min(3, len(candidates)) + 1):
        for subset in combinations(candidates, width):
            key = (second_order_score(traces, subset), width, subset)
            if key < best_key:
                best_key, best = key, subset
    return best


# Frozen only after the first-order macro library was established.  No source
# trace in TRACES has this exact primitive sequence.  The task combines a
# residual-derived constraint step with synthesis/promotion and causal future
# qualification.  Success is exact completion under a four-call process budget.
HELD_OUT_TASK: PrimitiveTrace = (
    "PUSH", "VERIFY_FAILURE", "RESIDUAL",
    "INFER_CONSTRAINT",
    "SYNTHESIZE", "RETAIN", "PROMOTE",
    "APPLY_FUTURE", "VERIFY_REACH", "ABLATE",
)
HELD_OUT_BUDGET = 4

# Matched sham library: same number and lengths as the earned library, but each
# expansion is deliberately wrong while remaining transparent.
SHAM_LIBRARY: Tuple[PrimitiveTrace, ...] = (
    ("PUSH", "VERIFY_FAILURE", "RETAIN"),
    ("SYNTHESIZE", "PROMOTE", "RETAIN"),
    ("APPLY_FUTURE", "ABLATE", "VERIFY_REACH"),
)


def task_cost(task: PrimitiveTrace, macros: Sequence[PrimitiveTrace]) -> int:
    return shortest_encoding(task, macros)[0]


def exact_task_expansion(task: PrimitiveTrace, macros: Sequence[PrimitiveTrace]) -> bool:
    names = _macro_names(macros)
    symbols = encode_as_symbols(task, macros)
    expansions = {name: macro for macro, name in names.items()}
    expanded = []
    for token in symbols:
        expanded.extend(expansions.get(token, (token,)))
    return tuple(expanded) == task


def run_recursive_compounding() -> RecursiveCompoundingReport:
    first = discover_library(TRACES)
    symbol_traces = {k: encode_as_symbols(v, first) for k, v in TRACES.items()}
    candidates = enumerate_second_order_motifs(symbol_traces)
    second = discover_second_order_library(symbol_traces)
    baseline = sum(len(t) for t in symbol_traces.values())
    second_total = second_order_score(symbol_traces, second)
    second_decision = (
        "PROMOTE_SECOND_ORDER_MACRO"
        if second and second_total < baseline
        else "NO_SECOND_ORDER_PROMOTION__RETAIN_FIRST_ORDER_LIBRARY"
    )

    cold = len(HELD_OUT_TASK)
    warm = task_cost(HELD_OUT_TASK, first)
    sham = task_cost(HELD_OUT_TASK, SHAM_LIBRARY)
    ablation: Dict[str, bool] = {}
    for i in range(len(first)):
        reduced = tuple(m for j, m in enumerate(first) if j != i)
        ablation[f"remove_M{i + 1}"] = task_cost(HELD_OUT_TASK, reduced) <= HELD_OUT_BUDGET

    exact = exact_task_expansion(HELD_OUT_TASK, first)
    cold_reaches = cold <= HELD_OUT_BUDGET
    warm_reaches = warm <= HELD_OUT_BUDGET
    sham_reaches = sham <= HELD_OUT_BUDGET
    capability_decision = (
        "PROMOTE_FIRST_ORDER_MACROS_AS_CAUSAL_PROCESS_CAPABILITY"
        if exact and warm_reaches and not cold_reaches and not sham_reaches and not any(ablation.values())
        else "NO_CAUSAL_PROCESS_CAPABILITY_PROMOTION"
    )

    return RecursiveCompoundingReport(
        first_order_macros=first,
        symbol_traces=symbol_traces,
        second_order_candidates=len(candidates),
        second_order_champion=second,
        second_order_baseline=baseline,
        second_order_total=second_total,
        second_order_decision=second_decision,
        held_out_primitive_cost=cold,
        held_out_warm_cost=warm,
        held_out_budget=HELD_OUT_BUDGET,
        cold_reaches=cold_reaches,
        warm_reaches=warm_reaches,
        sham_reaches=sham_reaches,
        ablation_reaches=ablation,
        exact_warm_expansion=exact,
        capability_decision=capability_decision,
    )


if __name__ == "__main__":
    r = run_recursive_compounding()
    print("first_order=" + ";".join("->".join(m) for m in r.first_order_macros))
    print(f"second_order_candidates={r.second_order_candidates}")
    print("second_order_champion=" + ";".join("->".join(m) for m in r.second_order_champion))
    print(f"second_order_baseline={r.second_order_baseline}")
    print(f"second_order_total={r.second_order_total}")
    print("second_order_decision=" + r.second_order_decision)
    print(f"held_out_primitive_cost={r.held_out_primitive_cost}")
    print(f"held_out_warm_cost={r.held_out_warm_cost}")
    print(f"held_out_budget={r.held_out_budget}")
    print(f"cold_reaches={str(r.cold_reaches).lower()}")
    print(f"warm_reaches={str(r.warm_reaches).lower()}")
    print(f"sham_reaches={str(r.sham_reaches).lower()}")
    print("ablation_reaches=" + ",".join(f"{k}:{str(v).lower()}" for k, v in sorted(r.ablation_reaches.items())))
    print(f"exact_warm_expansion={str(r.exact_warm_expansion).lower()}")
    print("capability_decision=" + r.capability_decision)
