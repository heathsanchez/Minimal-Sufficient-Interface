"""Blind recurrence selection with an external Lean proof gate.

The learner receives only target evaluations. Source constructors and search
bounds are frozen. No target-specific base or predecessor is supplied to the
candidate selector. Finite agreement is never called a mathematical proof.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product
import operator
import unittest

BASES = ("zero", "one", "input")
SEEDS = ("succ", "double")
PROBES = tuple(product(range(3), range(4)))
SOURCE_BOUND = 3

@dataclass(frozen=True)
class Program:
    base: str
    step: str

@dataclass(frozen=True)
class Definition:
    name: str
    program: Program

@dataclass(frozen=True)
class Target:
    name: str
    reference: object

@dataclass(frozen=True)
class Discovery:
    target: str
    selected: Program
    rejected: tuple

def base_value(base, x):
    if base == "zero": return 0
    if base == "one": return 1
    if base == "input": return x
    raise ValueError("Unknown base")

def evaluate(program, x, y, archive=()):
    if program.base not in BASES or type(x) is not int or type(y) is not int or x < 0 or y < 0:
        raise ValueError("Malformed program or input")
    value = base_value(program.base, x)
    for _ in range(y):
        if program.step == "succ":
            value += 1
        elif program.step == "double":
            value *= 2
        else:
            matches = [c for c in archive if c.name == program.step]
            if len(matches) != 1:
                raise ValueError("Unknown or forward dependency")
            cap = matches[0]
            value = evaluate(cap.program, x, value, archive[:archive.index(cap)])
    return value

def candidates(archive):
    return tuple(Program(b, s) for s in SEEDS + tuple(c.name for c in archive) for b in BASES)

def first_difference(program, reference, archive):
    for x, y in PROBES:
        if evaluate(program, x, y, archive) != reference(x, y):
            return (x, y)
    return None

def discover(archive, target):
    rejected, survivors = [], []
    for p in candidates(archive):
        witness = first_difference(p, target.reference, archive)
        if witness is None:
            survivors.append(p)
        else:
            rejected.append((p, witness))
    return tuple(survivors), tuple(rejected)

def unique_discovery(archive, target):
    survivors, rejected = discover(archive, target)
    if len(survivors) != 1:
        raise ValueError("No unique candidate; require more evidence or a new grammar")
    return Discovery(target.name, survivors[0], rejected)

# Addition is the already-verified baseline, not a new proof claim.
BASELINE = (Definition("add", Program("input", "succ")),)
MUL = Target("mul", operator.mul)
POW = Target("pow", pow)

def qualification():
    mul = unique_discovery(BASELINE, MUL)
    archive = BASELINE + (Definition("mul", mul.selected),)
    power = unique_discovery(archive, POW)
    return mul, power

def lean_definition(name, program):
    bases = {"zero": "0", "one": "1", "input": "x"}
    steps = {
        "succ": "Nat.succ acc",
        "double": "2 * acc",
        "add": "OpenDevelopment.generated0 x acc",
        "mul": "inferredMul x acc",
    }
    return (f"def {name} (x y : Nat) : Nat :=\n"
            f"  Nat.rec {bases[program.base]} (fun _ acc => {steps[program.step]}) y")

def lean_source():
    mul, power = qualification()
    return """import LemmaSynthesis.OpenDevelopment

namespace InferredRecurrence

/- Generic recurrence uniqueness. The selected source is not trusted merely
   because it agrees with finite probes. -/
theorem rec_unique (f : Nat → Nat) (b : Nat) (step : Nat → Nat)
    (h0 : f 0 = b)
    (hs : ∀ n, f (Nat.succ n) = step (f n)) :
    ∀ n, Nat.rec b (fun _ acc => step acc) n = f n := by
  intro n
  induction n with
  | zero =>
      exact h0.symm
  | succ n ih =>
      change step (Nat.rec b (fun _ acc => step acc) n) = f (Nat.succ n)
      rw [ih]
      exact (hs n).symm

