import itertools
import math
import unittest


BASE = 10


def output_digit(a_digits, b_digits, pos):
    a = sum(d * (BASE ** i) for i, d in enumerate(a_digits))
    b = sum(d * (BASE ** i) for i, d in enumerate(b_digits))
    return ((a + b) // (BASE ** pos)) % BASE


def causal_counterexample(order):
    """Return a verified conflict for any order violating low-to-high dependency.

    Positions are indexed by significance: 0 is the least significant digit.
    A conflict consists of two full additions whose input streams are identical
    up to some emitted position but whose required output at that position differs.
    """
    width = len(order)
    seen = set()
    for step, pos in enumerate(order):
        lower_unseen = [k for k in range(pos) if k not in seen]
        if lower_unseen:
            k = min(lower_unseen)
            a0 = [0] * width
            b0 = [0] * width
            a1 = [0] * width
            b1 = [0] * width

            # At the unseen trigger position, one world has sum 9 and the other
            # sum 10. Every position above it through `pos-1` has sum 9, so the
            # carry difference propagates exactly to the prematurely emitted pos.
            for j in range(k, pos):
                a0[j] = a1[j] = 9
                b0[j] = b1[j] = 0
            b1[k] = 1

            # The two examples agree on every input symbol exposed so far.
            prefix0 = tuple((a0[j], b0[j]) for j in order[: step + 1])
            prefix1 = tuple((a1[j], b1[j]) for j in order[: step + 1])
            assert prefix0 == prefix1

            y0 = output_digit(a0, b0, pos)
            y1 = output_digit(a1, b1, pos)
            assert y0 != y1
            return {
                "step": step,
                "position": pos,
                "unseen_trigger": k,
                "prefix": prefix0,
                "output_a": y0,
                "output_b": y1,
                "a_digits_a": tuple(a0),
                "b_digits_a": tuple(b0),
                "a_digits_b": tuple(a1),
                "b_digits_b": tuple(b1),
            }
        seen.add(pos)
    return None


class ArithmeticOrderGenesis(unittest.TestCase):
    def test_counterexamples_recover_unique_causal_order_without_direction_labels(self):
        # Do not offer the learner named "left" and "right" directions. Generate
        # every possible position order and let verified causal conflicts eliminate
        # orders that expose a digit before all lower-significance causes are known.
        census = {}
        for width in range(2, 8):
            survivors = []
            rejected = 0
            example = None
            for order in itertools.permutations(range(width)):
                witness = causal_counterexample(order)
                if witness is None:
                    survivors.append(order)
                else:
                    rejected += 1
                    example = example or (order, witness)

            self.assertEqual(survivors, [tuple(range(width))])
            self.assertEqual(rejected, math.factorial(width) - 1)
            census[width] = {
                "candidates": math.factorial(width),
                "rejected": rejected,
                "survivor": survivors[0],
                "example": example,
            }

        print(f"arithmetic order genesis census: {census}")

    def test_surviving_order_is_prefix_causal_by_dependency(self):
        for width in range(2, 12):
            self.assertIsNone(causal_counterexample(tuple(range(width))))


if __name__ == "__main__":
    unittest.main()
