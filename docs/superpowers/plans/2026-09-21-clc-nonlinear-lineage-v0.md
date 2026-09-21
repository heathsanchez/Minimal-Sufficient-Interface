# CLC Nonlinear Lineage V0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and qualify a finite Lean 4 development proving that certified structural projection preserves the four declared protected queries along every finite source-certified, quotient-compatible trace.

**Architecture:** Keep semantic certification in `CertifiedSource` and perform closure/query execution over a smaller `RawView`/`ClosedView`; quotienting produces a certified structural projection and never invents a transport over a collapsed boundary. Stable input/output ports preserve nonlinear masks, `SupportCompatible` supplies the local algebra needed for closure commutation, and dependent checked traces carry the simulation witness needed to rebase projected events after each step.

**Tech Stack:** Lean `v4.35.0-rc2`; Mathlib commit `44ba35c6daa9d69aff8fed9fff9bbde17ded774d`; Lake; GitHub Actions on `ubuntu-24.04`.

**Spec:** `docs/superpowers/specs/2026-09-20-clc-nonlinear-lineage-v0-design.md`

## Global Constraints

- Work only on branch `clc-nonlinear-lineage-v0`, based on `qck-v1-documentation` commit `baef39cd7b32c860e2d7aa80a95f3826b8a52738`.
- Do not modify existing `qcklean/QCK*.lean` theorem or test files; only add `qcklean/CLC/**`, extend `qcklean/lakefile.lean`, and add the CLC workflow.
- Preserve Lean `v4.35.0-rc2` and Mathlib `44ba35c6daa9d69aff8fed9fff9bbde17ded774d` exactly.
- Every executable identifier universe is finite and has `Fintype` and `DecidableEq`; events never enlarge the universe types.
- `Ωauth` is fixed during a trace; only support `Token` liveness changes. `CertId` revocation is outside V0.
- The occurrence relation is rank-increasing and acyclic; cyclic derivation is outside V0.
- The protected query grammar is exactly `reachable`, `dependsOn`, `currentlyWarranted`, and `hasAlternativeSupport`.
- Projection preserves stable edge/input-port/output-port identities; it never coalesces port masks.
- `ComponentwiseBoundaryModel` is an explicit restricted V0 instance, not a theorem that arbitrary CLC boundary tests factor componentwise.
- Transport category laws use pointwise/extensional `TransportEq` and semantic `CertEq`; never require literal equality of proof- and certificate-bearing structures.
- `ContinuationSafe` is proof-carrying and need not be decidable; no algorithm for discovering merge proofs is claimed.
- No `sorry`, `admit`, project-local `axiom`/`constant`, or `unsafe` declaration may occur under `qcklean/CLC/`.
- Every task follows red/green TDD and ends with a focused commit. Do not batch unrelated tasks.

## File Map

| Path | Responsibility |
|---|---|
| `qcklean/CLC/Verdict.lean` | Trivalent information order and decisive refinement |
| `qcklean/CLC/Transport.lean` | Finite forms, authority snapshot, verified transport category |
| `qcklean/CLC/Continuation.lean` | Continuation-safe setoid, protected observation quotient, naturality |
| `qcklean/CLC/Support.lean` | Normalized support antichains and token liveness/revocation |
| `qcklean/CLC/Hypergraph.lean` | Finite universe, stable port graph, certified source, raw/closed views |
| `qcklean/CLC/Query.lean` | Immediate dependency, reachability, protected query evaluation |
| `qcklean/CLC/Quotient.lean` | Structural projection, view equivalence, admissibility, path lifting |
| `qcklean/CLC/Flash.lean` | Rank closure, `SupportCompatible`, batch/Flash exactness |
| `qcklean/CLC/Grow.lean` | Checked atomic events, state-dependent projection, allowed traces, capstone |
| `qcklean/CLC/Fixtures.lean` | Positive finite model and mandatory spurious-path negative model |
| `qcklean/CLC/Audit.lean` | `#print axioms` for the public theorem surface |
| `qcklean/CLC/*Test.lean` | Compile-time interface and executable fixture tests per module |
| `qcklean/lakefile.lean` | Register every CLC module/test/audit as a `QCK` library root |
| `.github/workflows/clc-nonlinear-lineage-v0.yml` | Frozen-QCK guard, build, fixture, source, and axiom qualification |

## Review Focus

1. Two output ports targeting one quotient node must remain two rules with two masks; `HypergraphTest` and `QuotientTest` pin this.
2. Activating a node inside an already-active fibre must emit an `absorbNode` delta and add its base support; `GrowTest` pins this.
3. A quotient that permits cross-fibre conjunctive support mixing must fail `SupportCompatible`; `FlashTest` pins this.
4. Revocation must retain archived alternatives, preserve a live fallback, and forbid resurrection of the same token; `SupportTest` pins this.
5. A projected checked event must be safely rebased across `ViewEq` before the next dependent step; `GrowTest` pins this with a two-event trace whose intermediate states are only extensionally equal.

---

### Task 1: Trivalent verdict order

**Files:**
- Create: `qcklean/CLC/VerdictTest.lean`
- Create: `qcklean/CLC/Verdict.lean`

**Interfaces:**
- Consumes: only Mathlib finite-data basics.
- Produces: `CLC.Verdict`, `Verdict.le`, `Decisive`, `unknown_le`, and `decisive_eq_of_le`.

- [ ] **Step 1: Write the failing interface and executable tests**

```lean
-- qcklean/CLC/VerdictTest.lean
import CLC.Verdict

open CLC

#check Verdict.unknown
#check Verdict.eq
#check Verdict.dist
#check Decisive
#check unknown_le
#check decisive_eq_of_le

example : Verdict.unknown ≤ Verdict.eq := by decide
example : ¬ Verdict.eq ≤ Verdict.dist := by decide
example : Decisive Verdict.dist := by simp [Decisive]

#eval decide (Verdict.unknown ≤ Verdict.dist)
#eval decide (¬ Verdict.eq ≤ Verdict.dist)
```

- [ ] **Step 2: Run the test and confirm the missing-module failure**

Run:

```bash
cd qcklean
lake env lean CLC/VerdictTest.lean
```

Expected: FAIL with `unknown module prefix 'CLC'` or missing `CLC.Verdict`.

- [ ] **Step 3: Implement the flat information order**

```lean
-- qcklean/CLC/Verdict.lean
import Mathlib.Data.Fintype.Basic

namespace CLC

inductive Verdict
  | unknown
  | eq
  | dist
  deriving DecidableEq, Fintype, Repr

def Verdict.le : Verdict → Verdict → Prop
  | .unknown, _ => True
  | .eq, .eq => True
  | .dist, .dist => True
  | _, _ => False

instance : LE Verdict := ⟨Verdict.le⟩
instance (a b : Verdict) : Decidable (a ≤ b) := inferInstanceAs (Decidable (Verdict.le a b))

instance : PartialOrder Verdict where
  le := Verdict.le
  le_refl := by intro a; cases a <;> trivial
  le_trans := by intro a b c hab hbc; cases a <;> cases b <;> cases c <;> simp_all [Verdict.le]
  le_antisymm := by intro a b hab hba; cases a <;> cases b <;> simp_all [Verdict.le]

def Decisive (v : Verdict) : Prop := v = .eq ∨ v = .dist

@[simp] theorem unknown_le (v : Verdict) : Verdict.unknown ≤ v := by
  cases v <;> trivial

theorem decisive_eq_of_le {v w : Verdict} (hv : Decisive v) (hvw : v ≤ w) : w = v := by
  rcases hv with rfl | rfl <;> cases w <;> simp_all [Verdict.le]

end CLC
```

- [ ] **Step 4: Run the focused test**

Run: `cd qcklean && lake env lean CLC/VerdictTest.lean`

Expected: PASS; both `#eval` lines print `true`.

- [ ] **Step 5: Commit the verdict layer**

```bash
git add qcklean/CLC/Verdict.lean qcklean/CLC/VerdictTest.lean
git commit -m "feat(clc): add trivalent verdict order"
```

### Task 2: Finite forms and verified transport calculus

**Files:**
- Create: `qcklean/CLC/TransportTest.lean`
- Create: `qcklean/CLC/Transport.lean`

**Interfaces:**
- Consumes: `CLC.Verdict`, especially `decisive_eq_of_le`.
- Produces: `Form`, `Protected`, `AuthoritySnapshot`, `TransportData`, `VerifiedTransport`, `VerifiedTransport.id`, `VerifiedTransport.comp`, `TransportEq`, identity/associativity theorems, `Strict`, and `decisive_preserved`.

- [ ] **Step 1: Write the failing transport interface test**

```lean
-- qcklean/CLC/TransportTest.lean
import CLC.Transport

open CLC

#check Form
#check Protected
#check AuthoritySnapshot
#check TransportData
#check VerifiedTransport
#check VerifiedTransport.id
#check VerifiedTransport.comp
#check TransportEq
#check transport_comp_assoc
#check transport_id_left
#check transport_id_right
#check decisive_preserved
#check Strict
#check Strict.toDevelopmental
```

Add a finite two-state fixture in the same file: source evaluation is always `unknown`; target evaluation refines one protected test to `eq`. Construct a developmental transport and prove with `example` that `decisive_preserved` applies only when the source verdict is decisive. Define the executable checker below and show a deliberately reversed test pullback fails it:

```lean
def finiteRefines (a : TransportData Cert sourceForm targetForm) : Bool :=
  Finset.univ.all fun x => Finset.univ.all fun d =>
    decide (sourceForm.eval x (a.pullTest d) ≤ targetForm.eval (a.mapState x) d)

example : finiteRefines wrongPullback = false := by native_decide
```

- [ ] **Step 2: Run the interface test and confirm failure**

Run: `cd qcklean && lake env lean CLC/TransportTest.lean`

Expected: FAIL because `CLC.Transport` does not exist.

- [ ] **Step 3: Implement the exact transport data boundary**

Use this public structure; keep proof fields in `Prop` and certificate data inspectable:

