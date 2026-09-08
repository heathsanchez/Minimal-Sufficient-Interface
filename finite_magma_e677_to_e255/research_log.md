# Research Log — G20 Pure G-CROSS Cube-and-Conquer

## 2026-09-07 — Machinery Repair: Incremental Solver + Timeout Attribution

### Context
- **Frontier:** `gcross_location_partition_verified` (program_frontier.json @ `d2ef1e3`):
  pure G-CROSS G20 reduces to 13 location cubes after verified UNSAT of
  sigma d=0,1 (z_0=10,11).
- **Encoder:** `e677_k5_block_tree_completion_sat.py` @ `b10ebd9`, SHA256
  `52c25039720f9401244294339e4ab8f2e1517640e010e9b0c2c1dcad8f7b4117` (matches
  published certificate).

### Frozen baseline (commit 12c056b)
- Glucose42 cold-start, 90s/cube: SAT=0, UNSAT=0, UNKNOWN=13.
- All UNKNOWN attributed to external `timeout 600` process kill (no solver-level
  status distinction).

### Diagnosis of Hermes over-claim
1. "Irreducible hard core" — NOT established. UNKNOWN ≠ obstruction.
2. "PySAT cannot share learned clauses" — INCORRECT. PySAT supports incremental
   `solve(assumptions=)` on a single Solver instance; learned clauses retained.
   `get_learnts()` API absence only blocks clause extraction, not incremental reuse.
3. "External process killed" conflated with "solver returned UNKNOWN."

### Repair (commit 0b93e2c)
New runner `_cube_conquer_incremental.py`:
- Single `Solver` instance across all cubes (PySAT incremental API).
- `solve_limited(expect_interrupt=True)` with `threading.Timer` interrupt.
- Timeout attribution: `{"decided", "timeout", "error"}` — distinguishes
  solver-limited UNKNOWN from process-killed.
- Warm phase: solve z_0=10,11 (known UNSAT, 0.0s) to seed lemma database.

### Improvement experiment result
- Warm: z_0=10,11 → UNSAT (0.0s each, lemmas retained).
- 13 cubes incremental: SAT=0, UNSAT=0, UNKNOWN=13.
- All UNKNOWN attributed to `timeout` (solver-limited, not process-killed).
- **No cube improved** vs frozen baseline. Lemma retention from verified UNSSAT
  cubes does not advance the G-CROSS cubes.

### Conclusion
The machinery repair succeeded: timeout attribution is reliable, incremental
solving works. But lemma sharing from sigma d=0,1 UNSAT proofs does not
advance the hard cubes. The cubes are genuinely computationally hard for
Glucose42 — not an artifact of cold-starting or external kills.

### Next step
Per AGENTS.md: do not escalate timeouts or invent invariants. The structural
question is whether a **global coupling/coordination argument** across the 13
cubes (or a stronger symmetry reduction of the 20-point shell) can replace
per-cell brute force. A weaker solver (longer budget) is not a mathematical
advance.

### Open questions
- Does a proof-producing solver (e.g., Kissat with proof traces) yield a
  structured UNSAT core for any cube that suggests a lemma?
- Is there a shared symmetry across the 13 cubes that a global quotient
  exploits?
