"""Tournament recurrent developmental motifs across documented MSI traces.

The previous COMPOUND tournament rejected static merging of the five retained
calculus refinements.  This experiment changes only the composition grammar:
independent primitives remain independently ablatable, while recurrent ordered
subsequences may be promoted as transparent macros with exact expansion.

The trace corpus is frozen from CROSS_DOMAIN_DEVELOPMENTAL_EVIDENCE.md and the
linked executable evidence records.  Tokens are intentionally operational and
domain-neutral; they encode only transitions actually supported by those
records.  Candidate motifs are all contiguous subsequences of length 2..5 that
occur in at least two distinct documented domains.

Promotion uses an MDL-style judge.  A primitive event costs one token; a macro
call costs one token; a macro definition costs its expansion length plus one.
For every candidate library we compute the exact shortest encoding of every
trace by dynamic programming.  We exhaust all libraries of up to four macros.
Every promoted macro is transparent: expanding all calls reconstructs the
original trace exactly, preserving the prior causal/ablation coordinates.

Scope: exact for this frozen seven-trace corpus and this contiguous motif
grammar.  It does not prove a universal process calculus.
"""

from dataclasses import dataclass
from itertools import combinations
from typing import Dict, Iterable, Mapping, Sequence, Tuple

Trace = Tuple[str, ...]
Motif = Tuple[str, ...]

# Frozen operational traces distilled from the repository's cross-domain
# evidence ledger.  The ARC transfer-negative trace is intentionally retained
# so a macro library cannot be selected only from successful transfers.
TRACES: Mapping[str, Trace] = {
    "finite_recursive": (
        "PUSH", "VERIFY_FAILURE", "RESIDUAL", "COMPRESS", "RETAIN",
        "APPLY_FUTURE", "VERIFY_REACH", "ABLATE",
    ),
    "arithmetic": (
        "PUSH", "VERIFY_FAILURE", "RESIDUAL", "INFER_CONSTRAINT", "SYNTHESIZE",
        "RETAIN", "APPLY_FUTURE", "VERIFY_REACH",
    ),
    "interface_compilation": (
        "PUSH", "VERIFY_FAILURE", "RESIDUAL", "SYNTHESIZE", "RETAIN", "PROMOTE",
        "APPLY_FUTURE", "VERIFY_REACH", "ABLATE",
    ),
    "blind_recursive": (
        "PUSH", "VERIFY_FAILURE", "RESIDUAL", "SYNTHESIZE", "RETAIN", "PROMOTE",
        "APPLY_FUTURE", "VERIFY_REACH", "ABLATE", "RESIDUAL", "SYNTHESIZE",
        "RETAIN", "PROMOTE", "VERIFY_REACH",
    ),
    "lean_compounding": (
        "VERIFY_REACH", "RETAIN", "APPLY_FUTURE", "VERIFY_REACH", "ABLATE",
    ),
    "arc_within_episode": (
        "PUSH", "VERIFY_FAILURE", "RESIDUAL", "RETAIN", "INTERACT",
        "APPLY_FUTURE", "VERIFY_REACH",
    ),
    "arc_transfer_negative": (
        "PUSH", "RETAIN", "APPLY_FUTURE", "VERIFY_REACH", "ABLATE", "RESIDUAL",
        "INFER_CONSTRAINT", "REJECT_TRANSFER",
    ),
}


@dataclass(frozen=True)
class MotifReport:
    traces: int
    primitive_tokens: int
    candidates: int
    champion: Tuple[Motif, ...]
    encoded_trace_tokens: int
    definition_tokens: int
    total_description_tokens: int
    saved_tokens: int
    compression_ratio: float
    leave_one_out_savings: Mapping[str, int]
    exact_expansion: bool
    decision: str


def enumerate_motifs(traces: Mapping[str, Trace]) -> Tuple[Motif, ...]:
    domains: Dict[Motif, set[str]] = {}
    for domain, trace in traces.items():
        for width in range(2, 6):
            for i in range(len(trace) - width + 1):
                motif = trace[i : i + width]
                domains.setdefault(motif, set()).add(domain)
    return tuple(sorted(m for m, ds in domains.items() if len(ds) >= 2))


