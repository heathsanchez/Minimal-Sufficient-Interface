# E677 T6 full-D phase-frontier closure and attachment audit

Date: 2026-09-03.

## Verified scoped result

The n=7 shifted 141-state phase frontier has now been replayed against the necessary four-row T6 PAIR-KERNEL projection across the entire D-permutation space.

Nonlinear layers:

- kappa 18: 294 labelled D maps;
- kappa 22: 882;
- kappa 24: 1,470;
- kappa 26: 1,764;
- kappa 30: 588.

Total nonlinear D maps: 4,998. Every layer has zero survivors after its exact proved normalization.

Affine layer:

- 42 labelled affine maps D(x)=a*x+b;
- exact output-translation normalization D -> D+c reduces these to six D(x)=a*x representatives;
- 6 x 141 = 846 normalized D/phase pairs;
- zero survivors.

Affine evidence: GitHub Actions run 33729665828, job 100566478774, artifact 9883324075.

Therefore:

```text
4,998 nonlinear + 42 affine = 5,040 / 5,040 D permutations
```

have zero survivors in this phase frontier under the necessary four-row T6 projection.

This is a scoped branch closure. It does not claim the seven-row core is globally impossible and does not claim E677 -> E255.

## Attachment audit

Pinned upstream source: `Grisha-Pochuev/finite-magma-e677-to-e255` at `5a205195a84eec54dbcb2fd766f0b2d1ded1831b`.

`docs/ACTIVE_FRONTIER_MIN.md` describes the constructive size-7 route by saying the most developed exact reduction *uses cyclic P* and a normalized cyclic isotope Latin layer.

`lemmas/e677_cyclic_P_normalized_isotope_one_role_exclusion.md` begins its lossless-normalization section with:

```text
Continue in the order-49 cyclic branch
P_t(s)=t-s,
D(C_q(u))=A(q)+B(u) mod 7.
```

The gauge normalization is lossless within that cyclic isotope class, and its SAT witnesses attach back to the original routed tuple constraints within the branch. The source does not establish that an arbitrary E677 counterexample must have cyclic P or enter this order-49 cyclic isotope representation.

Hence the exact consequence is:

```text
full D-space closure inside cyclic-P phase frontier
    !=
global attachment of that frontier
```

Classification: `PARK_AND_REFRAME`.

The cyclic-P phase route is exhausted at its present representation and should not be widened by rhetoric or searched further without a new attachment theorem. The active mathematical residual returns to the less-assumptive size-free G-CROSS / renewal structure.

## Process consequence

The same push that routed to affine D also triggered the exhausted nonlinear-curvature workflow. That workflow failed solely because no curvature layer remained. This is process evidence, not mathematical evidence.

New retained process law:

```text
INAPPLICABLE != FAILED
```

Experiment applicability must be routed from the authoritative live residual. Exhausted experiment families should emit a clean skip and consume no mathematical search budget.
