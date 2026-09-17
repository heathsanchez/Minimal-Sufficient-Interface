# MG-ARC6 residual stable-state quotient — qualified null result

Date: 18 September 2026 NZ time

## Verdict

MG-ARC6 is **not promoted**. Its bounded residual gate activated on all three public diagnostics, but no pixel satisfied the conservative masking contract. Consequently the full candidate, the exact MG-ARC5 prior, and the no-quotient ablation produced identical task outcomes and identical action-source counts on every measured world.

This is useful negative evidence: the current residual is not explained by a small set of fixed raster positions that vary frequently under multiple independent interventions.

## Immutable evidence

- Branch: `arc3-residual-growth-v1`
- Tested head: `f42460fae4044680e5a08982adb7852b82741db0`
- Prior champion: `07fe94a80edfbb295049d4140aef14ef2b47524b`
- Run: https://github.com/heathsanchez/Minimal-Sufficient-Interface/actions/runs/35283549316
- Job: https://github.com/heathsanchez/Minimal-Sufficient-Interface/actions/runs/35283549316/job/105410717708
- Artifact: https://github.com/heathsanchez/Minimal-Sufficient-Interface/actions/runs/35283549316/artifacts/10524116719
- Artifact SHA256: `faf241656f51a919b7dd16f1140a8a37a9204577311a911b45e7e09fb5d4b930`
- Candidate generated-agent SHA256: `c24c7ec8915ea209d685a68054f9ccca92038b9fdd5a1b57b9172e8d72e61585`
- Exact MG-ARC5 prior generated-agent SHA256: `d9f0b95dfee14613425e8f557808e129b25e8a055ad481800b1024ce45281ead`
- 85/85 tests passed; standalone agent and notebook built; all 12 matched cells completed.

## Results

| World | MG-ARC6 | MG-ARC5 prior | no_quotient | Quotient mask |
|---|---:|---:|---:|---:|
| bt11 fixture | 5/5 WIN @73 | 5/5 WIN @73 | 5/5 WIN @73 | inactive |
| ft09 public | 0/400 | 0/400 | 0/400 | active, 0 pixels |
| ls20 public | 0/400 | 0/400 | 0/400 | active, 0 pixels |
| vc33 public | L1@64, L2@93 | L1@64, L2@93 | L1@64, L2@93 | active, 0 pixels |

The exact MG-ARC5 memory digests were also preserved on every world, confirming the quotient did not alter certified/refutation memory.

## Residual

The diagnostic sharply separates the remaining public failures:

- **ft09:** 281/399 explicit steps produced no observation change. The residual is sparse actionable intervention / grounding, not frame volatility.
- **ls20:** 390/399 explicit steps changed the observation and 355 distinct observations appeared in 399 steps. Exact state identity destroys recurrence, but the volatility is not concentrated at fixed pixels.
- **vc33:** MG-ARC5 remains the qualified two-level result; the new quotient stays behaviorally dormant.

The next warranted representation for ls20 is therefore **action-conditioned object transport**, not fixed-pixel masking. The existing primitive `effect_signature` intentionally sets spatial direction to zero for primitive actions, so it cannot compile directional movement semantics even when repeated movement is visible. A generic transport model can identify exact translated connected components, learn action→motion relations, and use them for frontier exploration without game-specific rules.

No Kaggle submission, merge, or official PR was made.
