#!/usr/bin/env python3
"""Resource-indexed consequence test.

Question: can a verified structure already derivable in the old *unbounded*
language still cause a genuine developmental phase change by becoming cheap?

For each unrelated finite transformation system we exhaustively compute:
  * the full denotational closure C_infty(G),
  * the budget-B reachable consequence set C_B(G),
  * the consequence-induced state quotient E_B,
  * every possible promotion K already in C_infty(G),
  * the best anonymous K1 by future frontier gain, and
  * a second K2 that becomes discoverable within the same budget only after K1.

Thus every accepted K is semantically conservative at infinity. Any gain is a
resource/representation effect rather than new denotational expressivity.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Sequence, Set, Tuple

Transform = Tuple[int, ...]
BUDGET = 2


def compose(f: Transform, g: Transform) -> Transform:
    """f after g."""
    return tuple(f[g[x]] for x in range(len(f)))


def closure(primitives: Sequence[Transform]) -> Dict[Transform, int]:
    n = len(primitives[0])
    ident = tuple(range(n))
    dist: Dict[Transform, int] = {ident: 0}
    q = deque([ident])
    while q:
        g = q.popleft()
        for p in primitives:
            h = compose(p, g)
            if h not in dist:
                dist[h] = dist[g] + 1
                q.append(h)
    return dist


def ball(dist: Dict[Transform, int], budget: int = BUDGET) -> Set[Transform]:
    return {f for f, d in dist.items() if d <= budget}


def signatures(fs: Iterable[Transform], n: int) -> Tuple[Tuple[int, ...], ...]:
    ordered = sorted(fs)
    # Protected observation is intentionally tiny and identical in all worlds:
    # did the transformed state land on anonymous state 0?
    return tuple(tuple(1 if f[x] == 0 else 0 for f in ordered) for x in range(n))


def equiv_pairs(fs: Iterable[Transform], n: int) -> Set[Tuple[int, int]]:
    sig = signatures(fs, n)
    return {(i, j) for i in range(n) for j in range(i + 1, n) if sig[i] == sig[j]}


@dataclass(frozen=True)
class Domain:
    name: str
    primitives: Tuple[Transform, ...]


def bxor(mask: int) -> Transform:
    return tuple(x ^ mask for x in range(8))


def rot3(x: int) -> int:
    return ((x << 1) & 7) | ((x >> 2) & 1)


def domains() -> Tuple[Domain, ...]:
    return (
        Domain("perm_s4", ((1, 2, 3, 0), (1, 0, 2, 3))),
        Domain("affine_z5", (
            tuple((x + 1) % 5 for x in range(5)),
            tuple((2 * x) % 5 for x in range(5)),
        )),
        Domain("dihedral_z7", (
            tuple((x + 1) % 7 for x in range(7)),
            tuple((-x) % 7 for x in range(7)),
        )),
        Domain("bitcube", (bxor(1), tuple(rot3(x) for x in range(8)))),
        Domain("finite_transform_monoid", ((1, 2, 3, 4, 4), (0, 0, 1, 2, 3))),
    )


def choose_k1(D: Domain):
    base_dist = closure(D.primitives)
    base_inf = set(base_dist)
    base_ball = ball(base_dist)
    n = len(D.primitives[0])
    base_eq = equiv_pairs(base_ball, n)
    rows = []
    for k, old_cost in base_dist.items():
        if old_cost <= 1:
            continue
        d1 = closure(D.primitives + (k,))
        # Exact semantic-conservativity gate.
        assert set(d1) == base_inf
        b1 = ball(d1)
        e1 = equiv_pairs(b1, n)
        rows.append((
            len(b1) - len(base_ball),       # reachable consequence gain
            len(base_eq) - len(e1),         # quotient refinement gain
            old_cost,                        # how much derivation was compressed
            k,
            d1,
        ))
    # Frozen anonymous rule: option value first, then quotient splits, then
    # compression depth; tuple order only breaks exact ties.
    rows.sort(key=lambda r: (r[0], r[1], r[2], r[3]), reverse=True)
    return base_dist, rows[0], rows


def choose_k2(D: Domain, base_dist, k1: Transform, d1):
    b0, b1 = ball(base_dist), ball(d1)
    newly_discoverable = sorted(b1 - b0)
    assert newly_discoverable
    rows = []
    for k2 in newly_discoverable:
        # The causal discovery gate: K2 is reachable under the same budget only
        # after K1 is installed.
        assert base_dist[k2] > BUDGET
        assert d1[k2] <= BUDGET
        d2 = closure(D.primitives + (k1, k2))
        assert set(d2) == set(base_dist)
        rows.append((len(ball(d2)) - len(b1), base_dist[k2], k2, d2))
    rows.sort(key=lambda r: (r[0], r[1], r[2]), reverse=True)
    return rows[0], newly_discoverable


def main() -> None:
    passes = 0
    quotient_modes = 0
    frontier_only_modes = 0
    for D in domains():
        base_dist, k1row, all_k1 = choose_k1(D)
        gain1, split1, old_cost1, k1, d1 = k1row
        (gain2, old_cost2, k2, d2), newly = choose_k2(D, base_dist, k1, d1)
        b0, b1, b2 = ball(base_dist), ball(d1), ball(d2)
        n = len(D.primitives[0])
        e0, e1, e2 = equiv_pairs(b0, n), equiv_pairs(b1, n), equiv_pairs(b2, n)

        # Sham = install something already primitive/unit-cost. It cannot alter
        # the budgeted frontier or quotient.
        sham = D.primitives[0]
        dsham = closure(D.primitives + (sham,))
        sham_gain = len(ball(dsham)) - len(b0)
        sham_split = len(e0) - len(equiv_pairs(ball(dsham), n))

        # Exact ancestor ablation is evaluated at discovery time: K2 is not in
        # the cold budgeted frontier, but is in the K1-warm frontier.
        ancestor_blocks_k2 = base_dist[k2] > BUDGET and d1[k2] <= BUDGET

        # Full semantic closure must remain byte-for-byte/set-identical through
        # both promotions: development changed metric accessibility, not what is
        # denotationally expressible in the limit.
        same_infty = set(base_dist) == set(d1) == set(d2)
        mode = "FRONTIER_AND_QUOTIENT" if split1 > 0 else "FRONTIER_ONLY"
        quotient_modes += int(split1 > 0)
        frontier_only_modes += int(split1 == 0)

        ok = (
            same_infty
            and gain1 > 0
            and gain2 > 0
            and sham_gain == 0
            and sham_split == 0
            and ancestor_blocks_k2
            and len(newly) > 0
        )
        passes += int(ok)
        print(
            f"DOMAIN {D.name} closure_inf={len(base_dist)} "
            f"ball0={len(b0)} ball1={len(b1)} ball2={len(b2)} "
            f"equiv_pairs={len(e0)}->{len(e1)}->{len(e2)} "
            f"k1_old_cost={old_cost1} k1_gain={gain1} k1_splits={split1} "
            f"newly_discoverable_after_k1={len(newly)} "
            f"k2_old_cost={old_cost2} k2_gain={gain2} "
            f"sham_gain={sham_gain} mode={mode} pass={ok}"
        )

        # Exhaustive census: every candidate promotion was semantically
        # conservative at infinity, because every candidate came from old
        # closure. Report how many nevertheless alter the bounded frontier.
        active = sum(1 for r in all_k1 if r[0] > 0)
        refining = sum(1 for r in all_k1 if r[1] > 0)
        print(
            f"CENSUS {D.name} candidate_promotions={len(all_k1)} "
            f"bounded_frontier_changers={active} quotient_refiners={refining}"
        )

    total = len(domains())
    print(f"CROSS_DOMAIN passes={passes}/{total} quotient_modes={quotient_modes} frontier_only_modes={frontier_only_modes}")
    assert passes == total
    assert quotient_modes > 0 and frontier_only_modes > 0
    print("UNBOUNDED_SEMANTIC_CLOSURE_INVARIANT=PASS")
    print("BOUNDED_REACHABILITY_PHASE_CHANGE=PASS")
    print("RESOURCE_RELATIVE_QUOTIENT_REFINEMENT_EXISTS=PASS")
    print("SEMANTICALLY_INERT_BUT_COMPUTATIONALLY_DEVELOPMENTAL_MODE_EXISTS=PASS")
    print("RECURSIVE_PROMOTION_COMPOUNDING=PASS")
    print("EXACT_ANCESTOR_DISCOVERY_ABLATION=PASS")
    print("SHAM_PROMOTION_CONTROL=PASS")
    print("RESOURCE_INDEXED_CONSEQUENCE_V1=PASS")


if __name__ == "__main__":
    main()
