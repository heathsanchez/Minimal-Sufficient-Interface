import CLC.Verdict

open CLC

#check Verdict.unknown
#check Verdict.eq
#check Verdict.dist
#check Decisive
#check unknown_le
#check decisive_eq_of_le

example : Verdict.unknown ≤ Verdict.eq := by decide
example : ¬ Verdict.eq ≤ Verdict.dist := by decide
example : Decisive Verdict.dist := by simp [Decisive]

#eval decide (Verdict.unknown ≤ Verdict.dist)
#eval decide (¬ Verdict.eq ≤ Verdict.dist)
