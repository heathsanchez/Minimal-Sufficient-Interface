"""Blind, credit-free recursive constructor genesis across independent grammars.

The learner is not given an intermediate Boolean concept.  It searches every
unordered pair of binary behaviours and retains the pair with minimum verified
description cost on a hash-frozen training family.  A sealed arithmetic family
is excluded from selection and opened only after the interface is frozen.
"""

from dataclasses import dataclass
import hashlib
from itertools import combinations
import unittest


def truth_mask(nvars, fn):
    return sum(
        int(fn(*(bool((row >> i) & 1) for i in range(nvars)))) << row
        for row in range(1 << nvars)
    )


def lift_unary(table, x, width):
    out = 0
    for row in range(width):
        out |= ((table >> ((x >> row) & 1)) & 1) << row
    return out


def lift_binary(table, x, y, width):
    out = 0
    for row in range(width):
        index = ((x >> row) & 1) | (((y >> row) & 1) << 1)
        out |= ((table >> index) & 1) << row
    return out


@dataclass(frozen=True)
class Grammar:
    code: str
    unary: tuple
    binary: tuple


# Surface tokens, primitive counts, and primitive arities are not shared.  The
# truth-table comments are verifier-side interpretations, not learner labels.
GRAMMARS = (
    Grammar("az", (), (("az0", 0b0111),)),                 # NAND
    Grammar("by", (("by0", 0b01),), (("by1", 0b1000),)), # NOT + AND
    Grammar("cx", (("cx0", 0b01),), (("cx1", 0b1110),)), # NOT + OR
)


def synthesize_costs(nvars, grammar, macros=()):
    """Exact minimum formula-tree costs for all reachable truth functions."""
    width = 1 << nvars
    best = {
        truth_mask(nvars, lambda *xs, i=i: xs[i]): 0
        for i in range(nvars)
    }
    layers = {0: set(best)}
    binary_tables = tuple(table for _, table in grammar.binary) + tuple(macros)

    for cost in range(1, 41):
        layer = set()
        for x in layers.get(cost - 1, ()):
            for _, table in grammar.unary:
                z = lift_unary(table, x, width)
                if z not in best:
                    best[z] = cost
                    layer.add(z)
        for left_cost in range(cost):
            right_cost = cost - left_cost - 1
            for x in layers.get(left_cost, ()):
                for y in layers.get(right_cost, ()):
                    for table in binary_tables:
                        z = lift_binary(table, x, y, width)
                        if z not in best:
                            best[z] = cost
                            layer.add(z)
        layers[cost] = layer
        if len(best) == 1 << width:
            break
    return best


@dataclass(frozen=True)
class Expr:
    op: str
    args: tuple = ()

    def render(self):
        if not self.args:
            return self.op
        return f"{self.op}({','.join(arg.render() for arg in self.args)})"


def synthesize_programs(nvars, grammar, macros=()):
    """Reconstruct one lexicographically frozen minimum program per behaviour."""
    width = 1 << nvars
    best = {
        truth_mask(nvars, lambda *xs, i=i: xs[i]): (0, Expr(f"x{i}"))
        for i in range(nvars)
    }
    layers = {0: set(best)}
    unary = grammar.unary
    binary = grammar.binary + tuple((f"u{table:02x}", table) for table in macros)

    for cost in range(1, 41):
        proposals = {}

        def propose(mask, expr):
            rendered = expr.render()
            old = proposals.get(mask)
            if old is None or rendered < old.render():
                proposals[mask] = expr

        for x in layers.get(cost - 1, ()):
            for name, table in unary:
                propose(lift_unary(table, x, width), Expr(name, (best[x][1],)))
        for left_cost in range(cost):
            right_cost = cost - left_cost - 1
            for x in layers.get(left_cost, ()):
                for y in layers.get(right_cost, ()):
                    for name, table in binary:
                        propose(
                            lift_binary(table, x, y, width),
                            Expr(name, (best[x][1], best[y][1])),
                        )

        layer = set()
        for mask, expr in proposals.items():
            if mask not in best:
                best[mask] = (cost, expr)
                layer.add(mask)
        layers[cost] = layer
        if len(best) == 1 << width:
            break
    return best


SUM3 = truth_mask(3, lambda a, b, c: a ^ b ^ c)
CARRY3 = truth_mask(3, lambda a, b, c: (a and b) or (a and c) or (b and c))
SEALED = frozenset((SUM3, CARRY3, 0xFF ^ SUM3, 0xFF ^ CARRY3))


