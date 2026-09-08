"""Bounded independent validation of the frozen MSI acquisition mechanisms.

No learner is changed here. Green means the measurements and proof checks ran;
scientific acceptance is recorded separately. The source-constructor checkout
is pinned to 7f962c53da728045ea8455976b9a4ee93c953ead.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import itertools
import json
import random
import unittest
from pathlib import Path

from experiments.mathgraph import recursive_obligation_synthesis as R

SEED = 20260908
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'source-constructor' / 'tests' / 'test_unscripted_constructor_family_genesis.py'
if not SOURCE.exists():
    SOURCE = ROOT / 'tests' / 'test_unscripted_constructor_family_genesis.py'
spec = importlib.util.spec_from_file_location('msi_frozen_constructor', SOURCE)
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
OUT = ROOT / 'results' / 'independent_genesis_validation.json'


def generated_laws():
    """Twelve seeded, unseen binary ASTs with one x and even y/z counts."""
    units = (R.op('y', 'x'), 'y', 'z', 'z')
    def trees(seq):
        if len(seq) == 1:
            yield seq[0]
        else:
            for k in range(1, len(seq)):
                for a in trees(seq[:k]):
                    for b in trees(seq[k:]):
                        yield R.op(a, b)
    all_laws = {t for perm in set(itertools.permutations(units)) for t in trees(perm)}
    ordered = sorted(all_laws, key=lambda t: hashlib.sha256(repr(t).encode()).digest())
    rng = random.Random(SEED)
    return [(ordered[i], 'x') for i in sorted(rng.sample(range(len(ordered)), 12))]


def inst(t, mapping):
    return mapping[t] if isinstance(t, str) and t in mapping else (
        t if isinstance(t, str) else ('op', inst(t[1], mapping), inst(t[2], mapping)))


def paths(t, needle, path=()):
    if t == needle:
        yield path
    if not isinstance(t, str):
        yield from paths(t[1], needle, path + (1,))
        yield from paths(t[2], needle, path + (2,))


def at_path(t, path, replacement):
    if not path:
        return replacement
    return ('op', at_path(t[1], path[1:], replacement), t[2]) if path[0] == 1 else (
        'op', t[1], at_path(t[2], path[1:], replacement))


def check_witness(law, variables, branch, witness):
    mapping = dict(witness.substitution)
    assert tuple(mapping) == tuple(variables)
    lhs, rhs = (inst(side, mapping) for side in law)
    side, other = (lhs, rhs) if witness.rewritten_side == 'lhs' else (rhs, lhs)
    return any((at_path(side, path, branch[1]), other) == witness.equation
               for path in paths(side, branch[0]))


def free_vars(t):
    return {t} if isinstance(t, str) else free_vars(t[1]) | free_vars(t[2])


def evaluate(t, table, env, n):
    if isinstance(t, str):
        return env[t]
    return table[n * evaluate(t[1], table, env, n) + evaluate(t[2], table, env, n)]


def holds(eq, table, env, n):
    return evaluate(eq[0], table, env, n) == evaluate(eq[1], table, env, n)


def finite_models(law, n=2):
    for table in itertools.product(range(n), repeat=n * n):
        if all(holds(law, table, dict(zip(('x', 'y', 'z'), values)), n)
               for values in itertools.product(range(n), repeat=3)):
            yield table


def semantic_check(law, seed, chain, n=2):
    models = list(finite_models(law, n))
    assert models, 'Vacuous model test'
    variables = sorted(set().union(*(free_vars(a) | free_vars(b) for a, b in chain)))
    checks = failures = 0
    for table in models:
        for values in itertools.product(range(n), repeat=len(variables)):
            env = dict(zip(variables, values))
            if holds(seed, table, env, n):
                for eq in chain[1:]:
                    checks += 1
                    failures += not holds(eq, table, env, n)
    return {'models': len(models), 'checks': checks, 'failures': failures}


def generated_worlds():
    """Twelve independently sampled target tables, not a list of answers."""
    rng = random.Random(SEED + 1)
    worlds = []
    for i in range(4):
        table = tuple(rng.randrange(3) for _ in range(9))
        worlds.append((f'local_binary_{i}', lambda f,g,x,t=table: t[3*f[x]+g[x]]))
    for i in range(4):
        table = tuple(rng.randrange(3) for _ in range(27))
        worlds.append((f'local_state_{i}', lambda f,g,x,t=table: t[9*x+3*f[x]+g[x]]))
    for i in range(4):
        table = tuple(rng.randrange(3) for _ in range(9))
        worlds.append((f'composite_pair_{i}', lambda f,g,x,t=table: t[3*f[g[x]]+g[f[x]]]))
    return worlds


def functional_evaluation(name, oracle, remove_verifier=False):
    n = 3
    discovery = C.permutations(n)
    if remove_verifier:
        # The oracle is not consulted at all during ablated acquisition.
        data = [(f,g,x,None) for f in discovery for g in discovery for x in range(n)]
    else:
        data = C.rows(discovery, discovery, n, oracle)
    kind, model = C.choose_extension_family(data)
    frozen = copy.deepcopy((kind, model))
    heldout = [(f,g,x,None) for f in C.all_maps(n) for g in C.all_maps(n)
               if not (f in discovery and g in discovery) for x in range(n)]
    # No oracle or label is supplied to the deployed model. Score afterward.
    predictions = []
    for row in heldout:
        try:
            predictions.append(C.predict(*frozen, row) if model is not None else None)
        except KeyError:
            predictions.append(None)
    truth = [oracle(f,g,x) for f,g,x,_ in heldout]
    errors = sum(a != b for a,b in zip(predictions, truth) if a is not None)
    coverage = sum(a is not None for a in predictions)
    return {'name': name, 'family': kind, 'train': len(data), 'heldout': len(heldout),
            'coverage': coverage, 'errors': errors, 'exact': coverage == len(truth) and errors == 0,
            'unverified': len(truth)-coverage, 'acquisition_verifier': not remove_verifier,
            'missing_labels_accepted': remove_verifier and model is not None}


class IndependentGenesisValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = {'protocol': 'msi-independent-v1', 'seed': SEED,
                      'recursive_source': '1a8e59d40c21ae8f621e933c858e2d4f794da293',
                      'constructor_source': '7f962c53da728045ea8455976b9a4ee93c953ead',
                      'claims': {}, 'results': {}}

    @classmethod
    def tearDownClass(cls):
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(cls.report, indent=2, sort_keys=True) + '\n')
        print('INDEPENDENT_GENESIS_VALIDATION=' + json.dumps(cls.report, sort_keys=True))

    def test_01_generated_source_grammars_and_independent_semantics(self):
        laws = generated_laws()
        entries = []
        for law in laws:
            chain, witnesses = R.replay(law, ('x','y','z'), R.SEED, 3, 'u')
            assert all(check_witness(law, ('x','y','z'), chain[i], w)
                       for i,w in enumerate(witnesses))
            semantic = semantic_check(law, R.SEED, chain)
            entries.append({'law': R.render(law[0])+' = x', 'sizes': [R.size(e[0]) for e in chain],
                            **semantic})
        # Independent oracle rejects a deliberately false consequence.
        xor = (0,1,1,0)
        self.assertTrue(holds(laws[0], xor, {'x':0,'y':0,'z':0}, 2))
        self.assertTrue(holds(R.SEED, xor, {'A':1,'p':0,'q':1}, 2))
        self.assertFalse(holds(('p','q'), xor, {'A':1,'p':0,'q':1}, 2))
        self.assertEqual(len({repr(law) for law in laws}), 12)
        self.assertTrue(all(e['models'] >= 1 and e['checks'] > 0 for e in entries))
        self.assertTrue(all(e['failures'] == 0 for e in entries))
        self.report['results']['generated_laws'] = entries
        self.report['claims']['generated_laws'] = 'PASS: 12 source ASTs, three recursive promotions, independent proof replay and all two-element models'

    def test_02_source_distinct_functional_tasks(self):
        entries = [functional_evaluation(name, oracle) for name,oracle in generated_worlds()]
        self.assertTrue(all(e['train'] == 108 and e['heldout'] == 2079 for e in entries))
        self.report['results']['functional_tasks'] = entries
        self.report['claims']['functional_transfer'] = {
            'exact': sum(e['exact'] for e in entries), 'total': len(entries),
            'incorrect_predictions': sum(e['errors'] for e in entries),
            'unsupported': sum(e['family'] is None for e in entries)}

    def test_03_verifier_removal_and_acquisition_ablation(self):
        worlds = [('sequential', lambda f,g,x: f[g[x]]),
                  ('pointwise', lambda f,g,x: min(f[x],g[x])),
                  ('gated', lambda f,g,x: f[x] if x == 0 else g[x])]
        entries = []
        for name, oracle in worlds:
            retained = functional_evaluation(name, oracle)
            no_labels = functional_evaluation(name, oracle, remove_verifier=True)
            self.assertTrue(retained['exact'])
            self.assertEqual(no_labels['coverage'], 0)
            self.assertFalse(no_labels['exact'])
            self.assertTrue(no_labels['missing_labels_accepted'])
            entries.append({'name':name, 'retained':retained, 'no_labels':no_labels})
        self.report['results']['verifier_ablation'] = entries
        self.report['claims']['verifier_ablation'] = 'PASS: retained prediction needs no verifier; removing acquisition labels gives no certified predictions. Missing-label rejection is not implemented in the frozen learner.'


if __name__ == '__main__':
    unittest.main(verbosity=2)
