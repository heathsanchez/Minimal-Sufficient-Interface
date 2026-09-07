# Exact order-9 three-Bad form 23 exclusion

Date: 2026-09-03

Status: **VERIFIED UNSAT in two independent SAT engines.**

This result is retained as a finite exact consequence of the current E677→E255 order-9 no-HIT programme. It does not by itself solve the global implication.

## Frozen verifier

External repository: `Grisha-Pochuev/finite-magma-e677-to-e255`

Pinned commit:

```text
5a205195a84eec54dbcb2fd766f0b2d1ded1831b
```

Checker:

```text
tools/e677_order9_no_hit_bad_count_sat.py
```

Frozen checker blob:

```text
efe356acd0047eef8ae5645b2cb04ac2a493632d
```

## Exact form

Form `23/24` is

```text
C:square-Good,D0=2;
D-2cycle,tail->D0;
f1=3,f3=2.
```

The canonical strict extra roots are

```text
(0,2), (0,3), (3,0).
```

For each root the product is split exhaustively into

```text
Good / row value / third Bad value,
```

giving nine aggregate leaves. Residual Good relabelling leaves exactly two named Good representatives:

```text
root=(0,2), product=4;
root=(0,3), product=4.
```

## Exact result

GitHub Actions run:

```text
33702219353
```

Job:

```text
100483735097
```

CaDiCaL195:

```text
canonical outcomes: 9/9 UNSAT
Good representatives: 2/2 UNSAT
UNKNOWN: 0
SAT: 0
```

Glucose42:

```text
canonical outcomes: 9/9 UNSAT
Good representatives: 2/2 UNSAT
UNKNOWN: 0
SAT: 0
```

The workflow-level coverage validator emitted

```text
ORDER9_FORM23_EXACTLY_EXCLUDED_IN_TWO_ENGINES
```

Artifact:

```text
id: 9873972384
sha256: 67bbba27a018f5e573de6e77465115e67f3d6b49b2e02e7da67a9dd6e4f2e317
```

## Consequence

The exact three-Bad order-9 closure advances from

```text
18/24 -> 19/24.
```

The remaining top forms are exactly

```text
11,15,18,21,24.
```

Forms `11` and `18` have the next-smallest representative surface and should be tested before the larger remaining forms. The size-free global frontier remains the simultaneous G-CROSS / Good-row renewal network.