```lean
-- qcklean/CLC/Transport.lean
import CLC.Verdict
import Mathlib.Data.Fintype.Sigma

namespace CLC

universe u

structure Form where
  State : Type u
  Test : Type u
  stateFinite : Fintype State
  testFinite : Fintype Test
  decState : DecidableEq State
  decTest : DecidableEq Test
  protected : Test → Bool
  eval : State → Test → Verdict

attribute [instance] Form.stateFinite Form.testFinite Form.decState Form.decTest

def Protected (A : Form) := {d : A.Test // A.protected d = true}

structure AuthoritySnapshot (Cert : Type u) [DecidableEq Cert] where
  accepts : Cert → Bool
  live : Cert → Bool
  idCert : Cert
  compCert : Cert → Cert → Cert
  accepts_id : accepts idCert = true
  live_id : live idCert = true
  accepts_comp : ∀ {a b}, accepts a = true → accepts b = true → accepts (compCert a b) = true
  live_comp : ∀ {a b}, live a = true → live b = true → live (compCert a b) = true
  certEq : Cert → Cert → Prop
  certEq_refl : ∀ a, certEq a a
  certEq_symm : ∀ {a b}, certEq a b → certEq b a
  certEq_trans : ∀ {a b c}, certEq a b → certEq b c → certEq a c
  accepts_congr : ∀ {a b}, certEq a b → accepts a = accepts b
  live_congr : ∀ {a b}, certEq a b → live a = live b
  comp_congr : ∀ {a a' b b'}, certEq a a' → certEq b b' →
    certEq (compCert a b) (compCert a' b')
  comp_assoc : ∀ a b c,
    certEq (compCert (compCert a b) c) (compCert a (compCert b c))
  id_left : ∀ a, certEq (compCert idCert a) a
  id_right : ∀ a, certEq (compCert a idCert) a

structure TransportData (Cert : Type u) (A B : Form) where
  mapState : A.State → B.State
  pullTest : B.Test → A.Test
  pullProtected : ∀ d, B.protected d = true → A.protected (pullTest d) = true
  liftProtected : Protected A → Protected B
  refine : ∀ x d, A.eval x (pullTest d) ≤ B.eval (mapState x) d
  split : ∀ p, pullTest (liftProtected p).1 = p.1
  cert : Cert

structure VerifiedTransport {Cert : Type u} [DecidableEq Cert]
    (Ωauth : AuthoritySnapshot Cert) (A B : Form) extends TransportData Cert A B where
  checked : Ωauth.accepts cert = true
  liveAt : Ωauth.live cert = true
```

Implement identity and composition by composing `mapState`, reversing `pullTest`, composing `liftProtected`, and using `Ωauth.compCert a.cert b.cert`. Prove refinement with transitivity of `≤`; prove the split law by rewriting the two component split laws.

Define transport equality pointwise so dependent proof fields and certificate bytes never enter structure equality:

```lean
structure TransportEq
    (a b : VerifiedTransport Ωauth A B) : Prop where
  mapState_eq : ∀ x, a.mapState x = b.mapState x
  pullTest_eq : ∀ d, a.pullTest d = b.pullTest d
  liftProtected_eq : ∀ p, (a.liftProtected p).1 = (b.liftProtected p).1
  certificate_semantic_eq : Ωauth.certEq a.cert b.cert
```

Prove:

```lean
theorem transport_id_left (a : VerifiedTransport Ωauth A B) :
  TransportEq ((VerifiedTransport.id Ωauth B).comp a) a

theorem transport_id_right (a : VerifiedTransport Ωauth A B) :
  TransportEq (a.comp (VerifiedTransport.id Ωauth A)) a

theorem transport_comp_assoc
    (a : VerifiedTransport Ωauth A B)
    (b : VerifiedTransport Ωauth B C)
    (c : VerifiedTransport Ωauth C D) :
  TransportEq ((a.comp b).comp c) (a.comp (b.comp c))

def Strict (a : TransportData Cert A B) : Prop :=
  ∀ x d, A.eval x (a.pullTest d) = B.eval (a.mapState x) d

theorem Strict.toDevelopmental (h : Strict a) :
  ∀ x d, A.eval x (a.pullTest d) ≤ B.eval (a.mapState x) d

theorem decisive_preserved
    (a : VerifiedTransport Ωauth A B) (x : A.State) (p : Protected A)
    (h : Decisive (A.eval x p.1)) :
    B.eval (a.mapState x) (a.liftProtected p).1 = A.eval x p.1
```

For `decisive_preserved`, rewrite `a.split p` into `a.refine`, then apply `decisive_eq_of_le` and symmetry. Use pointwise `rfl` for state/test/lift components and `Ωauth.id_left`, `Ωauth.id_right`, and `Ωauth.comp_assoc` for semantic certificate equality. Do not prove equality of `VerifiedTransport` structures.

- [ ] **Step 4: Run transport tests**

Run: `cd qcklean && lake env lean CLC/TransportTest.lean`

Expected: PASS; the strict, developmental-refinement, composition, and rejected-pullback examples compile.

- [ ] **Step 5: Commit the transport calculus**

```bash
git add qcklean/CLC/Transport.lean qcklean/CLC/TransportTest.lean
git commit -m "feat(clc): prove verified transport calculus"
```

### Task 3: Continuation-safe equivalence and protected behavior

**Files:**
- Create: `qcklean/CLC/ContinuationTest.lean`
- Create: `qcklean/CLC/Continuation.lean`

**Interfaces:**
- Consumes: verified transport identity/composition.
- Produces: `ContinuationSafe`, `continuationSafeSetoid`, `continuationSafe_map`, `ProtectedBehavior`, `observeProtected`, `behaviorMap`, and `behaviorMap_naturality`.

- [ ] **Step 1: Write the failing continuation interface test**

```lean
-- qcklean/CLC/ContinuationTest.lean
import CLC.Continuation

open CLC

#check ContinuationSafe
#check continuationSafeSetoid
#check continuationSafe_refl
#check continuationSafe_symm
#check continuationSafe_trans
#check continuationSafe_map
#check ProtectedBehavior
#check observeProtected
#check behaviorMap
#check behaviorMap_naturality
#check ContinuationNeutral
#check BehavioralInverse
#check behaviorMap_neutral
#check behaviorMap_inverse_left
#check behaviorMap_inverse_right
```

Reuse the finite form/authority fixture from `TransportTest` by moving shared fixture definitions into a private namespace duplicated in this test, not into production code. Add examples that reflexivity, symmetry, transitivity, and one-step forward mapping compile.

- [ ] **Step 2: Run the test and confirm failure**

Run: `cd qcklean && lake env lean CLC/ContinuationTest.lean`

Expected: FAIL because `CLC.Continuation` is missing.

- [ ] **Step 3: Implement the continuation setoid and induced action**

```lean
-- qcklean/CLC/Continuation.lean
import CLC.Transport

namespace CLC

universe u

def ContinuationSafe {Cert : Type u} [DecidableEq Cert]
    (Ωauth : AuthoritySnapshot Cert) (A : Form) (x y : A.State) : Prop :=
  ∀ (B : Form) (a : VerifiedTransport Ωauth A B) (p : Protected B),
    B.eval (a.mapState x) p.1 = B.eval (a.mapState y) p.1

theorem continuationSafe_refl : ContinuationSafe Ωauth A x x := by
  intro B a p; rfl

theorem continuationSafe_symm (h : ContinuationSafe Ωauth A x y) :
    ContinuationSafe Ωauth A y x := by
  intro B a p; exact (h B a p).symm

theorem continuationSafe_trans
    (hxy : ContinuationSafe Ωauth A x y)
    (hyz : ContinuationSafe Ωauth A y z) :
    ContinuationSafe Ωauth A x z := by
  intro B a p; exact (hxy B a p).trans (hyz B a p)

def continuationSafeSetoid (Ωauth : AuthoritySnapshot Cert) (A : Form) : Setoid A.State :=
  ⟨ContinuationSafe Ωauth A, continuationSafe_refl, continuationSafe_symm, continuationSafe_trans⟩

theorem continuationSafe_map
    (a : VerifiedTransport Ωauth A B)
    (hxy : ContinuationSafe Ωauth A x y) :
    ContinuationSafe Ωauth B (a.mapState x) (a.mapState y) := by
  intro C b p
  exact hxy C (a.comp b) p

abbrev ProtectedBehavior (Ωauth : AuthoritySnapshot Cert) (A : Form) :=
  Quotient (continuationSafeSetoid Ωauth A)
```

Define `observeProtected Ωauth A p` with `Quotient.lift`; well-definedness follows by applying continuation safety to `VerifiedTransport.id Ωauth A`. Define `behaviorMap a` with `Quotient.map a.mapState` and `continuationSafe_map`. Prove naturality on representatives with `Quotient.inductionOn`; the result must state that mapping a representative and then quotienting equals quotienting and then applying `behaviorMap`.

Add the generic closed-loop obstruction layer without introducing any domain-specific semantics:

```lean
def ContinuationNeutral
    (loop : VerifiedTransport Ωauth A A) : Prop :=
  ∀ x : A.State, ContinuationSafe Ωauth A (loop.mapState x) x

structure BehavioralInverse
    (a : VerifiedTransport Ωauth A B)
    (r : VerifiedTransport Ωauth B A) : Prop where
  sourceLoop : ContinuationNeutral (a.comp r)
  targetLoop : ContinuationNeutral (r.comp a)
```

Prove:

```lean
theorem behaviorMap_neutral
    (loop : VerifiedTransport Ωauth A A)
    (h : ContinuationNeutral loop) :
    behaviorMap loop = id

theorem behaviorMap_inverse_left
    (a : VerifiedTransport Ωauth A B)
    (r : VerifiedTransport Ωauth B A)
    (h : BehavioralInverse a r) :
    Function.LeftInverse (behaviorMap r) (behaviorMap a)

theorem behaviorMap_inverse_right
    (a : VerifiedTransport Ωauth A B)
    (r : VerifiedTransport Ωauth B A)
    (h : BehavioralInverse a r) :
    Function.RightInverse (behaviorMap r) (behaviorMap a)
```

