# Upstream candidate — recursor export soundness

**Status:** CANDIDATE / not yet submitted as a mathlib PR.

## Smallest externally useful result

A Lean export consumer must not trust an exported `RecursorVal` merely because it is present in the export. For an ordinary inductive declaration, the accepted recursor set must be the set reconstructed/authorized by the inductive declaration; an extra exported recursor can otherwise introduce an inhabitant of an actually empty type.

The existing frozen reproducer is `heathsanchez/lean-kernel-arena`, branch `mathgraph-recursor-soundness`, test `tests/extra-rec.lean` / `tests/extra-rec.ndjson` / `tests/extra-rec.yaml`.

The reproducer constructs an extra recursor `rogue` with type `False` using the private kernel-bypassing environment insertion path and then declares `inconsistent : False := rogue`. The expected result for an independent checker is rejection. This is distinct from mutating the rules of a legitimate recursor: the entire recursor constant is fabricated.

## Why this is the clean candidate

1. The failure has a minimal semantic statement: **reject exported recursors not authorized by the reconstructed inductive declaration**.
2. The witness is tiny (`False` plus one fabricated recursor) and does not depend on MSI terminology.
3. It has a static exported artifact, so the consumer-side test is reproducible even if the private environment API changes.
4. It is independently useful to Lean export/checker tooling.

## Upstream routing gate

Do **not** submit this blindly to mathlib. First determine where the defective trust boundary lives:

- If the issue is in mathlib code that imports/reconstructs Lean declarations, reduce the fix/test against current mathlib and submit there.
- If the issue is in Lean core/export semantics, submit to `leanprover/lean4` instead.
- If it is specific to an independent checker/arena contract, upstream the regression test to the Lean Kernel Arena rather than manufacturing a mathlib change.

The scientific result is the recursor-soundness witness; the correct upstream repository is an engineering fact to establish before PR creation.

## PR-ready acceptance criteria

- minimal reproducer retained;
- legitimate ordinary inductive recursors still accepted;
- fabricated extra recursor rejected;
- test demonstrates failure before fix and success after fix;
- no MathGraph/MSI-specific dependency;
- current upstream head tested;
- exact upstream SHA and toolchain pinned in PR description.

## Current provenance

- Arena branch: `mathgraph-recursor-soundness`
- Arena branch head observed 2026-09-01: `68dbf8ef445fbddd5b0fb1e5051ade5a1111af95`
- Test source: `tests/extra-rec.lean`
- Static export: `tests/extra-rec.ndjson`
- Expected outcome: `reject`

This file is the third shipping track, not evidence that a mathlib PR already exists.
