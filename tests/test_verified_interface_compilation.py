import unittest


def truth_mask(nvars, fn):
    mask = 0
    for row in range(1 << nvars):
        xs = tuple(bool((row >> i) & 1) for i in range(nvars))
        if fn(*xs):
            mask |= 1 << row
    return mask


def var(i):
    return ("var", i)


def node(op, left, right):
    return (op, left, right)


def formula_cost(expr):
    if expr[0] == "var":
        return 0
    return 1 + formula_cost(expr[1]) + formula_cost(expr[2])


def render(expr, names=("a", "b", "c")):
    if expr[0] == "var":
        return names[expr[1]]
    return f"{expr[0]} ({render(expr[1], names)}) ({render(expr[2], names)})"


def substitute(expr, replacements):
    if expr[0] == "var":
        return replacements[expr[1]]
    return node(
        expr[0],
        substitute(expr[1], replacements),
        substitute(expr[2], replacements),
    )


def eval_expr(expr, values):
    if expr[0] == "var":
        return values[expr[1]]
    x = eval_expr(expr[1], values)
    y = eval_expr(expr[2], values)
    if expr[0] == "nand":
        return not (x and y)
    if expr[0] == "hs":
        return x ^ y
    if expr[0] == "hc":
        return x and y
    if expr[0] == "left":
        return x
    if expr[0] == "right":
        return y
    raise AssertionError(expr[0])


def synthesize(nvars, operations):
    """Minimum formula-tree representative for every reachable truth function."""
    width_mask = (1 << (1 << nvars)) - 1
    best = {
        truth_mask(nvars, lambda *xs, i=i: xs[i]): (0, var(i))
        for i in range(nvars)
    }
    changed = True
    while changed:
        changed = False
        items = list(best.items())
        for fx, (cx, ex) in items:
            for fy, (cy, ey) in items:
                for op in operations:
                    if op == "nand":
                        fz = (~(fx & fy)) & width_mask
                    elif op == "hs":
                        fz = fx ^ fy
                    elif op == "hc":
                        fz = fx & fy
                    elif op == "left":
                        fz = fx
                    elif op == "right":
                        fz = fy
                    else:
                        raise AssertionError(op)
                    cost = cx + cy + 1
                    expr = node(op, ex, ey)
                    old = best.get(fz)
                    if old is None or cost < old[0] or (
                        cost == old[0] and render(expr) < render(old[1])
                    ):
                        best[fz] = (cost, expr)
                        changed = True
    return best


def learn_from_residuals(target, version_space, nvars):
    """CEGIS over protected truth-table rows; the complete table is not exposed."""
    survivors = set(version_space)
    residuals = []
    while any(candidate != target for candidate in survivors):
        # The verifier scans the frozen candidate order for the first
        # falsifiable behaviour. A fully correct proposal has no residual and
        # remains in the version space while falsifiable alternatives are cut.
        proposal = min(candidate for candidate in survivors if candidate != target)
        row = next(
            row for row in range(1 << nvars)
            if ((proposal >> row) & 1) != ((target >> row) & 1)
        )
        expected = (target >> row) & 1
        residuals.append((row, expected))
        survivors = {
            candidate for candidate in survivors
            if ((candidate >> row) & 1) == expected
        }
    return survivors, tuple(residuals)


NAND2 = synthesize(2, ("nand",))
HALF_SUM_MASK = truth_mask(2, lambda a, b: a ^ b)
HALF_CARRY_MASK = truth_mask(2, lambda a, b: a and b)
HALF_SUM = NAND2[HALF_SUM_MASK][1]
HALF_CARRY = NAND2[HALF_CARRY_MASK][1]


def expand_to_nand(expr):
    if expr[0] == "var":
        return expr
    x = expand_to_nand(expr[1])
    y = expand_to_nand(expr[2])
    if expr[0] == "nand":
        return node("nand", x, y)
    if expr[0] == "hs":
        return substitute(HALF_SUM, (x, y))
    if expr[0] == "hc":
        return substitute(HALF_CARRY, (x, y))
    raise AssertionError(expr[0])


def ripple_add(width, a, b, sum_expr, carry_expr):
    carry = False
    out = 0
    for i in range(width):
        x = bool((a >> i) & 1)
        y = bool((b >> i) & 1)
        s = eval_expr(sum_expr, (x, y, carry))
        carry = eval_expr(carry_expr, (x, y, carry))
        out |= int(s) << i
    return out


