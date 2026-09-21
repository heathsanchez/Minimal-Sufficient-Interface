import CLC.Grow
import CLC.Fixtures

open CLC
open CLC.Fixtures

#check SourceEvent
#check CheckedSourceEvent
#check ClosedSource
#check AllowedStep
#check AllowedTrace
#check mapEvent
#check rebaseChecked
#check applyRaw_congr
#check flashStep_congr
#check projectTrace
#check growSource
#check growProjected
#check grow_dissolve_preserves_protected_queries

example (Q : ProtectedQuery PositiveLabel) :
    evalQuery positiveQ
        (sourceClosedView (growSource positiveClosed positiveTraceNil)).raw
        (sourceClosedView (growSource positiveClosed positiveTraceNil)).closed Q =
      evalQuery id
        (growProjected positiveProjected positiveProjectedTraceNil).raw
        (growProjected positiveProjected positiveProjectedTraceNil).closed Q :=
  grow_dissolve_preserves_protected_queries positiveHQ positiveTraceNil Q

example :
    evalQuery positiveQ
        (sourceClosedView (growSource positiveClosed positiveTraceNil)).raw
        (sourceClosedView (growSource positiveClosed positiveTraceNil)).closed
        (.reachable .evidence .claim) =
      evalQuery id
        (growProjected positiveProjected positiveProjectedTraceNil).raw
        (growProjected positiveProjected positiveProjectedTraceNil).closed
        (.reachable .evidence .claim) :=
  grow_dissolve_preserves_protected_queries positiveHQ positiveTraceNil _

example :
    evalQuery positiveQ
        (sourceClosedView (growSource positiveClosed positiveTraceNil)).raw
        (sourceClosedView (growSource positiveClosed positiveTraceNil)).closed
        (.dependsOn .evidence .claim) =
      evalQuery id
        (growProjected positiveProjected positiveProjectedTraceNil).raw
        (growProjected positiveProjected positiveProjectedTraceNil).closed
        (.dependsOn .evidence .claim) :=
  grow_dissolve_preserves_protected_queries positiveHQ positiveTraceNil _

example :
    evalQuery positiveQ
        (sourceClosedView (growSource positiveClosed positiveTraceNil)).raw
        (sourceClosedView (growSource positiveClosed positiveTraceNil)).closed
        (.currentlyWarranted .claim) =
      evalQuery id
        (growProjected positiveProjected positiveProjectedTraceNil).raw
        (growProjected positiveProjected positiveProjectedTraceNil).closed
        (.currentlyWarranted .claim) :=
  grow_dissolve_preserves_protected_queries positiveHQ positiveTraceNil _

example :
    evalQuery positiveQ
        (sourceClosedView (growSource positiveClosed positiveTraceNil)).raw
        (sourceClosedView (growSource positiveClosed positiveTraceNil)).closed
        (.hasAlternativeSupport .claim) =
      evalQuery id
        (growProjected positiveProjected positiveProjectedTraceNil).raw
        (growProjected positiveProjected positiveProjectedTraceNil).closed
        (.hasAlternativeSupport .claim) :=
  grow_dissolve_preserves_protected_queries positiveHQ positiveTraceNil _

example : ∃ nodes edges rankDelta baseDelta,
    projectedFirstEvent.event =
      ViewEvent.absorbStructure nodes edges rankDelta baseDelta := by
  exact ⟨_, _, _, _, rfl⟩

example : dormantSupport ∈
    (growProjected positiveReplayProjected positiveProjectedTrace).closed
      PositiveLabel.claim := by
  native_decide
