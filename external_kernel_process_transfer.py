"""Independent transfer test against a pre-existing Lean-kernel tournament workflow.

Source workflow: metalogiclabs/mathgraph-lean-kernel Actions run 33615735855,
job 100201004827, exact SHA be522309e26962fd180ce892997b977b1acbf131.
The workflow predates this test.  Its scientific stages are frozen verbatim below.

Two levels are tested separately:
1. exact transfer of the three previously earned MSI process macros under a
   conservative semantics-preserving adapter;
2. transfer of the higher-level PDRC skeleton
   PROPOSE -> DECIDE -> RETAIN -> COMPOUND.

The adapter is intentionally sparse: a workflow stage is mapped only to a token
that its name explicitly supports.  We do not insert missing intermediate MSI
operations to manufacture macro matches.
"""

from dataclasses import dataclass
from typing import Mapping, Tuple

from sequential_motif_tournament import TRACES, discover_library

Stage = str
Trace = Tuple[str, ...]

KERNEL_STAGES: Tuple[Stage, ...] = (
    "Freeze base, prove structural license boundary, generate candidates",
    "Build frozen Arena workloads",
    "Exact semantic replay of all candidates",
    "Deterministic incremental tournament versus retained Pi law",
    "Lawbook retention, negative evidence, and next-grammar residual",
)

# Sparse adapter fixed from the literal stage semantics.  No MSI-only token is
# inserted unless the external stage explicitly names or entails it.
LOW_LEVEL_ADAPTER: Mapping[Stage, Trace] = {
    KERNEL_STAGES[0]: ("PUSH",),
    KERNEL_STAGES[1]: ("PREPARE_VERIFIER",),
    KERNEL_STAGES[2]: ("VERIFY_REACH",),
    KERNEL_STAGES[3]: ("DECIDE_TOURNAMENT",),
    KERNEL_STAGES[4]: ("RETAIN", "RESIDUAL"),
}

HIGH_LEVEL_ADAPTER: Mapping[Stage, Trace] = {
    KERNEL_STAGES[0]: ("PROPOSE",),
    KERNEL_STAGES[1]: tuple(),
    KERNEL_STAGES[2]: ("DECIDE",),
    KERNEL_STAGES[3]: ("DECIDE",),
    KERNEL_STAGES[4]: ("RETAIN", "COMPOUND"),
}

PDRC = ("PROPOSE", "DECIDE", "RETAIN", "COMPOUND")


@dataclass(frozen=True)
class ExternalTransferReport:
    low_trace: Trace
    learned_macros: Tuple[Trace, ...]
    exact_macro_hits: Tuple[bool, ...]
    exact_macro_coverage: int
    high_trace: Trace
    pdrc_order_preserved: bool
    pdrc_distinct_phases: int
    decision: str


def flatten(adapter: Mapping[Stage, Trace]) -> Trace:
    return tuple(tok for stage in KERNEL_STAGES for tok in adapter[stage])


def contains_contiguous(trace: Trace, motif: Trace) -> bool:
    w = len(motif)
    return any(trace[i:i+w] == motif for i in range(len(trace)-w+1))


def is_subsequence(needle: Trace, haystack: Trace) -> bool:
    i = 0
    for tok in haystack:
        if i < len(needle) and tok == needle[i]:
            i += 1
    return i == len(needle)


def run_external_transfer() -> ExternalTransferReport:
    learned = discover_library(TRACES)
    low = flatten(LOW_LEVEL_ADAPTER)
    hits = tuple(contains_contiguous(low, m) for m in learned)
    high = flatten(HIGH_LEVEL_ADAPTER)
    pdrc_ok = is_subsequence(PDRC, high)
    distinct = len(set(tok for tok in high if tok in PDRC))

    if all(hits):
        decision = "TRANSFER_EXACT_LEARNED_MACROS"
    elif pdrc_ok and distinct == 4:
        decision = "NO_EXACT_MACRO_TRANSFER__PDRC_SKELETON_TRANSFERS"
    else:
        decision = "NO_PROCESS_TRANSFER__CHANGE_ABSTRACTION"

    return ExternalTransferReport(
        low_trace=low,
        learned_macros=learned,
        exact_macro_hits=hits,
        exact_macro_coverage=sum(hits),
        high_trace=high,
        pdrc_order_preserved=pdrc_ok,
        pdrc_distinct_phases=distinct,
        decision=decision,
    )


if __name__ == "__main__":
    r = run_external_transfer()
    print("low_trace=" + "->".join(r.low_trace))
    print("learned_macros=" + ";".join("->".join(m) for m in r.learned_macros))
    print("exact_macro_hits=" + ",".join(str(x).lower() for x in r.exact_macro_hits))
    print(f"exact_macro_coverage={r.exact_macro_coverage}/{len(r.learned_macros)}")
    print("high_trace=" + "->".join(r.high_trace))
    print(f"pdrc_order_preserved={str(r.pdrc_order_preserved).lower()}")
    print(f"pdrc_distinct_phases={r.pdrc_distinct_phases}/4")
    print("decision=" + r.decision)