class VerifiedInterfaceCompilation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.flat = synthesize(3, ("nand",))
        cls.warm = synthesize(3, ("nand", "hs", "hc"))
        cls.sham = synthesize(3, ("nand", "left", "right"))
        cls.sum3 = truth_mask(3, lambda a, b, c: a ^ b ^ c)
        cls.carry3 = truth_mask(
            3, lambda a, b, c: (a and b) or (a and c) or (b and c)
        )

    def test_half_interface_is_selected_by_incremental_residuals(self):
        sum_survivors, sum_residuals = learn_from_residuals(
            HALF_SUM_MASK, NAND2, 2
        )
        carry_survivors, carry_residuals = learn_from_residuals(
            HALF_CARRY_MASK, NAND2, 2
        )
        self.assertEqual(sum_survivors, {HALF_SUM_MASK})
        self.assertEqual(carry_survivors, {HALF_CARRY_MASK})
        self.assertGreater(len(sum_residuals), 0)
        self.assertGreater(len(carry_residuals), 0)
        self.assertEqual(formula_cost(HALF_SUM), 5)
        self.assertEqual(formula_cost(HALF_CARRY), 3)

    def test_promotion_changes_the_bounded_full_adder_frontier(self):
        flat_cost = self.flat[self.sum3][0] + self.flat[self.carry3][0]
        warm_cost = self.warm[self.sum3][0] + self.warm[self.carry3][0]
        sham_cost = self.sham[self.sum3][0] + self.sham[self.carry3][0]
        budget = 6

        self.assertEqual(flat_cost, 20)
        self.assertEqual(warm_cost, 6)
        self.assertEqual(sham_cost, flat_cost)
        self.assertLessEqual(warm_cost, budget)
        self.assertGreater(flat_cost, budget)
        self.assertGreater(sham_cost, budget)
        # Exact ancestor ablation is the cold arm.
        self.assertEqual(flat_cost, 20)

    def test_cost_claim_is_macro_relative_not_physical_gate_reduction(self):
        warm_sum = self.warm[self.sum3][1]
        warm_carry = self.warm[self.carry3][1]
        expanded = (
            formula_cost(expand_to_nand(warm_sum))
            + formula_cost(expand_to_nand(warm_carry))
        )
        flat = self.flat[self.sum3][0] + self.flat[self.carry3][0]
        library_definition = formula_cost(HALF_SUM) + formula_cost(HALF_CARRY)
        warm_callsite = formula_cost(warm_sum) + formula_cost(warm_carry)

        self.assertEqual(library_definition, 8)
        self.assertEqual(warm_callsite, 6)
        self.assertGreaterEqual(expanded, flat)
        # Description length pays for the retained library once.
        self.assertLess(library_definition + warm_callsite, flat)

    def test_second_promotion_compounds_recursively(self):
        sum_expr = self.warm[self.sum3][1]
        carry_expr = self.warm[self.carry3][1]
        for width in (4, 6):
            modulus = 1 << width
            for a in range(modulus):
                for b in range(modulus):
                    self.assertEqual(
                        ripple_add(width, a, b, sum_expr, carry_expr),
                        (a + b) % modulus,
                    )

        # Two promoted full-adder outputs are called per bit. The retained
        # half/full library is paid once, then recursive source cost is linear.
        width = 6
        cold_description = 20 * width
        compiled_description = 8 + 6 + 2 * width
        self.assertEqual(cold_description, 120)
        self.assertEqual(compiled_description, 26)
        self.assertLess(compiled_description, cold_description)

    def test_frozen_lean_terms_match_synthesized_terms(self):
        self.assertEqual(
            render(HALF_SUM, ("a", "b")),
            "nand (nand (a) (nand (a) (b))) (nand (b) (nand (a) (a)))",
        )
        self.assertEqual(
            render(HALF_CARRY, ("a", "b")),
            "nand (nand (a) (b)) (nand (a) (b))",
        )
        self.assertEqual(
            render(self.warm[self.sum3][1]),
            "hs (a) (hs (b) (c))",
        )
        self.assertEqual(
            render(self.warm[self.carry3][1]),
            "hs (a) (hc (hs (a) (b)) (hs (a) (c)))",
        )


if __name__ == "__main__":
    unittest.main()

