import Std

set_option maxHeartbeats 0
set_option maxRecDepth 100000

def nand (a b : Bool) : Bool := !(a && b)

/- Stage 1: minimum NAND-formula representatives found by the executable
   residual-driven synthesis test. -/
def hs (a b : Bool) : Bool :=
  nand (nand a (nand a b)) (nand b (nand a a))

def hc (a b : Bool) : Bool :=
  nand (nand a b) (nand a b)

theorem halfAdder_exhaustive :
    (List.range 2).all (fun a => (List.range 2).all (fun b =>
      hs (a == 1) (b == 1) == ((a + b) % 2 == 1) &&
      hc (a == 1) (b == 1) == (a + b >= 2))) = true := by
  decide

/- Stage 2: minimum formula representatives after `hs` and `hc` are promoted
   as unit-cost constructors in the warm grammar. -/
def faSum (a b c : Bool) : Bool :=
  hs a (hs b c)

def faCarry (a b c : Bool) : Bool :=
  hs a (hc (hs a b) (hs a c))

theorem fullAdder_exhaustive :
    (List.range 2).all (fun a => (List.range 2).all (fun b =>
      (List.range 2).all (fun c =>
        faSum (a == 1) (b == 1) (c == 1) == ((a + b + c) % 2 == 1) &&
        faCarry (a == 1) (b == 1) (c == 1) == (a + b + c >= 2)))) = true := by
  decide

def bitsLE (n width : Nat) : List Bool :=
  (List.range width).map (fun i => n.testBit i)

def ripple : List Bool → List Bool → Bool → List Bool
  | a :: as, b :: bs, carry =>
      faSum a b carry :: ripple as bs (faCarry a b carry)
  | _, _, _ => []

def rippleCorrectAt (width a b : Nat) : Bool :=
  ripple (bitsLE a width) (bitsLE b width) false ==
    bitsLE ((a + b) % (2 ^ width)) width

theorem ripple4_exhaustive :
    (List.range 16).all (fun a =>
      (List.range 16).all (fun b => rippleCorrectAt 4 a b)) = true := by
  decide

theorem ripple6_exhaustive :
    (List.range 64).all (fun a =>
      (List.range 64).all (fun b => rippleCorrectAt 6 a b)) = true := by
  decide

