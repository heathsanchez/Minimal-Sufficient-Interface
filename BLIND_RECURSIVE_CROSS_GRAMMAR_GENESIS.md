# Blind recursive cross-grammar constructor genesis

This is the strongest immediately executable, credit-free precursor to the
decisive MSI experiment. It combines blind interface selection, independent
surface grammars, a sealed held-out task, causal controls, structural
interventions, and more than three successive constructor promotions.

The executable protocol is
[`tests/test_blind_recursive_cross_grammar_genesis.py`](tests/test_blind_recursive_cross_grammar_genesis.py).
The independently checked semantic certificate is
[`lean/BlindRecursiveCrossGrammarGenesis.lean`](lean/BlindRecursiveCrossGrammarGenesis.lean).

## Frozen protocol

Three functionally complete grammars have disjoint surface tokens and different
primitive signatures:

| grammar | primitive arities | verifier interpretation |
|---|---|---|
| `az` | one binary primitive | NAND |
| `by` | one unary, one binary | NOT + AND |
| `cx` | one unary, one binary | NOT + OR |

No primitive translation, interface identity, or semantic intermediate name is
given to the learner.

The candidate interface language is every unordered pair of the 16 possible
binary Boolean behaviours: 120 libraries. Each library is promoted only for
evaluation as two unit-cost constructors. The selection criterion is minimum
verified formula-tree description cost over 160 three-input behaviours selected
by the frozen hash order `SHA256("msi-blind-v1:" + mask)`.

The four arithmetic behaviours corresponding to the two full-adder outputs and
their complements are excluded before the first 160 masks are selected. They
remain sealed until after the interface is frozen. The remaining 96 behaviours
form the held-out family.

## Blind recovery result

The independent selections were:

| grammar | selected truth-table masks | optimum ties |
|---|---:|---:|
| `az` | `(6,11)` | `(6,11)`, `(6,13)` |
| `by` | `(6,11)` | `(6,11)`, `(6,13)` |
| `cx` | `(2,9)` | `(2,9)`, `(4,9)` |

These are not the same literal tables. They are one coordinate-free orbit under
input exchange, interface-component exchange, and Boolean output recoding. All
six optimum survivors lie in that orbit; there is no harmful cross-orbit tie.

This is the desired grammar-independent form of recovery: different coordinates
need not produce identical syntax, but they recover the same behavioural object
up to the transformations that protected behaviour cannot distinguish.

## Hash-held-out transfer

| grammar | cold held-out cost | retained-interface cost | sham cost | reduction |
|---|---:|---:|---:|---:|
| `az` | 571 | **267** | 571 | 53.2% |
| `by` | 696 | **261** | 696 | 62.5% |
| `cx` | 682 | **264** | 682 | 61.3% |

The sham contains two unit-cost projections. `RAW_HISTORY` and exact ancestor
ablation retain the same search and verified examples but do not install an
executable interface; both therefore have the cold frontier.

## Sealed task and first causal phase change

Only after selection is frozen is the sealed three-input arithmetic family
opened:

| arm | `az` cost | `by` cost | `cx` cost |
|---|---:|---:|---:|
| COLD / RAW / ABLATION | 20 | 29 | 29 |
| SHAM | 20 | 29 | 29 |
| WARM | **6** | **6** | **6** |

At the preregistered formula budget 6, only WARM succeeds in every grammar.
The retained binary interface was not selected using either sealed output.

## Three further promotions

The two verified full-adder outputs are promoted as one two-output constructor.
An unchanged residual eliminator then searches 60 anonymous two-block wiring
programs. At widths 2, 4 and 8, exactly four concrete counterexamples leave one
survivor:

1. evaluate the low block;
2. route its final bit into the high block;
3. preserve low-before-high output order;
4. return the high block's final bit.

The wiring is selected operationally; no `carry`, `low`, or `high` label is
visible to the learner.

Each promoted block makes the next doubling reachable with two constructor
calls. Exact ancestor ablation requires four calls at generations 4 and 8, and
the first block promotion would require twelve calls to the retained binary
library. Under the common budget 2:

\[
\boxed{
K_{t+1}\in Discover_2(G+K_t),
\qquad
K_{t+1}\notin Discover_2(G+K_{t-1}).
}
\]

Python exhausts every input and both incoming-bit values through width 8. Lean
independently checks all 131,072 eight-bit cases.

## Structural interventions

The verifier also edits the internal edge between two-bit blocks. It replaces
the learned routed value with the original incoming bit, constant zero,
constant one, or the complement of the routed value. The retained interface
predicts the changed outputs for every four-bit input pair and both incoming
values. Lean separately certifies exhaustive edge deletion.

This distinguishes intervention-sensitive composition from replaying the
ordinary addition table.

## Claim boundary

Established:

1. an intermediate interface can be selected without specifying its identity;
2. independent complete grammars recover one behavioural interface orbit;
3. the frozen interface compresses a hash-held-out family and uniquely crosses
   a sealed resource frontier against sham, raw-history and ablation controls;
4. the result compounds through three further verifier-selected promotions;
5. the learned composition predicts structural interventions;
6. a separate Lean checker certifies the frozen programs and eight-bit result.

Not established:

- transfer between unrelated natural or empirical domains;
- discovery of the protected task itself;
- representation learning from raw sensory observations;
- physical circuit improvement when promoted constructors are expanded;
- unrestricted or open-ended self-improvement.

Therefore this result closes the strongest synthetic alternatives to recursive
constructor genesis. It is not, by itself, the final experiment that removes
all empirical doubt. That still requires the same protocol on genuinely
source-distinct natural domains with independently generated observation
languages.
