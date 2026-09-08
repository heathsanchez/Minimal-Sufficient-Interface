"""Bounded G20 13-cube case-split with per-cube Glucose42 timeout.

Reuses _cert_arity.py encoding (exact 15-way partition: z_0 in {5..9,12,13,14,15..19}).
Each cube gets 90s via solve_limited + interrupt (Glucose42 respects interrupts).
Writes _cube_results.json after each cube.  13 cubes max ~20min.
"""
import sys, time, json, threading
sys.path.insert(0, "tools")
import _cert_arity as C
from pysat.solvers import Solver

CUBES = [5,6,7,8,9,12,13,14,15,16,17,18,19]
LAYER = {v: "square" if v < 10 else ("sigma" if v < 15 else "kappa") for v in range(5, 20)}
base_extra = [C.z_good_clause(i) for i in range(5)]
PER_CUBE = 90

out = {}
for v in CUBES:
    t0 = time.time()
    with Solver(name="glucose42", bootstrap_with=C.clauses + base_extra, use_timer=True) as s:
        tmr = threading.Timer(PER_CUBE, s.interrupt)
        tmr.daemon = True
        tmr.start()
        try:
            r = s.solve_limited(assumptions=C.all_sel + [C.cell(10, 1, v)], expect_interrupt=True)
        finally:
            tmr.cancel()
        dt = time.time() - t0
    st = "UNSAT" if r is False else ("SAT" if r is True else "UNKNOWN")
    out[str(v)] = {"status": st, "time": round(dt, 1), "layer": LAYER[v]}
    print(f"cube z_0={v} ({LAYER[v]}): {st} ({dt:.1f}s)", flush=True)
    with open("_cube_results.json", "w") as f:
        json.dump({"solved": out, "remaining": True}, f, indent=2)

unknown = [v for v, r in out.items() if r["status"] == "UNKNOWN"]
unsat = [v for v, r in out.items() if r["status"] == "UNSAT"]
sat = [v for v, r in out.items() if r["status"] == "SAT"]
summary = {"solved": out, "sat": sat, "unsat": unsat, "unknown": unknown,
           "all_unsat": len(unknown) == 0 and len(sat) == 0}
with open("_cube_results.json", "w") as f:
    json.dump(summary, f, indent=2)
print(f"\n=== done: SAT={len(sat)} UNSAT={len(unsat)} UNKNOWN={len(unknown)} ===")
print(f"all_unsat={summary['all_unsat']}")
print("T6_GCROSS_CUBE_CONQUER_FINISHED", flush=True)
