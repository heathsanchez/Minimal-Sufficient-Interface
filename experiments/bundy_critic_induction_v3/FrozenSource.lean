import Std
/-!
Pre-frozen external-inspired proof tasks. No expected invariant or proof scripts
appear here. Source inspiration: David Thrane Christiansen, *Functional
Programming in Lean*, leanprover/fp-lean at
0abeea545d560a324e2561f7210fbd6ed154fa02, tail recursion and proofs.
The functions here are self-contained adaptations, not byte-identical imports.
-/
namespace BundyInductionV3

-- Development calibration. Both independent recursive implementations compute
-- reverse, but their equality requires relating a free accumulator to a fold.
def revPlain : List Nat → List Nat
  | [] => []
  | x :: xs => revPlain xs ++ [x]

def revAccum (acc : List Nat) : List Nat → List Nat
  | [] => acc
  | x :: xs => revAccum (x :: acc) xs

-- Protected problems (different carriers and monoid-like operations).
def sumPlain : List Nat → Nat
  | [] => 0
  | x :: xs => sumPlain xs + x

def sumAccum (acc : Nat) : List Nat → Nat
  | [] => acc
  | x :: xs => sumAccum (x + acc) xs

def prodPlain : List Nat → Nat
  | [] => 1
  | x :: xs => prodPlain xs * x

def prodAccum (acc : Nat) : List Nat → Nat
  | [] => acc
  | x :: xs => prodAccum (x * acc) xs

def mapRevPlain (f : Nat → Nat) : List Nat → List Nat
  | [] => []
  | x :: xs => mapRevPlain f xs ++ [f x]

def mapRevAccum (f : Nat → Nat) (acc : List Nat) : List Nat → List Nat
  | [] => acc
  | x :: xs => mapRevAccum f (f x :: acc) xs

def wordsPlain : List (List Nat) → List Nat
  | [] => []
  | x :: xs => wordsPlain xs ++ x

def wordsAccum (acc : List Nat) : List (List Nat) → List Nat
  | [] => acc
  | x :: xs => wordsAccum (x ++ acc) xs

-- Protected false-invariant countercontrol: same reference output but a helper
-- that appends to the accumulator on the wrong side in a noncommutative monoid.
def badPlain : List Nat → List Nat := revPlain

def badAccum (acc : List Nat) : List Nat → List Nat
  | [] => acc
  | x :: xs => badAccum (acc ++ [x]) xs

end BundyInductionV3
