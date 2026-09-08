# G20 Cube-and-Conquer Provenance

## Source recovery
The finite-domain encoder `e677_k5_block_tree_completion_sat.py` was recovered
from the upstream repo `Grisha-Pochuev/finite-magma-e677-to-e255`.

- **Committed encoder** at upstream commit `b10ebd9` (and `223c4e5`):
  SHA256 `52c25039720f9401244294339e4ab8f2e1517640e010e9b0c2c1dcad8f7b4117`
  — matches the published certificate
  `e677_zero_root_reuse_computational_certificate.md`.
- The working-tree copy at upstream `223c4e5` has SHA256 `c67c45f9...` (modified
  from the certificate version). The **certificate version was restored** for
  this work; no encoding was reconstructed from memory.

## Formula
The committed encoder builds the G20 four-layer shell:
- 5 Bad K5 orbit points (z-Bad), 3 Good layers of 5 points each (z-Good).
- Equivariant shift constraints (`--equivariant-four-layer`).
- Full E677 pair equation on all applicable triples.
- Terminal K5 base shell (`--terminal-k5 --blocks 1 --extra 15`).
- 24,400 variables, 679,780 clauses.

Controls reproduced from the certificate:
- order-15 base shell (`--skip-e677`): SAT VERIFIED, 0.175s
- order-15 full E677 (k=0 all-ZIPPER): UNSAT, 0.43s
- k=0/1/2 G-CROSS arity (_cert_arity.py): all UNSAT

## Cube-and-conquer partition
The 15-way exact location partition
(`gcross_location_partition_verified`, program_frontier.json @ `d2ef1e3`):
- z_0 = 5 Bad points (all-ZIPPER): verified UNSAT (0.0s each)
- z_0 = 10, 11 (sigma d=0, 1): verified UNSAT (_cert_arity.py k-arity)
- **13 surviving Good-location cubes**: square{5,6,7,8,9},
  sigma d=2,3,4 {12,13,14}, kappa{15,16,17,18,19}

Cube assumption: `C.all_sel + [C.cell(10, 1, v)]` — fixes z_0=v at row 10,
column 1, forcing that Good location's first-row z-value to v.

## Timeout handling
- **Frozen baseline** (`_cube_conquer_bounded.py`): Glucose42, 90s/cube,
  fresh Solver per cube. Result: SAT=0, UNSAT=0, UNKNOWN=13.
- **Improved runner** (`_cube_conquer_incremental.py`): single Solver instance
  with incremental `solve(assumptions=)`, `solve_limited` + Timer interrupt,
  timeout attribution (`decided`/`timeout`/`error`). Warm with z_0=10,11
  UNSAT proofs. Result: SAT=0, UNSAT=0, UNKNOWN=13 — no improvement.

## Results
- `_cube_results.json`: frozen baseline (13 UNKNOWN at ~90.2s each)
- `_cube_results_incremental.json`: incremental runner (13 UNKNOWN at ~90.1s,
  all `timeout` attribution — solver-limited, not process-killed)
- `_inc_improvement_result.json`: solver-swap test (Glucose42 vs CaDiCaL195 on
  z_0=5, both UNKNOWN)

## Provenance gap
Commits `12c056b`, `ce9afdb`, `0b93e2c`, `7825ca7` exist on the local clone
at `/home/node/finite-magma-e677-to-e255` but **cannot be pushed** to upstream
(`Grisha-Pochuev/finite-magma-e677-to-e255`) — 403 permission denied. The
materials are mirrored here for inspection.
