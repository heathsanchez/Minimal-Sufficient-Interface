"""Bounded, externally checked self-development qualification.

The raw grammar and policy constructors are declared in advance. No claim of
unrestricted genesis, optimal general learning, or a new foundational theorem.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from hashlib import sha256
import json
import unittest

X = ("x",)
RAW = ("zero", "succ", "double")
POLICIES = ("raw", "reuse")
BOUND = 3


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def affine_raw(term):
    """Independent exact semantics: a*x+b, valid for every natural x."""
    tag = term[0]
    if tag == "x" and len(term) == 1:
        return (1, 0)
    if tag == "zero" and len(term) == 1:
        return (0, 0)
    if tag in ("succ", "double") and len(term) == 2:
        a, b = affine_raw(term[1])
        return (a, b + 1) if tag == "succ" else (2*a, 2*b)
    raise ValueError("Not a raw, well-typed term")


def raw_size(term):
    affine_raw(term)
    return 1 if len(term) == 1 else 1 + raw_size(term[1])


def substitute(template, argument):
    if template == X:
        return argument
    if template == ("zero",):
        return template
    return (template[0], substitute(template[1], argument))


@dataclass(frozen=True)
class Certificate:
    target: tuple[int, int]
    raw_term: tuple
    identity: str


class Verifier:
    """Authority over certificates and transitions; never trusts cached scores."""
    @staticmethod
    def certificate(target, raw_term):
        if not isinstance(target, tuple) or len(target) != 2:
            raise ValueError("Malformed target")
        if any(type(v) is not int or v < 0 for v in target):
            raise ValueError("Target must be a natural affine map")
        if affine_raw(raw_term) != target:
            raise ValueError("Certificate does not establish its target")
        return Certificate(target, raw_term, digest([target, raw_term]))

    @staticmethod
    def check(cert):
        if not isinstance(cert, Certificate):
            raise ValueError("Uncertified capability")
        if Verifier.certificate(cert.target, cert.raw_term) != cert:
            raise ValueError("Forged or altered certificate")
        return True

    @staticmethod
    def state(state):
        if state.policy not in POLICIES or state.bound != BOUND:
            raise ValueError("Unapproved policy or resource change")
        identities = set()
        for cert in state.archive:
            Verifier.check(cert)
            if cert.identity in identities:
                raise ValueError("Duplicate capability")
            identities.add(cert.identity)
        return True


def expand(term, archive):
    tag = term[0]
    if tag == "macro" and len(term) == 3:
        cert = next((c for c in archive if c.identity == term[1]), None)
        if cert is None:
            raise ValueError("Unknown capability")
        Verifier.check(cert)
        return substitute(cert.raw_term, expand(term[2], archive))
    if tag in ("x", "zero"):
        affine_raw(term)
        return term
    if tag in ("succ", "double") and len(term) == 2:
        return (tag, expand(term[1], archive))
    raise ValueError("Unknown constructor")


@dataclass(frozen=True)
class State:
    policy: str = "raw"
    bound: int = BOUND
    archive: tuple[Certificate, ...] = ()


def enumerate_terms(state):
    """Complete bottom-up enumeration modulo exact affine semantics."""
    Verifier.state(state)
    operations = list(RAW)
    if state.policy == "reuse":
        operations += [("macro", cert.identity) for cert in state.archive]
    seen = set()
    layer = [X, ("zero",)]
    for size in range(1, state.bound + 1):
        candidates = layer if size == 1 else [
            (op, child) if isinstance(op, str) else (op[0], op[1], child)
            for child in previous for op in operations if op != "zero"
        ]
        previous = []
        for term in candidates:
            signature = affine_raw(expand(term, state.archive))
            if signature not in seen:
                seen.add(signature)
                previous.append(term)
                yield size, term, signature


def synthesize(state, target):
    return next(((n, term) for n, term, signature in enumerate_terms(state)
                 if signature == target), None)


@dataclass(frozen=True)
class Evidence:
    kind: str
    target: tuple[int, int]
    source: tuple
    certificate: Certificate
    policy_before: str
    policy_after: str
    cost: int


class Development:
    """One interpreter for object and process obligations; policy is state data."""
    def __init__(self, verifier=Verifier):
        self.verifier = verifier

    def object(self, state, target):
        self.verifier.state(state)
        found = synthesize(state, target)
        if found is None:
            return state, None
        cost, source = found
        cert = self.verifier.certificate(target, expand(source, state.archive))
        archive = state.archive if cert in state.archive else state.archive + (cert,)
        new = replace(state, archive=archive)
        self.verifier.state(new)
        evidence = Evidence("object", target, source, cert, state.policy, new.policy, cost)
        return new, evidence

    def process(self, state, target):
        """Search a declared policy grammar for the least adequate policy edit."""
        self.verifier.state(state)
        if synthesize(state, target) is not None:
            return state, None  # no demonstrated process residual
        for policy in POLICIES:
            candidate = replace(state, policy=policy)
            new, evidence = self.object(candidate, target)
            if evidence is not None:
                assert new.bound == state.bound
                assert new.archive[:len(state.archive)] == state.archive
                return new, replace(evidence, kind="process", policy_before=state.policy)
        return state, None


def verify_evidence(before, after, evidence):
    Verifier.state(before)
    Verifier.state(after)
    Verifier.check(evidence.certificate)
    assert after.bound == before.bound == BOUND
    assert after.archive[:len(before.archive)] == before.archive
    assert evidence.policy_before == before.policy
    assert evidence.policy_after == after.policy
    assert evidence.cost <= BOUND
    assert evidence.certificate in after.archive
    assert affine_raw(expand(evidence.source, before.archive)) == evidence.target
    assert any(n == evidence.cost and term == evidence.source
               for n, term, _ in enumerate_terms(replace(before, policy=after.policy)))
    if evidence.kind == "process":
        assert synthesize(before, evidence.target) is None
        assert after.policy in POLICIES
    else:
        assert evidence.kind == "object" and before.policy == after.policy
    return True


def qualification():
    d = Development()
    initial = State()
    # Targets are frozen before execution; no target implementation is supplied.
    targets = ((2, 1), (4, 3), (8, 7))
    a, e1 = d.object(initial, targets[0])
    assert e1 and verify_evidence(initial, a, e1)
    assert synthesize(a, targets[1]) is None
    b, e2 = d.process(a, targets[1])
    assert e2 and verify_evidence(a, b, e2)
    assert b.policy == "reuse"
    # The third task is not consulted in the policy-selection step.
    c, e3 = d.object(b, targets[2])
    assert e3 and verify_evidence(b, c, e3)
    assert synthesize(replace(b, policy="raw"), targets[2]) is None
    assert synthesize(replace(b, archive=(e1.certificate,)), targets[2]) is None
    for target in targets:
        assert synthesize(c, target) is not None
    return {"scope": "finite declared grammar", "bound": BOUND,
            "targets": targets, "policy_change": [a.policy, b.policy],
            "source_sizes": [e1.cost, e2.cost, e3.cost],
            "expanded_sizes": [raw_size(e.certificate.raw_term) for e in (e1, e2, e3)],
            "heldout_transfer": True, "policy_ablation": True,
            "second_capability_ablation": True, "unrestricted_genesis": False}


class QualificationTests(unittest.TestCase):
    def test_recursive_development(self):
        self.assertTrue(qualification()["heldout_transfer"])

    def test_exact_semantics(self):
        for term in [X, ("zero",), ("succ", ("double", X))]:
            a, b = affine_raw(term)
            self.assertTrue(all((a*x+b) == self.evaluate_raw(term, x) for x in range(12)))

    @staticmethod
    def evaluate_raw(term, x):
        if term == X: return x
        if term == ("zero",): return 0
        v = QualificationTests.evaluate_raw(term[1], x)
        return v+1 if term[0] == "succ" else 2*v

    def test_complete_raw_bound(self):
        self.assertIsNone(synthesize(State(), (4, 3)))
        self.assertIsNone(synthesize(State(), (8, 7)))
        self.assertEqual(synthesize(State(), (2, 1))[0], 3)

    def test_no_unearned_upgrade(self):
        self.assertEqual(Development().process(State(), (4, 3)), (State(), None))
        self.assertEqual(Development().process(State(), (2, 1)), (State(), None))

    def test_reject_forgery_and_resource_escape(self):
        good = Verifier.certificate((2, 1), ("succ", ("double", X)))
        bad = replace(good, target=(4, 3))
        with self.assertRaises(ValueError): Verifier.check(bad)
        with self.assertRaises(ValueError): Verifier.state(State(archive=(bad,)))
        with self.assertRaises(ValueError): Verifier.state(State(bound=7))
        with self.assertRaises(ValueError): Verifier.state(State(policy="unrestricted"))

    def test_reject_unknown_capability(self):
        with self.assertRaises(ValueError): expand(("macro", "forged", X), ())

    def test_no_false_process_residual(self):
        state = State(policy="reuse")
        new, evidence = Development().process(state, (2, 1))
        self.assertEqual((new, evidence), (state, None))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(QualificationTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        print("RECURSIVE_SOLVENT_QUALIFICATION=" + json.dumps(qualification(), sort_keys=True))
    raise SystemExit(0 if result.wasSuccessful() else 1)
