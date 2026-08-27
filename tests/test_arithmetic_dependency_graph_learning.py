import heapq
import unittest


BASE = 10


def propose_order(width, edges):
    """Deterministic topological proposal, preferring larger positions first.

    This deliberately starts with the causally worst order and changes only when
    verifier counterexamples add precedence constraints.
    """
    succ = {i: set() for i in range(width)}
    indeg = [0] * width
    for a, b in edges:
        if b not in succ[a]:
            succ[a].add(b)
            indeg[b] += 1

    heap = [-i for i in range(width) if indeg[i] == 0]
    heapq.heapify(heap)
    out = []
    while heap:
        x = -heapq.heappop(heap)
        out.append(x)
        for y in succ[x]:
            indeg[y] -= 1
            if indeg[y] == 0:
                heapq.heappush(heap, -y)
    if len(out) != width:
        raise AssertionError("learned precedence relation became cyclic")
    return tuple(out)


def value_lsd(digits):
    return sum(d * (BASE ** i) for i, d in enumerate(digits))


def output_digit(a_digits, b_digits, pos):
    return ((value_lsd(a_digits) + value_lsd(b_digits)) // (BASE ** pos)) % BASE


def structural_counterexample(order):
    """Return a concrete causal residual and a justified precedence edge.

    If position `pos` is proposed before its immediate lower neighbour `pos-1`,
    two additions can share every visible input in the proposed prefix yet require
    different output at `pos`: an unseen carry is triggered at `pos-1`.
    """
    seen = set()
    width = len(order)
    for step, pos in enumerate(order):
        if pos > 0 and (pos - 1) not in seen:
            trigger = pos - 1
            a0 = [0] * width
            b0 = [0] * width
            a1 = [0] * width
            b1 = [0] * width
            a0[trigger] = a1[trigger] = 9
            b1[trigger] = 1

            prefix0 = tuple((a0[j], b0[j]) for j in order[: step + 1])
            prefix1 = tuple((a1[j], b1[j]) for j in order[: step + 1])
            assert prefix0 == prefix1
            y0 = output_digit(a0, b0, pos)
            y1 = output_digit(a1, b1, pos)
            assert y0 != y1
            return {
                "edge": (trigger, pos),
                "step": step,
                "position": pos,
                "visible_prefix": prefix0,
                "output_a": y0,
                "output_b": y1,
            }
        seen.add(pos)
    return None


def learn_order(width):
    edges = set()
    trace = []
    while True:
        order = propose_order(width, edges)
        residual = structural_counterexample(order)
        if residual is None:
            return order, frozenset(edges), tuple(trace)
        edge = residual["edge"]
        if edge in edges:
            raise AssertionError("verifier returned an already-retained structural constraint")
        edges.add(edge)
        trace.append((order, residual))


class ArithmeticDependencyGraphLearning(unittest.TestCase):
    def test_counterexamples_build_causal_structure_without_factorial_search(self):
        census = {}
        for width in (2, 3, 10, 32, 128):
            order, edges, trace = learn_order(width)
            self.assertEqual(order, tuple(range(width)))
            self.assertEqual(edges, frozenset((i, i + 1) for i in range(width - 1)))
            self.assertEqual(len(trace), width - 1)
            self.assertIsNone(structural_counterexample(order))
            census[width] = {
                "counterexamples": len(trace),
                "learned_edges": len(edges),
                "final_prefix": order[: min(width, 8)],
            }

        print(f"arithmetic dependency-graph learning: {census}")


if __name__ == "__main__":
    unittest.main()