The proofs must live at the continuation-safe quotient level: a syntactic return to the same form is not enough. Add one positive strict re-encoding fixture whose forward/reverse composites are continuation-neutral, and one negative closed-loop fixture with an explicit future protected witness separating the looped state from the original state. The negative fixture must fail solely because the closed loop is behaviorally non-neutral; do not add any fixture-specific semantics.

- [ ] **Step 4: Run continuation tests**

Run: `cd qcklean && lake env lean CLC/ContinuationTest.lean`

Expected: PASS; no `Fintype` or `DecidableEq` instance is asserted for `ProtectedBehavior`; the neutral-loop quotient action is identity, the strict re-encoding pair is behaviorally invertible, and the non-neutral loop fixture is rejected.

- [ ] **Step 5: Commit continuation safety**

```bash
git add qcklean/CLC/Continuation.lean qcklean/CLC/ContinuationTest.lean
git commit -m "feat(clc): formalize continuation-safe behavior"
```

### Task 4: Support antichains and irreversible token state

**Files:**
- Create: `qcklean/CLC/SupportTest.lean`
- Create: `qcklean/CLC/Support.lean`

**Interfaces:**
- Consumes: finite `Finset` operations only.
- Produces: `Support`, `SupportFamily`, `normalize`, `Normalized`, `TokenSnapshot`, `supportLive`, `liveView`, checked enable/revoke operations, `normalize_live_nonempty_iff`, `revocation_fallback`, and `revoked_not_reenableable`.

- [ ] **Step 1: Write failing antichain/liveness tests**

```lean
-- qcklean/CLC/SupportTest.lean
import CLC.Support

open CLC

inductive Tok | a | b | c deriving DecidableEq, Fintype, Repr

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

#check normalize_idempotent
#check normalize_antichain
#check normalize_live_nonempty_iff
#check revocation_fallback
#check revoked_not_reenableable
```

Also add a dormant fixture with support `{c}` absent from `σ.live`; enable `c` and prove `liveView` becomes nonempty without changing the stored family.

- [ ] **Step 2: Run the support test and confirm failure**

Run: `cd qcklean && lake env lean CLC/SupportTest.lean`

Expected: FAIL because `CLC.Support` is missing.

- [ ] **Step 3: Implement normalization and token transitions**

```lean
-- qcklean/CLC/Support.lean
import Mathlib.Data.Finset.Powerset

namespace CLC

universe u

abbrev Support (Token : Type u) := Finset Token
abbrev SupportFamily (Token : Type u) := Finset (Support Token)

def normalize [DecidableEq Token] (F : SupportFamily Token) : SupportFamily Token :=
  F.filter fun s => ∀ t ∈ F, ¬ t ⊂ s

def Normalized [DecidableEq Token] (F : SupportFamily Token) : Prop :=
  normalize F = F

structure TokenSnapshot (Token : Type u) [DecidableEq Token] where
  live : Finset Token
  revoked : Finset Token
  disjoint : Disjoint live revoked

def supportLive [DecidableEq Token] (σ : TokenSnapshot Token) (s : Support Token) : Prop :=
  s ⊆ σ.live

instance [DecidableEq Token] (σ : TokenSnapshot Token) (s : Support Token) :
    Decidable (supportLive σ s) := inferInstance

def liveView [DecidableEq Token] (σ : TokenSnapshot Token) (F : SupportFamily Token) :
    SupportFamily Token :=
  (normalize F).filter (supportLive σ)

def CanEnable [DecidableEq Token] (σ : TokenSnapshot Token) (t : Token) : Prop :=
  t ∉ σ.live ∧ t ∉ σ.revoked

def CanRevoke [DecidableEq Token] (σ : TokenSnapshot Token) (t : Token) : Prop :=
  t ∈ σ.live
```

Define `enable σ t h` by inserting `t` into `live`; define `revoke σ t h` by erasing `t` from `live` and inserting it into `revoked`. Discharge disjointness with `Finset.disjoint_left`, `Finset.mem_insert`, and the hypotheses in `h`.

Prove the exact public laws:

```lean
theorem normalize_idempotent (F : SupportFamily Token) :
  normalize (normalize F) = normalize F

theorem normalize_antichain {s t}
    (hs : s ∈ normalize F) (ht : t ∈ normalize F) : ¬ s ⊂ t

theorem normalize_live_nonempty_iff :
  (liveView σ F).Nonempty ↔ ∃ s ∈ F, supportLive σ s

theorem revocation_fallback
    (hrev : CanRevoke σ t)
    (hs : s ∈ F) (hlive : supportLive σ s) (ht : t ∉ s) :
  supportLive (revoke σ t hrev) s

theorem revoked_not_reenableable (hrev : CanRevoke σ t) :
  ¬ CanEnable (revoke σ t hrev) t
```

For `normalize_live_nonempty_iff`, use finiteness to choose a subset-minimal live member of `F`; conversely, every normalized live member came from `F`. This is the lemma needed later to show that `Min⊆` preserves current warrant.

- [ ] **Step 4: Run support tests**

Run: `cd qcklean && lake env lean CLC/SupportTest.lean`

Expected: PASS; normalization, fallback, dormant activation, and forbidden resurrection all compile and evaluate as expected.

- [ ] **Step 5: Commit support semantics**

```bash
git add qcklean/CLC/Support.lean qcklean/CLC/SupportTest.lean
git commit -m "feat(clc): add alternative support and revocation semantics"
```

### Task 5: Stable-port certified hypergraph and restricted boundary model

**Files:**
- Create: `qcklean/CLC/HypergraphTest.lean`
- Create: `qcklean/CLC/Hypergraph.lean`

**Interfaces:**
- Consumes: `Form`, `VerifiedTransport`, `SupportFamily`, and `TokenSnapshot`.
- Produces: `FiniteUniverse`, `RawView`, `ValidRaw`, `ComponentwiseBoundaryModel.form`, `CertifiedSource`, active port predicates, the immediate dependency relation, and the rank-local support operators `ruleSupports`, `rankStep`, `prefixFamilies`, and `maxRank`.

- [ ] **Step 1: Write the failing port/boundary tests**

Create finite enums `Node = a₁ | a₂ | b`, `Edge = merge`, `InPort = left | right`, `OutPort = result`, `OutPort2 = first | second`, `Token`, `FormCode`, and `Cert`, all deriving `DecidableEq`, `Fintype`, and `Repr`.

```lean
-- qcklean/CLC/HypergraphTest.lean
import CLC.Hypergraph

open CLC

#check FiniteUniverse
#check RawView
#check ValidRaw
#check ComponentwiseBoundaryModel.form
#check CertifiedSource
#check Immediate

-- A two-component boundary test selects exactly one component.
example :
    (ComponentwiseBoundaryModel.form (fun _ : Fin 2 => boolForm)).eval
      (fun | 0 => false | 1 => true) ⟨1, Bool.true⟩ = Verdict.eq := by
  rfl

-- Both conjunctive input ports remain present even when a later label map
-- sends their incident nodes to the same label.
example : raw.mask OutPort.result = {InPort.left, InPort.right} := by native_decide
example : Immediate raw Node.a₁ Node.b := by decide
example : Immediate raw Node.a₂ Node.b := by decide
```

Add a second edge with two distinct output ports targeting the same node and different masks; assert both ports remain active and their masks are unequal.

- [ ] **Step 2: Run the hypergraph test and confirm failure**

Run: `cd qcklean && lake env lean CLC/HypergraphTest.lean`

Expected: FAIL because `CLC.Hypergraph` is missing.

- [ ] **Step 3: Implement finite universes and raw stable-port views**

```lean
-- qcklean/CLC/Hypergraph.lean
import CLC.Transport
import CLC.Support
import Mathlib.Data.Fintype.Sigma

namespace CLC

universe u

structure FiniteUniverse where
  NodeId : Type u
  EdgeId : Type u
  InPort : Type u
  OutPort : Type u
  Token : Type u
  FormCode : Type u
  CertId : Type u
  nodeFinite : Fintype NodeId
  edgeFinite : Fintype EdgeId
  inPortFinite : Fintype InPort
  outPortFinite : Fintype OutPort
  tokenFinite : Fintype Token
  formCodeFinite : Fintype FormCode
  certFinite : Fintype CertId
  nodeDecEq : DecidableEq NodeId
  edgeDecEq : DecidableEq EdgeId
  inPortDecEq : DecidableEq InPort
  outPortDecEq : DecidableEq OutPort
  tokenDecEq : DecidableEq Token
  formCodeDecEq : DecidableEq FormCode
  certDecEq : DecidableEq CertId

attribute [instance] FiniteUniverse.nodeFinite FiniteUniverse.edgeFinite
  FiniteUniverse.inPortFinite FiniteUniverse.outPortFinite
  FiniteUniverse.tokenFinite FiniteUniverse.formCodeFinite FiniteUniverse.certFinite
  FiniteUniverse.nodeDecEq FiniteUniverse.edgeDecEq FiniteUniverse.inPortDecEq
  FiniteUniverse.outPortDecEq FiniteUniverse.tokenDecEq
  FiniteUniverse.formCodeDecEq FiniteUniverse.certDecEq

structure RawView (U : FiniteUniverse) (Label : Type u)
    [Fintype Label] [DecidableEq Label] where
  activeNodes : Finset Label
  activeEdges : Finset U.EdgeId
  rank : Label → Nat
  inOwner : U.InPort → U.EdgeId
  outOwner : U.OutPort → U.EdgeId
  inputNode : U.InPort → Label
  outputNode : U.OutPort → Label
  mask : U.OutPort → Finset U.InPort
  edgeToken : U.EdgeId → U.Token
  base : Label → SupportFamily U.Token
  sigma : TokenSnapshot U.Token

def ActiveInPort (R : RawView U Label) (p : U.InPort) : Prop := R.inOwner p ∈ R.activeEdges
def ActiveOutPort (R : RawView U Label) (p : U.OutPort) : Prop := R.outOwner p ∈ R.activeEdges

def Immediate (R : RawView U Label) (x y : Label) : Prop :=
  ∃ o, ActiveOutPort R o ∧ R.outputNode o = y ∧
    ∃ p ∈ R.mask o, R.inputNode p = x
```

