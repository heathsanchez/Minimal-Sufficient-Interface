import Std

namespace GrammarGenesis

structure Table where
  ff : Bool
  ft : Bool
  tf : Bool
  tt : Bool
  deriving DecidableEq, Repr

def zeroTable : Table := ⟨false, false, false, false⟩
def oneTable : Table := ⟨true, true, true, true⟩
def xTable : Table := ⟨false, false, true, true⟩
def yTable : Table := ⟨false, true, false, true⟩
def negTable (t : Table) : Table := ⟨!t.ff, !t.ft, !t.tf, !t.tt⟩

def tableAt (t : Table) (x y : Bool) : Bool :=
  match x, y with
  | false, false => t.ff
  | false, true => t.ft
  | true, false => t.tf
  | true, true => t.tt

def tableOf (f : Bool → Bool → Bool) : Table :=
  ⟨f false false, f false true, f true false, f true true⟩

theorem tableAt_of (f : Bool → Bool → Bool) (x y : Bool) :
    tableAt (tableOf f) x y = f x y := by
  cases x <;> cases y <;> rfl

theorem table_ext (a b : Table)
    (h : ∀ x y, tableAt a x y = tableAt b x y) : a = b := by
  cases a with
  | mk a0 a1 a2 a3 =>
    cases b with
    | mk b0 b1 b2 b3 =>
      have h0 := h false false
      have h1 := h false true
      have h2 := h true false
      have h3 := h true true
      simp only [tableAt] at h0 h1 h2 h3
      cases h0
      cases h1
      cases h2
      cases h3
      rfl

def binaryTable (op a b : Table) : Table :=
  tableOf (fun x y => tableAt op (tableAt a x y) (tableAt b x y))

def learnedTable : Table := ⟨true, true, true, false⟩
def acquisitionTable : Table := ⟨true, true, true, false⟩
def heldoutTable : Table := ⟨false, true, true, false⟩

inductive Op where
  | not
  | learned
  deriving DecidableEq, Repr

structure Gate where
  op : Op
  a : Nat
  b : Nat
  deriving DecidableEq, Repr

structure Program where
  gates : List Gate
  output : Nat
  deriving DecidableEq, Repr

def lookup : List Table → Nat → Table
  | [], _ => zeroTable
  | t :: _, 0 => t
  | _ :: ts, n + 1 => lookup ts n

def gateValue (w : List Table) (g : Gate) : Table :=
  match g.op with
  | .not => negTable (lookup w g.a)
  | .learned => binaryTable learnedTable (lookup w g.a) (lookup w g.b)

def run : List Table → List Gate → List Table
  | w, [] => w
  | w, g :: gs => run (w ++ [gateValue w g]) gs

def initial : List Table := [zeroTable, oneTable, xTable, yTable]
def programTable (p : Program) : Table :=
  lookup (run initial p.gates) p.output
def eval (p : Program) (x y : Bool) : Bool :=
  tableAt (programTable p) x y

def unaryTables : List Table :=
  [zeroTable, oneTable, xTable, yTable, negTable xTable, negTable yTable]

theorem initial_unary : ∀ t, t ∈ initial → t ∈ unaryTables := by
  intro t h
  simp only [initial, List.mem_cons, List.mem_nil_iff, or_false] at h
  rcases h with rfl | rfl | rfl | rfl <;> decide

theorem unary_closed (t : Table) (h : t ∈ unaryTables) :
    negTable t ∈ unaryTables := by
  simp only [unaryTables, List.mem_cons, List.mem_nil_iff, or_false] at h
  rcases h with rfl | rfl | rfl | rfl | rfl | rfl <;> decide

theorem lookup_unary (w : List Table) (i : Nat)
    (hw : ∀ t, t ∈ w → t ∈ unaryTables) :
    lookup w i ∈ unaryTables := by
  induction w generalizing i with
  | nil =>
      change zeroTable ∈ unaryTables
      decide
  | cons a as ih =>
      cases i with
      | zero =>
          change a ∈ unaryTables
          exact hw a (by simp)
      | succ i =>
          change lookup as i ∈ unaryTables
          apply ih i
          intro t ht
          exact hw t (by simp [ht])

theorem run_unary (gs : List Gate) (w : List Table)
    (h : ∀ g, g ∈ gs → g.op = .not)
    (hw : ∀ t, t ∈ w → t ∈ unaryTables) :
    ∀ t, t ∈ run w gs → t ∈ unaryTables := by
  induction gs generalizing w with
  | nil =>
      simpa [run] using hw
  | cons g gs ih =>
      have hg : g.op = .not := h g (by simp)
      have hr : ∀ g', g' ∈ gs → g'.op = .not := by
        intro g' hg'
        exact h g' (by simp [hg'])
      change ∀ t, t ∈ run (w ++ [gateValue w g]) gs → t ∈ unaryTables
      apply ih (w ++ [gateValue w g]) hr
      intro t ht
      rcases List.mem_append.mp ht with ha | hb
      · exact hw t ha
      · simp only [List.mem_singleton] at hb
        subst t
        simp only [gateValue, hg]
        exact unary_closed _ (lookup_unary w g.a hw)

def Old (p : Program) : Prop :=
  p.gates.length ≤ 4 ∧ ∀ g, g ∈ p.gates → g.op = .not

theorem old_table_unary (p : Program) (h : Old p) :
    programTable p ∈ unaryTables := by
  unfold programTable
  apply lookup_unary
  exact run_unary p.gates initial h.2 initial_unary

def acquired : Program := ⟨[⟨.learned, 2, 3⟩], 4⟩
def transferred : Program := ⟨[⟨.learned, 2, 3⟩, ⟨.learned, 2, 4⟩, ⟨.learned, 3, 4⟩, ⟨.learned, 5, 6⟩], 7⟩

theorem acquired_bound : acquired.gates.length ≤ 4 := by decide
theorem transferred_bound : transferred.gates.length ≤ 4 := by decide

theorem acquired_correct (x y : Bool) :
    eval acquired x y = tableAt acquisitionTable x y := by
  cases x <;> cases y <;> decide

theorem transferred_correct (x y : Bool) :
    eval transferred x y = tableAt heldoutTable x y := by
  cases x <;> cases y <;> decide

theorem acquisition_not_unary : acquisitionTable ∉ unaryTables := by decide
theorem heldout_not_unary : heldoutTable ∉ unaryTables := by decide

theorem old_obstruction (p : Program) (h : Old p)
    (target : Table) (hn : target ∉ unaryTables) :
    ¬ ∀ x y, eval p x y = tableAt target x y := by
  intro he
  have ht : programTable p = target := by
    apply table_ext
    intro x y
    exact he x y
  exact hn (ht ▸ old_table_unary p h)

theorem acquisition_obstruction (p : Program) (h : Old p) :
    ¬ ∀ x y, eval p x y = tableAt acquisitionTable x y :=
  old_obstruction p h acquisitionTable acquisition_not_unary

theorem heldout_ablation (p : Program) (h : Old p) :
    ¬ ∀ x y, eval p x y = tableAt heldoutTable x y :=
  old_obstruction p h heldoutTable heldout_not_unary

end GrammarGenesis
