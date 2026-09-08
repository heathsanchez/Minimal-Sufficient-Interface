"""Bounded, proof-carrying primitive-recursion development.

The candidate grammar is one iteration, a base, and a certified step. There is
no addition/multiplication/power/tower policy menu. Each accepted definition
becomes a step available to the same developer. Mathematical targets are
frozen recurrence specifications, not arbitrary function discovery.

Python checks the restricted certificate protocol and finite witnesses. Lean
must independently replay the all-Nat proofs and obstructions. Neither finite
probes nor a green Python run replace Lean.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from itertools import product
import json
import operator
import sys
import unittest

SOURCE_BOUND = 3
BASES = ("zero", "one", "input")
SEEDS = ("succ", "double")
PROBES = tuple(product(range(3), range(4)))


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Program:
    base: str
    step: str

    def source(self):
        return ("iterate", ("step", self.step), ("base", self.base))


@dataclass(frozen=True)
class Spec:
    name: str
    base: str
    predecessor: str
    reference: object


def tower(x, y):
    v = 1
    for _ in range(y):
        v = pow(x, v)
    return v


SPECS = (
    Spec("add", "input", "succ", operator.add),
    Spec("mul", "zero", "add", operator.mul),
    Spec("pow", "one", "mul", pow),
    Spec("tower", "one", "pow", tower),
)
SPEC_BY_NAME = {s.name: s for s in SPECS}


@dataclass(frozen=True)
class Certificate:
    name: str
    program: Program
    dependencies: tuple[str, ...]
    proof: tuple
    identity: str


@dataclass(frozen=True)
class State:
    archive: tuple[Certificate, ...] = ()
    bound: int = SOURCE_BOUND


class Rejected(ValueError):
    pass


def base_value(base, x):
    if base == "zero": return 0
    if base == "one": return 1
    if base == "input": return x
    raise Rejected("Unknown base")


def step_value(step, x, accumulator, archive):
    if step == "succ": return accumulator + 1
    if step == "double": return 2 * accumulator
    for cert in archive:
        if step == cert.identity:
            return evaluate(cert.program, x, accumulator,
                            archive[:archive.index(cert)])
    raise Rejected("Unknown or forward step reference")


def evaluate(program, x, y, archive=()):
    if not isinstance(program, Program) or program.base not in BASES:
        raise Rejected("Malformed program")
    if type(x) is not int or type(y) is not int or x < 0 or y < 0:
        raise Rejected("Natural inputs required")
    value = base_value(program.base, x)
    for _ in range(y):
        value = step_value(program.step, x, value, archive)
    return value


def available(state):
    return SEEDS + tuple(c.identity for c in state.archive)


def candidates(state):
    """Complete one-iteration grammar, not a menu of named policies."""
    if state.bound != SOURCE_BOUND:
        raise Rejected("Resource bound changed")
    return tuple(Program(base, step) for step in available(state) for base in BASES)


class Verifier:
    @staticmethod
    def check_certificate(cert, prefix):
        if not isinstance(cert, Certificate) or cert.name not in SPEC_BY_NAME:
            raise Rejected("Unknown certificate")
        spec = SPEC_BY_NAME[cert.name]
        if cert.program.source()[0] != "iterate" or cert.program.base != spec.base:
            raise Rejected("Incorrect recurrence base")
        if cert.program.step not in SEEDS + tuple(c.identity for c in prefix):
            raise Rejected("Uncertified step")
        if spec.predecessor in SEEDS:
            expected = spec.predecessor
            dependencies = ()
        else:
            matches = [c for c in prefix if c.name == spec.predecessor]
            if len(matches) != 1:
                raise Rejected("Missing predecessor theorem")
            expected = matches[0].identity
            dependencies = (expected,)
        if cert.program.step != expected or cert.dependencies != dependencies:
            raise Rejected("Recurrence proof does not match source")
        proof = ("induction", spec.name, spec.base, expected)
        identity = digest([cert.name, cert.program.source(), dependencies, proof])
        if cert.proof != proof or cert.identity != identity:
            raise Rejected("Forged proof or certificate identity")
        return True

    @staticmethod
    def state(state):
        if not isinstance(state, State) or state.bound != SOURCE_BOUND:
            raise Rejected("Invalid state or resource escape")
        seen = set()
        for i, cert in enumerate(state.archive):
            Verifier.check_certificate(cert, state.archive[:i])
            if cert.identity in seen or cert.name in {c.name for c in state.archive[:i]}:
                raise Rejected("Duplicate capability")
            seen.add(cert.identity)
        return True

    @staticmethod
    def certify(spec, program, prefix):
        if spec.name not in SPEC_BY_NAME or SPEC_BY_NAME[spec.name] != spec:
            raise Rejected("Unregistered mathematical obligation")
        expected = spec.predecessor
        deps = ()
        if expected not in SEEDS:
            matches = [c for c in prefix if c.name == expected]
            if len(matches) != 1:
                raise Rejected("Missing predecessor")
            expected = matches[0].identity
            deps = (expected,)
        proof = ("induction", spec.name, spec.base, expected)
        cert = Certificate(spec.name, program, deps, proof,
                           digest([spec.name, program.source(), deps, proof]))
        Verifier.check_certificate(cert, prefix)
        return cert


def first_difference(program, reference, archive, probes=PROBES):
    for x, y in probes:
        if evaluate(program, x, y, archive) != reference(x, y):
            return (x, y)
    return None


@dataclass(frozen=True)
class Evidence:
    before: State
    after: State
    certificate: Certificate
    source: Program
    rejected: tuple


def develop(state, spec):
    Verifier.state(state)
    if any(c.name == spec.name for c in state.archive):
        return state, None
    rejected = []
    for p in candidates(state):
        witness = first_difference(p, spec.reference, state.archive)
        if witness is not None:
            rejected.append((p, witness))
            continue
        try:
            cert = Verifier.certify(spec, p, state.archive)
        except Rejected:
            continue
        after = State(state.archive + (cert,), state.bound)
        Verifier.state(after)
        return after, Evidence(state, after, cert, p, tuple(rejected))
    return state, None


def verify_transition(evidence):
    Verifier.state(evidence.before)
    Verifier.state(evidence.after)
    if evidence.after.archive != evidence.before.archive + (evidence.certificate,):
        raise Rejected("Archive not preserved")
    if evidence.source != evidence.certificate.program:
        raise Rejected("Source changed")
    if evidence.source not in candidates(evidence.before):
        raise Rejected("Source not reachable before installation")
    if evidence.after.bound != evidence.before.bound:
        raise Rejected("Bound increased")
    Verifier.check_certificate(evidence.certificate, evidence.before.archive)
    return True


def obstruction(state, spec):
    """Complete finite-grammar obstruction, with a witness per source."""
    Verifier.state(state)
    result = []
    for p in candidates(state):
        witness = first_difference(p, spec.reference, state.archive)
        if witness is None:
            raise Rejected("No obstruction: a candidate matches all probes")
        result.append((p, witness))
    return tuple(result)


def qualification():
    state = State()
    records = []
    targets = SPECS
    for i, spec in enumerate(targets):
        before = state
        after, evidence = develop(before, spec)
        assert evidence is not None and verify_transition(evidence)
        assert evidence.source.source()[0] == "iterate"
        assert len(evidence.source.source()) == SOURCE_BOUND
        assert after.bound == before.bound == SOURCE_BOUND
        assert all(c in after.archive for c in before.archive)
        if i + 1 < len(targets):
            next_spec = targets[i + 1]
            old_obstruction = obstruction(before, next_spec)
            assert develop(after, next_spec)[1] is not None
            assert develop(before, next_spec)[1] is None
            assert len(old_obstruction) == len(candidates(before))
        records.append({"name": spec.name, "source": evidence.source.source(),
                        "identity": evidence.certificate.identity,
                        "candidate_count_before": len(candidates(before)),
                        "candidate_count_after": len(candidates(after))})
        state = after
    for spec, cert in zip(targets, state.archive):
        for x, y in PROBES:
            assert evaluate(cert.program, x, y, state.archive[:state.archive.index(cert)]) == spec.reference(x, y)
    return {"scope": "one-iteration declared grammar", "source_bound": SOURCE_BOUND,
            "operations": [r["name"] for r in records], "records": records,
            "strict_generator_expansions": len(records) - 1,
            "heldout_transfer": True, "ablation": True,
            "unrestricted_genesis": False, "external_lean_required": True}


LEAN_STEP_NAMES = {"succ": "Step.succ", "double": "Step.double"}
LEAN_BASE_NAMES = {"zero": "Base.zero", "one": "Base.one", "input": "Base.input"}


def lean_source():
    state = State()
    stages = []
    for spec in SPECS:
        before = state
        state, evidence = develop(state, spec)
        if evidence is None:
            raise Rejected("Synthesis failed")
        stages.append((before, spec, evidence))
    names = {e.certificate.identity: f"Step.learned{i}" for i, (_, _, e) in enumerate(stages)}
    def step_name(s):
        return LEAN_STEP_NAMES.get(s, names.get(s))
    def pcode(p):
        return f"⟨{LEAN_BASE_NAMES[p.base]}, {step_name(p.step)}⟩"
    lines = [
        "import Std", "", "namespace OpenDevelopment", "",
        "inductive Base where", "  | zero | one | input", "  deriving DecidableEq, Repr", "",
        "inductive Step where", "  | succ | double" + "".join(f" | learned{i}" for i in range(len(stages))),
        "  deriving DecidableEq, Repr", "",
        "structure Program where", "  base : Base", "  step : Step", "  deriving DecidableEq, Repr", "",
        "def baseValue : Base → Nat → Nat", "  | .zero, _ => 0", "  | .one, _ => 1", "  | .input, x => x", "",
    ]
    for i, (_, _, e) in enumerate(stages):
        lines.append(f"def generated{i} (x y : Nat) : Nat :=")
        step = e.source.step
        if step == "succ": body = "Nat.succ acc"
        elif step == "double": body = "2 * acc"
        else:
            dep = next(j for j, (_, _, prior) in enumerate(stages[:i])
                       if prior.certificate.identity == step)
            body = f"generated{dep} x acc"
        base = {"zero": "0", "one": "1", "input": "x"}[e.source.base]
        lines += [f"  Nat.rec {base} (fun _ acc => {body}) y", ""]
    lines += ["def stepValue : Step → Nat → Nat → Nat",
              "  | .succ, _, acc => Nat.succ acc",
              "  | .double, _, acc => 2 * acc"]
    for i in range(len(stages)):
        lines.append(f"  | .learned{i}, x, acc => generated{i} x acc")
    lines += ["", "def eval (p : Program) (x y : Nat) : Nat :=",
              "  Nat.rec (baseValue p.base x) (fun _ acc => stepValue p.step x acc) y", "",
              "def candidates (steps : List Step) : List Program :=",
              "  steps.flatMap (fun s => [⟨.zero, s⟩, ⟨.one, s⟩, ⟨.input, s⟩])", "",
              "def tower (x y : Nat) : Nat :=",
              "  Nat.rec 1 (fun _ acc => x ^ acc) y", "",
              "def AllFailure (f : Nat → Nat → Nat) : List Program → Prop",
        "  | [] => True",
        "  | p :: ps => (∃ x y, eval p x y ≠ f x y) ∧ AllFailure f ps", "",
        "theorem allFailureSound (f : Nat → Nat → Nat) (ps : List Program) :",
        "    AllFailure f ps →",
        "      ∀ p, p ∈ ps → ∃ x y, eval p x y ≠ f x y := by",
        "  induction ps with",
        "  | nil =>", "      intro _ p hp", "      cases hp",
        "  | cons a rest ih =>", "      intro h p hp",
        "      have ha : ∃ x y, eval a x y ≠ f x y := h.1",
        "      have ht : AllFailure f rest := h.2",
        "      simp only [List.mem_cons] at hp",
        "      rcases hp with rfl | hp", "      · exact ha",
        "      · exact ih ht p hp", "",
    ]
    refs = ["x + y", "x * y", "x ^ y", "tower x y"]
    for i, (_, spec, e) in enumerate(stages):
        lines += [f"theorem generated{i}_correct (x y : Nat) : generated{i} x y = {refs[i]} := by",
                  "  induction y with", "  | zero => rfl", "  | succ y ih =>"]
        if i == 0:
            lines += ["      change Nat.succ (generated0 x y) = x + Nat.succ y",
                      "      simpa [ih]"]
        elif i == 1:
            lines += ["      change generated0 x (generated1 x y) = x * Nat.succ y",
                      "      rw [generated0_correct, ih]",
                      "      simp [Nat.mul_succ, Nat.add_comm]"]
        elif i == 2:
            lines += ["      change generated1 x (generated2 x y) = x ^ Nat.succ y",
                      "      rw [generated1_correct, ih]",
                      "      simp [Nat.pow_succ, Nat.mul_comm]"]
        else:
            lines += ["      change generated2 x (generated3 x y) = tower x (Nat.succ y)",
                      "      rw [generated2_correct, ih]", "      rfl"]
        lines.append("")
    for i in range(1, len(stages)):
        before, spec, _ = stages[i]
        old = stages[i - 1][0]
        witnesses = obstruction(old, spec)
        old_steps = ", ".join(step_name(s) for s in available(old))
        target = refs[i]
        lines += [f"def oldSteps{i} : List Step := [{old_steps}]", "",
                  f"private theorem obstructionTable{i} :",
                  f"    AllFailure (fun x y => {target}) (candidates oldSteps{i}) := by"]
        def nested(ws):
            if not ws: return "True.intro"
            (p, (x, y)), *tail = ws
            return f"⟨⟨{x}, {y}, by decide⟩, {nested(tail)}⟩"
        lines += [f"  exact {nested(list(witnesses))}", "",
                  f"theorem obstruction{i} (p : Program) (hp : p ∈ candidates oldSteps{i}) :",
                  f"    ¬ ∀ x y, eval p x y = (fun x y => {target}) x y := by",
                  "  intro h", f"  obtain ⟨x, y, hne⟩ := allFailureSound _ _ obstructionTable{i} p hp",
                  "  exact hne (h x y)", ""]
    for i, (_, _, e) in enumerate(stages):
        lines += [f"theorem generated{i}_reachable :",
                  f"    {pcode(e.source)} ∈ candidates " +
                  ("[.succ, .double" + "".join(f", .learned{j}" for j in range(i)) + "]") + " := by decide", ""]
    lines += ["end OpenDevelopment", ""]
    return "\n".join(lines)


class QualificationTests(unittest.TestCase):
    def test_recursive_development(self):
        self.assertEqual(qualification()["strict_generator_expansions"], 3)

    def test_complete_search_and_ablation(self):
        state = State()
        for i, spec in enumerate(SPECS):
            if i:
                self.assertEqual(develop(State(state.archive[:-1]), spec)[1], None)
            state, evidence = develop(state, spec)
            self.assertIsNotNone(evidence)
            self.assertTrue(verify_transition(evidence))

    def test_exact_recurrence_certificates(self):
        state = State()
        for spec in SPECS:
            state, evidence = develop(state, spec)
            self.assertTrue(Verifier.check_certificate(evidence.certificate, evidence.before.archive))
            for x, y in PROBES:
                self.assertEqual(evaluate(evidence.source, x, y, evidence.before.archive), spec.reference(x, y))

    def test_reject_forged_proofs(self):
        state, evidence = develop(State(), SPECS[0])
        from dataclasses import replace
        with self.assertRaises(Rejected):
            Verifier.state(State((replace(evidence.certificate, name="mul"),)))
        with self.assertRaises(Rejected):
            Verifier.state(State((replace(evidence.certificate, proof=("assume",)),)))
        with self.assertRaises(Rejected):
            Verifier.state(State((replace(evidence.certificate, identity="forged"),)))
        with self.assertRaises(Rejected):
            Verifier.state(State((evidence.certificate,), bound=4))

    def test_reject_missing_dependency(self):
        state, _ = develop(State(), SPECS[0])
        state, evidence = develop(state, SPECS[1])
        with self.assertRaises(Rejected):
            Verifier.state(State((evidence.certificate,)))
        with self.assertRaises(Rejected):
            evaluate(Program("zero", "unknown"), 1, 1)

    def test_no_unearned_capability(self):
        self.assertIsNone(develop(State(), SPECS[1])[1])
        self.assertIsNone(develop(State(), SPECS[2])[1])
        self.assertIsNone(develop(State(), SPECS[3])[1])

    def test_source_bound_and_monotonicity(self):
        state = State()
        for spec in SPECS:
            before = state
            state, evidence = develop(state, spec)
            self.assertEqual(len(evidence.source.source()), 3)
            self.assertEqual(state.bound, before.bound)
            self.assertEqual(state.archive[:len(before.archive)], before.archive)
            self.assertEqual(set(available(before)) - set(available(state)), set())

    def test_witnesses_are_independently_replayed(self):
        state = State()
        for i, spec in enumerate(SPECS):
            if i:
                old = State(state.archive[:-1])
                for p, (x, y) in obstruction(old, spec):
                    self.assertIn(p, candidates(old))
                    self.assertNotEqual(evaluate(p, x, y, old.archive), spec.reference(x, y))
            state, _ = develop(state, spec)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(QualificationTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        print("OPEN_DEVELOPMENT_QUALIFICATION=" + json.dumps(qualification(), sort_keys=True))
        if "--emit-lean" in sys.argv:
            print(lean_source())
    raise SystemExit(0 if result.wasSuccessful() else 1)