Define `ValidRaw R` with these exact fields: every active edge has at least one input and output port; each masked input port has the same owner as its output port; every incident node of an active port is active; every selected parent rank is strictly below its output rank; every base family is normalized; and `R.sigma.disjoint` is retained.

Define support propagation before quotienting so `SupportCompatible` can be stated without an import cycle. `ruleSupports R F o` enumerates every finite support `s` for which there is a function `choose : U.InPort → Support U.Token` selecting one member of `F (R.inputNode p)` for every `p ∈ R.mask o`, with `s` equal to the union of the chosen supports plus `R.edgeToken (R.outOwner o)`. Use `Finset.univ` over the finite type `Support U.Token`, then filter by this decidable predicate.

```lean
def rankStep (R : RawView U Label) (r : Nat)
    (F : Label → SupportFamily U.Token) : Label → SupportFamily U.Token :=
  fun z =>
    if z ∈ R.activeNodes ∧ R.rank z = r then
      normalize (F z ∪
        ((Finset.univ.filter fun o =>
          ActiveOutPort R o ∧ R.outputNode o = z).biUnion
            (ruleSupports R F)))
    else F z

def prefixFamilies (R : RawView U Label) : Nat → Label → SupportFamily U.Token
  | 0 => R.base
  | n + 1 => rankStep R n (prefixFamilies R n)

def maxRank (R : RawView U Label) : Nat := Finset.univ.sup R.rank
```

- [ ] **Step 4: Implement the explicit componentwise boundary instance and certified source**

The componentwise construction must be visibly named and documented as V0-only:

```lean
namespace ComponentwiseBoundaryModel

noncomputable def form {I : Type u} [Fintype I] [DecidableEq I]
    (A : I → Form) : Form where
  State := ∀ i, (A i).State
  Test := Σ i, (A i).Test
  stateFinite := inferInstance
  testFinite := inferInstance
  decState := Classical.decEq _
  decTest := Classical.decEq _
  protected := fun d => (A d.1).protected d.2
  eval := fun x d => (A d.1).eval (x d.1) d.2

end ComponentwiseBoundaryModel
```

For an edge `e`, define `InputBoundary R e := {p : U.InPort // R.inOwner p = e}` and the analogous `OutputBoundary`. Define their componentwise forms from `formAt (nodeCode (R.inputNode p))` and `formAt (nodeCode (R.outputNode p))`.

```lean
structure CertifiedSource (U : FiniteUniverse)
    (Ωauth : AuthoritySnapshot U.CertId) where
  raw : RawView U U.NodeId
  valid : ValidRaw raw
  formAt : U.FormCode → Form
  nodeCode : U.NodeId → U.FormCode
  nodeState : ∀ n, (formAt (nodeCode n)).State
  edgeTransport : ∀ e,
    VerifiedTransport Ωauth (inputBoundaryForm raw formAt nodeCode e)
      (outputBoundaryForm raw formAt nodeCode e)
  edgeSound : ∀ e,
    (edgeTransport e).mapState (inputBoundaryState raw nodeCode nodeState e) =
      outputBoundaryState raw nodeCode nodeState e
  activeOccurrenceLive : ∀ e ∈ raw.activeEdges, raw.edgeToken e ∈ raw.sigma.live
```

Do not add a generic factorization theorem. The only boundary implementation in V0 is `ComponentwiseBoundaryModel.form`, and `CertifiedSource.edgeTransport` explicitly refers to it.

- [ ] **Step 5: Run hypergraph tests**

Run: `cd qcklean && lake env lean CLC/HypergraphTest.lean`

Expected: PASS; the two component test, conjunctive two-port mask, and coalesced-output-port fixture all compile.

- [ ] **Step 6: Commit the nonlinear source model**

```bash
git add qcklean/CLC/Hypergraph.lean qcklean/CLC/HypergraphTest.lean
git commit -m "feat(clc): add stable-port certified hypergraphs"
```

### Task 6: Executable protected query language

**Files:**
- Create: `qcklean/CLC/QueryTest.lean`
- Create: `qcklean/CLC/Query.lean`

**Interfaces:**
- Consumes: `RawView`, `Immediate`, normalized support families, and token liveness.
- Produces: `PathN`, `Reachable`, `ProtectedQuery`, `labelFamily`, `evalQuery`, and Boolean/Prop correctness lemmas.

- [ ] **Step 1: Write failing query tests**

Build a three-node chain and a diamond using finite enums and raw views. Use explicit closed-family functions in the test; closure itself is not required yet.

```lean
-- qcklean/CLC/QueryTest.lean
import CLC.Query

open CLC

#check PathN
#check Reachable
#check ProtectedQuery
#check labelFamily
#check evalQuery
#check reachable_iff_eval_true

example : evalQuery id chainRaw chainFamilies
    (.reachable ChainNode.a ChainNode.c) = true := by native_decide

example : evalQuery id chainRaw chainFamilies
    (.dependsOn ChainNode.a ChainNode.c) = false := by native_decide

example : evalQuery id alternativeRaw alternativeFamilies
    (.hasAlternativeSupport AltNode.claim) = true := by native_decide
```

Add disconnected and empty-active-set cases. Add a label map that identifies two source nodes and prove `labelFamily` normalizes the union across both representatives rather than asking for two alternatives at one representative.

- [ ] **Step 2: Run the query test and confirm failure**

Run: `cd qcklean && lake env lean CLC/QueryTest.lean`

Expected: FAIL because `CLC.Query` is missing.

- [ ] **Step 3: Implement bounded positive reachability**

```lean
-- qcklean/CLC/Query.lean
import CLC.Hypergraph

namespace CLC

universe u

def PathN (R : RawView U Label) : Nat → Label → Label → Prop
  | 0, _, _ => False
  | n + 1, x, y => Immediate R x y ∨ ∃ z, Immediate R x z ∧ PathN R n z y

def Reachable (R : RawView U Label) (x y : Label) : Prop :=
  ∃ n < Fintype.card Label, PathN R (n + 1) x y

instance (R : RawView U Label) (x y : Label) : Decidable (Reachable R x y) :=
  inferInstance
```

Prove that `Reachable` is exactly the positive transitive closure of `Immediate` for `ValidRaw R`: forward induction converts `PathN`; backward induction uses strict rank growth to remove repeated nodes and bound path length by `Fintype.card Label`.

- [ ] **Step 4: Implement the four-constructor evaluator**

```lean
inductive ProtectedQuery (Label : Type u)
  | reachable (from to : Label)
  | dependsOn (parent child : Label)
  | currentlyWarranted (node : Label)
  | hasAlternativeSupport (node : Label)

def labelFamily (label : Node → Label) (R : RawView U Node)
    (closed : Node → SupportFamily U.Token) (a : Label) : SupportFamily U.Token :=
  normalize <| (Finset.univ.filter fun x =>
    x ∈ R.activeNodes ∧ label x = a).biUnion closed

def evalQuery (label : Node → Label) (R : RawView U Node)
    (closed : Node → SupportFamily U.Token) : ProtectedQuery Label → Bool
  | .reachable a b => decide (∃ x ∈ R.activeNodes, label x = a ∧
      ∃ y ∈ R.activeNodes, label y = b ∧ Reachable R x y)
  | .dependsOn a b => decide (∃ x ∈ R.activeNodes, label x = a ∧
      ∃ y ∈ R.activeNodes, label y = b ∧ Immediate R x y)
  | .currentlyWarranted a => decide (liveView R.sigma (labelFamily label R closed a)).Nonempty
  | .hasAlternativeSupport a => decide (2 ≤ (labelFamily label R closed a).card)
```

Prove one `_eq_true_iff` theorem per constructor. Do not add a catch-all semantic predicate.

- [ ] **Step 5: Run query tests**

Run: `cd qcklean && lake env lean CLC/QueryTest.lean`

Expected: PASS for chain, disconnected, diamond, immediate-vs-transitive, warrant, and label-level alternative cases.

- [ ] **Step 6: Commit the protected query grammar**

```bash
git add qcklean/CLC/Query.lean qcklean/CLC/QueryTest.lean
git commit -m "feat(clc): add executable protected queries"
```

### Task 7: Certified structural projection and spurious-path rejection

**Files:**
- Create: `qcklean/CLC/QuotientTest.lean`
- Create: `qcklean/CLC/Quotient.lean`
- Create: `qcklean/CLC/Fixtures.lean` with the negative fixture only; the positive fixture is extended in Task 11.

**Interfaces:**
- Consumes: `CertifiedSource`, continuation safety, rank-local support operators, and query evaluation.
- Produces: `fibreMin`, `projectRaw`, `ViewEq`, `SupportCompatible`, `AdmissibleQuotient`, forward incidence, path lifting, query-specific preservation lemmas, and `spuriousPath_not_admissible`.

- [ ] **Step 1: Write the failing projection and negative-fixture tests**

```lean
-- qcklean/CLC/QuotientTest.lean
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
```

Add the Review Focus fixture where two output ports have the same projected output node but unequal masks. Assert the projected `outOwner`, `mask`, and port identities equal the source values pointwise.

- [ ] **Step 2: Run the quotient test and confirm failure**

Run: `cd qcklean && lake env lean CLC/QuotientTest.lean`

Expected: FAIL because `CLC.Quotient`/`CLC.Fixtures` are missing.

- [ ] **Step 3: Implement canonical finite projection**

