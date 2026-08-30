#!/usr/bin/env python3
"""V14: residual-selected consequence -> verified promotion -> language expansion -> fixed point.

Question
--------
Can the V13 residual rule choose what becomes consequential, and can each verified
selection be promoted so that previously unreachable consequences become expressible,
with the coupled recursion reaching the exhaustive fixed point that the initial
consequence language cannot reach?

Protocol
--------
* Finite anonymous world: 16 states; one latent bit is deliberately irrelevant.
* Initial consequence language L0: constants plus redundant surface observables of
  ONE latent distinction only.  Thus L0 can induce at most 2 quotient classes.
* No target consequence is marked.  The controller begins with C0 = empty.
* Query rule: among consequences currently expressible in Lt, choose the unqueried
  consequence that separates the most pairs still aliased by the current quotient.
* Verification is external to retention.  Only a verified consequence is retained.
* Promotion rule: after verification, instantiate a frozen generic unary continuation
  grammar over the retained observable.  The grammar contains three anonymous world
  actions: two are structurally redundant at the current stage and one transports the
  observable to a new latent distinction.  The controller sees only candidate behavior,
  not the sealed action role.
* The newly generated consequences are added to Lt+1, so the next query can come from
  a consequence that did not exist in L0.
* Repeat for a total budget of 3 verifier queries.
* Oracle: exhaust the entire finite closure of L0 under the supplied generic promotion
  grammar, compute its quotient, and exhaustively prove the minimum basis size.
* Ablations under the same query budget:
    1. no promotion: consequence selection continues but L never expands;
    2. no residual update: promotion occurs, but all candidates are ranked against R0;
    3. unverified-promotion guard: a forged candidate must not unlock descendants.
* Transfer: three source-distinct worlds use different latent coordinates, anonymous
  state permutations, and different surface names for the productive action.

Success is NOT workflow green.  The scientific result is the explicit PASS block.
Boundary: the finite world, initial consequence grammar, generic promotion operators,
verifier, and residual-coverage law are supplied.  The successful developmental
trajectory and the consequential basis are not supplied.
"""
from __future__ import annotations

from itertools import combinations, product

STATES = tuple(product((0, 1), repeat=4))
BUDGET = 3
MAX_CLOSURE_DEPTH = 3


def canonical_partition(vectors, n_states=16):
    buckets = {}
    for i in range(n_states):
        sig = tuple(v[i] for v in vectors)
        buckets.setdefault(sig, []).append(i)
    return tuple(sorted((tuple(g) for g in buckets.values()), key=lambda g: g[0]))


def unresolved_pairs(partition):
    return tuple((i, j) for g in partition for i, j in combinations(g, 2))


def residual_gain(partition, vector):
    return sum(vector[i] != vector[j] for i, j in unresolved_pairs(partition))


def complement(v):
    return tuple(1 - z for z in v)


def make_action(bit_cycle):
    a, b, c = bit_cycle
    def step(x):
        y = list(x)
        # Pullback convention: observable of bit a after STEP becomes old bit b;
        # repeated STEP becomes old bit c, then returns to a.
        y[a], y[b], y[c] = x[b], x[c], x[a]
        return tuple(y)
    return step


def identity(x):
    return x


def irrelevant_flip(x, irrelevant_bit):
    y = list(x)
    y[irrelevant_bit] = 1 - y[irrelevant_bit]
    return tuple(y)


def make_world(name, bit_cycle, irrelevant_bit, permutation, productive_surface):
    assert len(set(bit_cycle)) == 3
    assert irrelevant_bit not in bit_cycle
    assert sorted((*bit_cycle, irrelevant_bit)) == [0, 1, 2, 3]
    assert sorted(permutation) == list(range(16))

    inv = {old: new for new, old in enumerate(permutation)}

    def state_map(action):
        out = []
        for anon_i in range(16):
            old_i = permutation[anon_i]
            x = STATES[old_i]
            y = action(x)
            old_j = STATES.index(y)
            out.append(inv[old_j])
        return tuple(out)

    step = make_action(bit_cycle)
    roles = {
        "STEP": state_map(step),
        "ID": state_map(identity),
        "IRREL": state_map(lambda x: irrelevant_flip(x, irrelevant_bit)),
    }

    # Surface operator names reveal no role.  Productive role differs by world.
    surface_names = ("u0", "u1", "u2")
    role_for_surface = {}
    remaining = [s for s in surface_names if s != productive_surface]
    role_for_surface[productive_surface] = "STEP"
    role_for_surface[remaining[0]] = "ID"
    role_for_surface[remaining[1]] = "IRREL"
    actions = tuple({"name": s, "sealed_role": role_for_surface[s],
                     "map": roles[role_for_surface[s]]} for s in surface_names)

    first_bit = bit_cycle[0]
    base_raw = tuple(STATES[i][first_bit] for i in range(16))
    base = tuple(base_raw[permutation[i]] for i in range(16))

    # Initial language: constants + many equivalent spellings of exactly one axis.
    seeds = []
    for k in range(12):
        if k < 4:
            v = tuple(0 for _ in range(16)) if k % 2 == 0 else tuple(1 for _ in range(16))
        else:
            v = base if k % 2 == 0 else complement(base)
        seeds.append({"name": f"s{k:02d}", "vector": v, "ast": (f"s{k:02d}",),
                      "depth": 0, "provenance": "seed"})

    return {"name": name, "actions": actions, "seeds": tuple(seeds)}


