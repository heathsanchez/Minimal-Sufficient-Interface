"""Transfer a source-derived completion consequence into MathGraph's proof DAG.

This is an isolated solver-core experiment, not a Stage 2 submission.  The
source law is the only input to development.  The target is exposed only to
the existing solver's closure test.  Every injected equality is independently
replayed from the original source before it can enter the search state.
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
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def to_ast(t):
    return ast.V(t[1]) if t[0] == "var" else ast.A(to_ast(t[1]), to_ast(t[2]))


def to_mg(t):
    return ("var", t.name) if isinstance(t, ast.V) else ("op", to_mg(t.left), to_mg(t.right))


def variables(t):
    return ast.vars(t)


def instantiate(t, mapping):
    return to_mg(dev.instantiate(t, mapping))


def source_recipe(m, source):
    return m.Recipe(source[0], source[1], "source", data=(
        tuple((v, ("var", v)) for v in source[2]), False))


def instance(m, recipe, mapping):
    lhs = m.substitute_partial(recipe.lhs, mapping)
    rhs = m.substitute_partial(recipe.rhs, mapping)
    return m.Recipe(lhs, rhs, "instantiate", (recipe,), tuple(sorted(mapping.items())))


def symmetry(m, recipe):
    return m.Recipe(recipe.rhs, recipe.lhs, "symmetry", (recipe,))


def trans(m, left, right):
    assert left.rhs == right.lhs, "Broken equality chain"
    return m.Recipe(left.lhs, right.rhs, "transitivity", (left, right))


def lift(m, recipe, root, path):
    assert m.get_subterm(root, path) == recipe.lhs
    current = recipe
    for index in range(len(path) - 1, -1, -1):
        context = m.get_subterm(root, path[:index])
        if path[index] == "L":
            sibling = context[2]
            current = m.Recipe(("op", current.lhs, sibling),
                ("op", current.rhs, sibling), "congruence", (current,), ("left", sibling))
        else:
            sibling = context[1]
            current = m.Recipe(("op", sibling, current.lhs),
                ("op", sibling, current.rhs), "congruence", (current,), ("right", sibling))
    assert current.lhs == root
    return current


def rule_recipe(m, source, seed, index, prefix):
    """Build the source or its promoted rule using only equality constructors."""
    base = source_recipe(m, source)
    renamed = {v: ast.V(prefix + v) for v in source[2]}
    branch = instance(m, base, {v: to_mg(t) for v, t in renamed.items()})
    if index == 0:
        return branch
    if index != 1:
        raise ValueError("Only the certified promotion is supported")
    path, attachment = dev.attachment(seed)
    lhs, rhs = seed
    arguments = {"A": lhs.left, "p": lhs.right, "w": ast.V("w")}
    source_args = {v: dev.instantiate(arguments[t.name], renamed)
                   for v, t in attachment.items()}
    original = dev.instantiate(lhs, source_args)
    promoted = ast.replace_at(original, path, dev.instantiate(rhs, renamed))
    source_step = instance(m, base, {v: to_mg(t) for v, t in source_args.items()})
    assert source_step.lhs == to_mg(original)
    back = lift(m, symmetry(m, branch), to_mg(promoted), tuple("L" if p == 0 else "R" for p in path))
    result = trans(m, back, source_step)
    expected = ast.rename_rule(dev.promote(seed), prefix)
    assert (result.lhs, result.rhs) == tuple(map(to_mg, expected))
    return result


def step(m, source, seed, index, prefix, env, root, path):
    recipe = rule_recipe(m, source, seed, index, prefix)
    renamed = ast.rename_rule((seed, dev.promote(seed))[index], prefix)
    mapping = {v: to_mg(ast.subst(ast.V(v), env))
               for v in variables(renamed[0]) | variables(renamed[1])}
    recipe = instance(m, recipe, mapping)
    return lift(m, recipe, root, tuple("L" if p == 0 else "R" for p in path))


def compile_completion(m, source):
    seed = to_ast(source[0]), to_ast(source[1])
    residual = dev.residual(seed)
    i, j, path = residual["pair"]
    peak = to_mg(residual["peak"])

    def chain(first_index, prefix, first_path, trace):
        current = peak
        proof = step(m, source, seed, first_index, prefix,
                     residual["substitution"], current, first_path)
        current = proof.rhs
        for before, after, index, path, env in trace:
            assert current == to_mg(before)
            nxt = step(m, source, seed, index, f"N{index}_", env, current, path)
            assert nxt.rhs == to_mg(after)
            proof = trans(m, proof, nxt)
            current = nxt.rhs
        return proof

    left = chain(i, f"O{i}_", (), residual["left_trace"])
    right = chain(j, f"I{j}_", path, residual["right_trace"])
    assert left.rhs == to_mg(residual["left_nf"])
    assert right.rhs == to_mg(residual["right_nf"])
    result = trans(m, symmetry(m, left), right)
    assert result.lhs != result.rhs
    nodes, root = m.CompactSuperposition(m, source, source, time.monotonic() + 30,
        {"maximum_term_size": 10000}).compile(result)
    assert m.replay_dag(source, nodes, root, maximum_term_size=10000,
                        maximum_nodes=100000), "Independent DAG replay rejected completion"
    assert (nodes[root].lhs, nodes[root].rhs) == (result.lhs, result.rhs)
    goal = result.lhs, result.rhs, tuple(sorted(m.term_variables(result.lhs) | m.term_variables(result.rhs)))
    certificate, proof_nodes = m.make_dag_certificate(goal, nodes, root)
    return result, goal, certificate, {"proof_nodes": proof_nodes, "pair": [i, j, list(path)]}


def run_core(m, source, goal, extra=None, seconds=10.0):
    """Use the actual pinned CompactSuperposition and its existing scheduler."""
    limits = dict(m.COMPACT_SUPERPOSITION_PROBE)
    limits.update(seconds=seconds, maximum_term_size=65, maximum_replay_term_size=10000,
        maximum_depth=12, maximum_rules=1000, maximum_rounds=128,
        new_clauses_per_round=512, maximum_clauses=12000,
        normalization_steps=128, maximum_proof_nodes=100000)
    deadline = time.monotonic() + seconds
    search = m.CompactSuperposition(m, source, goal, deadline, limits)
    initial = list(search.clauses)
    if extra is not None:
        assert search.add_clause(extra), "Completion was already present in the frozen initial state"
    # The existing source-only best-first completion scheduler, with all
    # initial proof-bearing clauses activated.  Both arms use identical code.
    import heapq
    active, heap, queued = [], [], set()
    serial = added = 0

    def variants(clause):
        oriented = search.orient(clause)
        if oriented is not None:
            return [oriented]
        out = []
        if clause.lhs[0] != "var":
            out.append(clause)
        if clause.rhs[0] != "var":
            out.append(symmetry(m, clause))
        return out

    def endpoint_key(recipe):
        names = {}
        forward = (m.alpha_canonical_term(recipe.lhs, names), m.alpha_canonical_term(recipe.rhs, names))
        names = {}
        reverse = (m.alpha_canonical_term(recipe.rhs, names), m.alpha_canonical_term(recipe.lhs, names))
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

    def activate(clause, depth):
        base = len(active)
        active.extend(variants(clause))
        for ni in range(base, len(active)):
            snapshot = list(active)
            for oi, other in enumerate(snapshot):
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

    for clause in initial:
        activate(clause, 0)
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
        clause = search.clauses[-1]
        search.superpositions += 1
        found = finish()
        if found is None:
            activate(clause, depth)
    return found, {"added_clauses": added, "generated": search.generated,
                   "active": len(active), "pending": len(heap), "expired": time.monotonic() >= deadline}


def standalone_goal(m, source, goal):
    render = m.render_term
    args = " ".join(source[2])
    target_args = " ".join(goal[2])
    return "\n".join(["import Std", "", "class Magma (G : Type) where", "  op : G → G → G",
        "infixl:70 \" ◇ \" => Magma.op", "",
        "def Goal : Prop := ∀ (G : Type) [Magma G],",
        f"  (∀ ({args} : G), {render(source[0])} = {render(source[1])}) →",
        f"  (∀ ({target_args} : G), {render(goal[0])} = {render(goal[1])})", ""])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--solver", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=10.0)
    args = parser.parse_args()
    m = load_solver(args.solver)
    cases = {
        "E40909": "(((((y ◇ x) ◇ y) ◇ y) ◇ z) ◇ y) = x",
        "E11116": "y ◇ ((x ◇ (z ◇ x)) ◇ (y ◇ y)) = x",
    }
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
                path = args.output / f"{name}_{label}.lean"
                path.write_text(found["certificate"])
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