```lean
-- qcklean/CLC/Quotient.lean
import CLC.Continuation
import CLC.Query

namespace CLC

universe u

def fibreMin (q : Node → Label) (R : RawView U Node)
    (F : Node → SupportFamily U.Token) (z : Label) : SupportFamily U.Token :=
  normalize <| (Finset.univ.filter fun x =>
    x ∈ R.activeNodes ∧ q x = z).biUnion F

def fibreRank (q : Node → Label) (R : RawView U Node) (z : Label) : Nat :=
  (Finset.univ.filter fun x => x ∈ R.activeNodes ∧ q x = z).sup R.rank

def projectRaw (q : Node → Label) (R : RawView U Node) : RawView U Label where
  activeNodes := R.activeNodes.image q
  activeEdges := R.activeEdges
  rank := fibreRank q R
  inOwner := R.inOwner
  outOwner := R.outOwner
  inputNode := q ∘ R.inputNode
  outputNode := q ∘ R.outputNode
  mask := R.mask
  edgeToken := R.edgeToken
  base := fibreMin q R R.base
  sigma := R.sigma
```

Define `ViewEq R S` with equality of active node/edge sets and snapshots plus pointwise equality of ranks, port owners/incidence, masks, edge tokens, and base families. Prove `ViewEq.refl/symm/trans`, `RawView.ext`, and `ViewEq.toEq`; the latter is used for dependent rebasing later.

- [ ] **Step 4: Define local structural admissibility**

```lean
def LocalPathLifting (R : RawView U Node) (q : Node → Label) : Prop :=
  ∀ x, x ∈ R.activeNodes → ∀ z,
    Immediate (projectRaw q R) (q x) z →
      ∃ y, y ∈ R.activeNodes ∧ Immediate R x y ∧ q y = z

structure SupportCompatible (R : RawView U Node) (q : Node → Label) : Prop where
  base_commutes : ∀ z, (projectRaw q R).base z = fibreMin q R R.base z
  maxRank_commutes : maxRank (projectRaw q R) = maxRank R
  step_commutes : ∀ r, r < maxRank R + 1 → ∀ z,
    fibreMin q R (rankStep R r (prefixFamilies R r)) z =
      rankStep (projectRaw q R) r
        (fibreMin q R (prefixFamilies R r)) z
  same_snapshot : (projectRaw q R).sigma = R.sigma

structure AdmissibleQuotient
    (Ωauth : AuthoritySnapshot U.CertId)
    (S : CertifiedSource U Ωauth) (q : U.NodeId → Label) : Prop where
  typed : ∀ {x y}, x ∈ S.raw.activeNodes → y ∈ S.raw.activeNodes →
    q x = q y → S.nodeCode x = S.nodeCode y
  ranked : ∀ {x y}, x ∈ S.raw.activeNodes → y ∈ S.raw.activeNodes →
    q x = q y → S.raw.rank x = S.raw.rank y
  continuation : ∀ {x y} (hx : x ∈ S.raw.activeNodes) (hy : y ∈ S.raw.activeNodes),
    q x = q y →
      ContinuationSafe Ωauth (S.formAt (S.nodeCode x))
        (S.nodeState x)
        (cast
          (congrArg (fun code => (S.formAt code).State)
            (typed hx hy ‹q x = q y›).symm)
          (S.nodeState y))
  pathLift : LocalPathLifting S.raw q
  supportCompatible : SupportCompatible S.raw q
```

Prove `quotient_immediate_forward` directly from retained ports. Prove `quotient_path_lift` by induction on `PathN`, starting from an active representative supplied by membership in `activeNodes.image q`. Use these to prove `reachable_preserved` and `dependsOn_preserved` in both directions. Prove `projectedValid (hq : AdmissibleQuotient Ωauth S q) : ValidRaw (projectRaw q S.raw)` from `S.valid`, ranked-fibre coherence, retained ports/masks, and normalized `fibreMin`.

For support queries, prove that `labelFamily q R F z = labelFamily id (projectRaw q R) (fibreMin q R F) z`; then derive separate `currentlyWarranted_preserved` and `hasAlternativeSupport_preserved` theorems. These are generic family-projection theorems and do not assume closure commutation yet.

- [ ] **Step 5: Implement the mandatory spurious-path fixture**

```lean
-- relevant public names in qcklean/CLC/Fixtures.lean
namespace CLC.Fixtures

inductive RawNode | a₁ | a₂ | b₁ | b₂ | c deriving DecidableEq, Fintype, Repr
inductive QuotLabel | a | b | c deriving DecidableEq, Fintype, Repr
inductive SpuriousEdge | ab | bc deriving DecidableEq, Fintype, Repr
inductive SpuriousIn | fromA | fromB deriving DecidableEq, Fintype, Repr
inductive SpuriousOut | toB | toC deriving DecidableEq, Fintype, Repr
inductive SpuriousToken | ab | bc deriving DecidableEq, Fintype, Repr

def spuriousQ : RawNode → QuotLabel
  | .a₁ | .a₂ => .a
  | .b₁ | .b₂ => .b
  | .c => .c

def spuriousRank : RawNode → Nat
  | .a₁ | .a₂ => 0
  | .b₁ | .b₂ => 1
  | .c => 2

def spuriousRaw : RawView SpuriousUniverse RawNode where
  activeNodes := Finset.univ
  activeEdges := Finset.univ
  rank := spuriousRank
  inOwner := fun | .fromA => .ab | .fromB => .bc
  outOwner := fun | .toB => .ab | .toC => .bc
  inputNode := fun | .fromA => .a₁ | .fromB => .b₂
  outputNode := fun | .toB => .b₁ | .toC => .c
  mask := fun | .toB => {.fromA} | .toC => {.fromB}
  edgeToken := fun | .ab => .ab | .bc => .bc
  base := fun _ => ∅
  sigma :=
    { live := Finset.univ
      revoked := ∅
      disjoint := by simp }

def spuriousProjected := projectRaw spuriousQ spuriousRaw

theorem spurious_lifting_fails : ¬ LocalPathLifting spuriousRaw spuriousQ := by
  intro h
  obtain ⟨y, _, hstep, hqy⟩ := h RawNode.b₁ (by decide) QuotLabel.c (by native_decide)
  fin_cases y <;> simp_all [Immediate, spuriousRaw, spuriousQ]

theorem spuriousPath_not_admissible :
    ∀ (Ωauth : AuthoritySnapshot SpuriousUniverse.CertId)
      (S : CertifiedSource SpuriousUniverse Ωauth),
      S.raw = spuriousRaw → ¬ AdmissibleQuotient Ωauth S spuriousQ := by
  intro Ωauth S hraw h
  have hlift : LocalPathLifting spuriousRaw spuriousQ := by
    simpa [hraw] using h.pathLift
  exact spurious_lifting_fails hlift

end CLC.Fixtures
```

Define `SpuriousUniverse` immediately above this snippet by assigning its seven type fields to `RawNode`, `SpuriousEdge`, `SpuriousIn`, `SpuriousOut`, `SpuriousToken`, `Unit`, and `Unit`, with every finite/decidable field set to `inferInstance`. This contains exactly two active edges and the two displayed one-port masks; no additional dependency is permitted.

- [ ] **Step 6: Run the first conceptual checkpoint**

Run:

```bash
cd qcklean
lake env lean CLC/ContinuationTest.lean
lake env lean CLC/QuotientTest.lean
```

Expected: PASS, including both `continuationSafe_map` and `spuriousPath_not_admissible`.

- [ ] **Step 7: Commit certified projection and the negative control**

```bash
git add qcklean/CLC/Quotient.lean qcklean/CLC/QuotientTest.lean \
  qcklean/CLC/Fixtures.lean
git commit -m "feat(clc): reject spurious quotient paths"
```

### Task 8: Batch support closure and projection commutation

**Files:**
- Create: `qcklean/CLC/FlashTest.lean`
- Create: `qcklean/CLC/Flash.lean`
- Modify: `qcklean/CLC/Fixtures.lean` to add a positive support-compatible fixture.

**Interfaces:**
- Consumes: `maxRank`, `prefixFamilies`, `SupportCompatible`, `projectRaw`, `fibreMin`, and protected queries.
- Produces: `batchFamilies`, `ClosedView`, `ClosedViewEq`, `batchClose`, `aggregateClosedData`, `projectClosed`, `batch_projection_commutes`, `supportCompatibleB`, and closed-query preservation.

- [ ] **Step 1: Write failing batch/projection tests**

```lean
-- initial qcklean/CLC/FlashTest.lean
import CLC.Flash
import CLC.Fixtures

open CLC
open CLC.Fixtures

#check batchFamilies
#check ClosedView
#check batchClose
#check supportCompatibleB
#check supportCompatibleB_eq_true_iff
#check aggregateClosedData
#check projectClosed
#check batch_projection_commutes
#check closed_queries_preserved

example : (batchClose positiveRaw positiveValid).closed PositiveNode.claim =
    {{PositiveToken.left, PositiveToken.edge},
     {PositiveToken.right, PositiveToken.edge}} := by native_decide

example : supportCompatibleB positiveRaw positiveQ = true := by native_decide
example : supportCompatibleB crossMixingRaw crossMixingQ = false := by native_decide
```

The positive fixture must include two incomparable support routes to one claim. The cross-mixing fixture must have a quotient edge whose two input positions can draw supports from incompatible representatives; it must fail the rank-local equation even though its ordinary path relation can lift.

- [ ] **Step 2: Run the Flash test and confirm failure**

Run: `cd qcklean && lake env lean CLC/FlashTest.lean`

Expected: FAIL because `CLC.Flash` is missing.

- [ ] **Step 3: Implement finite rank closure and closed views**

```lean
-- qcklean/CLC/Flash.lean
import CLC.Quotient

namespace CLC

universe u

def batchFamilies (R : RawView U Label) : Label → SupportFamily U.Token :=
  prefixFamilies R (maxRank R + 1)

structure ClosedView (U : FiniteUniverse) (Label : Type u)
    [Fintype Label] [DecidableEq Label] where
  raw : RawView U Label
  valid : ValidRaw raw
  closed : Label → SupportFamily U.Token
  liveCache : Label → SupportFamily U.Token
  closed_correct : closed = batchFamilies raw
  live_correct : liveCache = fun z => liveView raw.sigma (closed z)

def batchClose (R : RawView U Label) (hR : ValidRaw R) : ClosedView U Label where
  raw := R
  valid := hR
  closed := batchFamilies R
  liveCache := fun z => liveView R.sigma (batchFamilies R z)
  closed_correct := rfl
  live_correct := rfl
```

