import CLC.Support

open CLC

inductive Tok | a | b | c deriving DecidableEq, Repr

instance : Fintype Tok where
  elems := {.a, .b, .c}
  complete := by intro t; cases t <;> simp

def fam : SupportFamily Tok :=
  {{Tok.a}, {Tok.a, Tok.b}, {Tok.b, Tok.c}}

example : normalize fam = {{Tok.a}, {Tok.b, Tok.c}} := by native_decide

def σ0 : TokenSnapshot Tok where
  live := {Tok.a, Tok.b, Tok.c}
  revoked := ∅
  disjoint := by decide

example : supportLive σ0 {Tok.b, Tok.c} := by decide
example : (revoke σ0 Tok.a (by decide)).live = {Tok.b, Tok.c} := by native_decide
example : supportLive (revoke σ0 Tok.a (by decide)) {Tok.b, Tok.c} := by decide
example : ¬ CanEnable (revoke σ0 Tok.a (by decide)) Tok.a := by decide

def dormantFamily : SupportFamily Tok := {{Tok.c}}

def dormantSnapshot : TokenSnapshot Tok where
  live := {Tok.a}
  revoked := ∅
  disjoint := by decide

example : liveView dormantSnapshot dormantFamily = ∅ := by native_decide

example : (liveView
    (enable dormantSnapshot Tok.c (by decide)) dormantFamily).Nonempty := by
  native_decide

example : dormantFamily = dormantFamily := rfl

#check normalize_idempotent
#check normalize_antichain
#check normalize_live_nonempty_iff
#check revocation_fallback
#check revoked_not_reenableable
