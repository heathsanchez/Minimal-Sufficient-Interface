# Constructor realization qualification

Scope: a declared finite constructor algebra and a frozen swap residual. This does not establish unrestricted representation-language genesis.

The Python qualification exercises ten small cases: symmetry, position, composition, constant, predicate, resolution, search operator, ambiguity, impossibility, and transfer/ablation. Search is bounded by AST size and finite observation semantics. Empty bounded search means bounded exhaustion, not impossibility. The resolution test uses an already supplied resolution constructor.

The Lean file independently checks generation from raw primitives, adequacy, a global AST-size lower bound for the declared Boolean grammar, ambiguity, transfer, and an unbounded-depth impossibility theorem for the specified equality-only grammar. It does not claim every symmetry-breaking relation must be an ordering, or that arbitrary substrates can generate missing primitives.

Run `python tests/ccc_realization_qualification.py` and `LEAN_PATH=lean lean lean/LemmaSynthesis/ConstructorRealization.lean` from the repository root. CI is the external Lean check.
