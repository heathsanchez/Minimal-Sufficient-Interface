# QCK v1 downstream migration

## Status

The constitutional theorem surface is frozen at:

`fc112771bd0a24e40e31e4eaef61ca0442103dd4`

Frozen branch: `qck-v1-frozen`.

Downstream migration proceeds on `qck-v1-migration`.  The frozen branch is not
to be edited.

## Rule

Existing MSI / consequential-development code is now treated as an adapter or
developmental layer.  It must not become a second source of constitutional
semantics when QCK v1 already fixes the concept.

## Canonical mappings

| Existing concept | QCKN role after migration |
| --- | --- |
| `msi.Interface.equivalent` / `partition` | finite-set domain realization of consequential equivalence |
| `Interface.preserves_equivalence` | finite-set analogue of `KernelStable` |
| `Interface.residual_witness` | finite separator search |
| `consequential_core.PairResidual` | ledger form of `NewContextDefect` |
| `ClosureResidual` | domain residual indicating the current capability language cannot realize the required consequence contract |
| `AcquisitionResidual` | developmental residual; handled above QCK by intervention policy |
| `CertifiedRepair` | authority-approved developmental intervention, not a QCK semantic primitive |
| `ProvenanceToken` | provenance/rollback metadata for RealityGraph/.mg |
| `quotient_admissible` | legacy finite predicate; new code should call the QCKN adapter assessment |
| `compile_repair` | developmental compilation into retained state, outside QCK Core |

## First migrated interface

`qckn.finite_adapter` exposes the frozen two-way operation assessment in the
finite/discrete setting:

`CertifiedSubstitution | NewContextDefect`.

A defect contains an explicit source pair that is identified by the current
interface but whose images are distinguished by protected consequences.  It can
be compiled directly into the existing `PairResidual` ledger without changing
the constitutional meaning.

This keeps legacy experiments usable while making the direction of authority
one-way:

```text
frozen QCK v1 semantics
        ↓
domain adapter
        ↓
typed residual
        ↓
MDA intervention
        ↓
authority verification
        ↓
RealityGraph / .mg retention
```

## Migration invariants

1. The frozen QCK branch never imports MDA, RealityGraph, domain code, or policy.
2. Downstream code may implement finite/discrete analogues, but names and
   contracts must point back to the frozen QCK vocabulary.
3. A RED becomes a typed reusable separator whenever possible.
4. Developmental policy may choose what to do about a residual; it may not
   redefine what counts as consequence-preserving substitution.
5. Old overlapping predicates remain compatibility shims until their callers
   migrate, then should be removed or made aliases.


## MDA boundary

The first policy layer now lives in `qckn.mda`.

It receives typed QCK-aligned outcomes and returns only interventions licensed
for that outcome.  The final choice is made by an explicit prospective-cost
function, so semantic classification and economic/search policy remain
separate.

For example, a `NewContextDefect` can license `SPLIT`, `EXPAND`,
`RESTRUCTURE`, `CONSTRUCT`, or `VERIFY`; MDA chooses the cheapest
currently warranted option instead of baking one repair into QCK semantics.

The focused workflow `QCK v1 downstream migration` enforces two invariants:
the frozen `qcklean` theorem surface is byte-for-byte unchanged from the
qualified v1 commit, and the finite adapter/MDA tests pass.
