# Arithmetic Structural Development

This experiment moves MSI out of arbitrary finite maps into a familiar domain where a hidden compositional state is known to be necessary: positional addition.

The learner is **not** given a variable named `carry`, nor a two-state automaton, nor the transition table for addition.

It receives:

- decimal digit-pair inputs `(a,b)`;
- verified next output digits from the arithmetic environment;
- a family of possible one-step future digit-pair contexts;
- histories of at most two processed digit positions during discovery.

The starting interface identifies all histories.

## Stateless interface falsifier

A purely local interface is immediately wrong. The same next input `(0,0)` can require different verified outputs after different histories:

- after history `(0,0)`, the next output is `0`;
- after history `(5,5)`, the next output is `1`.

So current input alone is not a sufficient compositional interface.

## Residual-driven refinement

For histories `h`, define their observable future signature relative to retained contexts `B` by the verified next output under each `c in B`.

The learner begins with `B = ∅` and repeatedly finds two histories currently merged but separated by some protected future context. It then retains one concrete separator and recomputes the quotient.

Across all **10,101** decimal histories of length at most two, the process needs only **one** retained future context, `(0,0)`, and the resulting quotient has exactly **two** behavioural interface states.

The learner is not told what those two states mean. They are discovered extensionally as the minimal distinction needed to make future decimal behaviour compositional.

The recovered partition is exactly the partition induced by all **100** one-step decimal digit-pair continuations.

## Learned quotient dynamics

Using only the discovered quotient classes and verified traces, the experiment synthesizes:

- an output table for every learned interface state and every decimal digit-pair input;
- a next-interface-state transition table;
- a terminal-output table.

The learned quotient is checked for compositional sufficiency: every history in the same learned class must induce the same next output and the same next learned class under every digit pair.

This yields a deterministic two-state transducer without supplying the hidden state representation in advance.

## Length extrapolation

Discovery uses only histories of length at most two.

The learned machine is then frozen and evaluated outside that regime.

It computes exact addition for:

- all **1,000,000** ordered pairs of three-digit decimal numbers `0..999`;
- **204** deterministic forty-digit cases, including long propagation chains and varied pseudo-random inputs.

All tests pass exactly.

CI census:

```text
arithmetic structural development: discovery_histories=10101; protected_one_step_contexts=100; retained_separator_contexts=1; learned_interface_states=2; exhaustive_3digit_pairs=1000000; long_40digit_cases=204; retained=((0, 0),)
```

See [`tests/test_arithmetic_structural_development.py`](tests/test_arithmetic_structural_development.py).

## What this establishes

Within this scaffolded arithmetic setting:

\[
\boxed{
\text{verified compositional failure}
\to
\text{future separator}
\to
\text{new latent interface state}
\to
\text{quotient dynamics}
\to
\text{length-general exact computation}.
}
\]

The important point is not that the system rediscovers the human word "carry". It discovers the **behavioural equivalence classes that play that role** because histories that were previously merged have different verified futures.

That is a concrete instance of structural development:

\[
\boxed{
\text{failure determines what hidden state must become visible for composition to work.}
}
\]

## Boundary

This is not open-ended arithmetic discovery.

The experiment still supplies:

- decimal positional digit decomposition;
- least-significant-digit-first processing order;
- the primitive digit-pair input alphabet;
- trusted exact arithmetic verification;
- the family of one-step future contexts to search.

It does **not** yet discover positional notation, scan direction, the digit alphabet, or addition itself from raw observations.

The result is therefore best read as a first domain-level demonstration that MSI can recover a hidden compositional state representation from verified failures and then exploit that representation outside the discovery length regime.
