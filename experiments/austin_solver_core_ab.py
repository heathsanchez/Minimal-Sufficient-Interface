"""Proof-carrying Austin completion transfer into the pinned MathGraph core.

This is a bounded solver-core diagnostic, not an official Stage 2 submission.
Development sees only the premise. Every injected equality is replayed from
that premise; the held-out goal is used only by the existing closure test.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

import austin_completion_development as dev
import austin_critical_pair_residual as ast


def load_solver(path):
    spec = importlib.util.spec_from_file_location("mathgraph_austin_ab", path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def to_ast(t):
    return ast.V(t[1]) if t[0] == "var" else ast.A(to_ast(t[1]), to_ast(t[2]))


def to_mg(t):
    return ("var", t.name) if isinstance(t, ast.V) else ("op", to_mg(t.left), to_mg(t.right))


def variables(t):
    return dev.vars(t)


def instance(m, recipe, mapping):
    return m.Recipe(m.substitute_partial(recipe.lhs, mapping),
        m.substitute_partial(recipe.rhs, mapping), "instantiate", (recipe,),
        tuple(sorted(mapping.items())))


def source_recipe(m, source):
    return m.Recipe(source[0], source[1], "source", data=(
        tuple((v, ("var", v)) for v in source[2]), False))


def symmetry(m, r):
    return m.Recipe(r.rhs, r.lhs, "symmetry", (r,))


def trans(m, a, b):
    assert a.rhs == b.lhs, "Broken equality chain"
    return m.Recipe(a.lhs, b.rhs, "transitivity", (a, b))


def lift(m, r, root, path):
    assert m.get_subterm(root, path) == r.lhs
    for i in range(len(path) - 1, -1, -1):
        ctx = m.get_subterm(root, path[:i])
        if path[i] == "L":
            s = ctx[2]
            r = m.Recipe(("op", r.lhs, s), ("op", r.rhs, s),
                "congruence", (r,), ("left", s))
        else:
            s = ctx[1]
            r = m.Recipe(("op", s, r.lhs), ("op", s, r.rhs),
                "congruence", (r,), ("right", s))
    assert r.lhs == root
    return r


def rule_recipe(m, source, seed, index, prefix):
    base = source_recipe(m, source)
    # w is the fresh promotion variable, not an original source binder.
    renamed = {v: ast.V(prefix + v) for v in set(source[2]) | {"w"}}
    branch = instance(m, base, {v: to_mg(renamed[v]) for v in source[2]})
    if index == 0:
        return branch
    if index != 1:
        raise ValueError("Uncertified rule")
    path, attachment = dev.attachment(seed)
    lhs, rhs = seed
    args = {"A": lhs.left, "p": lhs.right, "w": ast.V("w")}
    source_args = {v: dev.instantiate(args[t.name], renamed)
                   for v, t in attachment.items()}
    original = dev.instantiate(lhs, source_args)
    promoted = ast.replace_at(original, path, dev.instantiate(rhs, renamed))
    source_step = instance(m, base, {v: to_mg(source_args[v]) for v in source[2]})
    assert source_step.lhs == to_mg(original)
    back = lift(m, symmetry(m, branch), to_mg(promoted),
                tuple("L" if p == 0 else "R" for p in path))
    result = trans(m, back, source_step)
    expected = ast.rename_rule(dev.promote(seed), prefix)
    assert (result.lhs, result.rhs) == tuple(map(to_mg, expected))
    return result


def step(m, source, seed, index, prefix, env, root, path):
    r = rule_recipe(m, source, seed, index, prefix)
    renamed = ast.rename_rule((seed, dev.promote(seed))[index], prefix)
    # Simultaneous substitution is essential: matching environments can
    # contain names which also occur inside their replacement terms.
    mapping = {v: to_mg(dev.instantiate(ast.V(v), env))
               for v in variables(renamed[0]) | variables(renamed[1])}
    r = instance(m, r, mapping)
    return lift(m, r, root, tuple("L" if p == 0 else "R" for p in path))


def compile_completion(m, source):
    seed = to_ast(source[0]), to_ast(source[1])
    residual = dev.residual(seed)
    i, j, path = residual["pair"]
    peak = to_mg(residual["peak"])

    def chain(index, prefix, first_path, trace):
        r = step(m, source, seed, index, prefix, residual["substitution"], peak, first_path)
        for before, after, k, p, env in trace:
            assert r.rhs == to_mg(before)
            nxt = step(m, source, seed, k, f"N{k}_", env, r.rhs, p)
            assert nxt.rhs == to_mg(after)
            r = trans(m, r, nxt)
        return r

    left = chain(i, f"O{i}_", (), residual["left_trace"])
    right = chain(j, f"I{j}_", path, residual["right_trace"])
    assert left.rhs == to_mg(residual["left_nf"])
    assert right.rhs == to_mg(residual["right_nf"])
    result = trans(m, symmetry(m, left), right)
    assert result.lhs != result.rhs
    search = m.CompactSuperposition(m, source, source, time.monotonic() + 30,
        dict(m.COMPACT_SUPERPOSITION_PROBE, maximum_term_size=10000))
    nodes, root = search.compile(result)
    assert m.replay_dag(source, nodes, root, maximum_term_size=10000,
                        maximum_nodes=100000), "Independent DAG replay rejected completion"
    assert (nodes[root].lhs, nodes[root].rhs) == (result.lhs, result.rhs)
    goal = result.lhs, result.rhs, tuple(sorted(m.term_variables(result.lhs) | m.term_variables(result.rhs)))
    certificate, count = m.make_dag_certificate(goal, nodes, root)
    return result, goal, certificate, {"proof_nodes": count, "pair": [i, j, list(path)]}


def run_core(m, source, goal, extra=None, seconds=10.0):
    """Same pinned CompactSuperposition scheduler in both arms."""
    import heapq
    limits = dict(m.COMPACT_SUPERPOSITION_PROBE)
    limits.update(seconds=seconds, maximum_term_size=65, maximum_replay_term_size=10000,
        maximum_depth=12, maximum_rules=1000, maximum_rounds=128,
        new_clauses_per_round=512, maximum_clauses=12000,
        normalization_steps=128, maximum_proof_nodes=100000)
    deadline = time.monotonic() + seconds
    search = m.CompactSuperposition(m, source, goal, deadline, limits)
    initial = list(search.clauses)
    if extra is not None:
        assert search.add_clause(extra), "Completion was already present in the initial state"
    active, heap, queued = [], [], set()
    serial = added = 0

    def variants(r):
        oriented = search.orient(r)
        if oriented is not None:
            return [oriented]
        out = []
        if r.lhs[0] != "var":
            out.append(r)
        if r.rhs[0] != "var":
            out.append(symmetry(m, r))
        return out

    def endpoint_key(r):
        names = {}
        forward = (m.alpha_canonical_term(r.lhs, names), m.alpha_canonical_term(r.rhs, names))
        names = {}
        reverse = (m.alpha_canonical_term(r.rhs, names), m.alpha_canonical_term(r.lhs, names))
        return min(forward, reverse)

    def push_pairs(outer, inner, oi, ii, depth):
        nonlocal serial
        for path in m.nonvariable_positions(outer.lhs, maximum_depth=limits["maximum_depth"], include_root=True):
            if time.monotonic() >= deadline:
                return
            candidate = search.critical_pair(outer, inner, oi, ii, path)
            if candidate is None or max(m.term_size(candidate.lhs), m.term_size(candidate.rhs)) > limits["maximum_term_size"]:
                continue
            key = endpoint_key(candidate)
            if key in queued:
                continue
            queued.add(key)
            serial += 1
            heapq.heappush(heap, (m.term_size(candidate.lhs) + m.term_size(candidate.rhs) + 2 * depth,
                candidate.cost, serial, depth, key, candidate))
            if len(heap) > 20000:
                heap.sort()
                del heap[20000:]
                heapq.heapify(heap)

    def activate(r, depth):
        base = len(active)
        active.extend(variants(r))
        for ni in range(base, len(active)):
            for oi, other in enumerate(list(active)):
                push_pairs(active[ni], other, ni, oi, depth + 1)
                if oi < base:
                    push_pairs(other, active[ni], oi, ni, depth + 1)

    def finish():
        proof = search.target_proof(search.rules())
        if proof is None or (proof.lhs, proof.rhs) != goal[:2]:
            return None
        nodes, root = search.compile(proof)
        if not m.replay_dag(source, nodes, root, maximum_term_size=10000, maximum_nodes=100000):
            raise AssertionError("Solver produced an invalid proof")
        assert (nodes[root].lhs, nodes[root].rhs) == goal[:2]
        code, count = m.make_dag_certificate(goal, nodes, root)
        return {"certificate": code, "proof_nodes": count, "added_clauses": added}

    for r in initial:
        activate(r, 0)
    if extra is not None:
        activate(extra, 0)
    found = finish()
    while found is None and heap and added < 128 and len(search.clauses) < limits["maximum_clauses"] and time.monotonic() < deadline:
        _, _, _, depth, key, candidate = heapq.heappop(heap)
        queued.discard(key)
        candidate = search.interreduce(candidate, list(active))
        if candidate.lhs == candidate.rhs or not search.add_clause(candidate):
            continue
        added += 1
        r = search.clauses[-1]
        search.superpositions += 1
        found = finish()
        if found is None:
            activate(r, depth)
    return found, {"added_clauses": added, "generated": search.generated,
                   "active": len(active), "pending": len(heap), "expired": time.monotonic() >= deadline}


def standalone_goal(m, source, goal):
    render = m.render_term
    return "\n".join(["import Std", "", "class Magma (G : Type) where", "  op : G → G → G",
        "infixl:70 \" ◇ \" => Magma.op", "", "def Goal : Prop := ∀ (G : Type) [Magma G],",
        f"  (∀ ({' '.join(source[2])} : G), {render(source[0])} = {render(source[1])}) →",
        f"  (∀ ({' '.join(goal[2])} : G), {render(goal[0])} = {render(goal[1])})", ""])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--solver", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=10.0)
    args = parser.parse_args()
    m = load_solver(args.solver)
    cases = {"E40909": "(((((y ◇ x) ◇ y) ◇ y) ◇ z) ◇ y) = x",
             "E11116": "y ◇ ((x ◇ (z ◇ x)) ◇ (y ◇ y)) = x"}
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    for name, text in cases.items():
        source = m.parse_equation(text)
        extra, goal, generated, meta = compile_completion(m, source)
        controls = {}
        for label, enabled in (("baseline", False), ("installed", True), ("ablation", False)):
            found, metrics = run_core(m, source, goal, extra if enabled else None, args.seconds)
            controls[label] = {"replay": found is not None, **metrics}
            if found is not None:
                (args.output / f"{name}_{label}.lean").write_text(found["certificate"])
                controls[label]["certificate_sha256"] = hashlib.sha256(found["certificate"].encode()).hexdigest()
                controls[label]["proof_nodes"] = found["proof_nodes"]
        assert controls["baseline"]["replay"] == controls["ablation"]["replay"]
        (args.output / f"{name}_generated.lean").write_text(generated)
        (args.output / f"{name}_JudgeProblem.lean").write_text(standalone_goal(m, source, goal))
        results.append({"case": name, "source": text, "goal": [m.render_term(goal[0]), m.render_term(goal[1])],
                        "completion": meta, "controls": controls})
        print("AUSTIN_SOLVER_CORE_AB " + json.dumps(results[-1], sort_keys=True), flush=True)
    (args.output / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print("AUSTIN_SOLVER_CORE_AB_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