def shortest_encoding(trace: Trace, macros: Sequence[Motif]) -> Tuple[int, Tuple[Tuple[str, ...], ...]]:
    """Exact shortest tokenization; macro calls retain their full expansion."""
    n = len(trace)
    best = [10**9] * (n + 1)
    path: list[Tuple[Tuple[str, ...], ...] | None] = [None] * (n + 1)
    best[0], path[0] = 0, tuple()
    for i in range(n):
        assert path[i] is not None
        if best[i] + 1 < best[i + 1]:
            best[i + 1] = best[i] + 1
            path[i + 1] = path[i] + ((trace[i],),)
        for macro in macros:
            w = len(macro)
            if trace[i : i + w] == macro and best[i] + 1 < best[i + w]:
                best[i + w] = best[i] + 1
                path[i + w] = path[i] + (macro,)
    assert path[n] is not None
    return best[n], path[n]


def expand_encoding(encoding: Iterable[Tuple[str, ...]]) -> Trace:
    return tuple(token for unit in encoding for token in unit)


def library_score(traces: Mapping[str, Trace], macros: Sequence[Motif]) -> Tuple[int, int, int]:
    encoded = sum(shortest_encoding(trace, macros)[0] for trace in traces.values())
    definitions = sum(len(m) + 1 for m in macros)
    return encoded + definitions, encoded, definitions


def discover_library(traces: Mapping[str, Trace], max_macros: int = 4) -> Tuple[Motif, ...]:
    candidates = enumerate_motifs(traces)
    baseline = sum(len(t) for t in traces.values())
    best_key = (baseline, 0, tuple())
    best: Tuple[Motif, ...] = tuple()
    for width in range(1, min(max_macros, len(candidates)) + 1):
        for subset in combinations(candidates, width):
            total, _, _ = library_score(traces, subset)
            key = (total, width, subset)
            if key < best_key:
                best_key, best = key, subset
    return best


def run_motif_tournament() -> MotifReport:
    candidates = enumerate_motifs(TRACES)
    champion = discover_library(TRACES)
    total, encoded, definitions = library_score(TRACES, champion)
    primitive = sum(len(t) for t in TRACES.values())

    exact = True
    for trace in TRACES.values():
        _, enc = shortest_encoding(trace, champion)
        exact = exact and expand_encoding(enc) == trace

    loo: Dict[str, int] = {}
    for held_out, trace in TRACES.items():
        train = {k: v for k, v in TRACES.items() if k != held_out}
        library = discover_library(train)
        compressed, _ = shortest_encoding(trace, library)
        loo[held_out] = len(trace) - compressed

    decision = (
        "PROMOTE_TRANSPARENT_SEQUENTIAL_MACROS"
        if exact and total < primitive and all(v > 0 for v in loo.values())
        else "NO_PROMOTION__CHANGE_COMPOSITION_GRAMMAR"
    )
    return MotifReport(
        traces=len(TRACES),
        primitive_tokens=primitive,
        candidates=len(candidates),
        champion=champion,
        encoded_trace_tokens=encoded,
        definition_tokens=definitions,
        total_description_tokens=total,
        saved_tokens=primitive - total,
        compression_ratio=primitive / total,
        leave_one_out_savings=loo,
        exact_expansion=exact,
        decision=decision,
    )


if __name__ == "__main__":
    r = run_motif_tournament()
    print(f"traces={r.traces}")
    print(f"primitive_tokens={r.primitive_tokens}")
    print(f"candidate_motifs={r.candidates}")
    print("champion=" + ";".join("->".join(m) for m in r.champion))
    print(f"encoded_trace_tokens={r.encoded_trace_tokens}")
    print(f"definition_tokens={r.definition_tokens}")
    print(f"total_description_tokens={r.total_description_tokens}")
    print(f"saved_tokens={r.saved_tokens}")
    print(f"compression_ratio={r.compression_ratio:.6f}")
    print("leave_one_out=" + ",".join(f"{k}:{v}" for k, v in sorted(r.leave_one_out_savings.items())))
    print(f"exact_expansion={str(r.exact_expansion).lower()}")
    print("decision=" + r.decision)
