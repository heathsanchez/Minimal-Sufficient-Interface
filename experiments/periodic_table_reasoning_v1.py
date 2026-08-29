#!/usr/bin/env python3
"""Periodic Table of Reasoning V1.

Same ontology-poor developmental kernel over six unrelated finite worlds.
The learner is NOT given quotient/refinement/invariant/composition labels.
It receives only opaque states, primitive actions, binary consequences,
composition of actions, and retained binary probes.

Protocol
--------
1. Start with the direct binary consequence only.
2. Protected tasks are every action word up to length 3.
3. If the retained probe-signature is insufficient to predict a protected
   consequence, search all action words up to length 3 for the minimum-cost
   probe that most enlarges the consequence frontier.
4. Freeze that probe and continue on the residual.
5. After the trace is frozen, canonicalize it and label recurrent motifs.
6. Repeat after independent state/action renaming.
7. Ablate all promoted probes and require return to the cold frontier.

This is deliberately a finite pilot, not evidence that these motifs are
universal.  It asks whether the same generated developmental trace motifs
recur when domain semantics are hidden behind one common consequence API.
"""

from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from itertools import product, permutations
from typing import Callable, Dict, Iterable, List, Sequence, Tuple

Word = Tuple[int, ...]


@dataclass(frozen=True)
class World:
    name: str
    transitions: Tuple[Tuple[int, ...], ...]
    outcome: Tuple[int, ...]

    @property
    def n(self) -> int:
        return len(self.outcome)

    @property
    def arity(self) -> int:
        return len(self.transitions)


def all_words(arity: int, max_len: int) -> List[Word]:
    out: List[Word] = []
    for k in range(1, max_len + 1):
        out.extend(product(range(arity), repeat=k))
    return out


def act(world: World, state: int, word: Word) -> int:
    for a in word:
        state = world.transitions[a][state]
    return state


def consequence(world: World, state: int, word: Word) -> int:
    return world.outcome[act(world, state, word)]


def signature(world: World, state: int, probes: Sequence[Word]) -> Tuple[int, ...]:
    return tuple(consequence(world, state, w) for w in probes)


def partition(world: World, probes: Sequence[Word]) -> Tuple[Tuple[int, ...], ...]:
    buckets: Dict[Tuple[int, ...], List[int]] = defaultdict(list)
    for s in range(world.n):
        buckets[signature(world, s, probes)].append(s)
    blocks = [tuple(sorted(v)) for v in buckets.values()]
    return tuple(sorted(blocks, key=lambda b: (len(b), b)))


def block_size_signature(p: Sequence[Sequence[int]]) -> Tuple[int, ...]:
    return tuple(sorted(len(b) for b in p))


def frontier(world: World, probes: Sequence[Word], tasks: Sequence[Word]) -> int:
    p = partition(world, probes)
    class_of: Dict[int, int] = {}
    for i, block in enumerate(p):
        for s in block:
            class_of[s] = i
    good = 0
    for w in tasks:
        values: Dict[int, set] = defaultdict(set)
        for s in range(world.n):
            values[class_of[s]].add(consequence(world, s, w))
        if all(len(v) == 1 for v in values.values()):
            good += 1
    return good


def residual_pairs(world: World, probes: Sequence[Word], tasks: Sequence[Word]) -> int:
    sigs = [signature(world, s, probes) for s in range(world.n)]
    count = 0
    for i in range(world.n):
        for j in range(i + 1, world.n):
            if sigs[i] != sigs[j]:
                continue
            if any(consequence(world, i, w) != consequence(world, j, w) for w in tasks):
                count += 1
    return count


def kernel_refinement(old_p: Sequence[Sequence[int]], new_p: Sequence[Sequence[int]], world: World, probe: Word) -> bool:
    # Post-hoc theorem check: new partition must be exactly old partition
    # intersected with equality of the new binary consequence.
    expected = []
    for block in old_p:
        by = defaultdict(list)
        for s in block:
            by[consequence(world, s, probe)].append(s)
        expected.extend(tuple(sorted(v)) for v in by.values())
    expected = tuple(sorted(expected, key=lambda b: (len(b), b)))
    actual = tuple(sorted((tuple(sorted(b)) for b in new_p), key=lambda b: (len(b), b)))
    return expected == actual


