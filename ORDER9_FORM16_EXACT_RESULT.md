# Exact order-9 three-Bad form 16 exclusion

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

Form `16/24` is

```text
C:square-Good,D0=2;
D-3cycle;
f1=2,f2=2.
```

The normalized Bad labels are `{0,2,3}` and the canonical strict extra roots are

```text
(0,2), (0,3).
```

For each root the product is split exhaustively into

```text
Good / row value / third Bad value,
```

giving six aggregate leaves. Residual Good relabelling reduces the two Good leaves to one named representative each, both product `4`.

## Exact result

GitHub Actions run:

```text
33701899597
```

Job:

```text
100482770679
```

CaDiCaL195:

```text
canonical outcomes: 6/6 UNSAT
Good representatives: 2/2 UNSAT
UNKNOWN: 0
SAT: 0
```

Glucose42:

```text
canonical outcomes: 6/6 UNSAT
Good representatives: 2/2 UNSAT
UNKNOWN: 0
SAT: 0
```

The workflow-level coverage validator emitted

```text
ORDER9_FORM16_EXACTLY_EXCLUDED_IN_TWO_ENGINES
```

Artifact:

```text
id: 9873859424
sha256: 4ddcbced44f487c54294db574a743130499c315c6a1f50064da9473f6d0610b8
```

## Consequence

The exact three-Bad order-9 closure advances from

```text
17/24 -> 18/24.
```

The remaining top forms are exactly

```text
11,15,18,21,23,24.
```

The next finite residual is form `23`, selected because the frozen checker gives it only two Good-product representatives, the smallest remaining representative surface after form 16. The size-free global frontier remains the simultaneous G-CROSS network.
