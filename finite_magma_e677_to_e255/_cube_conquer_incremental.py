"""Incremental cube-and-conquer: single Solver instance, learned clauses retained.

Repair over _cube_conquer_bounded.py:
1. Single Solver instance across all cubes (PySAT incremental solve(assumptions=))
2. Interrupt properly cleared before each reuse (no stale signal handling)
3. Timeout attribution: solver-limited UNKNOWN vs external kill
4. Reuse UNSAT proof lemmas from easy cubes (z_0=10,11) to warm hard cubes

Tests whether incremental lemma retention advances cube z_0=5 (previously UNKNOWN
with cold-started solver).
"""
import sys, time, threading, json
sys.path.insert(0, "tools")
import _cert_arity as C
from pysat.solvers import Solver

base_extra = [C.z_good_clause(i) for i in range(5)]
clauses = C.clauses + base_extra
all_sel = C.all_sel

CUBES = [5, 6, 7, 8, 9, 12, 13, 14, 15, 16, 17, 18, 19]
LAYER = {v: "square" if v < 10 else ("sigma" if v < 15 else "kappa") for v in range(5, 20)}
PER_CUBE = 90

def solve_incremental(s, assumptions, seconds):
    """Solve with timer-based interrupt. Returns (status, dt, reason).

    reason: 'decided' (r in False/True), 'timeout' (timer fired), 'error'
    (exception with no timer fire), 'unknown' (solver returned None, no timer).
    """
    t0 = time.time()
    timer_fired = [False]

    def do_interrupt():
        timer_fired[0] = True
        s.interrupt()

    tmr = threading.Timer(seconds, do_interrupt)
    tmr.daemon = True
    tmr.start()
    try:
        r = s.solve_limited(assumptions=assumptions, expect_interrupt=True)
        if timer_fired[0]:
            reason = "timeout"
        else:
            reason = "unknown"
    except Exception as exc:
        if timer_fired[0]:
            reason = "timeout"
        else:
            reason = "error"
        r = None
    finally:
        tmr.cancel()
        if hasattr(s, "clear_interrupt"):
            s.clear_interrupt()
    dt = time.time() - t0
    if r is False:
        return "UNSAT", round(dt, 1), "decided"
    if r is True:
        return "SAT", round(dt, 1), "decided"
    return "UNKNOWN", round(dt, 1), reason

# Direct partition exclusion verification (NOT k-arity inference):
# z_0=10,11 (sigma d=0,1) must be UNSAT under the full E677 encoding.
print("=== partition exclusion verification (z_0=10,11 = sigma d=0,1) ===", flush=True)
exclusions = {}
for v in [10, 11]:
    t0 = time.time()
    with Solver(name="glucose42", bootstrap_with=clauses) as s_ex:
        r_ex = s_ex.solve(assumptions=all_sel + [C.cell(10, 1, v)])
        dt_ex = time.time() - t0
    st_ex = "UNSAT" if r_ex is False else ("SAT" if r_ex is True else "UNKNOWN")
    exclusions[str(v)] = {"status": st_ex, "time": round(dt_ex, 1), "sigma_d": v - 10}
    print(f"  exclusion z_0={v} (sigma d={v-10}): {st_ex} ({dt_ex:.1f}s)", flush=True)

# Single solver instance — retains learned clauses across cubes
s = Solver(name="glucose42", bootstrap_with=clauses, use_timer=True)
out = {}

# Warm: solve the easy UNSAT cubes first (z_0=10,11 = sigma d=0,1)
# to populate the clause database with G-CROSS proof lemmas
print("=== warming with verified UNSAT cubes (z_0=10,11) ===", flush=True)
for v in [10, 11]:
    st, dt, reason = solve_incremental(s, all_sel + [C.cell(10, 1, v)], 30)
    print(f"  warm z_0={v} (sigma d={v-10}): {st} ({dt:.1f}s, {reason})", flush=True)

# Now solve the 13 hard cubes incrementally (learned lemmas retained)
print("=== solving 13 cubes incrementally (lemma-shared) ===", flush=True)
for v in CUBES:
    st, dt, reason = solve_incremental(s, all_sel + [C.cell(10, 1, v)], PER_CUBE)
    out[str(v)] = {"status": st, "time": dt, "layer": LAYER[v], "reason": reason}
    print(f"cube z_0={v} ({LAYER[v]}): {st} ({dt:.1f}s, {reason})", flush=True)
    with open("_cube_results_incremental.json", "w") as f:
        json.dump({"solved": out, "method": "incremental-glucose42-learned-retained",
                   "exclusions": exclusions, "remaining": True}, f, indent=2)

s.delete()

# Compare against frozen baseline (REQUIRED — do NOT invent baseline results)
baseline_path = "finite_magma_e677_to_e255/_cube_results.json"
try:
    with open(baseline_path) as f:
        baseline = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError(
        f"Baseline {baseline_path} required for comparison; refusing to invent."
    )

improved = []
for v in CUBES:
    bv = baseline["solved"][str(v)]
    nv = out[str(v)]
    if bv["status"] == "UNKNOWN" and nv["status"] in ("SAT", "UNSAT"):
        improved.append(v)
        print(f"  IMPROVED cube z_0={v}: baseline={bv['status']} -> incremental={nv['status']} ({nv['time']:.1f}s)", flush=True)

summary = {
    "method": "incremental-glucose42-learned-retained",
    "frozen_baseline": "Glucose42 cold-start, 90s/cube, 13 UNKNOWN",
    "exclusions_verified": exclusions,
    "solved": out,
    "improved": improved,
    "sat": [v for v, r in out.items() if r["status"] == "SAT"],
    "unsat": [v for v, r in out.items() if r["status"] == "UNSAT"],
    "unknown": [v for v, r in out.items() if r["status"] == "UNKNOWN"],
    "timeout_attribution": {v: r["reason"] for v, r in out.items()},
}
with open("_cube_results_incremental.json", "w") as f:
    json.dump(summary, f, indent=2)
print(f"\n=== done: SAT={len(summary['sat'])} UNSAT={len(summary['unsat'])} UNKNOWN={len(summary['unknown'])} ===", flush=True)
print(f"improved cubes: {improved}", flush=True)
print("T6_GCROSS_INCREMENTAL_FINISHED", flush=True)