Define `ClosedViewEq C D` as `ViewEq C.raw D.raw` plus pointwise equality of `closed` and `liveCache`. Prove equivalence, `rawEq`, and `closedViewEq_query` showing `evalQuery` is invariant under it.

- [ ] **Step 4: Prove support compatibility is executable**

```lean
def supportCompatibleB (R : RawView U Node) (q : Node → Label) : Bool :=
  decide (maxRank (projectRaw q R) = maxRank R) &&
    (Finset.range (maxRank R + 1)).all fun r =>
      Finset.univ.all fun z =>
        decide (
          fibreMin q R (rankStep R r (prefixFamilies R r)) z =
          rankStep (projectRaw q R) r
            (fibreMin q R (prefixFamilies R r)) z)

theorem supportCompatibleB_eq_true_iff :
  supportCompatibleB R q = true ↔ SupportCompatible R q
```

The reverse direction constructs `base_commutes` and `same_snapshot` by reflexivity, obtains `maxRank_commutes` from the leading decision, and obtains `step_commutes` from `Finset.all_eq_true`. The forward direction evaluates each certified rank/node equation. Add the cross-mixing false fixture before proceeding.

- [ ] **Step 5: Prove batch/projection commutation and construct projected closure**

First prove prefix commutation by induction:

```lean
theorem prefix_projection_commutes
    (h : SupportCompatible R q) (n : Nat) (hn : n ≤ maxRank R + 1)
    (z : Label) :
  fibreMin q R (prefixFamilies R n) z =
    prefixFamilies (projectRaw q R) n z
```

The zero case uses `h.base_commutes`; the successor case supplies `Nat.lt_of_succ_le hn` to `h.step_commutes` and rewrites with the induction hypothesis pointwise. Then prove:

```lean
theorem batch_projection_commutes
    (h : SupportCompatible R q) (z : Label) :
  fibreMin q R (batchFamilies R) z =
    batchFamilies (projectRaw q R) z
```

At the endpoint, rewrite the projected fold bound with `h.maxRank_commutes`.

Define:

```lean
structure ClosedData (U : FiniteUniverse) (Label : Type u)
    [Fintype Label] [DecidableEq Label] where
  raw : RawView U Label
  closed : Label → SupportFamily U.Token
  liveCache : Label → SupportFamily U.Token

def aggregateClosedData (q : Node → Label) (C : ClosedView U Node) : ClosedData U Label :=
  { raw := projectRaw q C.raw
    closed := fibreMin q C.raw C.closed
    liveCache := fun z => liveView C.raw.sigma (fibreMin q C.raw C.closed z) }

def projectClosed (q : Node → Label) (C : ClosedView U Node)
    (h : SupportCompatible C.raw q)
    (hvalid : ValidRaw (projectRaw q C.raw)) : ClosedView U Label :=
  { raw := projectRaw q C.raw
    valid := hvalid
    closed := fibreMin q C.raw C.closed
    liveCache := fun z => liveView C.raw.sigma (fibreMin q C.raw C.closed z)
    closed_correct := funext (batch_projection_commutes h)
    live_correct := rfl }
```

Prove `closed_queries_preserved hq C Q` by cases on `Q`, using Task 7 path/query lemmas and `batch_projection_commutes`. This is the second conceptual checkpoint: all four query constructors preserve answers at a closed state.

- [ ] **Step 6: Run batch/projection tests**

Run:

```bash
cd qcklean
lake env lean CLC/FlashTest.lean
lake env lean CLC/QuotientTest.lean
```

Expected: PASS; the positive fixture commutes and the cross-mixing fixture is rejected.

- [ ] **Step 7: Commit closure commutation**

```bash
git add qcklean/CLC/Flash.lean qcklean/CLC/FlashTest.lean \
  qcklean/CLC/Fixtures.lean
git commit -m "feat(clc): prove support closure commutes with projection"
```

### Task 9: Incremental Flash exactness

**Files:**
- Modify: `qcklean/CLC/Flash.lean`
- Modify: `qcklean/CLC/FlashTest.lean`
- Modify: `qcklean/CLC/Fixtures.lean`

**Interfaces:**
- Consumes: batch-closed views and rank-increasing reachability.
- Produces: `ViewEvent`, `EventValid`, `CheckedViewEvent`, `applyRaw`, `affected`, `flashFamilies`, `flashStep`, and `flashStep_exact`.

- [ ] **Step 1: Add failing insertion/revocation tests**

```lean
-- append to qcklean/CLC/FlashTest.lean
#check ViewEvent
#check EventValid
#check CheckedViewEvent
#check applyRaw
#check affected
#check flashStep
#check flashStep_exact

example :
    ClosedViewEq (flashStep closed0 addSupportChecked)
      (batchClose (applyRaw closed0.raw addSupportChecked)
        addSupportChecked.validAfter) :=
  flashStep_exact closed0 addSupportChecked

example :
    (flashStep closed0 revokeLeftChecked).closed = closed0.closed := by
  funext z
  exact provenance_unchanged_by_token_event closed0 revokeLeftChecked z

example :
    (flashStep closed0 revokeLeftChecked).liveCache PositiveNode.claim =
      {{PositiveToken.right, PositiveToken.edge}} := by native_decide
```

Repeat the exactness example for: structural bundle activation, base-support insertion, fresh-token enablement, and revocation. Include an unaffected disconnected node and assert its closed family is definitionally retained by `flashFamilies`.

- [ ] **Step 2: Run the focused test and confirm the new API is missing**

Run: `cd qcklean && lake env lean CLC/FlashTest.lean`

Expected: FAIL on missing `ViewEvent`/`flashStep` declarations.

- [ ] **Step 3: Implement atomic view events and checked application**

```lean
inductive ViewEvent (U : FiniteUniverse) (Label : Type u)
  | absorbStructure
      (nodes : Finset Label) (edges : Finset U.EdgeId)
      (rankDelta : Label → Nat)
      (baseDelta : Label → SupportFamily U.Token)
  | addBaseSupport (node : Label) (support : Support U.Token)
  | enableToken (token : U.Token)
  | revokeToken (token : U.Token)

def EventPrecondition (R : RawView U Label) : ViewEvent U Label → Prop
  | .absorbStructure nodes edges rankDelta _ =>
      Disjoint edges R.activeEdges ∧
      (∀ z ∈ nodes, z ∈ R.activeNodes → rankDelta z = R.rank z) ∧
      (∀ edge ∈ edges, R.edgeToken edge ∈ R.sigma.live)
  | .addBaseSupport node support =>
      node ∈ R.activeNodes ∧ support.Nonempty ∧
      ∀ t ∈ support, t ∉ R.sigma.revoked
  | .enableToken token => CanEnable R.sigma token
  | .revokeToken token => CanRevoke R.sigma token

def applyRawWith (R : RawView U Label) (e : ViewEvent U Label)
    (h : EventPrecondition R e) : RawView U Label :=
  match e with
  | .absorbStructure nodes edges rankDelta baseDelta =>
      { R with activeNodes := R.activeNodes ∪ nodes,
               activeEdges := R.activeEdges ∪ edges,
               rank := fun z => if z ∈ nodes then rankDelta z else R.rank z,
               base := fun z => if z ∈ nodes then
                 normalize (R.base z ∪ baseDelta z) else R.base z }
  | .addBaseSupport node support =>
      { R with base := fun z =>
          if z = node then normalize (R.base z ∪ {support}) else R.base z }
  | .enableToken token => { R with sigma := enable R.sigma token h }
  | .revokeToken token => { R with sigma := revoke R.sigma token h }

def EventValid (R : RawView U Label) (e : ViewEvent U Label) : Prop :=
  ∃ h : EventPrecondition R e, ValidRaw (applyRawWith R e h)

structure CheckedViewEvent (R : RawView U Label) where
  event : ViewEvent U Label
  precondition : EventPrecondition R event
  validAfter : ValidRaw (applyRawWith R event precondition)

def applyRaw (R : RawView U Label) (e : CheckedViewEvent R) : RawView U Label :=
  applyRawWith R e.event e.precondition
```

The dependent precondition is what supplies `enable`/`revoke` with its proof. Declare `applyRawWith` as `private`; expose only `CheckedViewEvent` and `applyRaw`.

- [ ] **Step 4: Implement affected-region recomputation**

`absorbStructure` is deliberately idempotent on node activation but not on data: an already-active label still absorbs `baseDelta`. This is the internal event used by the state-dependent source-to-projection map.

Define `changedRoots C e` as:

- absorbed nodes plus output nodes of activated edges for `absorbStructure`;
- the target node for `addBaseSupport`;
- every active node whose `C.closed` family contains the enabled/revoked token for token events.

Define `affected C e z` as membership in `changedRoots` or positive reachability from a root to `z` in the post-event raw view.

For structural/base insertions, define `flashFamilies` by a rank fold over the post-event view: unaffected nodes retain `C.closed z`; affected nodes reset to the post-event base and receive only rank-valid derived contributions. For token events, set `flashFamilies C e := C.closed` and recompute `liveCache` only for affected nodes, retaining the old cache elsewhere.

Prove the key induction:

```lean
theorem flashFamilies_eq_batch
    (C : ClosedView U Label) (e : CheckedViewEvent C.raw) :
  flashFamilies C e = batchFamilies (applyRaw C.raw e)
```

At an unaffected node, show no changed root reaches it, so neither its base nor any predecessor contribution changed. At an affected node, use the rank induction hypothesis for every masked parent. Token cases reduce using unchanged provenance.

- [ ] **Step 5: Construct `flashStep` and prove exactness**

