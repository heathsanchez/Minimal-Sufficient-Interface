"""Exact COMPOUND tournament for the retained five-refinement calculus.

The preceding 32-calculus tournament established that all five retained
refinements are independently observable under the supplied 91-attack grammar.
This experiment asks the next question: can any of those refinements be bundled
into coarser macro-operators without losing consequential distinctions?

We enumerate all 52 set partitions of the five refinements.  A partition is
interpreted as a synchronized macro scheme: refinements inside one block must
switch together.  Reality judges each scheme by the number of previously
certified observational classes it can still realize.  A structural-license
check forbids grouping refinements whose causal effect signatures differ.

An opaque 32-valued codebook sentinel is also included.  It preserves all 32
states by recoding them into one symbol, but is deliberately unlicensed because
it destroys explicit causal/ablation coordinates.  This mirrors the rule that
empirical survival is not sufficient for promotion.

Scope: exact only for synchronized grouping of the current five refinements and
the current finite attack grammar.  A negative result licenses changing the
composition grammar, not claiming universal indecomposability.
"""

from dataclasses import dataclass
from itertools import product
from typing import Dict, Iterable, List, Sequence, Tuple

from calculus_tournament import REFINEMENTS, enumerate_calculi, observational_signature
from self_attack_synthesis import attack_outcome, enumerate_attack_grammar


Block = Tuple[int, ...]
Partition = Tuple[Block, ...]


@dataclass(frozen=True)
class CompoundCandidate:
    name: str
    kind: str
    partition: Partition
    coordinates: int
    structurally_licensed: bool
    realized_classes: int
    lossless: bool


@dataclass(frozen=True)
class CompoundTournamentReport:
    partition_candidates: int
    total_candidates: int
    full_classes: int
    lawful_candidates: int
    lossless_candidates: int
    licensed_lossless_candidates: int
    champion: CompoundCandidate
    best_nontrivial_classes: int
    unlicensed_empirical_survivors: Tuple[str, ...]
    decision: str
    next_grammar: Tuple[str, ...]


def set_partitions(n: int) -> Tuple[Partition, ...]:
    """Canonical exhaustive set partitions of range(n)."""
    out: List[Partition] = []

    def rec(i: int, blocks: List[List[int]]) -> None:
        if i == n:
            out.append(tuple(tuple(block) for block in blocks))
            return
        for j in range(len(blocks)):
            blocks[j].append(i)
            rec(i + 1, blocks)
            blocks[j].pop()
        blocks.append([i])
        rec(i + 1, blocks)
        blocks.pop()

    rec(0, [])
    return tuple(out)


def refinement_effect_signature(index: int) -> Tuple[object, ...]:
    """Causal signature of toggling one refinement across all contexts/attacks."""
    attacks = enumerate_attack_grammar()
    effects: List[object] = []
    for context in product((False, True), repeat=len(REFINEMENTS) - 1):
        lo_bits = list(context)
        lo_bits.insert(index, False)
        hi_bits = list(context)
        hi_bits.insert(index, True)
        lo_name = "C_" + "".join("1" if b else "0" for b in lo_bits)
        hi_name = "C_" + "".join("1" if b else "0" for b in hi_bits)
        variants = {v.name: v for v in enumerate_calculi()}
        lo, hi = variants[lo_name], variants[hi_name]
        for attack in attacks:
            effects.append((attack_outcome(lo, attack), attack_outcome(hi, attack)))
    return tuple(effects)


def partition_is_structurally_licensed(partition: Partition) -> bool:
    signatures = tuple(refinement_effect_signature(i) for i in range(len(REFINEMENTS)))
    return all(
        len(block) == 1 or all(signatures[i] == signatures[block[0]] for i in block[1:])
        for block in partition
    )