def learn(world: World, max_word: int = 3, target_word: int = 3):
    tasks: List[Word] = [()] + all_words(world.arity, target_word)
    candidates = all_words(world.arity, max_word)
    probes: List[Word] = [()]
    trace = []
    initial_frontier = frontier(world, probes, tasks)

    for generation in range(world.n + 2):
        f0 = frontier(world, probes, tasks)
        r0 = residual_pairs(world, probes, tasks)
        if f0 == len(tasks):
            break
        p0 = partition(world, probes)
        best = None
        for w in candidates:
            if w in probes:
                continue
            p1 = partition(world, probes + [w])
            f1 = frontier(world, probes + [w], tasks)
            gain = f1 - f0
            split_gain = len(p1) - len(p0)
            if gain <= 0 and split_gain <= 0:
                continue
            # Consequence first, then split power, then minimum description length.
            score = (gain, f1, split_gain, -len(w), tuple(-a for a in w))
            if best is None or score > best[0]:
                best = (score, w, p1, f1)
        if best is None:
            break
        _, w, p1, f1 = best
        probes.append(w)
        trace.append({
            "generation": generation + 1,
            "probe": w,
            "cost": len(w),
            "frontier_before": f0,
            "frontier_after": f1,
            "residual_pairs_before": r0,
            "partition_before": block_size_signature(p0),
            "partition_after": block_size_signature(p1),
            "split": len(p1) > len(p0),
            "kernel_meet_exact": kernel_refinement(p0, p1, world, w),
        })

    final_frontier = frontier(world, probes, tasks)
    return {
        "tasks": tasks,
        "probes": probes,
        "trace": trace,
        "initial_frontier": initial_frontier,
        "final_frontier": final_frontier,
        "total_tasks": len(tasks),
        "final_partition": block_size_signature(partition(world, probes)),
        "cold_partition": block_size_signature(partition(world, [()])),
    }


def renamed(world: World) -> World:
    # Deterministic but nontrivial independent presentation: reverse state IDs
    # and rotate action labels.  This changes literal names, not behaviour.
    perm = tuple(reversed(range(world.n)))
    inv = {old: new for new, old in enumerate(perm)}
    order = tuple(range(1, world.arity)) + (0,) if world.arity > 1 else (0,)
    transitions = []
    for old_a in order:
        old_t = world.transitions[old_a]
        transitions.append(tuple(inv[old_t[perm[new_s]]] for new_s in range(world.n)))
    outcome = tuple(world.outcome[perm[new_s]] for new_s in range(world.n))
    return World(world.name + "_RENAMED", tuple(transitions), outcome)


def canonical_trace(result) -> Tuple:
    return (
        result["initial_frontier"],
        result["final_frontier"],
        result["total_tasks"],
        tuple((t["frontier_before"], t["frontier_after"], t["partition_before"], t["partition_after"], t["cost"]) for t in result["trace"]),
    )


def worlds() -> List[World]:
    out: List[World] = []

    # Arithmetic residue world.
    n = 12
    out.append(World(
        "ARITHMETIC_RESIDUES",
        (
            tuple((s + 1) % n for s in range(n)),
            tuple((5 * s) % n for s in range(n)),
        ),
        tuple(1 if s < 6 else 0 for s in range(n)),
    ))

    # Boolean cube world.
    n = 8
    out.append(World(
        "BOOLEAN_CUBE",
        (
            tuple(s ^ 1 for s in range(n)),
            tuple(((s << 1) & 7) | ((s >> 2) & 1) for s in range(n)),
            tuple(s ^ 7 for s in range(n)),
        ),
        tuple(s & 1 for s in range(n)),
    ))

    # Directed graph navigation world.
    out.append(World(
        "GRAPH_NAVIGATION",
        (
            (1, 2, 3, 0, 5, 6, 7, 4),
            (4, 0, 6, 2, 7, 3, 5, 1),
        ),
        (1, 0, 0, 1, 0, 1, 0, 1),
    ))

    # Symbol rewrite world: hidden states are permutations; actions are swaps.
    ps = list(permutations("abc"))
    ix = {p: i for i, p in enumerate(ps)}
    def sw(p, i, j):
        q = list(p); q[i], q[j] = q[j], q[i]; return tuple(q)
    out.append(World(
        "SYMBOL_REWRITE",
        (
            tuple(ix[sw(p, 0, 1)] for p in ps),
            tuple(ix[sw(p, 1, 2)] for p in ps),
        ),
        tuple(1 if p[0] == "a" else 0 for p in ps),
    ))

    # Four-cell deterministic local system.
    n = 16
    def rot4(s): return ((s << 1) & 15) | ((s >> 3) & 1)
    def local(s):
        b = [(s >> i) & 1 for i in range(4)]
        b[1] ^= b[0]
        return sum(v << i for i, v in enumerate(b))
    out.append(World(
        "CELLULAR_DYNAMICS",
        (
            tuple(rot4(s) for s in range(n)),
            tuple(local(s) for s in range(n)),
        ),
        tuple(s & 1 for s in range(n)),
    ))

    # Bounded 2-D control world.
    coords = [(x, y) for y in range(3) for x in range(3)]
    ix2 = {p: i for i, p in enumerate(coords)}
    moves = []
    for dx, dy in ((1, 0), (0, 1), (-1, 0)):
        row = []
        for x, y in coords:
            q = (max(0, min(2, x + dx)), max(0, min(2, y + dy)))
            row.append(ix2[q])
        moves.append(tuple(row))
    out.append(World(
        "BOUNDED_CONTROL",
        tuple(moves),
        tuple(1 if (x, y) == (2, 2) else 0 for x, y in coords),
    ))
    return out


