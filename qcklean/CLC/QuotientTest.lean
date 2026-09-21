import CLC.Fixtures

open CLC
open CLC.Fixtures

#check fibreMin
#check projectRaw
#check ViewEq
#check SupportCompatible
#check AdmissibleQuotient
#check quotient_immediate_forward
#check quotient_path_lift
#check reachable_preserved
#check dependsOn_preserved
#check currentlyWarranted_preserved
#check hasAlternativeSupport_preserved
#check spuriousPath_not_admissible

example : Reachable spuriousProjected QuotLabel.a QuotLabel.c := by native_decide
example : ¬ Reachable spuriousRaw RawNode.a₁ RawNode.c := by native_decide
example : ¬ Reachable spuriousRaw RawNode.a₂ RawNode.c := by native_decide
example : ¬ LocalPathLifting spuriousRaw spuriousQ := spurious_lifting_fails

def reviewQ : RawNode → QuotLabel
  | .a₁ | .a₂ => .a
  | .b₁ | .b₂ | .c => .b

def reviewProjected := projectRaw reviewQ spuriousRaw

example : reviewProjected.outputNode SpuriousOut.toB =
    reviewProjected.outputNode SpuriousOut.toC := rfl

example (o : SpuriousOut) : reviewProjected.outOwner o = spuriousRaw.outOwner o := rfl
example (o : SpuriousOut) : reviewProjected.mask o = spuriousRaw.mask o := rfl
example : reviewProjected.mask SpuriousOut.toB ≠
    reviewProjected.mask SpuriousOut.toC := by native_decide

