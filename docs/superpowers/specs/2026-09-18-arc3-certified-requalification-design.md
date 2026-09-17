# MG-ARC5 Certified Requalification Design

## Purpose

MG-ARC4 separates a witnessed source capability from the action budget allowed for speculative use at a later target. It bounds negative transfer but does not answer the applicability question: whether the target is exhibiting the same relevant consequences that justified the source capability.

MG-ARC5 adds a bounded, explicit requalification contract. A successful source program earns an ordered witness of observed action-conditioned consequences. A later target may spend a short probe prefix to test whether those consequences extend. Only a matching prefix may unlock the remainder of the existing target-scoped transfer allowance.

This is a bounded operational certificate, not a proof of behavioral equivalence under all continuations and not a QCK closure theorem.

## Invariants

1. A source success remains source-scoped evidence. Target mismatch never erases it.
2. A target probe mismatch means `CONTRACT_MISMATCH` for that use, not semantic refutation of the source program.
3. Insufficient evidence remains `UNKNOWN`/unqualified. Budget exhaustion remains `EXPIRED_UNCONFIRMED`.
4. Requalification is based on observed consequences, not frame similarity alone.
5. The probe is bounded and included in the existing target action allowance; it cannot mint additional budget.
6. RESET, changed raster, restart, another source program, or a larger runtime parameter cannot refund spent target allowance.
7. Primitive-by-primitive legality and exact terminal-refutation checks continue to outrank speculative transfer.
8. Existing affordance acquisition, exact replay and public-game evaluator semantics are unchanged.
9. `.mg` records active source capability, witness/certificate provenance, target trial disposition and resource use separately.
10. MG-ARC4 files remain loadable without fabricating a witness.

## Source certificate

A capability retains its existing source context, program and witnessed level transition. MG-ARC5 additionally stores up to the first eight observed action/effect checkpoints from the successful suffix.

Each checkpoint is:

```text
(index, action_key, descriptor, structural_effect_signature)
```

`structural_effect_signature` is the existing normalized effect tuple:

```text
(changed_cells, bbox_width, bbox_height, dx_sign, dy_sign, components)
```

The descriptor is the existing consequence-controller descriptor. Primitive descriptors are action IDs; parameterized Action6 descriptors include local normalized pattern and component shape. Exact target frame hashes are not part of the portability contract.

The certificate also records `protected_outcome = LEVEL_INCREMENT` and a deterministic digest over its canonical payload.

A capability that predates MG-ARC5 has no consequence certificate and therefore may remain stored but cannot claim consequence-certified target reuse. Legacy loading does not synthesize a certificate.

## Target requalification

At a new completed-level target:

1. Select the freshest eligible certified source capability.
2. Start a `transfer_probe` using the source program from action 0.
3. After each probe action's next observation arrives, compute the same descriptor/effect signature as at the source.
4. Compare against the corresponding source checkpoint.
5. On mismatch, record target disposition `CONTRACT_MISMATCH`, clear the speculative macro and return control to acquisition.
6. If all available checkpoints in the bounded probe prefix match, record `PREFIX_REQUALIFIED` and permit the remaining source program/repetition only within the already-recorded MG-ARC4 target allowance.
7. If actual level progress occurs at any time, record `WITNESSED_PROGRESS`; the new successful target suffix earns its own source-scoped capability and certificate.

The bounded prefix has maximum length eight and never exceeds the source witness length or remaining target allowance. `PREFIX_REQUALIFIED` means only that the declared finite checkpoint contract matched. It does not assert whole-history or arbitrary-continuation equivalence.

## Data model

MG-ARC5 adds canonical `capability_contracts` rows keyed by the existing capability identity and adds target-trial statuses:

- `OPEN_PROBE`
- `PREFIX_REQUALIFIED`
- `CONTRACT_MISMATCH`
- `EXPIRED_UNCONFIRMED`
- `WITNESSED_PROGRESS`

Each target-trial row retains issued action count and the number of matched checkpoints. Parsing rejects malformed contracts, inconsistent action/checkpoint indices, unsupported capability references, invalid statuses, duplicate rows and aggregate target overspend.

## Controller boundaries

`ConsequenceController` owns observation semantics. It captures structural effect checkpoints and compares target probe effects because it already computes descriptors and effect signatures.

`MemoryGraphController` owns program scheduling and target allowance. It asks `.mg` for eligible capability records, labels actions `transfer_probe` until requalified, and labels subsequent macro actions `transfer`.

`ArcMemoryGraph` owns canonical persistent facts and status transitions. It does not inspect images or infer semantics.

## Qualification

Tests must demonstrate:

- source witness is captured only on observed level progress;
- canonical MG-ARC5 restart preserves witness and trial state;
- one target checkpoint mismatch stops reuse without refuting/deleting source capability;
- matching the bounded prefix changes status to `PREFIX_REQUALIFIED`;
- target allowance still caps total probe + transfer actions across reset/restart/source alternatives;
- legacy MG-ARC4 loads with no fabricated certificate;
- the generated standalone agent behaves identically to modular source for the new path.

Matched development diagnostics use the same pinned `bt11`, `ft09`, `ls20` and `vc33` worlds and budgets as MG-ARC4. Promotion requires preserving the `bt11` five-level WIN within 73 interactions and preserving at least two completed `vc33` levels within 400. The comparison records the `vc33` second-level milestone and transfer/probe action counts. A reduction from 109 toward the no-transfer 93 milestone is evidence of lower developmental cost, not a hidden-generalization result.

No result on ft09 or ls20 is a success gate. No public result is described as sealed generalization, a Kaggle score or a complete ARC-3 solve unless directly established.