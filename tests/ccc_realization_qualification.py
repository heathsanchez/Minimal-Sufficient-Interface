"""Finite residual-driven realization qualification; no unrestricted-genesis claim."""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from itertools import product
import json
import operator
import sys
import unittest

@dataclass(frozen=True)
class Op:
    inputs: tuple[str, ...]
    output: str
    fn: object

RAW = {
    "eq": Op(("n", "n"), "b", operator.eq),
    "less": Op(("n", "n"), "b", operator.lt),
    "succ": Op(("n",), "n", lambda a: a + 1),
    "double": Op(("n",), "n", lambda a: 2 * a),
    "not": Op(("b",), "b", operator.not_),
    "and": Op(("b", "b"), "b", operator.and_),
    "or": Op(("b", "b"), "b", operator.or_),
}

def evaluate(expr, env):
    tag, *args = expr
    if tag == "arg":
        return env[args[0]]
    if tag == "zero":
        return 0
    return RAW[tag].fn(*(evaluate(a, env) for a in args))

def enumerate_language(variables, primitives, universe, max_size):
    """Bottom-up typed enumeration, retaining minimum-size semantic representatives."""
    layers, seen = {}, set()
    for size in range(1, max_size + 1):
        layer = {"n": [], "b": []}
        proposals = []
        if size == 1:
            proposals = [("n", ("arg", v)) for v in variables]
            if "zero" in primitives:
                proposals.append(("n", ("zero",)))
        else:
            for name in primitives:
                if name == "zero":
                    continue
                op = RAW[name]
                if len(op.inputs) == 1:
                    proposals.extend((op.output, (name, child))
                                     for child in layers[size - 1][op.inputs[0]])
                else:
                    for left_size in range(1, size - 1):
                        right_size = size - 1 - left_size
                        proposals.extend((op.output, (name, a, b))
                                         for a, b in product(layers[left_size][op.inputs[0]],
                                                             layers[right_size][op.inputs[1]]))
        for typ, expr in proposals:
            signature = (typ, tuple(evaluate(expr, env) for env in universe))
            if signature not in seen:
                seen.add(signature)
                layer[typ].append(expr)
        layers[size] = layer
    return layers

def synthesize(variables, primitives, universe, typ, examples, max_size=4):
    layers = enumerate_language(variables, primitives, universe, max_size)
    return [(size, expr) for size, layer in layers.items() for expr in layer[typ]
            if all(evaluate(expr, env) == value for env, value in examples)]

def first(*args, **kwargs):
    return next(iter(synthesize(*args, **kwargs)), None)

def reachable(start, target, moves, budget):
    queue, seen = deque([(start, 0)]), {start}
    while queue:
        state, depth = queue.popleft()
        if state == target:
            return depth
        if depth == budget:
            continue
        for move in moves:
            nxt = evaluate(move, (state, 0))
            if nxt not in seen and 0 <= nxt <= 64:
                seen.add(nxt)
                queue.append((nxt, depth + 1))
    return None

def literal_value(lit, valuation):
    return not valuation[lit[1]] if isinstance(lit, tuple) else valuation[lit]

def clause_value(clause, valuation):
    return any(literal_value(lit, valuation) for lit in clause)

def resolve_clauses(a, b):
    """Supplied generic resolution constructor, not a discovered inference rule."""
    result = set()
    for lit in a:
        opposite = lit[1] if isinstance(lit, tuple) else ("not", lit)
        if opposite in b:
            result.add(frozenset((a - {lit}) | (b - {opposite})))
    return result