```lean
def flashStep (C : ClosedView U Label)
    (e : CheckedViewEvent C.raw) : ClosedView U Label where
  raw := applyRaw C.raw e
  valid := e.validAfter
  closed := flashFamilies C e
  liveCache := flashLiveCache C e
  closed_correct := flashFamilies_eq_batch C e
  live_correct := flashLiveCache_correct C e

theorem flashStep_exact (C : ClosedView U Label)
    (e : CheckedViewEvent C.raw) :
  ClosedViewEq (flashStep C e)
    (batchClose (applyRaw C.raw e) e.validAfter)
```

- [ ] **Step 6: Run every Flash event test**

Run: `cd qcklean && lake env lean CLC/FlashTest.lean`

Expected: PASS for the four event classes, affected/unaffected nodes, dormant activation, fallback revocation, and exact equality with batch closure.

- [ ] **Step 7: Commit incremental Flash**

```bash
git add qcklean/CLC/Flash.lean qcklean/CLC/FlashTest.lean \
  qcklean/CLC/Fixtures.lean
git commit -m "feat(clc): prove incremental Flash exactness"
```

### Task 10: Certified growth, dependent projected traces, and capstone

**Files:**
- Create: `qcklean/CLC/GrowTest.lean`
- Create: `qcklean/CLC/Grow.lean`
- Modify: `qcklean/CLC/Fixtures.lean` to add the full positive multi-event trace.

**Interfaces:**
- Consumes: certified sources, admissible quotients, checked view events, Flash exactness, closure commutation, and all query-specific preservation lemmas.
- Produces: `SourceEvent`, `CheckedSourceEvent`, `applySource`, `ClosedSource`, `AllowedStep`, `AllowedTrace`, `mapEvent`, `rebaseChecked`, congruence lemmas, `projectTrace`, `growSource`, `growProjected`, and `grow_dissolve_preserves_protected_queries`.

- [ ] **Step 1: Write the failing growth/capstone tests**

```lean
-- qcklean/CLC/GrowTest.lean
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

-- Empty trace.
example (Q : ProtectedQuery PositiveLabel) :
    evalQuery positiveQ
        (sourceClosedView (growSource positiveClosed positiveTraceNil)).raw
        (sourceClosedView (growSource positiveClosed positiveTraceNil)).closed Q =
      evalQuery id
        (growProjected positiveProjected positiveProjectedTraceNil).raw
        (growProjected positiveProjected positiveProjectedTraceNil).closed Q :=
  grow_dissolve_preserves_protected_queries positiveHQ positiveTraceNil Q

-- The two-event trace first activates another representative in an already
-- active fibre, then enables its dormant support token.
example : ∃ nodes edges rankDelta baseDelta,
    projectedFirstEvent.event =
      ViewEvent.absorbStructure nodes edges rankDelta baseDelta := by
  exact ⟨_, _, _, _, rfl⟩

example : dormantSupport ∈
    (growProjected positiveProjected positiveProjectedTrace).closed PositiveLabel.claim := by
  native_decide
```

Add one theorem application for each protected query and one mixed structural-insertion/revocation trace. Ensure the second projected event is checked only after `rebaseChecked` transports it across the first step's `ClosedViewEq`.

- [ ] **Step 2: Run the growth test and confirm failure**

Run: `cd qcklean && lake env lean CLC/GrowTest.lean`

Expected: FAIL because `CLC.Grow` is missing.

- [ ] **Step 3: Implement source events and state-dependent deltas**

```lean
-- qcklean/CLC/Grow.lean
import CLC.Flash

namespace CLC

universe u

inductive SourceEvent (U : FiniteUniverse)
  | activateStructure (nodes : Finset U.NodeId) (edges : Finset U.EdgeId)
  | addBaseSupport (node : U.NodeId) (support : Support U.Token)
  | enableToken (token : U.Token)
  | revokeToken (token : U.Token)

structure CheckedSourceEvent
    (S : CertifiedSource U Ωauth) (e : SourceEvent U) where
  sourcePrecondition :
    match e with
    | .activateStructure nodes edges =>
        Disjoint nodes S.raw.activeNodes ∧ Disjoint edges S.raw.activeEdges
    | .addBaseSupport node support =>
        node ∈ S.raw.activeNodes ∧ support.Nonempty ∧
          ∀ t ∈ support, t ∉ S.raw.sigma.revoked
    | .enableToken token => CanEnable S.raw.sigma token
    | .revokeToken token => CanRevoke S.raw.sigma token
  sourceDelta : CheckedViewEvent S.raw
  sourceDelta_matches : sourceDelta.event = sourceViewEvent S e sourcePrecondition
```

`sourceViewEvent` converts source activation to `ViewEvent.absorbStructure nodes edges S.raw.rank`, with `baseDelta z = S.raw.base z` on newly activated nodes and empty elsewhere. Other constructors map directly.

Define `applySource S e` by replacing `S.raw` with `applyRaw S.raw e.sourceDelta`. Reuse all semantic tables and transports. Prove once that source events change only active sets, base families, and `σ`; rewrite boundary-form indices with this static-table equality when rebuilding `edgeTransport` and `edgeSound`.

Define `ClosedSource` with fields `source`, `closed`, and `raw_eq : closed.raw = source.raw`; `sourceClosedView` returns `closed`. Define `sourceStep` using `applySource` and `flashStep`, transporting the source/raw equality explicitly.

- [ ] **Step 4: Implement the state-dependent projected event and one-step simulation**

```lean
def mapEvent (C : ClosedSource U Ωauth) (q : U.NodeId → Label)
    (e : SourceEvent U) (checked : CheckedSourceEvent C.source e) :
    ViewEvent U Label :=
  match e with
  | .activateStructure nodes edges =>
      .absorbStructure
        (nodes.image q) edges
        (fun z => fibreRank q (applyRaw C.closed.raw
          checked.sourceDelta) z)
        (fun z => fibreMin q C.source.raw
          (fun x => if x ∈ nodes then C.source.raw.base x else ∅) z)
  | .addBaseSupport node support => .addBaseSupport (q node) support
  | .enableToken token => .enableToken token
  | .revokeToken token => .revokeToken token
```

The event data above must remain state-dependent. In particular, activation of `x₂` with `q x₁ = q x₂` still supplies `baseDelta (q x₂)` even though the projected label is already active.

```lean
structure AllowedStep
    (Ωauth : AuthoritySnapshot U.CertId)
    (q : U.NodeId → Label)
    (C : ClosedSource U Ωauth)
    (hq : AdmissibleQuotient Ωauth C.source q)
    (e : SourceEvent U) where
  checkedSource : CheckedSourceEvent C.source e
  projectedDelta : CheckedViewEvent (projectRaw q C.source.raw)
  projectedDelta_eq : projectedDelta.event = mapEvent C q e checkedSource
  rawCommutes :
    ViewEq
      (projectRaw q (applySource C.source checkedSource).raw)
      (applyRaw (projectRaw q C.source.raw) projectedDelta)
  nextAdmissible :
    AdmissibleQuotient Ωauth (applySource C.source checkedSource) q
```

Prove `rawCommutes` by cases on `e`. The activation case must explicitly use fibre base union and ranked-fibre coherence; token cases are pointwise reflexive.

- [ ] **Step 5: Implement extensional rebasing and Flash congruence**

```lean
def rebaseChecked (h : ViewEq R S) (e : CheckedViewEvent R) :
    CheckedViewEvent S := by
  rw [h.toEq]
  exact e

theorem applyRaw_congr (h : ViewEq R S) (e : CheckedViewEvent R) :
    ViewEq (applyRaw R e) (applyRaw S (rebaseChecked h e)) := by
  subst S
  exact ViewEq.refl _

def rebaseClosedChecked (h : ClosedViewEq C D)
    (e : CheckedViewEvent C.raw) : CheckedViewEvent D.raw :=
  rebaseChecked h.rawEq e

theorem flashStep_congr (h : ClosedViewEq C D)
    (e : CheckedViewEvent C.raw) :
    ClosedViewEq (flashStep C e)
      (flashStep D (rebaseClosedChecked h e)) := by
  subst D
  exact ClosedViewEq.refl _
```

If `subst` does not consume the extensional relation directly, call `ViewEq.toEq`/`ClosedViewEq.toEq` first. Do not weaken checked-event indexing.

- [ ] **Step 6: Implement dependent traces and both growth folds**

```lean
inductive AllowedTrace
    (Ωauth : AuthoritySnapshot U.CertId) (q : U.NodeId → Label) :
    (C : ClosedSource U Ωauth) →
    AdmissibleQuotient Ωauth C.source q →
    List (SourceEvent U) → Type (u + 1)
  | nil (C) (hq) : AllowedTrace Ωauth q C hq []
  | cons {C hq e es}
      (step : AllowedStep Ωauth q C hq e)
      (tail : AllowedTrace Ωauth q (sourceStep C step.checkedSource)
        step.nextAdmissible es) :
      AllowedTrace Ωauth q C hq (e :: es)

inductive ProjectedTrace : (C : ClosedView U Label) → Type (u + 1)
  | nil (C) : ProjectedTrace C
  | cons {C} (e : CheckedViewEvent C.raw)
      (tail : ProjectedTrace (flashStep C e)) : ProjectedTrace C
```

Define `growSource` and `growProjected` by recursion on these traces. Define `projectTrace hq hE` recursively while threading a `ClosedViewEq` between the actual projected state and the canonical projection of the current source. Rebase `step.projectedDelta` with that witness before calling `flashStep`; use `rawCommutes`, `flashStep_exact`, `batch_projection_commutes`, and `flashStep_congr` to construct the next witness.

Before the capstone, add the two transport accessors forced by `ClosedSource.raw_eq`:

```lean
def closedSupportCompatible
    (C : ClosedSource U Ωauth) (hq : AdmissibleQuotient Ωauth C.source q) :
    SupportCompatible (sourceClosedView C).raw q := by
  rw [C.raw_eq]
  exact hq.supportCompatible

def closedProjectedValid
    (C : ClosedSource U Ωauth) (hq : AdmissibleQuotient Ωauth C.source q) :
    ValidRaw (projectRaw q (sourceClosedView C).raw) := by
  rw [C.raw_eq]
  exact projectedValid hq
```