""" + lean_definition("inferredMul", mul.selected) + """

theorem inferredMul_correct (x y : Nat) : inferredMul x y = x * y := by
  exact rec_unique (fun n => x * n) 0
    (fun a => OpenDevelopment.generated0 x a)
    (by simp)
    (by
      intro n
      simpa only [OpenDevelopment.generated0_correct, Nat.mul_succ]
        using (Nat.add_comm (x * n) x))
    y

""" + lean_definition("inferredPow", power.selected) + """

theorem inferredPow_correct (x y : Nat) : inferredPow x y = x ^ y := by
  exact rec_unique (fun n => x ^ n) 1
    (fun a => inferredMul x a)
    (by simp)
    (by
      intro n
      simpa only [inferredMul_correct, Nat.pow_succ]
        using (Nat.mul_comm (x ^ n) x))
    y

/- Reuse the pinned all-Nat obstructions; do not turn probe exhaustion
   into an unrestricted impossibility claim. -/
theorem oldMul_inexpressible (p : OpenDevelopment.Program)
    (hp : p ∈ OpenDevelopment.candidates [.succ, .double]) :
    ¬ ∀ x y, OpenDevelopment.eval p x y = x * y := by
  exact OpenDevelopment.obstruction1 p hp

theorem oldPow_inexpressible (p : OpenDevelopment.Program)
    (hp : p ∈ OpenDevelopment.candidates [.succ, .double, .learned0]) :
    ¬ ∀ x y, OpenDevelopment.eval p x y = x ^ y := by
  exact OpenDevelopment.obstruction2 p hp

end InferredRecurrence
"""

class InferredRecurrenceTests(unittest.TestCase):
    def test_no_supplied_recurrence(self):
        self.assertEqual(tuple(Target.__dataclass_fields__), ("name", "reference"))
        self.assertEqual(len(candidates(BASELINE)), 9)

    def test_missing_predecessor_is_inferred(self):
        mul, power = qualification()
        self.assertEqual(mul.selected, Program("zero", "add"))
        self.assertEqual(power.selected, Program("one", "mul"))
        self.assertEqual(len(mul.rejected), 8)
        self.assertEqual(len(power.rejected), 11)

    def test_replay_and_dependency_ablation(self):
        mul, power = qualification()
        archive = BASELINE + (Definition("mul", mul.selected),)
        for x, y in PROBES:
            self.assertEqual(evaluate(mul.selected, x, y, BASELINE), MUL.reference(x, y))
            self.assertEqual(evaluate(power.selected, x, y, archive), POW.reference(x, y))
        self.assertEqual(discover(BASELINE, POW)[0], ())
        with self.assertRaises(ValueError):
            evaluate(power.selected, 2, 3, BASELINE)

    def test_negative_and_ambiguous_tasks_are_not_promoted(self):
        archive = BASELINE + (Definition("mul", Program("zero", "add")),)
        outside = Target("outside", lambda x, y: x + y*y)
        self.assertEqual(discover(archive, outside)[0], ())
        with self.assertRaises(ValueError):
            unique_discovery(archive, outside)

    def test_witnesses_and_source_bound(self):
        mul, power = qualification()
        for discovery, archive, target in (
            (mul, BASELINE, MUL),
            (power, BASELINE + (Definition("mul", mul.selected),), POW),
        ):
            self.assertEqual(len(discovery.rejected) + 1, len(candidates(archive)))
            self.assertEqual(len({p for p, _ in discovery.rejected}), len(discovery.rejected))
            for p, (x, y) in discovery.rejected:
                self.assertNotEqual(evaluate(p, x, y, archive), target.reference(x, y))
            self.assertEqual(len(("iterate", ("step", discovery.selected.step),
                                  ("base", discovery.selected.base))), SOURCE_BOUND)

if __name__ == "__main__":
    unittest.main()
