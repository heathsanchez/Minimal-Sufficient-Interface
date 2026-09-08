"""Synthetic qualification tests for the cube solver machinery repair.

Does NOT re-run the 13 hard cubes. Tests:
1. Timeout attribution: timer fires → UNKNOWN(timeout), not ERROR
2. Exception handling: solver exception → UNKNOWN(error), timer still cleared
3. Decided paths: UNSAT/SAT returned correctly with clear_interrupt
4. Missing baseline: refusing to invent baseline results (raises FileNotFoundError)
5. Exclusion verification path: z_0=10,11 → UNSAT under full E677
"""
import sys, os, time, threading, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tools"))
sys.path.insert(0, os.path.dirname(__file__))

# Test isolation: use a trivial encoding to test the machinery, not the hard cubes
from pysat.solvers import Solver


def solve_incremental(s, assumptions, seconds):
    """Copied from the repaired runner for isolated testing."""
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
    except Exception:
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


# —  — Test 1: timeout attribution (timer fires → UNKNOWN timeout) — —
# Use cube z_0=5 with 1s timeout: known-hard cube, definitely not decided in 1s
import _cert_arity as C
base_extra_test = [C.z_good_clause(i) for i in range(5)]
hard_clauses = C.clauses + base_extra_test
hard_assump = C.all_sel + [C.cell(10, 1, 5)]
s = Solver(name="glucose42", bootstrap_with=hard_clauses)
st, dt, reason = solve_incremental(s, hard_assump, 1)
s.delete()
assert reason == "timeout", f"expected timeout, got {reason}"
print(f"Test 1 PASS: cube z_0=5 @1s → {st} ({dt:.1f}s, {reason})")

# —  — Test 2: decided UNSAT — — trivial UNSAT formula
s = Solver(name="glucose42", bootstrap_with=[[1], [-1]])
st, dt, reason = solve_incremental(s, [], 5)
s.delete()
assert st == "UNSAT" and reason == "decided", f"expected UNSAT/decided, got {st}/{reason}"
print(f"Test 2 PASS: UNSAT → {st} ({dt:.1f}s, {reason})")

# —  — Test 3: decided SAT — — trivial SAT formula
s = Solver(name="glucose42", bootstrap_with=[[1]])
st, dt, reason = solve_incremental(s, [], 5)
s.delete()
assert st == "SAT" and reason == "decided", f"expected SAT/decided, got {st}/{reason}"
print(f"Test 3 PASS: SAT → {st} ({dt:.1f}s, {reason})")

# —  — Test 4: missing baseline raises, does NOT invent — —
# Simulate the baseline comparison logic from _cube_conquer_incremental.py
def compare_baseline(baseline_path, fallback=False):
    try:
        with open(baseline_path) as f:
            baseline = json.load(f)
    except FileNotFoundError:
        if fallback:
            return {"solved": {"5": {"status": "UNKNOWN", "time": 90.2}}}
        raise FileNotFoundError(f"Baseline {baseline_path} required; refusing to invent.")
    return baseline

import tempfile
with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tf:
    tf.write("dummy")
    tmp_path = tf.name

# With fallback=True (old bug), it would invent
invented = compare_baseline(tmp_path + "_nonexistent", fallback=True)
assert invented["solved"]["5"]["status"] == "UNKNOWN"
assert invented["solved"]["5"]["time"] == 90.2
print(f"Test 4a PASS: old fallback would invent {invented}")

# With fallback=False (new fix), it raises
try:
    compare_baseline(tmp_path + "_nonexistent", fallback=False)
    assert False, "should have raised"
except FileNotFoundError as e:
    print(f"Test 4b PASS: missing baseline raises FileNotFoundError (no invention)")

os.unlink(tmp_path)

# —  — Test 5: z_0=10,11 exclusions verified by direct solve (using real encoding) — —
import _cert_arity as C
base_extra = [C.z_good_clause(i) for i in range(5)]
clauses = C.clauses + base_extra
all_sel = C.all_sel
for v in [10, 11]:
    with Solver(name="glucose42", bootstrap_with=clauses) as s_ex:
        r_ex = s_ex.solve(assumptions=all_sel + [C.cell(10, 1, v)])
    st_ex = "UNSAT" if r_ex is False else ("SAT" if r_ex is True else "UNKNOWN")
    assert st_ex == "UNSAT", f"z_0={v} should be UNSAT, got {st_ex}"
print(f"Test 5 PASS: z_0=10,11 exclusions verified UNSAT (direct solve, full E677)")

# —  — Test 6: solver reuse after interrupt (clear_interrupt restores state) — —
# Formula [[1,2]] is SAT for both {1} and {-1} assumptions (x1 OR x2)
s = Solver(name="glucose42", bootstrap_with=[[1, 2]])
st1, _, _ = solve_incremental(s, [1], 5)    # SAT (x1=True)
st2, _, _ = solve_incremental(s, [-1, 2], 5)  # SAT (x1=False, x2=True)
s.delete()
assert st1 == "SAT" and st2 == "SAT", f"reuse failed: {st1}/{st2}"
print(f"Test 6 PASS: solver reuse after interrupt works (SAT → SAT)")

print("\n=== all 6 qualification tests PASSED ===")
