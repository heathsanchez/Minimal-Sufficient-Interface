# Final compressed kernel

The extensional refinement dynamics do not require a distinguished top element if the initial interface state is supplied externally.

The algebraic core is an idempotent commutative semigroup (equivalently, a meet-semilattice without requiring a named top):

\[
(L,\wedge)
\]

with update

\[
\boxed{E_{t+1}=E_t\wedge K_t.}
\]

The required laws are

\[
a\wedge a=a,\qquad a\wedge b=b\wedge a,\qquad (a\wedge b)\wedge c=a\wedge(b\wedge c).
\]

They correspond exactly to three operational invariances:

- idempotence: repeating the same verified constraint changes nothing;
- commutativity: order of accumulated verified constraints does not matter;
- associativity: grouping/batching accumulated constraints does not matter.

The induced refinement order is

\[
a\le b\iff a\wedge b=a.
\]

Then every update satisfies

\[
E_{t+1}\le E_t.
\]

If `L` is finite and every accepted update is strict whenever the current state is not yet sufficient, repeated updates terminate.

A distinguished top `⊤` is needed only if we want a canonical uninformed initial state or a canonical empty meet:

\[
\bigwedge\varnothing=\top.
\]

Thus there are two exact versions of the kernel:

1. **Supplied initial state:** `(L, ∧)` — an idempotent commutative semigroup / meet-semilattice.
2. **Canonical uninformed state:** `(L, ∧, ⊤)` — a meet-semilattice with top.

The state-identification realization remains `Eq(X)` under intersection. The abstract algebra captures only extensional refinement dynamics; semantics, provenance, accessibility, cost, separator witnesses, and capability generation live above it.