def synchronized_variants(partition: Partition):
    variants = {v.name: v for v in enumerate_calculi()}
    out = []
    for macro_bits in product((False, True), repeat=len(partition)):
        bits = [False] * len(REFINEMENTS)
        for block, bit in zip(partition, macro_bits):
            for i in block:
                bits[i] = bit
        name = "C_" + "".join("1" if b else "0" for b in bits)
        out.append(variants[name])
    return tuple(out)


def realized_class_count(partition: Partition) -> int:
    attacks = enumerate_attack_grammar()
    return len({observational_signature(v, attacks) for v in synchronized_variants(partition)})


def evaluate_partition(partition: Partition) -> CompoundCandidate:
    blocks = tuple("+".join(REFINEMENTS[i] for i in block) for block in partition)
    realized = realized_class_count(partition)
    return CompoundCandidate(
        name="macro__" + "__".join(blocks),
        kind="synchronized_partition",
        partition=partition,
        coordinates=len(partition),
        structurally_licensed=partition_is_structurally_licensed(partition),
        realized_classes=realized,
        lossless=(realized == 32),
    )


def opaque_codebook_sentinel() -> CompoundCandidate:
    return CompoundCandidate(
        name="opaque_32_state_codebook",
        kind="opaque_recode",
        partition=tuple(),
        coordinates=1,
        structurally_licensed=False,
        realized_classes=32,
        lossless=True,
    )


def run_compounding_tournament() -> CompoundTournamentReport:
    partitions = set_partitions(len(REFINEMENTS))
    candidates = tuple(evaluate_partition(p) for p in partitions) + (opaque_codebook_sentinel(),)
    lawful = tuple(c for c in candidates if c.structurally_licensed)
    lossless = tuple(c for c in candidates if c.lossless)
    licensed_lossless = tuple(c for c in candidates if c.lossless and c.structurally_licensed)
    if not licensed_lossless:
        raise AssertionError("no licensed lossless representation of retained calculus")
    champion = min(licensed_lossless, key=lambda c: (c.coordinates, c.name))
    nontrivial = tuple(c for c in candidates if c.kind == "synchronized_partition" and c.coordinates < 5)
    best_nontrivial = max(c.realized_classes for c in nontrivial)
    unlicensed_survivors = tuple(sorted(c.name for c in lossless if not c.structurally_licensed))
    decision = (
        "NO_COMPOUND_MERGE__RETAIN_FIVE_INDEPENDENT_REFINEMENTS__CHANGE_COMPOSITION_GRAMMAR"
        if champion.coordinates == 5
        else "PROMOTE_COMPOUND_OPERATOR"
    )
    next_grammar = (
        "sequential operator motifs",
        "conditional/state-dependent composition",
        "trace-level recurrent subgraphs",
        "residual-driven macro introduction with exact expansion ablation",
    )
    return CompoundTournamentReport(
        partition_candidates=len(partitions),
        total_candidates=len(candidates),
        full_classes=32,
        lawful_candidates=len(lawful),
        lossless_candidates=len(lossless),
        licensed_lossless_candidates=len(licensed_lossless),
        champion=champion,
        best_nontrivial_classes=best_nontrivial,
        unlicensed_empirical_survivors=unlicensed_survivors,
        decision=decision,
        next_grammar=next_grammar,
    )


if __name__ == "__main__":
    r = run_compounding_tournament()
    print(f"partition_candidates={r.partition_candidates}")
    print(f"total_candidates={r.total_candidates}")
    print(f"full_classes={r.full_classes}")
    print(f"lawful_candidates={r.lawful_candidates}")
    print(f"lossless_candidates={r.lossless_candidates}")
    print(f"licensed_lossless_candidates={r.licensed_lossless_candidates}")
    print(f"champion={r.champion.name}")
    print(f"champion_coordinates={r.champion.coordinates}")
    print(f"best_nontrivial_classes={r.best_nontrivial_classes}")
    print("unlicensed_empirical_survivors=" + ",".join(r.unlicensed_empirical_survivors))
    print("decision=" + r.decision)
    print("next_grammar=" + ";".join(r.next_grammar))