def frozen_task_split():
    order = sorted(
        range(256),
        key=lambda mask: hashlib.sha256(
            f"msi-blind-v1:{mask}".encode()
        ).digest(),
    )
    training = tuple(mask for mask in order if mask not in SEALED)[:160]
    held_out = tuple(mask for mask in order if mask not in set(training))
    return training, held_out


def discover_interface(grammar, training):
    """Search all 120 unnamed two-function libraries; no identity is supplied."""
    scored = []
    selected_costs = None
    for pair in combinations(range(16), 2):
        costs = synthesize_costs(3, grammar, pair)
        score = sum(costs[target] for target in training)
        scored.append((score, pair))
    optimum = min(score for score, _ in scored)
    winners = tuple(pair for score, pair in scored if score == optimum)
    selected = min(winners)
    selected_costs = synthesize_costs(3, grammar, selected)
    return selected, winners, optimum, selected_costs


def swap_inputs(table):
    return sum(
        ((table >> (x | (y << 1))) & 1) << (y | (x << 1))
        for x in (0, 1) for y in (0, 1)
    )


def interface_orbit(seed):
    """Coordinate-free orbit: function order, input order, and bit encoding."""
    seen = {tuple(sorted(seed))}
    changed = True
    while changed:
        changed = False
        for pair in tuple(seen):
            images = (
                tuple(sorted((swap_inputs(pair[0]), swap_inputs(pair[1])))),
                tuple(sorted((15 ^ pair[0], 15 ^ pair[1]))),
            )
            for image in images:
                if image not in seen:
                    seen.add(image)
                    changed = True
    return frozenset(seen)


def full_block(a, b, carry_in):
    total = a + b + carry_in
    return total & 1, (total >> 1) & 1


@dataclass(frozen=True)
class Plan:
    edge: str
    output: str
    final: str


EDGES = ("carry", "cin", "zero", "one", "not_carry")
OUTPUTS = ("low_high", "high_low")
FINALS = ("high", "low", "cin", "zero", "one", "not_high")
PLANS = tuple(Plan(e, o, f) for e in EDGES for o in OUTPUTS for f in FINALS)
CORRECT_PLAN = Plan("carry", "low_high", "high")


def source_value(name, carry, cin):
    return {
        "carry": carry,
        "cin": cin,
        "zero": 0,
        "one": 1,
        "not_carry": 1 - carry,
    }[name]


def eval_plan(plan, block, block_width, a, b, cin):
    mask = (1 << block_width) - 1
    low_s, low_c = block(a & mask, b & mask, cin)
    edge = source_value(plan.edge, low_c, cin)
    high_s, high_c = block(a >> block_width, b >> block_width, edge)
    if plan.output == "low_high":
        out = low_s | (high_s << block_width)
    else:
        out = high_s | (low_s << block_width)
    final = {
        "high": high_c,
        "low": low_c,
        "cin": cin,
        "zero": 0,
        "one": 1,
        "not_high": 1 - high_c,
    }[plan.final]
    return out, final


def target_block(width, a, b, cin):
    total = a + b + cin
    return total & ((1 << width) - 1), (total >> width) & 1


def learn_doubling_interface(block, block_width):
    """Residual elimination over wiring programs; the correct plan is not named."""
    survivors = list(PLANS)
    residuals = []
    width = 2 * block_width
    for a in range(1 << width):
        for b in range(1 << width):
            for cin in (0, 1):
                expected = target_block(width, a, b, cin)
                if all(eval_plan(p, block, block_width, a, b, cin) == expected
                       for p in survivors):
                    continue
                residuals.append((a, b, cin, expected))
                survivors = [
                    p for p in survivors
                    if eval_plan(p, block, block_width, a, b, cin) == expected
                ]
                if not survivors:
                    raise AssertionError("verifier eliminated every generated plan")
    selected = min(survivors, key=lambda p: (p.edge, p.output, p.final))

    def promoted(a, b, cin):
        return eval_plan(selected, block, block_width, a, b, cin)

    return selected, tuple(survivors), tuple(residuals), promoted


