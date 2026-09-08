import unittest

from experiments.austin_dual_transfer import compile_e5295, law5295, transferred_law5295
from experiments.austin_promotion_compiler import render_promotion


class AustinDualTransferTests(unittest.TestCase):
    def test_e40909_dual_is_exactly_e5295(self):
        self.assertEqual(transferred_law5295(), law5295())

    def test_same_compiler_discovers_e5295_promotion(self):
        ps = compile_e5295()
        self.assertEqual(len(ps), 1)
        self.assertEqual(render_promotion(ps[0]), "(p⋄(z⋄(p⋄(p⋄q)))) = A")


if __name__ == "__main__":
    unittest.main()