- [ ] **Step 7: Prove the grow–dissolve theorem**

```lean
theorem grow_dissolve_preserves_protected_queries
    (hq : AdmissibleQuotient Ωauth C.source q)
    (hE : AllowedTrace Ωauth q C hq E)
    (Q : ProtectedQuery Label) :
    evalQuery q
        (sourceClosedView (growSource C hE)).raw
        (sourceClosedView (growSource C hE)).closed Q =
      evalQuery id
        (growProjected
          (projectClosed q (sourceClosedView C)
            (closedSupportCompatible C hq) (closedProjectedValid C hq))
          (projectTrace hq hE)).raw
        (growProjected
          (projectClosed q (sourceClosedView C)
            (closedSupportCompatible C hq) (closedProjectedValid C hq))
          (projectTrace hq hE)).closed Q
```

Prove by induction on `hE`. The nil case is `closed_queries_preserved`. The cons case rewrites the source step with `flashStep_exact`, the projected step with the threaded `ClosedViewEq`, applies the induction hypothesis to the tail, and finishes with `closedViewEq_query`. Keep the conclusion Boolean and query-relative.

- [ ] **Step 8: Run all semantic checkpoints**

Run:

```bash
cd qcklean
lake env lean CLC/ContinuationTest.lean
lake env lean CLC/QuotientTest.lean
lake env lean CLC/FlashTest.lean
lake env lean CLC/GrowTest.lean
```

Expected: PASS for `continuationSafe_map`, `spuriousPath_not_admissible`, Flash exactness/commutation, and `grow_dissolve_preserves_protected_queries`.

- [ ] **Step 9: Commit finite certified growth**

```bash
git add qcklean/CLC/Grow.lean qcklean/CLC/GrowTest.lean \
  qcklean/CLC/Fixtures.lean
git commit -m "feat(clc): prove grow-dissolve query preservation"
```

### Task 11: Public audit, Lake roots, and CI qualification

**Files:**
- Create: `qcklean/CLC/Audit.lean`
- Modify: `qcklean/lakefile.lean`
- Create: `.github/workflows/clc-nonlinear-lineage-v0.yml`

**Interfaces:**
- Consumes: every public CLC theorem and fixture.
- Produces: one reproducible qualification target with frozen-QCK guards, source audit, all tests, all fixtures, and axiom-surface checks.

- [ ] **Step 1: Write the axiom audit**

```lean
-- qcklean/CLC/Audit.lean
import CLC.Grow
import CLC.Fixtures

#print axioms CLC.transport_comp_assoc
#print axioms CLC.decisive_preserved
#print axioms CLC.continuationSafe_map
#print axioms CLC.normalize_live_nonempty_iff
#print axioms CLC.quotient_path_lift
#print axioms CLC.Fixtures.spuriousPath_not_admissible
#print axioms CLC.batch_projection_commutes
#print axioms CLC.flashStep_exact
#print axioms CLC.grow_dissolve_preserves_protected_queries
```

- [ ] **Step 2: Register every module and test in Lake**

Replace only the `roots` array in `qcklean/lakefile.lean` with the existing roots followed by:

```lean
`CLC.Verdict, `CLC.VerdictTest,
`CLC.Transport, `CLC.TransportTest,
`CLC.Continuation, `CLC.ContinuationTest,
`CLC.Support, `CLC.SupportTest,
`CLC.Hypergraph, `CLC.HypergraphTest,
`CLC.Query, `CLC.QueryTest,
`CLC.Quotient, `CLC.QuotientTest,
`CLC.Flash, `CLC.FlashTest,
`CLC.Grow, `CLC.GrowTest,
`CLC.Fixtures, `CLC.Audit
```

Do not change the package name, Lean arguments, Mathlib URL, or pinned revision.

- [ ] **Step 3: Run the full local build before adding CI**

Run:

```bash
cd qcklean
lake update
lake exe cache get
lake build QCK
for f in CLC/*Test.lean; do lake env lean "$f"; done
lake env lean CLC/Audit.lean 2>&1 | tee /tmp/clc-axioms.log
! grep -E 'sorryAx' /tmp/clc-axioms.log
```

Expected: PASS. Axiom output may contain only `propext`, `Classical.choice`, and `Quot.sound`, matching the existing QCK audit policy.

- [ ] **Step 4: Add the dedicated workflow**

```yaml
# .github/workflows/clc-nonlinear-lineage-v0.yml
name: CLC Nonlinear Lineage V0

on:
  push:
    branches: [clc-nonlinear-lineage-v0]
    paths:
      - 'qcklean/**'
      - 'docs/superpowers/specs/2026-09-20-clc-nonlinear-lineage-v0-design.md'
      - 'docs/superpowers/plans/2026-09-21-clc-nonlinear-lineage-v0.md'
      - '.github/workflows/clc-nonlinear-lineage-v0.yml'
  workflow_dispatch:

permissions:
  contents: read

jobs:
  clc-v0:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - name: Verify frozen QCK sources
        run: |
          test "$(git hash-object qcklean/QCKCore.lean)" = "b9b1921c49c9947a02009be124286cfe3c723cb4"
          git diff --exit-code baef39cd7b32c860e2d7aa80a95f3826b8a52738 -- 'qcklean/QCK*.lean'
      - name: Install Lean via elan
        run: |
          curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh -s -- -y
          echo "$HOME/.elan/bin" >> "$GITHUB_PATH"
      - name: Fetch pinned Mathlib
        working-directory: qcklean
        run: |
          lake update
          lake exe cache get
      - name: Reject placeholders and local axioms
        working-directory: qcklean
        run: |
          set -euo pipefail
          ! grep -RInE '(^|[^[:alnum:]_])(sorry|admit|axiom|constant|unsafe)([^[:alnum:]_]|$)' CLC \
            | grep -vE '^[^:]+:[0-9]+:[[:space:]]*#print[[:space:]]+axioms([[:space:]]|$)'
      - name: Build QCK and CLC
        working-directory: qcklean
        run: lake build QCK
      - name: Run every CLC interface and fixture test
        working-directory: qcklean
        run: |
          set -euo pipefail
          for file in CLC/*Test.lean; do lake env lean "$file"; done
      - name: Audit CLC theorem dependencies
        working-directory: qcklean
        run: |
          set -euo pipefail
          lake env lean CLC/Audit.lean 2>&1 | tee /tmp/clc-axioms.log
          ! grep -E 'sorryAx' /tmp/clc-axioms.log
          if grep -F 'depends on axioms:' /tmp/clc-axioms.log \
            | grep -vE "depends on axioms: \[(propext|Classical\.choice|Quot\.sound)(, (propext|Classical\.choice|Quot\.sound))*\]$"; then
            echo "Unexpected foundational dependency detected"
            exit 1
          fi
```

- [ ] **Step 5: Run the complete qualification command locally**

Run:

```bash
cd qcklean
lake build QCK
for f in CLC/*Test.lean; do lake env lean "$f"; done
lake env lean CLC/Audit.lean
```

Expected: all existing QCK roots and every CLC root compile; all finite `#eval`/`native_decide` fixtures pass; audit contains no `sorryAx` or unapproved axiom.

- [ ] **Step 6: Commit qualification**

```bash
git add qcklean/lakefile.lean qcklean/CLC/Audit.lean \
  .github/workflows/clc-nonlinear-lineage-v0.yml
git commit -m "ci(clc): qualify nonlinear lineage V0"
```

### Task 12: Final branch verification and evidence record

**Files:**
- Modify only if verification finds a defect: the file that owns that defect and its paired test.
- Do not create a release document or broaden the theorem claim.

**Interfaces:**
- Consumes: the completed branch.
- Produces: a clean branch head whose local and CI evidence supports exactly the V0 claim boundary.

- [ ] **Step 1: Verify scope and frozen files**

Run:

```bash
git diff --name-only baef39cd7b32c860e2d7aa80a95f3826b8a52738...HEAD
git diff --exit-code baef39cd7b32c860e2d7aa80a95f3826b8a52738...HEAD -- 'qcklean/QCK*.lean'
```

Expected: changes are limited to the approved spec/plan, `qcklean/CLC/**`, `qcklean/lakefile.lean`, and the CLC workflow; the frozen-source diff is empty.

- [ ] **Step 2: Run fresh qualification from the committed head**

Run:

```bash
cd qcklean
lake clean
lake update
lake exe cache get
lake build QCK
for f in CLC/*Test.lean; do lake env lean "$f"; done
lake env lean CLC/Audit.lean 2>&1 | tee /tmp/clc-final-axioms.log
! grep -E 'sorryAx' /tmp/clc-final-axioms.log
```

Expected: PASS from a clean build.

- [ ] **Step 3: Scan the exact CLC source surface**

Run:

```bash
! rg -n '(sorry|admit|axiom|constant|unsafe)' CLC \
  -g '*.lean' -g '!Audit.lean'
rg -n 'grow_dissolve_preserves_protected_queries|spuriousPath_not_admissible|continuationSafe_map|flashStep_exact' CLC
```

Expected: the forbidden scan is empty; all four checkpoint theorem names are present in implementation, tests, and audit.

- [ ] **Step 4: Push the branch and wait for the dedicated workflow**

Run:

```bash
git push -u origin clc-nonlinear-lineage-v0
gh run watch --repo heathsanchez/Minimal-Sufficient-Interface --exit-status
```

Expected: `CLC Nonlinear Lineage V0` completes successfully at the pushed commit.

- [ ] **Step 5: Record the final immutable evidence in the handoff**

Capture the branch head SHA, workflow run URL, `lake build QCK` result, test count, and the printed axiom surface in the final response. State the bounded claim exactly as the spec does: preservation of four protected answers along finite source-certified, quotient-compatible traces; do not claim arbitrary future or backward-simulation preservation.
