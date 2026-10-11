import Std
import FrozenSource
namespace BundyCriticV4

theorem mirror_count (t : Tree Nat) : leafCount (mirror t) = leafCount t := by
  induction t with
  | leaf x => rfl
  | node l r ihl ihr =>
    simp only [mirror, leafCount]
    omega

theorem mirror_involution (t : Tree Nat) : mirror (mirror t) = t := by
  induction t with
  | leaf x => rfl
  | node l r ihl ihr =>
    simp [mirror, ihl, ihr]

theorem mirror_leaves (t : Tree Nat) :
    leaves (mirror t) = (leaves t).reverse := by
  induction t with
  | leaf x => rfl
  | node l r ihl ihr =>
    simp [mirror, leaves, ihl, ihr, List.reverse_append]

theorem mirror_height (t : Tree Nat) : height (mirror t) = height t := by
  induction t with
  | leaf x => rfl
  | node l r ihl ihr =>
    simp [mirror, height, ihl, ihr, Nat.max_comm]

theorem wrong_count_is_not_leaf_count :
    ¬ (∀ t : Tree Nat, wrongCount t = leafCount t) := by
  intro h
  have bad := h (Tree.node (Tree.leaf 1) (Tree.leaf 2))
  have hne : wrongCount (Tree.node (Tree.leaf 1) (Tree.leaf 2)) ≠
      leafCount (Tree.node (Tree.leaf 1) (Tree.leaf 2)) := by decide
  exact hne bad

end BundyCriticV4