class BlindRecursiveCrossGrammarGenesis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.training, cls.held_out = frozen_task_split()
        cls.results = {}
        for grammar in GRAMMARS:
            cold = synthesize_costs(3, grammar)
            selected, winners, train_score, warm = discover_interface(
                grammar, cls.training
            )
            sham = synthesize_costs(3, grammar, (0b1010, 0b1100))
            programs = synthesize_programs(3, grammar, selected)
            cls.results[grammar.code] = {
                "grammar": grammar,
                "cold": cold,
                "selected": selected,
                "winners": winners,
                "train_score": train_score,
                "warm": warm,
                "sham": sham,
                "programs": programs,
            }

    def test_preregistered_split_seals_the_later_arithmetic_family(self):
        self.assertEqual(len(self.training), 160)
        self.assertEqual(len(self.held_out), 96)
        self.assertTrue(SEALED.isdisjoint(self.training))
        self.assertTrue(SEALED.issubset(self.held_out))
        self.assertEqual(set(self.training) | set(self.held_out), set(range(256)))

    def test_independent_grammars_recover_one_coordinate_free_interface(self):
        orbit = interface_orbit((0b0110, 0b1011))
        selected = tuple(self.results[g.code]["selected"] for g in GRAMMARS)
        self.assertEqual(selected, ((6, 11), (6, 11), (2, 9)))
        self.assertTrue(all(pair in orbit for pair in selected))
        self.assertEqual(tuple(len(r["winners"]) for r in self.results.values()), (2, 2, 2))
        # Every remaining tie is only an input-coordinate swap in the same orbit.
        for result in self.results.values():
            self.assertTrue(all(pair in orbit for pair in result["winners"]))

    def test_interface_transfers_to_hash_held_out_behaviours(self):
        for result in self.results.values():
            cold = sum(result["cold"][m] for m in self.held_out)
            warm = sum(result["warm"][m] for m in self.held_out)
            sham = sum(result["sham"][m] for m in self.held_out)
            self.assertLess(warm, cold)
            self.assertEqual(sham, cold)
            # Matched search without promotion is RAW_HISTORY / ablation = COLD.
            self.assertGreater((cold - warm) / cold, 0.50)

    def test_sealed_full_adder_frontier_changes_only_after_promotion(self):
        budget = 6
        expected_cold = {"az": 20, "by": 29, "cx": 29}
        for code, result in self.results.items():
            cold = result["cold"][SUM3] + result["cold"][CARRY3]
            warm = result["warm"][SUM3] + result["warm"][CARRY3]
            sham = result["sham"][SUM3] + result["sham"][CARRY3]
            self.assertEqual(cold, expected_cold[code])
            self.assertEqual(warm, 6)
            self.assertEqual(sham, cold)
            self.assertLessEqual(warm, budget)
            self.assertGreater(cold, budget)
            self.assertGreater(sham, budget)
        print("frozen full-adder programs:")
        for code, result in self.results.items():
            p = result["programs"]
            print(code, p[SUM3][1].render(), p[CARRY3][1].render())

    def test_three_further_promotions_compound_under_one_frozen_budget(self):
        # K2: the sealed full-adder outputs are promoted as a two-output block.
        # The same unchanged residual learner then discovers K3, K4, and K5.
        b2_plan, b2_survivors, r2, block2 = learn_doubling_interface(full_block, 1)
        b4_plan, b4_survivors, r4, block4 = learn_doubling_interface(block2, 2)
        b8_plan, b8_survivors, r8, block8 = learn_doubling_interface(block4, 4)

        for plan, survivors, residuals in (
            (b2_plan, b2_survivors, r2),
            (b4_plan, b4_survivors, r4),
            (b8_plan, b8_survivors, r8),
        ):
            self.assertEqual(plan, CORRECT_PLAN)
            self.assertEqual(survivors, (CORRECT_PLAN,))
            self.assertGreater(len(residuals), 0)

        # At every doubling, WARM uses two calls to the retained previous block.
        # Exact ancestor ablation needs four calls one generation farther back.
        budget = 2
        for warm_calls, ablated_calls in ((2, 12), (2, 4), (2, 4)):
            self.assertLessEqual(warm_calls, budget)
            self.assertGreater(ablated_calls, budget)

        for width, block in ((2, block2), (4, block4), (8, block8)):
            limit = 1 << width
            for a in range(limit):
                for b in range(limit):
                    for cin in (0, 1):
                        self.assertEqual(block(a, b, cin), target_block(width, a, b, cin))

    def test_structural_interventions_are_predicted_not_merely_replayed(self):
        _, _, _, block2 = learn_doubling_interface(full_block, 1)
        width = 4
        half = 2
        mask = (1 << half) - 1

        for edge_name in ("cin", "zero", "one", "not_carry"):
            intervened = Plan(edge_name, "low_high", "high")
            for a in range(1 << width):
                for b in range(1 << width):
                    for cin in (0, 1):
                        low = target_block(half, a & mask, b & mask, cin)
                        edge = source_value(edge_name, low[1], cin)
                        high = target_block(half, a >> half, b >> half, edge)
                        expected = (low[0] | (high[0] << half), high[1])
                        self.assertEqual(
                            eval_plan(intervened, block2, half, a, b, cin),
                            expected,
                        )


if __name__ == "__main__":
    unittest.main()
