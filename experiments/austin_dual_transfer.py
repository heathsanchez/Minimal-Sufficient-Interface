"""Transfer test: E5295 must arise from E40909 by pure syntactic duality.

No E5295-specific constructor is supplied.  We reverse every binary node of
E40909, check that the result is exactly E5295, then feed the dual law through
the same coordinate-preserving promotion compiler.
"""

from experiments.austin_promotion_compiler import O, V, Op, Term, discover_promotions, law40909, render_promotion


def dual(t: Term) -> Term:
    if isinstance(t, Op):
        return O(dual(t.right), dual(t.left))
    return t


def law5295():
    x, y, z = V("x"), V("y"), V("z")
    lhs = O(y, O(z, O(y, O(y, O(x, y)))))
    return lhs, x, frozenset({"x", "y", "z"})


def transferred_law5295():
    lhs, rhs, variables = law40909()
    return dual(lhs), dual(rhs), variables


def compile_e5295():
    A, p, q = V("A"), V("p"), V("q")
    lhs, rhs, variables = transferred_law5295()
    return discover_promotions(lhs, rhs, variables, O(A, p), q)


if __name__ == "__main__":
    direct = law5295()
    transferred = transferred_law5295()
    assert direct == transferred
    ps = compile_e5295()
    assert len(ps) == 1
    print("E40909 dual = E5295")
    print("E5295 promotion:", render_promotion(ps[0]))
