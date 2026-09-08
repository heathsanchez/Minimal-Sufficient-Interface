import LemmaSynthesis.SearchPolicy

/-!
# Residual-structural derivation of the Target-4 search constraint

This experiment removes the hand-written `K_meta4 := ⟨2, 2⟩` step from the
Target-4/5 policy repair.  The search constraint is computed from the structure
of the generalized target term itself:

* required depth = constructor nesting depth;
* safe arity = largest operator arity actually required by that term.

The external Lean kernel then checks that this derived constraint is exactly the
previously calibrated constraint and that feeding it through the unchanged
`SelectPolicy` reproduces the verified policy repair.

This closes only the constraint-derivation seam.  It does not yet show that the
same object-level synthesis schema performs the meta-level policy update.
-/

namespace DerivedSearchConstraint

open SearchPolicyAsState

mutual
  def termDepth {S : Signature} {s : S.Srt} : Term S s → Nat
    | .var _ _ => 0
    | .op _ args => 1 + argsDepth args

  def argsDepth {S : Signature} {ss : List S.Srt} : Args S ss → Nat
    | .nil => 0
    | .cons t rest => max (termDepth t) (argsDepth rest)
end

mutual
  def maxUsedArity {S : Signature} {s : S.Srt} : Term S s → Nat
    | .var _ _ => 0
    | .op o args => max (S.arity o).length (argsMaxUsedArity args)

  def argsMaxUsedArity {S : Signature} {ss : List S.Srt} : Args S ss → Nat
    | .nil => 0
    | .cons t rest => max (maxUsedArity t) (argsMaxUsedArity rest)
end

def deriveConstraint {S : Signature} {s : S.Srt} (t : Term S s) : SearchConstraint :=
  ⟨termDepth t, maxUsedArity t⟩

/- No numeric policy constants are supplied here: both fields are computed from
   the residual/generalized term `add_mul_n_b_acc`. -/
def derivedKMeta4 : SearchConstraint := deriveConstraint add_mul_n_b_acc

def derivedPolicy : SearchPolicy := SelectPolicy derivedKMeta4

/- The structural compiler reproduces the old manually recorded constraint. -/
theorem derived_constraint_matches_calibration : derivedKMeta4 = K_meta4 := by
  native_decide

/- Consequently the existing frozen selector returns exactly the calibrated
   repaired policy, without hand-supplying depth=2 or arityCap=2. -/
theorem derived_policy_matches_selected : derivedPolicy = selectedPolicy := by
  native_decide

/- Re-run the causal before/after qualification through the derived constraint. -/
theorem baseline_still_fails :
    containsTerm
      (search baselineSearch SigMul mulOps (fun _ => [0, 1, 2]) MSort.Nat)
      add_mul_n_b_acc = false := by
  native_decide

theorem derived_policy_reaches_invariant :
    containsTerm
      (search derivedPolicy SigMul mulOps (fun _ => [0, 1, 2]) MSort.Nat)
      add_mul_n_b_acc = true := by
  native_decide

theorem derived_policy_is_a_real_change : derivedPolicy ≠ baselineSearch := by
  native_decide

end DerivedSearchConstraint
