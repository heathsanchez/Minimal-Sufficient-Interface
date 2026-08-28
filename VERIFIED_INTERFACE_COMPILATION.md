# Verified interface compilation

This experiment tests whether a behaviourally adequate construction can be
retained as a new unit in the constructor language, change a later
resource-bounded synthesis frontier, and then be promoted again for recursive
reuse.

It is an above-kernel developmental experiment. It does not change the frozen
MSI equations.

The executable census is
[`tests/test_verified_interface_compilation.py`](tests/test_verified_interface_compilation.py).
The independently checked semantic certificate is
[`lean/AdderInterfaceCompilation.lean`](lean/AdderInterfaceCompilation.lean).

## Frozen grammar and protected behaviour

The cold grammar contains only input variables and binary NAND:

\[
t ::= x_i \mid \operatorname{nand}(t,t).
\]

Programs are identified extensionally by their Boolean truth tables. Protected
rows are supplied incrementally: the learner proposes a surviving behaviour,
the verifier returns the first input row on which it differs from the protected
output, and the version space is refined by that row.

Two protected output behaviours are learned independently:

- the low result bit of adding two bits;
- the carry bit of adding two bits.

The minimum NAND-formula representatives have costs 5 and 3 respectively.
They are retained anonymously as the two-output interface `hs` and `hc`.

## Promotion changes the later synthesis frontier

The next protected task is a three-input full adder. Under formula-tree cost:

| arm | available constructors | minimum total cost of sum and carry |
|---|---|---:|
| COLD | NAND | 20 |
| WARM | NAND + retained `hs`, `hc` | **6** |
| SHAM | NAND + left/right projections | 20 |
| ANCESTOR_ABLATION | NAND | 20 |

With the synthesis budget frozen at 6, WARM succeeds and every matched control
fails. Thus the retained interface changes the bounded discovery frontier:

\[
\boxed{
K_2\in Discover_6(G+K_1),
\qquad
K_2\notin Discover_6(G).
}
\]

The measured compression is `20/6 = 3.33×` in the promoted-constructor cost
model.

## Second promotion and recursive compounding

The full-adder outputs are then retained as a second interface and composed
recursively into ripple addition. Python exhausts all input pairs at widths 4
and 6. Lean independently certifies:

- every half-adder input;
- every full-adder input;
- all 256 four-bit input pairs;
- all 4,096 six-bit input pairs.

The developmental chain is therefore:

\[
\boxed{
\text{NAND grammar}
\to
\text{verified residual rows}
\to
\text{retained half-adder interface}
\to
\text{changed full-adder frontier}
\to
\text{retained full-adder interface}
\to
\text{recursive multi-bit composition}.
}
\]

This adds a second kind of recursive witness to MSI. The existing finite result
shows that retained residual history can change a later query policy. This
result shows that a retained behavioural program can change the later
**constructor language** and itself become substrate for another promotion.

## Cost discipline

The result is not a claim of reduced physical NAND-gate complexity.

The cold cost counts formula-tree NAND nodes. The warm cost counts each retained
interface call as one constructor node. If all calls are expanded back into
NAND formula trees, the 3.33× number does not persist. The demonstrated gain is
library-relative description length and bounded search reach.

That distinction is deliberate. A retained developmental product earns the
right to be treated as a unit in later construction. The scientific claim is
that this change of language alters what is reachable under a fixed search
budget, not that naming a macro makes its physical implementation free.

The executable test reports both views and charges the retained library
definition once in its amortized description-length calculation.

## Claim boundary

Established here:

1. a finite constructor grammar can generate minimum extensionally adequate
   programs under incremental verifier residuals;
2. retaining those programs as constructors strictly changes a matched later
   synthesis frontier;
3. exact ancestor ablation restores the cold frontier;
4. a second promotion supports verified recursive reuse outside the original
   two- and three-input synthesis domains.

Not established here:

- open-world concept invention;
- discovery of the addition task or its protected outputs;
- semantic transfer to an unrelated natural domain;
- physical circuit optimization;
- unrestricted recursive self-improvement.

The appropriate interpretation is:

\[
\boxed{
\textbf{verified closed-world interface discovery can be compiled into the
constructor language and causally compound under a resource bound.}
}
\]

