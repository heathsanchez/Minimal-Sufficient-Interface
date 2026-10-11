import Std

/-! V4 frozen source-only branching-recursion tasks.
No candidate invariant, target proof, or critic code is present here. -/
namespace BundyCriticV4

inductive Tree (α : Type) where
  | leaf : α → Tree α
  | node : Tree α → Tree α → Tree α
deriving Repr

def leaves : Tree α → List α
  | .leaf x => [x]
  | .node l r => leaves l ++ leaves r

def mirror : Tree α → Tree α
  | .leaf x => .leaf x
  | .node l r => .node (mirror r) (mirror l)

def leafCount : Tree α → Nat
  | .leaf _ => 1
  | .node l r => leafCount l + leafCount r

def height : Tree α → Nat
  | .leaf _ => 1
  | .node l r => Nat.max (height l) (height r) + 1

-- Deliberately false control: branching recursion cannot preserve this.
def wrongCount : Tree α → Nat
  | .leaf _ => 1
  | .node l r => wrongCount l + wrongCount r + 1

end BundyCriticV4