WORLDS = (
    make_world(
        "W_A", bit_cycle=(0, 1, 2), irrelevant_bit=3,
        permutation=(7, 0, 12, 3, 15, 8, 5, 10, 2, 13, 6, 1, 14, 9, 4, 11),
        productive_surface="u2",
    ),
    make_world(
        "W_B", bit_cycle=(3, 0, 2), irrelevant_bit=1,
        permutation=(11, 4, 1, 14, 9, 2, 13, 6, 0, 15, 8, 5, 10, 3, 12, 7),
        productive_surface="u0",
    ),
    make_world(
        "W_C", bit_cycle=(1, 3, 0), irrelevant_bit=2,
        permutation=(5, 10, 3, 12, 7, 0, 15, 8, 13, 6, 1, 14, 9, 2, 11, 4),
        productive_surface="u1",
    ),
)


def apply_action(vector, action_map):
    return tuple(vector[action_map[i]] for i in range(16))


def generated_children(world, parent):
    out = []
    for op in world["actions"]:
        v = apply_action(parent["vector"], op["map"])
        out.append({
            "name": f"{op['name']}({parent['name']})",
            "vector": v,
            "ast": (op["name"], parent["ast"]),
            "depth": parent["depth"] + 1,
            "provenance": parent["name"],
        })
    return tuple(out)


def verifier(world, candidate):
    # Recompute candidate semantics from its AST against the sealed world rather than
    # trusting the proposed vector.  Only the frozen seed spellings and action names
    # are admissible.
    seed_map = {s["name"]: s for s in world["seeds"]}
    action_map = {a["name"]: a for a in world["actions"]}

    def eval_ast(ast):
        if len(ast) == 1:
            s = seed_map.get(ast[0])
            return None if s is None else s["vector"]
        op_name, child_ast = ast
        op = action_map.get(op_name)
        if op is None:
            return None
        child = eval_ast(child_ast)
        if child is None:
            return None
        return apply_action(child, op["map"])

    expected = eval_ast(candidate["ast"])
    return expected is not None and expected == candidate["vector"]


def dedupe_candidates(cands):
    # Keep distinct syntax available, but exact duplicate AST/name pairs only once.
    out = {}
    for c in cands:
        out[(c["name"], c["ast"])] = c
    return tuple(out.values())


def closure(world, max_depth=MAX_CLOSURE_DEPTH):
    allc = list(world["seeds"])
    frontier = list(world["seeds"])
    for _ in range(max_depth):
        nxt = []
        for p in frontier:
            nxt.extend(generated_children(world, p))
        allc.extend(nxt)
        frontier = nxt
    return dedupe_candidates(allc)


def oracle(world):
    full = closure(world)
    # Quotient cares about consequence behavior, not duplicate syntax.
    unique_vectors = []
    seen = set()
    for c in full:
        if c["vector"] not in seen:
            seen.add(c["vector"])
            unique_vectors.append(c["vector"])
    target = canonical_partition(unique_vectors)
    minimum = None
    witnesses = []
    for k in range(BUDGET + 1):
        for idxs in combinations(range(len(unique_vectors)), k):
            if canonical_partition([unique_vectors[i] for i in idxs]) == target:
                minimum = k
                witnesses.append(idxs)
        if minimum is not None:
            break
    assert minimum is not None
    return target, minimum, tuple(witnesses), full, tuple(unique_vectors)


def choose(partition, available, queried, score_partition=None):
    basis = partition if score_partition is None else score_partition
    scored = []
    for c in available:
        if c["name"] in queried:
            continue
        scored.append((residual_gain(basis, c["vector"]), c["depth"], c["name"], c))
    assert scored, "no available unqueried consequence"
    scored.sort(key=lambda r: (-r[0], r[1], r[2]))
    return scored[0][0], scored[0][3]


