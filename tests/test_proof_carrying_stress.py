"""Independent stress qualification for the frozen proof-carrying equality compiler.

No target-specific synthesis rules, oracle answers, or changes to the compiler.
The oracle enumerates structural occurrences independently of core.replace_one.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from hashlib import sha256
from itertools import product
from pathlib import Path
import random
import unittest

from experiments.mathgraph import proof_carrying_obligation as pc
from experiments.mathgraph import recursive_obligation_synthesis as core
from experiments.mathgraph.proof_carrying_lean import PRELUDE, source_text

VARS = ('x', 'y', 'z')
O = core.op
SEED = core.SEED

# New source families, not the three cases in the original qualification.
LAWS = (
    ('LeftProjection', (O('x', 'y'), 'x'), ('x', 'y')),
    ('RightProjection', (O('x', 'y'), 'y'), ('x', 'y')),
    ('Commutative', (O('x', 'y'), O('y', 'x')), ('x', 'y')),
    ('Associative', (O(O('x', 'y'), 'z'), O('x', O('y', 'z'))), VARS),
    ('Idempotent', (O('x', 'x'), 'x'), ('x',)),
    ('Medial', (O(O('x', 'y'), O('z', 'w')), O(O('x', 'z'), O('y', 'w'))), ('x', 'y', 'z', 'w')),
)


def independent_substitute(t, mapping):
    if isinstance(t, str):
        return mapping.get(t, t)
    return ('op', independent_substitute(t[1], mapping), independent_substitute(t[2], mapping))


def independent_replacements(t, old, new):
    """Return (path, replacement), including nested and repeated occurrences."""
    if t == old:
        yield (), new
    if isinstance(t, str):
        return
    for path, result in independent_replacements(t[1], old, new):
        yield (0,) + path, ('op', result, t[2])
    for path, result in independent_replacements(t[2], old, new):
        yield (1,) + path, ('op', t[1], result)


def oracle(law, variables, atoms, residual=SEED):
    found = set()
    for values in product(atoms, repeat=len(variables)):
        mapping = dict(zip(variables, values))
        frozen = tuple(zip(variables, values))
        lhs, rhs = (independent_substitute(t, mapping) for t in law)
        for side_name, side, other in (('lhs', lhs, rhs), ('rhs', rhs, lhs)):
            for _, rewritten in independent_replacements(side, *residual):
                found.add((frozen, side_name, (rewritten, other)))
    return found


def value(t, env, table, n):
    if isinstance(t, str):
        return env[t]
    return table[n * value(t[1], env, table, n) + value(t[2], env, table, n)]


def holds(eq, env, table, n):
    return value(eq[0], env, table, n) == value(eq[1], env, table, n)


def models(law, variables, n):
    for table in product(range(n), repeat=n*n):
        if all(holds(law, dict(zip(variables, values)), table, n)
               for values in product(range(n), repeat=len(variables))):
            yield table


def compiled_cases():
    cases = []
    for label, law, variables in LAWS:
        state = pc.State(law, variables, SEED)
        candidates = core.synthesize(law, variables, branch_left=SEED[0],
                                     branch_right=SEED[1], atoms=('A', 'p', 'q', 'F'))
        # Retain a bounded, deterministic sample without selecting a desired answer.
        for candidate in candidates[:4]:
            state, _ = pc.compile_candidate(state, candidate)
        cases.append((label, state))
    return cases


class ProofCarryingStress(unittest.TestCase):
    def test_independent_oracle_and_contexts(self):
        rng = random.Random(20260909)
        cases = list(LAWS)
        def term(depth):
            if depth == 0 or rng.randrange(3) == 0:
                return rng.choice(VARS)
            return O(term(depth-1), term(depth-1))
        for i in range(16):
            cases.append((f'Random{i}', (term(3), term(3)), VARS))
        # Includes residual occurrences on both sides and at multiple depths.
        atoms = ('A', 'p', 'q', 'F')
        checked = 0
        left = right = nested = 0
        for label, law, variables in cases:
            state = pc.State(law, variables, SEED)
            actual = core.synthesize(law, variables, branch_left=SEED[0],
                                     branch_right=SEED[1], atoms=atoms)
            keys = {(c.substitution, c.rewritten_side, c.equation) for c in actual}
            self.assertEqual(keys, oracle(law, variables, atoms), label)
            self.assertEqual(len(keys), len(actual), label)
            for candidate in actual:
                after, cert = pc.compile_candidate(state, candidate)
                self.assertTrue(pc.check_state(after))
                self.assertEqual(cert.equation, candidate.equation)
                checked += 1
                left += candidate.rewritten_side == 'lhs'
                right += candidate.rewritten_side == 'rhs'
                nested += any(core.is_op(t) for _, t in candidate.substitution)
        self.assertGreater(checked, 0)
        self.assertGreater(left, 0)
        self.assertGreater(right, 0)
        self.assertGreater(nested, 0)
        print(f'INDEPENDENT_ORACLE=PASS cases={len(cases)} candidates={checked} lhs={left} rhs={right} compound_substitutions={nested}')

    def test_exhaustive_finite_semantics(self):
        checked = 0
        nonvacuous = 0
        for label, state in compiled_cases():
            # Every binary operation on two elements; all 19,683 operations on
            # three elements for the first three held-out law families.
            orders = (2, 3) if label in ('LeftProjection', 'RightProjection', 'Commutative') else (2,)
            for n in orders:
                count = 0
                for table in models(state.source, state.source_variables, n):
                    count += 1
                    names = sorted(set().union(*(pc.variables(t) for t in state.source + state.seed),
                                               *(pc.variables(t) for c in state.archive for t in c.equation)))
                    for values in product(range(n), repeat=len(names)):
                        env = dict(zip(names, values))
                        if not holds(state.seed, env, table, n):
                            continue
                        for cert in state.archive:
                            self.assertTrue(holds(cert.equation, env, table, n),
                                            (label, n, table, env, cert.identity))
                            checked += 1
                self.assertGreater(count, 0, (label, n))
                nonvacuous += count
        print(f'FINITE_SEMANTICS=PASS model_tables={nonvacuous} conditional_claim_checks={checked}')

    def test_recursive_reuse_and_negative_countermodel(self):
        for label, law in (('E40909', core.LAW_40909), ('E11116', core.LAW_11116)):
            state = pc.State(law, VARS, SEED)
            previous = None
            for i in range(5):
                state, cert = pc.next_branch(state, previous, f't{i}')
                self.assertEqual(cert.dependencies, () if i == 0 else (previous,))
                previous = cert.identity
            self.assertEqual(len(state.archive), 5)
            self.assertEqual(len({c.equation for c in state.archive}), 5)
            self.assertTrue(pc.check_state(state))
        law = LAWS[0][1]
        state = pc.State(law, LAWS[0][2], SEED)
        # Left projection satisfies the source law and the local seed, but not p=q.
        table = (0, 0, 1, 1)
        env = {'A': 0, 'p': 1, 'q': 0}
        self.assertTrue(holds(law, {'x': 0, 'y': 1}, table, 2))
        self.assertTrue(holds(SEED, env, table, 2))
        self.assertFalse(holds(('p', 'q'), env, table, 2))
        with self.assertRaises(pc.Rejected):
            pc.install(state, ('p', 'q'), pc.Proof('premise'))
        with self.assertRaises(pc.Rejected):
            pc.install(state, ('p', 'q'), pc.Proof('source', ((('x', 'p'), ('y', 'q')),)))
        print('RECURSIVE_REUSE=PASS generations=5 laws=2')
        print('NEGATIVE_COUNTERMODEL=PASS order=2')

    def test_deterministic_lean_replay(self):
        text = stress_lean_source()
        self.assertEqual(text, stress_lean_source())
        self.assertNotIn('sorry', text)
        self.assertNotIn('admit', text)
        self.assertIn('Derivation.sound', text)
        for label, _, _ in LAWS:
            self.assertIn('namespace ProofCarryingObligation.' + label, text)
        print('STRESS_SOURCE_SHA256=' + sha256(text.encode()).hexdigest())


def stress_lean_source():
    parts = [PRELUDE, '\nend ProofCarryingObligation\n']
    for label, state in compiled_cases():
        body = source_text(state)[len(PRELUDE):].rsplit('\nend ProofCarryingObligation', 1)[0]
        parts.extend((f'\nnamespace ProofCarryingObligation.{label}\n', body,
                      f'\nend ProofCarryingObligation.{label}\n'))
    return '\n'.join(parts)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--emit-lean', type=Path)
    args = parser.parse_args()
    if args.emit_lean:
        text = stress_lean_source()
        args.emit_lean.parent.mkdir(parents=True, exist_ok=True)
        args.emit_lean.write_text(text, encoding='utf-8')
        print('STRESS_SOURCE_SHA256=' + sha256(text.encode()).hexdigest())
    else:
        unittest.main(verbosity=2)
