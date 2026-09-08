"""Improvement test: Glucose42 (frozen baseline) vs CaDiCaL195 (different search heuristic) on cube z_0=5.

Search-procedure change only: CaDiCaL195 uses VSIDS + different
restart/phase heuristics vs Glucose42. Same encoding, same 90s budget,
same formula. No timeout increases, no new invariants, no encoding changes.

Also diagnoses PySAT lemma-sharing feasibility (get_learnts API availability).
"""
import sys, time, signal, json
sys.path.insert(0, "tools")
import _cert_arity as C
from pysat.solvers import Solver

base_extra = [C.z_good_clause(i) for i in range(5)]
clauses = C.clauses + base_extra
cube_assump = C.cell(10, 1, 5)
all_sel = C.all_sel

class TimeoutErr(Exception): pass
def _h(s, f): raise TimeoutErr()

def solve_timeout(name, clauses, assumptions, seconds):
    t0 = time.time()
    with Solver(name=name, bootstrap_with=clauses) as s:
        old = signal.signal(signal.SIGALRM, _h)
        signal.setitimer(signal.ITIMER_REAL, seconds)
        try:
            r = s.solve(assumptions=assumptions)
        except TimeoutErr:
            r = None
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)
        dt = time.time() - t0
    st = "UNSAT" if r is False else ("SAT" if r is True else "UNKNOWN")
    return st, round(dt, 1), r

# FROZEN BASELINE (matches committed cube_z_0=5: Glucose42, 90s, UNKNOWN)
st1, dt1, r1 = solve_timeout("glucose42", clauses, all_sel + [cube_assump], 90)
print(f"BASELINE cube z_0=5 (Glucose42, 90s): {st1} ({dt1:.1f}s)", flush=True)

# IMPROVEMENT: CaDiCaL195 (different search heuristic), same 90s budget
st2, dt2, r2 = solve_timeout("cadical195", clauses, all_sel + [cube_assump], 90)
print(f"CaDiCaL195 cube z_0=5 (90s): {st2} ({dt2:.1f}s)", flush=True)

# Lemma-sharing feasibility check
lemma_feasible = hasattr(Solver(name="glucose42", bootstrap_with=[]), "get_learnts")
s_test = Solver(name="glucose42", bootstrap_with=[[1]])
print(f"PySAT get_learnts available: {lemma_feasible}", flush=True)
s_test.delete()

result = {
    "cube": 5,
    "frozen_baseline": {"solver": "glucose42", "status": st1, "time": dt1},
    "improvement": {"solver": "cadical195", "status": st2, "time": dt2},
    "improved": st2 in ("SAT", "UNSAT") and st1 == "UNKNOWN",
    "lemma_sharing_feasible": lemma_feasible,
}
with open("_inc_improvement_result.json", "w") as f:
    json.dump(result, f, indent=2)
print(f"Improved: {result['improved']}", flush=True)