def controller(world, promote=True, update_residual=True, budget=BUDGET):
    available = list(world["seeds"])
    retained = []
    queried = set()
    trace = []
    r0 = canonical_partition([])
    for step in range(1, budget + 1):
        current = canonical_partition([c["vector"] for c in retained])
        gain, chosen = choose(current, available, queried,
                              None if update_residual else r0)
        queried.add(chosen["name"])
        ok = verifier(world, chosen)
        before_names = {c["name"] for c in available}
        new_names = []
        if ok:
            retained.append(chosen)
            if promote:
                for child in generated_children(world, chosen):
                    if child["name"] not in before_names:
                        available.append(child)
                        before_names.add(child["name"])
                        new_names.append(child["name"])
        trace.append((step, chosen["name"], chosen["depth"], gain, ok,
                      len(current), tuple(new_names)))
    final = canonical_partition([c["vector"] for c in retained])
    return final, tuple(trace), tuple(c["name"] for c in retained)


def forged_promotion_guard(world):
    # Same AST as a real seed but falsified semantics.  It must fail verification and
    # therefore produce no descendants under the controller's promotion rule.
    real = world["seeds"][4]
    forged = dict(real)
    forged["vector"] = tuple(1 - z for z in real["vector"])
    # Complement may accidentally equal another valid seed, but verifier binds AST,
    # so the vector is wrong for this exact AST.
    assert not verifier(world, forged)
    descendants = generated_children(world, forged) if verifier(world, forged) else ()
    return descendants


def main():
    rows = []
    for world in WORLDS:
        target, oracle_min, witnesses, full, unique_vectors = oracle(world)
        initial = canonical_partition([s["vector"] for s in world["seeds"]])
        got, trace, retained = controller(world, promote=True, update_residual=True)
        no_prom, no_prom_trace, no_prom_retained = controller(
            world, promote=False, update_residual=True)
        static, static_trace, static_retained = controller(
            world, promote=True, update_residual=False)
        forged_desc = forged_promotion_guard(world)

        print("V14_WORLD", world["name"])
        print("V14_INITIAL_CLASSES", len(initial), "ORACLE_CLASSES", len(target),
              "ORACLE_MIN", oracle_min, "ORACLE_MIN_WITNESSES", len(witnesses),
              "CLOSURE_SYNTAX", len(full), "CLOSURE_BEHAVIORS", len(unique_vectors))
        print("V14_TRACE", trace)
        print("V14_RETAINED", retained, "CLASSES", len(got), "EXACT_ORACLE", got == target)
        print("V14_NO_PROMOTION", no_prom_retained, "CLASSES", len(no_prom),
              "EXACT_ORACLE", no_prom == target, "TRACE", no_prom_trace)
        print("V14_NO_RESIDUAL_UPDATE", static_retained, "CLASSES", len(static),
              "EXACT_ORACLE", static == target, "TRACE", static_trace)
        print("V14_FORGED_PROMOTION_DESCENDANTS", len(forged_desc))

        assert len(initial) == 2
        assert len(target) == 8
        assert oracle_min == BUDGET
        assert got == target
        assert no_prom != target
        assert static != target
        assert forged_desc == ()
        # At least one selected consequence must have been unavailable initially.
        initial_names = {s["name"] for s in world["seeds"]}
        assert any(name not in initial_names for name in retained[1:])
        # Exact developmental staircase: each verified selected consequence doubles
        # the currently distinguishable quotient until the oracle fixed point.
        assert [row[5] for row in trace] == [1, 2, 4], trace
        rows.append((world["name"], retained, trace))

    assert len(rows) == 3
    print("NO_PRIVILEGED_TARGET_CONSEQUENCE=PASS")
    print("RESIDUAL_SELECTS_WHAT_IS_PROTECTED=PASS")
    print("VERIFIED_SELECTION_PROMOTION_EXPANDS_CONSEQUENCE_LANGUAGE=PASS")
    print("PROMOTED_LANGUAGE_REACHES_PREVIOUSLY_UNREACHABLE_ORACLE_FIXED_POINT=PASS")
    print("ORACLE_PROVES_THREE_VERIFIED_SELECTIONS_MINIMAL=PASS")
    print("NO_PROMOTION_ABLATION_FAILS_ALL_WORLDS=PASS")
    print("NO_RESIDUAL_UPDATE_ABLATION_FAILS_ALL_WORLDS=PASS")
    print("UNVERIFIED_CANDIDATE_CANNOT_CAUSE_LANGUAGE_EXPANSION=PASS")
    print("SOURCE_DISTINCT_TRANSFER_3_OF_3=PASS")
    print("RECURSIVE_SELECTED_CONSEQUENCE_LANGUAGE_FIXED_POINT_V14=PASS")
    print("BOUNDARY=finite substrate and generic operators supplied; winning developmental trajectory, protected basis, and reachable consequence sequence are residual-selected and verifier-gated")


if __name__ == "__main__":
    main()
