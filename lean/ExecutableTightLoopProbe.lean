import Std
import GenuinePolicyReflexivity

/-! # Executable tight-loop probe

Small executable probe for the ACT → VERIFY → CHANGE ONLY WHAT CONSEQUENCE FORCES loop.
Question: do P0 and P1 differ exactly at the inexpressibility boundary on concrete residuals?
No theorem is asserted here; this file is evidence-generation only.
-/

namespace ExecutableTightLoopProbe

open GenuinePolicyReflexivity

private def rExpressible : Residual Car := ⟨(false, false), (true, false)⟩
private def rInexpressible : Residual Car := ρ

private def isExpressible (r : Residual Car) : Bool := decide (Expressible I r)
private def policiesDiffer (r : Residual Car) : Bool := decide (P0 r ≠ P1 I r)

#eval (isExpressible rExpressible, policiesDiffer rExpressible, P0 rExpressible, P1 I rExpressible)
#eval (isExpressible rInexpressible, policiesDiffer rInexpressible, P0 rInexpressible, P1 I rInexpressible)

end ExecutableTightLoopProbe
