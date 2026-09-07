# PREREGISTRATION — constructor-language derivation from the symmetry-breaking constraint

**Status:** FROZEN (written before the class-level CI `34025101168` has landed; build gated on that green).

**Frozen inputs:**
- `ρ = (f x y, f y x)` — the swap witness; `σ = (0 1)` — position swap; `F_B = identity`.
- Substrate: variables with `Nat` indices (`x=0`, `y=1`), operators `a0`/`f`/`g`.
- Certified constraint (from `SymmetryClass.lean`): `Separates(R) ⇒ ¬Sym_σ(R)` — any separator must break σ.

**The residual (precise):**
The system can now DERIVE the required relation *class* (σ-breaking / asymmetric), but cannot yet
CONSTRUCT an inhabitant of that class without a supplied candidate-relation language.  In
`SymmetryClass.lean`, `lt` is still hand-supplied as `ltRel' = "compare the two `Nat` indices by <"`.

**Prediction (prospective, falsifiable):**
The constructor language for asymmetric relations is DETERMINED by the substrate's asymmetric primitives,
not freely chosen.  Specifically: an asymmetric relation over the witness must distinguish `x` (index 0)
from `y` (index 1); the only asymmetric primitive in the substrate is the `Nat` index order `<` (operator
order `a0<f<g` is the other candidate, but the witness's two subterms are both variables).  Hence the
system derives `lt` from the substrate's asymmetric primitive rather than naming it.

**Falsifiers:**
- `F1` — the symmetry-breaking constraint is satisfiable by a relation built from NO asymmetric primitive
  (i.e. an asymmetric relation constructible in a symmetric substrate).  If provable, the derivation is not
  substrate-determined.
- `F2` — the substrate has no asymmetric primitive and the witness is still separable.  If provable, the
  "only asymmetric primitive" premise is false.

**The honest seam this probe is expected to reveal (recorded in advance):**
The substrate's asymmetric primitives (`Nat` order, operator order) are themselves human-fixed.  If the
substrate were fully symmetric (unordered variables), the swap witness would be an UNREPAIRABLE collapse —
a theorem, not a search miss — and no adequate ontology could be constructed at all.  The symmetry-breaking
constraint is therefore necessary but NOT sufficient: it forces asymmetry, but the *source* of asymmetry is
the substrate.  That is where the constitutional bedrock (initial primitives) enters.