class RealizationQualification(unittest.TestCase):
    def setUp(self):
        self.world = list(product(range(4), repeat=2))
        self.swap = [((0, 1), True), ((1, 0), False)]

    def test_01_swap_symmetry(self):
        result = first((0, 1), ("eq", "less"), self.world, "b", self.swap, 3)
        self.assertEqual(result, (3, ("less", ("arg", 0), ("arg", 1))))
        self.assertIsNone(first((0, 1), ("eq", "less"), self.world, "b", self.swap, 2))
        self.assertTrue(all(evaluate(result[1], x) == y for x, y in self.swap))

    def test_02_missing_argument_position(self):
        examples = [((0, 3), 0), ((1, 3), 1)]
        result = first((0, 1), (), self.world, "n", examples, 1)
        self.assertEqual(result, (1, ("arg", 0)))
        self.assertIsNone(first((1,), (), self.world, "n", examples, 1))

    def test_03_missing_composition(self):
        examples = [((x, 0), 2*x+1) for x in range(4)]
        result = first((0,), ("succ", "double"), self.world, "n", examples, 3)
        self.assertEqual(result, (3, ("succ", ("double", ("arg", 0)))))
        self.assertIsNone(first((0,), ("succ", "double"), self.world, "n", examples, 2))

    def test_04_missing_constant(self):
        examples = [(env, 1) for env in self.world]
        result = first((0,), ("zero", "succ"), self.world, "n", examples, 2)
        self.assertEqual(result, (2, ("succ", ("zero",))))
        self.assertIsNone(first((0,), ("zero",), self.world, "n", examples, 2))

    def test_05_missing_predicate(self):
        examples = [(env, env[0] == 0) for env in self.world]
        result = first((0,), ("zero", "eq", "not"), self.world, "b", examples, 4)
        self.assertEqual(result[0], 3)
        self.assertIsNone(first((0,), ("zero", "not"), self.world, "b", examples, 4))

    def test_06_missing_proof_rule(self):
        p, q = "p", "q"
        premises = [frozenset((p, q)), frozenset((("not", p),))]
        generated = set().union(*(resolve_clauses(a, b) for a, b in product(premises, repeat=2)))
        self.assertIn(frozenset((q,)), generated)
        self.assertNotIn(frozenset((q,)), premises)
        for pv, qv in product((False, True), repeat=2):
            valuation = {p: pv, q: qv}
            self.assertTrue(not all(clause_value(c, valuation) for c in premises)
                            or clause_value(frozenset((q,)), valuation))

    def test_07_missing_search_operator(self):
        inc = ("succ", ("arg", 0))
        self.assertIsNone(reachable(0, 7, [inc], 3))
        layers = enumerate_language((0,), ("succ", "double"), self.world, 3)
        generated = next(expr for expr in layers[3]["n"]
                         if reachable(0, 7, [inc, expr], 3) is not None)
        self.assertEqual(reachable(0, 7, [inc, generated], 3), 3)
        self.assertIsNone(reachable(0, 7, [inc], 3))

    def test_08_ambiguous_realizations(self):
        less = ("less", ("arg", 0), ("arg", 1))
        alternative = ("not", ("less", ("arg", 1), ("arg", 0)))
        for expr in (less, alternative):
            self.assertTrue(all(evaluate(expr, x) == y for x, y in self.swap))
        self.assertEqual(evaluate(less, (2, 2)), False)
        self.assertEqual(evaluate(alternative, (2, 2)), True)
        new_evidence = self.swap + [((2, 2), False)]
        self.assertTrue(all(evaluate(less, x) == y for x, y in new_evidence))
        self.assertFalse(all(evaluate(alternative, x) == y for x, y in new_evidence))

    def test_09_impossible_realization(self):
        grammar = ("eq", "not", "and", "or")
        layers = enumerate_language((0, 1), grammar, self.world, 7)
        expressions = [e for layer in layers.values() for e in layer["b"]]
        self.assertTrue(expressions)
        self.assertTrue(all(evaluate(e, (a, b)) == evaluate(e, (b, a))
                            for e in expressions for a, b in self.world))
        self.assertFalse(synthesize((0, 1), grammar, self.world, "b", self.swap, 7))
        # The unrestricted-depth statement is proved separately in Lean.

    def test_10_recursive_transfer_and_ablation(self):
        result = first((0, 1), ("eq", "less"), self.world, "b", self.swap, 3)
        expr = result[1]
        heldout = [((2, 3), True), ((3, 2), False)]
        baseline = ("eq", ("arg", 0), ("arg", 1))
        score = lambda e: sum(evaluate(e, x) == y for x, y in heldout)
        self.assertEqual((score(baseline), score(expr), score(baseline)), (1, 2, 1))
        self.assertTrue(all(evaluate(expr, x) == y for x, y in heldout))

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RealizationQualification)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    summary = {"scope": "finite declared grammar", "tests": result.testsRun,
               "failures": len(result.failures), "errors": len(result.errors),
               "passed": result.wasSuccessful(), "unrestricted_genesis": False}
    print("REALIZATION_QUALIFICATION=" + json.dumps(summary, sort_keys=True))
    sys.exit(0 if result.wasSuccessful() else 1)
