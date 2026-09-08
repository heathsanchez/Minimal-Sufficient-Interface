"""Trusted arithmetic qualification for the target-blind developer.

The learner receives only query/predict/check. This is a transparent local
holdout, not a cryptographically protected benchmark. The verifier retains
recurrence specifications and checks the semantic provenance of each step.
Lean independently checks the emitted all-Nat theorems and finite obstructions.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from hashlib import sha256
import json
import operator
import unittest

from blind_development import (Program, State, Observation, Discovery, candidates,
                               discover, SOURCE_BOUND, BASES)

SEEDS = ('succ', 'double')
ADD_ID = 'certified-add'
SPECIFICATIONS = {
    'T17': ('zero', 'add', operator.mul),
    'T83': ('one', 'mul', pow),
}


def digest(x):
    return sha256(json.dumps(x, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


@dataclass(frozen=True)
class Certificate:
    target: str
    program: Program
    dependencies: tuple[str, ...]
    identity: str


@dataclass(frozen=True)
class Decision:
    accepted: bool
    certificate: Certificate | None = None
    witness: tuple[int, int, int] | None = None


class TrustedRegistry:
    def __init__(self):
        # The initial addition capability is the previously verified baseline.
        self.definitions = {ADD_ID: Program('input', 'succ')}
        self.semantics = {'succ': 'succ', 'double': 'double', ADD_ID: 'add'}
        self.certificates = {}
        self.state = State(SEEDS + (ADD_ID,))

    def _step(self, step, x, a):
        if step == 'succ': return a + 1
        if step == 'double': return 2 * a
        if step not in self.definitions: raise ValueError('Unknown step')
        return self.evaluate(self.definitions[step], x, a)

    def evaluate(self, p, x, y):
        if p.base not in BASES or p.step not in self.state.steps:
            raise ValueError('Uncertified program')
        if type(x) is not int or type(y) is not int or x < 0 or y < 0:
            raise ValueError('Natural inputs required')
        value = {'zero': 0, 'one': 1, 'input': x}[p.base]
        for _ in range(y):
            value = self._step(p.step, x, value)
        return value

    def _valid(self, cert):
        if not isinstance(cert, Certificate) or cert.target not in SPECIFICATIONS:
            return False
        base, semantic_step, _ = SPECIFICATIONS[cert.target]
        if cert.program.base != base or cert.program.step not in self.state.steps:
            return False
        if self.semantics[cert.program.step] != semantic_step:
            return False
        deps = () if cert.program.step in SEEDS else (cert.program.step,)
        return (cert.dependencies == deps and
                cert.identity == digest((cert.target, cert.program.source(), deps)))

    def check(self, target, p):
        if p not in candidates(self.state):
            raise ValueError('Candidate outside current grammar')
        if target not in SPECIFICATIONS:
            raise ValueError('Unknown target')
        if p.base == SPECIFICATIONS[target][0] and self.semantics[p.step] == SPECIFICATIONS[target][1]:
            deps = () if p.step in SEEDS else (p.step,)
            cert = Certificate(target, p, deps, digest((target, p.source(), deps)))
            assert self._valid(cert)
            return Decision(True, cert)
        # A finite counterexample is evidence, never a proof of universal equality.
        reference = SPECIFICATIONS[target][2]
        for x in range(4):
            for y in range(5):
                if self.evaluate(p, x, y) != reference(x, y):
                    return Decision(False, witness=(x, y, reference(x, y)))
        return Decision(False)

    def install(self, cert):
        if not self._valid(cert) or cert.program not in candidates(self.state):
            raise ValueError('Invalid certificate')
        if any(c.target == cert.target for c in self.certificates.values()):
            raise ValueError('Duplicate target')
        ident = 'cert-' + cert.identity
        self.definitions[ident] = cert.program
        self.semantics[ident] = {'T17': 'mul', 'T83': 'pow'}[cert.target]
        self.certificates[ident] = cert
        self.state = State(self.state.steps + (ident,), self.state.bound)
        return ident

    def oracle(self, target):
        registry = self
        class Interface:
            def query(self, x, y):
                return SPECIFICATIONS[target][2](x, y)
            def predict(self, p, x, y):
                return registry.evaluate(p, x, y)
            def check(self, p):
                return registry.check(target, p)
        return Interface()


def run_qualification():
    registry = TrustedRegistry()
    first = discover(registry.state, registry.oracle('T17'))
    assert first.reason == 'certified'
    before = registry.state
    installed = registry.install(first.certificate)
    assert registry.state.bound == before.bound == SOURCE_BOUND
    assert registry.state.steps[:-1] == before.steps
    second = discover(registry.state, registry.oracle('T83'))
    assert second.reason == 'certified'
    old = TrustedRegistry()
    ablation = discover(old.state, old.oracle('T83'))
    assert ablation.reason == 'exhausted' and ablation.program is None
    assert len({p for p, _ in ablation.eliminated}) == len(candidates(old.state))
    # Transfer is evaluated outside the query domain; it is not a claim about ARC.
    heldout = (5, 4)
    predicted = registry.evaluate(second.program, *heldout)
    observed = registry.oracle('T83').query(*heldout)
    assert predicted == observed == 625
    return {'scope': 'target-blind one-iteration grammar',
            'baseline': '790a049ce0df6eafd7dda9db31e19c881eb2f88b',
            'source_bound': SOURCE_BOUND, 'initial_candidates': len(candidates(before)),
            'after_install_candidates': len(candidates(registry.state)),
            'installed_step': installed, 'first': first, 'second': second,
            'ablation': ablation, 'heldout': heldout,
            'heldout_prediction': predicted, 'external_lean_required': True,
            'unrestricted_genesis': False}


LEAN_STEP_NAMES = {'succ': 'Step.succ', 'double': 'Step.double'}
LEAN_BASE_NAMES = {'zero': 'Base.zero', 'one': 'Base.one', 'input': 'Base.input'}


def lean_source():
    result = run_qualification()
    first, second, ablation = result['first'], result['second'], result['ablation']
    # The proof backend receives the private specification only after search.
    # Its generic recurrence theorem is independent of target names.
    lines = ['import LemmaSynthesis.OpenDevelopment', '',
             'namespace BlindDevelopment', 'open OpenDevelopment', '',
             'def recursor (b : Nat → Nat) (s : Nat → Nat → Nat) (x y : Nat) : Nat :=',
             '  Nat.rec (b x) (fun _ a => s x a) y', '',
             'theorem eval_eq_of_parts (p : Program) (b : Nat → Nat) (s : Nat → Nat → Nat)',
             '    (hb : ∀ x, baseValue p.base x = b x)',
             '    (hs : ∀ x a, stepValue p.step x a = s x a) :',
             '    ∀ x y, eval p x y = recursor b s x y := by',
             '  intro x y',
             '  have hstep : (fun _ a => stepValue p.step x a) = (fun _ a => s x a) := by',
             '    funext n a', '    exact hs x a',
             '  unfold eval recursor', '  rw [hb x, hstep]', '',
             'theorem mul_recursor (x y : Nat) :',
             '    recursor (fun _ => 0) (fun x a => x + a) x y = x * y := by',
             '  induction y with', '  | zero => rfl',
             '  | succ y ih =>', '      change x + recursor (fun _ => 0) (fun x a => x + a) x y = x * Nat.succ y',
             '      rw [ih]', '      simp [Nat.mul_succ, Nat.add_comm]', '',
             'theorem pow_recursor (x y : Nat) :',
             '    recursor (fun _ => 1) (fun x a => x * a) x y = x ^ y := by',
             '  induction y with', '  | zero => rfl',
             '  | succ y ih =>', '      change x * recursor (fun _ => 1) (fun x a => x * a) x y = x ^ Nat.succ y',
             '      rw [ih]', '      simp [Nat.pow_succ, Nat.mul_comm]', '']
    def source(p):
        step = {'succ': '.succ', 'double': '.double', ADD_ID: '.learned0'}
        step.update({result['installed_step']: '.learned1'})
        return f'⟨.{p.base}, {step[p.step]}⟩'
    for label, discovery, base, step_expr, step_proof, rec_thm, target in [
        ('acquired', first, '0', 'x + a', 'generated0_correct x a', 'mul_recursor', 'x * y'),
        ('transferred', second, '1', 'x * a', 'generated1_correct x a', 'pow_recursor', 'x ^ y')]:
        p = source(discovery.program)
        lines += [f'theorem {label}_correct (x y : Nat) : eval {p} x y = {target} := by',
                  f'  have hb : ∀ x, baseValue {p}.base x = {base} := by',
                  '    intro x', '    rfl',
                  f'  have hs : ∀ x a, stepValue {p}.step x a = {step_expr} := by',
                  '    intro x a', f'    exact {step_proof}',
                  f'  exact (eval_eq_of_parts {p} (fun _ => {base}) (fun x a => {step_expr}) hb hs x y).trans ({rec_thm} x y)', '']
    # Every source in the ablated grammar gets its own checked counterexample.
    lines += ['def ablatedSteps : List Step := [.succ, .double, .learned0]', '',
              'private theorem ablationTable :',
              '    AllFailure (fun x y => x ^ y) (candidates ablatedSteps) := by']
    witness = {p: o for p, o in ablation.eliminated}
    ordered = [witness[p] for p in candidates(State(SEEDS + (ADD_ID,)))]
    nested = 'True.intro'
    for o in reversed(ordered):
        nested = f'⟨⟨{o.x}, {o.y}, by decide⟩, {nested}⟩'
    lines += ['  exact ' + nested, '',
              'theorem ablation_obstruction (p : Program) (hp : p ∈ candidates ablatedSteps) :',
              '    ¬ ∀ x y, eval p x y = x ^ y := by',
              '  intro h',
              '  obtain ⟨x, y, hne⟩ := allFailureSound _ _ ablationTable p hp',
              '  exact hne (h x y)', '',
              'theorem acquired_reachable :',
              f'    {source(first.program)} ∈ candidates ablatedSteps := by decide', '',
              'theorem transferred_reachable :',
              f'    {source(second.program)} ∈ candidates [.succ, .double, .learned0, .learned1] := by decide', '',
              'end BlindDevelopment', '']
    return '\n'.join(lines)


class QualificationTests(unittest.TestCase):
    def test_blind_acquisition_and_transfer(self):
        q = run_qualification()
        self.assertEqual(q['first'].reason, 'certified')
        self.assertEqual(q['second'].reason, 'certified')
        self.assertEqual(q['heldout_prediction'], 625)
        self.assertEqual(q['initial_candidates'], 9)
        self.assertEqual(q['after_install_candidates'], 12)

    def test_ablation_is_complete(self):
        q = run_qualification()
        self.assertEqual(q['ablation'].reason, 'exhausted')
        self.assertEqual(len({p for p, _ in q['ablation'].eliminated}), 9)

    def test_no_predecessor_or_target_menu_in_developer(self):
        import inspect, blind_development
        src = inspect.getsource(blind_development)
        for forbidden in ('SPECIFICATIONS', 'T17', 'T83', 'operator.mul', 'Nat.mul_succ'):
            self.assertNotIn(forbidden, src)

    def test_reject_forgery_and_missing_dependency(self):
        r = TrustedRegistry()
        d = discover(r.state, r.oracle('T17'))
        with self.assertRaises(ValueError):
            r.install(replace(d.certificate, identity='forged'))
        with self.assertRaises(ValueError):
            r.install(replace(d.certificate, dependencies=()))
        r.install(d.certificate)
        with self.assertRaises(ValueError):
            r.install(d.certificate)

    def test_bound_and_unearned_capability(self):
        r = TrustedRegistry()
        self.assertEqual(run_qualification()['source_bound'], 3)
        with self.assertRaises(ValueError):
            candidates(State(r.state.steps, 4))
        with self.assertRaises(ValueError):
            r.evaluate(Program('one', 'uncertified'), 2, 3)
        self.assertEqual(discover(r.state, r.oracle('T83')).reason, 'exhausted')

    def test_all_elimination_witnesses_replay(self):
        q = run_qualification()
        for d, target, state in ((q['first'], 'T17', TrustedRegistry().state),
                                 (q['ablation'], 'T83', TrustedRegistry().state)):
            r = TrustedRegistry()
            oracle = r.oracle(target)
            for p, o in d.eliminated:
                self.assertIn(p, candidates(state))
                self.assertEqual(oracle.query(o.x, o.y), o.value)
                self.assertNotEqual(oracle.predict(p, o.x, o.y), o.value)

    def test_budget_and_indistinguishability(self):
        r = TrustedRegistry()
        self.assertEqual(discover(r.state, r.oracle('T17'), budget=0).reason, 'budget')
        self.assertEqual(discover(r.state, r.oracle('T17'), domain=((0, 0),)).reason,
                         'indistinguishable')

    def test_source_replay_and_no_admitted_proofs(self):
        s = lean_source()
        self.assertNotIn('sorry', s)
        self.assertNotIn('admit', s)
        self.assertEqual(s.encode(), __import__('pathlib').Path('lean/LemmaSynthesis/BlindDevelopment.lean').read_bytes())


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(QualificationTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        q = run_qualification()
        def report(d):
            return {'reason': d.reason, 'program': None if d.program is None else d.program.source(),
                    'queries': len(d.observations), 'checks': d.checks,
                    'eliminated': len({p for p, _ in d.eliminated})}
        print('BLIND_DEVELOPMENT_QUALIFICATION=' + json.dumps({
            'first': report(q['first']), 'second': report(q['second']),
            'ablation': report(q['ablation']), 'heldout': q['heldout'],
            'heldout_prediction': q['heldout_prediction'],
            'source_bound': q['source_bound'], 'external_lean_required': True,
            'unrestricted_genesis': False}, sort_keys=True))
    raise SystemExit(0 if result.wasSuccessful() else 1)
