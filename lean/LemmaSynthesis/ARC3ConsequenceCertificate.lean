import LemmaSynthesis.AdequacyTester
namespace FiniteConsequenceCertificate
private def old : List Nat := [0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 1, 2, 0, 1, 2, 0, 1, 1, 1, 2, 0, 0, 0, 2, 0, 1, 1, 1, 2, 3, 1, 1, 1, 2, 3, 0, 1, 3, 0, 1, 3, 1, 3, 0, 0, 0, 0, 2, 3, 0, 0, 0, 3, 0, 1, 1, 1, 1, 1, 3, 0, 0, 0, 0, 0, 3, 1, 3, 1, 3, 1, 3, 1, 1, 3, 2, 2, 1, 0, 2, 2, 0, 0, 2, 0, 0, 0, 2, 2, 2, 2, 0, 2, 3, 0, 3, 3, 0, 3, 2, 2, 2, 0, 2, 3, 3, 3, 3, 0, 0, 2, 3, 0]
private def outcome : List Nat := [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
private def repaired : List Nat := [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 1, 45, 46, 4, 5, 6, 47, 48, 10, 49, 50, 13, 51, 52, 53, 54, 55, 56, 20, 57, 58, 59, 24, 60, 26, 61, 62, 29, 63, 64, 32, 65, 34, 66, 67, 37, 68, 69, 70, 71, 42, 72, 73, 74, 45, 3, 75, 76, 6, 47, 9, 77, 78, 79, 79, 80, 81, 82, 83, 84, 85, 86, 20, 21, 22, 59, 87]
private def universe : List Nat := List.range 113
private def at (xs : List Nat) (i : Nat) : Nat := xs[i]!
private theorem finite_replay :
    AdequacyTester.adequacyWitnesses universe (at repaired) (at outcome) = [] := by
  decide
private theorem old_residual :
    AdequacyTester.adequacyWitnesses universe (at old) (at outcome) ≠ [] := by
  decide
end FiniteConsequenceCertificate
