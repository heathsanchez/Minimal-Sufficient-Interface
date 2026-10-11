import Std
/-! Frozen V5 indexed dependent source. No proof solutions are included. -/
namespace BundyCriticV5

inductive Vec (α : Type) : Nat → Type where
  | nil : Vec α 0
  | cons : α → Vec α n → Vec α (n+1)

def append : Vec α n → Vec α m → Vec α (n+m)
  | .nil, ys => ys
  | .cons x xs, ys => .cons x (append xs ys)

def length : Vec α n → Nat
  | .nil => 0
  | .cons _ xs => length xs + 1

def map (f : α → β) : Vec α n → Vec β n
  | .nil => .nil
  | .cons x xs => .cons (f x) (map f xs)

end BundyCriticV5
