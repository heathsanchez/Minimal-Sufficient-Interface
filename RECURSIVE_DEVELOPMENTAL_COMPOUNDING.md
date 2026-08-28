# Recursive developmental compounding

The finite MSI programme now includes a direct causal test of

\[
\boxed{
\text{development}_1
\longrightarrow
\text{changed developmental policy}
\longrightarrow
\text{development}_2.
}
\]

The purpose is narrower than open-ended invention. It asks whether verified experience in one episode can be compressed into a retained developmental structure that changes the matched discovery frontier on a source-distinct later episode.

The executable witness is [`tests/test_recursive_developmental_compounding.py`](tests/test_recursive_developmental_compounding.py).

## Frozen setup

There are two six-state episodes.

The source and target have:

- different protected future labels;
- different observation tables;
- disjoint literal query identities;
- the same generic verifier contract;
- the same binary observation language shape.

A residual is the first pair of states still merged by the currently retained queries but separated by the protected future label.

The constructor never receives the complete target quotient. It receives only verifier-certified residual pairs.

## Development 1: residual history becomes policy

The source episode begins with no retained query policy. Under the frozen candidate order it requires three queries:

```text
s0, s1, s7
```

and the verifier returns the residual sequence

```text
(0,3), (0,5), (2,3).
```

The literal query names are not retained as the transferable object.

Instead the source residuals are compressed through a mechanically generated, source-independent query fingerprint

\[
\phi(q)=\min\bigl(|q^{-1}(0)|,|q^{-1}(1)|\bigr).
\]

For every fingerprint class, the compiler records how many certified residual pairs queries of that class separate, averaged across queries in the class.

Thus the retained developmental object is a small policy over anonymous structural query classes, induced entirely from:

1. verifier-returned residual pairs; and
2. executable observation values.

No semantic query label or target-state identity is transferred.

## Development 2: matched source-distinct episode

The later episode uses different state ordering, a different observation table and disjoint query names `t0..t7`.

The developmental budget is frozen to exactly **one query**.

Five arms share the same target language, verifier, candidate order and budget:

- **WARM** — retains the compiled source developmental policy;
- **COLD** — no inherited policy;
- **RAW_HISTORY** — retains only literal source query identities;
- **SHAM** — compiles the same policy form from deterministically corrupted residual history;
- **ANCESTOR_ABLATION** — removes the learned policy before the target episode.

The result is exact:

| arm | selected target query | exact target MSI in one query | downstream capability admissible |
|---|---:|---:|---:|
| WARM | `t2` | yes | yes |
| COLD | `t0` | no | no |
| RAW_HISTORY | `t0` | no | no |
| SHAM | `t0` | no | no |
| ANCESTOR_ABLATION | `t0` | no | no |

So

\[
\boxed{
K_2\in Discover_1(S_1+P_1)
}
\]

while

\[
\boxed{
K_2\notin Discover_1(S_1)
}
\]

and exact ablation of the retained policy restores the cold frontier.

Here `P₁` is the policy induced by source residual history and `K₂` is the target distinction whose acquisition yields the exact protected target MSI within the one-query budget.

## Downstream executable consequence

The target also contains a fixed downstream action

```text
(0,1,0,1,0,1)
```

which is present in the common raw language for every arm.

Before the target interface is repaired, this action is not well-defined on the current quotient. The WARM arm discovers `t2`, reaches the exact future-relative quotient, and the action becomes quotient-admissible.

All four controls remain at an interface on which the same action is not quotient-admissible.

Therefore the experiment demonstrates a typed causal chain:

\[
\boxed{
\text{verified residual history}
\to
\text{retained developmental policy}
\to
\text{different later query choice}
\to
\text{exact later MSI}
\to
\text{newly admissible downstream capability}.
}
\]

## What is closed

Inside the controlled finite MSI setting, this closes the missing recursive causal arrow:

\[
\boxed{
\textbf{development changes later development.}
}
\]

The inherited object is not a literal solution from the first episode: source and target query identities are disjoint, raw literal history does not transfer, and a corrupted-history policy does not reproduce the effect.

The gain is also correctly typed. The downstream action already exists in the common raw constructor language, so the result establishes **developmental policy/discovery gain and quotient-admissibility gain**, not new syntactic formability.

## What remains open

This finite witness does **not** establish unrestricted natural-world or open-ended recursive self-extension.

The remaining external question is whether the same causal pattern survives when:

- observation fingerprints themselves must be learned from raw natural traces;
- the target domain is source-distinct in a semantic rather than finite synthetic sense;
- constructor languages are richer and resource-bounded;
- several developmental generations compound rather than one source-to-target transfer.

Those are transfer and scale questions above the frozen MSI kernel. They no longer constitute a missing logical link in the finite mechanism itself.