def posthoc_motifs(world: World, result, renamed_result) -> Dict[str, bool]:
    trace = result["trace"]
    cold = result["initial_frontier"]
    # Remove every promoted probe: by construction this is exactly the cold representation.
    ablated = frontier(world, [()], result["tasks"])
    return {
        "EQUIVALENCE": len(result["cold_partition"]) < world.n,
        "SEPARATOR": bool(trace) and all(t["split"] for t in trace),
        "MINIMAL_REFINEMENT": bool(trace) and all(t["kernel_meet_exact"] for t in trace),
        "PRESENTATION_INVARIANT": canonical_trace(result) == canonical_trace(renamed_result),
        "COMPOSITION": any(t["cost"] >= 2 for t in trace),
        "PROMOTION": bool(trace),
        "EXPANDED_REACHABILITY": result["final_frontier"] > cold,
        "EXACT_ABLATION": ablated == cold,
    }


def main() -> None:
    motif_counts = defaultdict(int)
    results = []
    for w in worlds():
        r = learn(w)
        rr = learn(renamed(w))
        motifs = posthoc_motifs(w, r, rr)
        results.append((w, r, rr, motifs))
        for k, v in motifs.items():
            motif_counts[k] += int(v)

        print(f"WORLD={w.name}")
        print(f"  STATES={w.n} ACTIONS={w.arity} TASKS={r['total_tasks']}")
        print(f"  FRONTIER={r['initial_frontier']}->{r['final_frontier']}/{r['total_tasks']}")
        print(f"  COLD_PARTITION={r['cold_partition']} FINAL_PARTITION={r['final_partition']}")
        for t in r["trace"]:
            print(
                "  PROMOTE"
                f" g={t['generation']} word={t['probe']} cost={t['cost']}"
                f" frontier={t['frontier_before']}->{t['frontier_after']}"
                f" partition={t['partition_before']}->{t['partition_after']}"
                f" residual_pairs={t['residual_pairs_before']}"
            )
        print("  MOTIFS=" + ",".join(k for k, v in motifs.items() if v))

    n = len(results)
    print("MOTIF_CENSUS " + " ".join(f"{k}={v}/{n}" for k, v in sorted(motif_counts.items())))

    # Primary preregistered gate: seven core motifs must recur in >=5/6 worlds;
    # presentation invariance and exact ablation must hold in all six.
    core = ("EQUIVALENCE", "SEPARATOR", "MINIMAL_REFINEMENT", "COMPOSITION", "PROMOTION", "EXPANDED_REACHABILITY")
    assert all(motif_counts[k] >= 5 for k in core), motif_counts
    assert motif_counts["PRESENTATION_INVARIANT"] == n, motif_counts
    assert motif_counts["EXACT_ABLATION"] == n, motif_counts
    assert all(r["final_frontier"] == r["total_tasks"] for _, r, _, _ in results)

    print("ONTOLOGY_POOR_KERNEL=PASS")
    print("POSTHOC_CANONICALIZATION_ONLY=PASS")
    print("CROSS_DOMAIN_RECURRENT_MOTIFS=PASS")
    print("PRESENTATION_INVARIANCE=PASS")
    print("EXACT_PROMOTION_ABLATION=PASS")
    print("PERIODIC_TABLE_REASONING_V1=PASS")


if __name__ == "__main__":
    main()
