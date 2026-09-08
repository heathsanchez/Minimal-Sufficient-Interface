import unittest

from experiments.austin_promotion_compiler import compile_named, render_promotion


class AustinPromotionCompilerTests(unittest.TestCase):
    def test_e40909_discovers_recursive_branch(self):
        promotions = compile_named("E40909")
        rendered = {render_promotion(p) for p in promotions}
        self.assertEqual(
            rendered,
            {"(((((q⋄A)⋄A)⋄z)⋄A)) = p"}.difference({"impossible"})
            if False else {"((((q⋄A)⋄A)⋄z)⋄A) = p"},
        )

    def test_e11116_discovers_recursive_branch(self):
        promotions = compile_named("E11116")
        rendered = {render_promotion(p) for p in promotions}
        self.assertEqual(rendered, {"(y⋄((p⋄q)⋄(y⋄y))) = p"})

    def test_each_case_has_unique_generic_attachment(self):
        self.assertEqual(len(compile_named("E40909")), 1)
        self.assertEqual(len(compile_named("E11116")), 1)


if __name__ == "__main__":
    unittest.main()
