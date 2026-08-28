import Std
import Std.Tactic.NativeDecide

set_option maxHeartbeats 0
set_option maxRecDepth 100000

/- Independent semantic certificate for the exact anonymous interfaces and
   programs frozen by `test_blind_recursive_cross_grammar_genesis.py`.
   Names record truth-table masks, not human semantic labels. -/

def u06 (a b : Bool) : Bool := a != b
def u11 (a b : Bool) : Bool := a || !b
def u02 (a b : Bool) : Bool := a && !b
def u09 (a b : Bool) : Bool := a == b

def az0 (a b : Bool) : Bool := !(a && b)
def by1 (a b : Bool) : Bool := a && b
def cx1 (a b : Bool) : Bool := a || b

/- Exact minimum programs produced after each grammar independently retained
   its coordinate representative of the learned interface orbit. -/
def azSum (a b c : Bool) : Bool := u06 (u06 a b) c
def azCarry (a b c : Bool) : Bool := az0 (az0 (u06 a b) c) (az0 a b)

def bySum (a b c : Bool) : Bool := u06 (u06 a b) c
def byCarry (a b c : Bool) : Bool := u06 (by1 (u06 a b) (u06 a c)) a

def cxSum (a b c : Bool) : Bool := u09 (u09 a b) c
def cxCarry (a b c : Bool) : Bool := u09 (cx1 (u09 a b) (u09 a c)) a

def expectedSum (a b c : Bool) : Bool := a != b != c
def expectedCarry (a b c : Bool) : Bool :=
  (a && b) || (a && c) || (b && c)

theorem independentGrammarProgramsAgree :
    (List.range 2).all (fun a => (List.range 2).all (fun b =>
      (List.range 2).all (fun c =>
        let x := a == 1
        let y := b == 1
        let z := c == 1
        azSum x y z == expectedSum x y z &&
        bySum x y z == expectedSum x y z &&
        cxSum x y z == expectedSum x y z &&
        azCarry x y z == expectedCarry x y z &&
        byCarry x y z == expectedCarry x y z &&
        cxCarry x y z == expectedCarry x y z)))) = true := by
  decide

def bitsLE (n width : Nat) : List Bool :=
  (List.range width).map (fun i => n.testBit i)

def ripple : List Bool → List Bool → Bool → List Bool
  | a :: as, b :: bs, carry =>
      azSum a b carry :: ripple as bs (azCarry a b carry)
  | _, _, _ => []

def rippleCorrectAt (width a b carry : Nat) : Bool :=
  ripple (bitsLE a width) (bitsLE b width) (carry == 1) ==
    bitsLE ((a + b + carry) % (2 ^ width)) width

theorem threePromotionsEightBitExhaustive :
    (List.range 256).all (fun a =>
      (List.range 256).all (fun b =>
        (List.range 2).all (fun carry => rippleCorrectAt 8 a b carry))) = true := by
  native_decide

/- Structural intervention certificate: deleting the carry edge between the
   low and high two-bit blocks computes two independent protected additions. -/
def isolatedTwoBitHalves (a b carry : Nat) : Nat :=
  let low := ((a % 4) + (b % 4) + carry) % 4
  let high := (((a / 4) % 4) + ((b / 4) % 4)) % 4
  low + 4 * high

def cutCarryAtTwo (a b carry : Nat) : List Bool :=
  ripple (bitsLE (a % 4) 2) (bitsLE (b % 4) 2) (carry == 1) ++
  ripple (bitsLE ((a / 4) % 4) 2) (bitsLE ((b / 4) % 4) 2) false

theorem deletedCarryInterventionExhaustive :
    (List.range 16).all (fun a =>
      (List.range 16).all (fun b =>
        (List.range 2).all (fun carry =>
          cutCarryAtTwo a b carry == bitsLE (isolatedTwoBitHalves a b carry) 4))) = true := by
  decide
