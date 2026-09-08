# Composite residual repair — exploratory successor

This is a post-discovery repair of the independently validated 8/12 constructor result, not a new confirmatory experiment. The frozen constructor source at `7f962c53da728045ea8455976b9a4ee93c953ead` is preserved byte-for-byte as `frozen_constructor.py` (Git blob `294fc3a43c4d155290430777695add4d5de56cb7`). The existing validation and its results are unchanged.

## Repair

The existing ordered families are tried first. Each rejected candidate retains a concrete pair of observations with the same representation key and different verifier outcomes. Only after every candidate in the existing families is contradicted does the learner generate unordered pairs of unary words from `t ::= F(t) | G(t) | x`, depth at most 2. The original primitive pair is excluded because it was already tested. There are 14 new paired candidates. They are ordered by total word length, then lexical order. No target-specific pair is supplied to the learner.

A candidate may be installed only when its lookup table is complete and all least-cost surviving candidates induce the same behavior on the entire declared finite input domain. Missing labels, incomplete tables, and ambiguous extensions are not certificates. The independent verifier reconstructs the candidate grammar, collision witnesses, complete tables, minimal tier, and behavioral equivalence from the recorded evidence. It does not receive the hidden target function. The retained source is a content-addressed bounded call, and deployment uses no verifier.

## Executed local result

The original generator is reproduced with seed 20260909, and a separate fresh generator uses seed 20260910. Each cohort contains four binary-local, four state-gated, and four composite-pair tasks. Acquisition uses 108 permutation rows; evaluation uses the original 2,079 held-out rows. The frozen baseline scores 8/12 exact in each cohort. The repaired learner scores 12/12 exact in each cohort, with zero incorrect covered predictions. All 24 certificates pass independent finite replay. All 24 full-domain post-test audits have zero errors. Removing the retained archive entry gives zero coverage, not a false prediction. The missing-feedback control returns `insufficient_evidence`; the target `(x + F(G(x)) + G(F(x))) mod 3` is correctly outside the declared grammar.

For the four original composite-pair tasks, the learner selects the generated pair `F(G(x)), G(F(x))`, after 21 concrete lower-candidate obstructions. This is a bounded minimum in the declared ordered grammar, not a claim that an arbitrary semantic constructor has been invented. The fresh tasks share the generator family and are not independent researcher-authored grammars. The post-discovery repair and its fresh seed do not turn the earlier 8/12 into a preregistered 12/12 result.

The local qualification suite has 17 passing tests, including source identity, frozen baseline reproduction, independent certificate replay, all saved certificates, missing/malformed/partial evidence, forged identities/content/obstructions, source-bound escape, actual archive removal, and an outside-grammar target. The local `results.json` SHA-256 is `b571d0fc2deebaa8faa16ebdab374251e0c6fecb16ef45a5bb8eec6e35785d3b`. The new CI workflow reproduces the experiment and uploads full evidence/certificates as an artifact. CI success is reported separately from scientific acceptance.

## Scope and next boundary

The repair establishes that a verified residual can trigger a more expressive generated observation interface and preserve its useful behavior across held-out inputs in this finite family. It does not establish arbitrary grammar genesis, general source-distinct transfer, the joint study's independent-grammar criterion, or new Lean kernel qualification. The next genuine test should use independently authored grammars and an unseen task family not chosen to fit this paired-word language. A stronger ablation should compare behavioral performance under missing feedback, rather than counting refusal alone as a causal gain.

Run `python experiments/mathgraph/run_composite_repair.py` and then `python -m unittest discover -s experiments/mathgraph -p test_composite_repair.py -v` from the repository root. No third-party Python dependencies are required.
