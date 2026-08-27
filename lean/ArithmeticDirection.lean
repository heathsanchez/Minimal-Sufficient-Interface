import Std

/-- Two decimal digits interpreted most-significant first. -/
def twoDigit (hi lo : Nat) : Nat := 10 * hi + lo

/-- The tens-position output digit of adding two two-digit numbers. -/
def tensOutput (ahi alo bhi blo : Nat) : Nat :=
  ((twoDigit ahi alo + twoDigit bhi blo) / 10) % 10

/-- With leading digit-pair `(0,0)` and zero suffix, the current output is `0`. -/
theorem tensOutput_zero_suffix : tensOutput 0 0 0 0 = 0 := by
  decide

/-- With the same leading digit-pair `(0,0)` but suffix `(9,1)`, a future carry changes the current output to `1`. -/
theorem tensOutput_carry_suffix : tensOutput 0 9 0 1 = 1 := by
  decide

/--
No most-significant-digit-first emitter whose current output depends only on the
already visible leading digit pair can be exact even for width two.

The two complete additions below present the same current input `(0,0)` but
require different current output digits. Hence the failure is structural: no
refinement of hidden state derived solely from the already processed prefix can
repair the missing information, because the deciding information lies in the
unseen suffix.
-/
theorem no_exact_msd_local_emitter
    (emit : Nat → Nat → Nat)
    (hZero : emit 0 0 = tensOutput 0 0 0 0)
    (hCarry : emit 0 0 = tensOutput 0 9 0 1) : False := by
  have hz : emit 0 0 = 0 := hZero.trans tensOutput_zero_suffix
  have hc : emit 0 0 = 1 := hCarry.trans tensOutput_carry_suffix
  have h01 : (0 : Nat) = 1 := hz.symm.trans hc
  exact (by decide : (0 : Nat) ≠ 1) h01
