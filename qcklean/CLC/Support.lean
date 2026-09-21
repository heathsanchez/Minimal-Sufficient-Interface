import Mathlib.Data.Finset.Powerset
import Mathlib.Data.Finset.Max

namespace CLC

universe u

abbrev Support (Token : Type u) := Finset Token
abbrev SupportFamily (Token : Type u) := Finset (Support Token)

def normalize {Token : Type u} [DecidableEq Token]
    (F : SupportFamily Token) : SupportFamily Token :=
  F.filter fun s => ∀ t ∈ F, ¬ t ⊂ s

def Normalized {Token : Type u} [DecidableEq Token]
    (F : SupportFamily Token) : Prop :=
  normalize F = F

structure TokenSnapshot (Token : Type u) [DecidableEq Token] where
  live : Finset Token
  revoked : Finset Token
  disjoint : Disjoint live revoked

def supportLive {Token : Type u} [DecidableEq Token]
    (σ : TokenSnapshot Token) (s : Support Token) : Prop :=
  s ⊆ σ.live

instance instDecidableSupportLive {Token : Type u} [DecidableEq Token]
    (σ : TokenSnapshot Token) (s : Support Token) :
    Decidable (supportLive σ s) := by
  change Decidable (s ⊆ σ.live)
  exact Finset.instDecidableRelSubset s σ.live

def liveView {Token : Type u} [DecidableEq Token]
    (σ : TokenSnapshot Token) (F : SupportFamily Token) :
    SupportFamily Token :=
  (normalize F).filter (supportLive σ)

def CanEnable {Token : Type u} [DecidableEq Token]
    (σ : TokenSnapshot Token) (t : Token) : Prop :=
  t ∉ σ.live ∧ t ∉ σ.revoked

def CanRevoke {Token : Type u} [DecidableEq Token]
    (σ : TokenSnapshot Token) (t : Token) : Prop :=
  t ∈ σ.live

instance instDecidableCanEnable {Token : Type u} [DecidableEq Token]
    (σ : TokenSnapshot Token) (t : Token) :
    Decidable (CanEnable σ t) := by
  unfold CanEnable
  infer_instance

instance instDecidableCanRevoke {Token : Type u} [DecidableEq Token]
    (σ : TokenSnapshot Token) (t : Token) :
    Decidable (CanRevoke σ t) := by
  unfold CanRevoke
  infer_instance

def enable {Token : Type u} [DecidableEq Token]
    (σ : TokenSnapshot Token) (t : Token) (h : CanEnable σ t) :
    TokenSnapshot Token where
  live := insert t σ.live
  revoked := σ.revoked
  disjoint := by
    rw [Finset.disjoint_left]
    intro a ha har
    rw [Finset.mem_insert] at ha
    rcases ha with rfl | ha
    · exact h.2 har
    · exact (Finset.disjoint_left.mp σ.disjoint ha) har

def revoke {Token : Type u} [DecidableEq Token]
    (σ : TokenSnapshot Token) (t : Token) (h : CanRevoke σ t) :
    TokenSnapshot Token where
  live := σ.live.erase t
  revoked := insert t σ.revoked
  disjoint := by
    rw [Finset.disjoint_left]
    intro a ha har
    have ha' := Finset.mem_erase.mp ha
    rw [Finset.mem_insert] at har
    rcases har with rfl | har
    · exact ha'.1 rfl
    · exact (Finset.disjoint_left.mp σ.disjoint ha'.2) har

theorem normalize_idempotent {Token : Type u} [DecidableEq Token]
    (F : SupportFamily Token) :
    normalize (normalize F) = normalize F := by
  ext s
  constructor
  · intro hs
    exact (Finset.mem_filter.mp hs).1
  · intro hs
    change s ∈ (normalize F).filter (fun s => ∀ t ∈ normalize F, ¬ t ⊂ s)
    rw [Finset.mem_filter]
    refine ⟨hs, ?_⟩
    intro t ht hts
    exact (Finset.mem_filter.mp hs).2 t (Finset.mem_filter.mp ht).1 hts

theorem normalize_antichain {Token : Type u} [DecidableEq Token]
    {F : SupportFamily Token} {s t : Support Token}
    (hs : s ∈ normalize F) (ht : t ∈ normalize F) : ¬ s ⊂ t := by
  exact (Finset.mem_filter.mp ht).2 s (Finset.mem_filter.mp hs).1

theorem normalize_live_nonempty_iff {Token : Type u} [DecidableEq Token]
    {σ : TokenSnapshot Token} {F : SupportFamily Token} :
    (liveView σ F).Nonempty ↔ ∃ s ∈ F, supportLive σ s := by
  constructor
  · rintro ⟨s, hs⟩
    have hs' := Finset.mem_filter.mp hs
    exact ⟨s, (Finset.mem_filter.mp hs'.1).1, hs'.2⟩
  · rintro ⟨s, hsF, hsLive⟩
    let G : SupportFamily Token := F.filter fun t => t ⊆ s
    have hG : G.Nonempty := by
      exact ⟨s, Finset.mem_filter.mpr ⟨hsF, Finset.Subset.rfl⟩⟩
    obtain ⟨t, htG, hmin⟩ := G.exists_min_image Finset.card hG
    have htF : t ∈ F := (Finset.mem_filter.mp htG).1
    have hts : t ⊆ s := (Finset.mem_filter.mp htG).2
    have htNorm : t ∈ normalize F := by
      change t ∈ F.filter (fun t => ∀ u ∈ F, ¬ u ⊂ t)
      rw [Finset.mem_filter]
      refine ⟨htF, ?_⟩
      intro u huF hut
      have huG : u ∈ G := Finset.mem_filter.mpr
        ⟨huF, hut.1.trans hts⟩
      exact (Nat.not_le_of_lt (Finset.card_lt_card hut)) (hmin u huG)
    refine ⟨t, Finset.mem_filter.mpr ⟨htNorm, ?_⟩⟩
    exact hts.trans hsLive

theorem revocation_fallback {Token : Type u} [DecidableEq Token]
    {σ : TokenSnapshot Token} {t : Token} {F : SupportFamily Token}
    {s : Support Token} (hrev : CanRevoke σ t)
    (_hs : s ∈ F) (hlive : supportLive σ s) (ht : t ∉ s) :
    supportLive (revoke σ t hrev) s := by
  intro a ha
  exact Finset.mem_erase.mpr ⟨by
    intro hat
    subst a
    exact ht ha, hlive ha⟩

theorem revoked_not_reenableable {Token : Type u} [DecidableEq Token]
    {σ : TokenSnapshot Token} {t : Token} (hrev : CanRevoke σ t) :
    ¬ CanEnable (revoke σ t hrev) t := by
  intro h
  exact h.2 (by simp [revoke])

end CLC
