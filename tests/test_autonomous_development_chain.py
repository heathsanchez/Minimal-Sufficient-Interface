"""Preregistered bounded test of a full verifier-governed development chain.

This does not introduce a new task split or a new operator tournament.  It reuses
the already frozen blind cross-grammar genesis protocol and asks the stronger
causal question that was still missing:

    MERGE -> counterexample -> SPLIT -> bounded closure obstruction ->
    EXTEND -> shared-interface MERGE -> held-out frontier collapse.

The learner is never given Boolean operator names.  The held-out frontier is
sealed during interface selection.  All claims here are bounded claims.
"""

from itertools import combinations
import hashlib
import unittest

from tests import test_blind_recursive_cross_grammar_genesis as genesis


def training_probes_ignoring_third_coordinate():
    """All 16 binary behaviours over two coordinates, lifted to eight states."""
    probes = []
    for table in range(16):
        mask = 0
        for state in range(8):
            a = (state >> 0) & 1
            b = (state >> 1) & 1
            bit = (table >> (a | (b << 1))) & 1
            mask |= bit << state
        probes.append(mask)
    return tuple(probes)


def behavioural_partition(probes):
    """Coarsest exact quotient induced by the supplied verifier behaviours."""
    buckets = {}
    for state in range(8):
        signature = tuple((probe >> state) & 1 for probe in probes)
        buckets.setdefault(signature, []).append(state)
    return tuple(sorted(tuple(block) for block in buckets.values()))


def conflict_pairs(partition, witness):
    out = []
    for block in partition:
        for left, right in combinations(block, 2):
            if ((witness >> left) & 1) != ((witness >> right) & 1):
                out.append((left, right))
    return tuple(out)


# Opaque raw sensors.  Names/semantics are not exposed to the selector.
# Multiple structurally adequate sensors deliberately remain so success cannot
# depend on a hand-named "third bit" feature.
RAW_SENSORS = (
    0b10101010,
    0b11001100,
    0b11110000,
    0b01101001,
    0b10010110,
)


def infer_missing_sensor(partition, witness):
    """Choose a minimum refinement that separates every verifier conflict."""
    conflicts = conflict_pairs(partition, witness)
    if not conflicts:
        raise AssertionError("witness does not falsify the current quotient")

    candidates = []
    for index, sensor in enumerate(RAW_SENSORS):
        if not all(
            ((sensor >> left) & 1) != ((sensor >> right) & 1)
            for left, right in conflicts
        ):
            continue

        refined = []
        for block in partition:
            for bit in (0, 1):
                cell = tuple(
                    state for state in block
                    if ((sensor >> state) & 1) == bit
                )
                if cell:
                    refined.append(cell)

        # First minimize representational size.  Only exact structural ties are
        # resolved by a frozen hash over opaque sensor identity.
        tie = hashlib.sha256(
            f"msi-development-sensor-v1:{index}:{sensor}".encode()
        ).digest()
        candidates.append((len(refined), tie, index, sensor, tuple(sorted(refined))))

    if not candidates:
        raise AssertionError("no available raw sensor repairs the obstruction")
    return min(candidates)


class AutonomousDevelopmentChain(unittest.TestCase):
    """Full causal chain built on the frozen cross-grammar genesis experiment."""

    @classmethod
    def setUpClass(cls):
        # Reuse the exact frozen split and blind tournament already exercised by
        # the independent genesis suite.  Do not create a post-hoc task family.
        genesis.BlindRecursiveCrossGrammarGenesis.setUpClass()
        cls.training = genesis.BlindRecursiveCrossGrammarGenesis.training
        cls.held_out = genesis.BlindRecursiveCrossGrammarGenesis.held_out
        cls.results = genesis.BlindRecursiveCrossGrammarGenesis.results

    def test_01_merge_is_the_coarsest_exact_training_quotient(self):
        probes = training_probes_ignoring_third_coordinate()
        partition = behavioural_partition(probes)

        self.assertEqual(len(partition), 4)
        self.assertTrue(all(len(block) == 2 for block in partition))

        # Inside a block every available continuation agrees.
        for block in partition:
            for left, right in combinations(block, 2):
                self.assertTrue(all(
                    ((probe >> left) & 1) == ((probe >> right) & 1)
                    for probe in probes
                ))

        # Across blocks at least one available continuation disagrees: this is
        # not an arbitrary compression but the exact behavioural quotient.
        for first, second in combinations(partition, 2):
            self.assertTrue(any(
                ((probe >> first[0]) & 1) != ((probe >> second[0]) & 1)
                for probe in probes
            ))

    def test_02_sealed_failure_withdraws_merge_and_forces_minimum_split(self):
        partition = behavioural_partition(training_probes_ignoring_third_coordinate())
        witness = genesis.truth_mask(3, lambda a, b, c: c)
        conflicts = conflict_pairs(partition, witness)

        self.assertEqual(len(conflicts), 4)
        blocks, _, _, sensor, refined = infer_missing_sensor(partition, witness)
        self.assertEqual(blocks, 8)
        self.assertEqual(len(refined), 8)
        self.assertTrue(all(len(block) == 1 for block in refined))
        self.assertTrue(all(
            ((sensor >> left) & 1) != ((sensor >> right) & 1)
            for left, right in conflicts
        ))

    def test_03_old_language_has_a_certified_bounded_closure_obstruction(self):
        # Exact semantic synthesis has already enumerated the minimum formula
        # cost of every one of the 256 three-input behaviours in each grammar.
        budget = 5
        reachable = {
            code: sum(result["cold"][target] <= budget for target in self.held_out)
            for code, result in self.results.items()
        }

        self.assertEqual(reachable, {"az": 41, "by": 35, "cx": 37})
        self.assertTrue(all(count < len(self.held_out) for count in reachable.values()))

    def test_04_extension_is_blind_sealed_and_cross_grammar(self):
        # These are verifier-side truth-table identities, not learner labels.
        selected = {
            code: result["selected"] for code, result in self.results.items()
        }
        self.assertEqual(selected, {
            "az": (6, 11),
            "by": (6, 11),
            "cx": (2, 9),
        })
        self.assertEqual(len(self.training), 160)
        self.assertEqual(len(self.held_out), 96)
        self.assertTrue(genesis.SEALED.issubset(self.held_out))
        self.assertTrue(all(len(result["winners"]) == 2 for result in self.results.values()))

    def test_05_one_retained_interface_collapses_the_whole_held_out_frontier(self):
        budget = 5
        for code, result in self.results.items():
            cold = sum(result["cold"][target] <= budget for target in self.held_out)
            warm = sum(result["warm"][target] <= budget for target in self.held_out)
            sham = sum(result["sham"][target] <= budget for target in self.held_out)

            self.assertEqual(warm, 96)
            self.assertEqual(sham, cold)
            self.assertGreaterEqual(warm - cold, 55)

    def test_06_targeted_ablation_breaks_the_full_frontier_transition(self):
        budget = 5
        for code, result in self.results.items():
            grammar = result["grammar"]
            left, right = result["selected"]
            left_only = genesis.synthesize_costs(3, grammar, (left,))
            right_only = genesis.synthesize_costs(3, grammar, (right,))

            warm = sum(result["warm"][target] <= budget for target in self.held_out)
            left_n = sum(left_only[target] <= budget for target in self.held_out)
            right_n = sum(right_only[target] <= budget for target in self.held_out)

            self.assertEqual(warm, 96)
            self.assertLess(left_n, 96)
            self.assertLess(right_n, 96)

    def test_07_phase_signature_is_joint_not_a_single_lucky_solve(self):
        budget = 5
        expected_cold_residuals = {"az": 55, "by": 61, "cx": 59}

        for code, result in self.results.items():
            cold_residuals = sum(
                result["cold"][target] > budget for target in self.held_out
            )
            warm_residuals = sum(
                result["warm"][target] > budget for target in self.held_out
            )

            self.assertEqual(cold_residuals, expected_cold_residuals[code])
            self.assertEqual(warm_residuals, 0)

            # After promotion, all 96 independently held-out behaviours factor
            # through the same retained two-operator interface; no target needs
            # another interface under the frozen budget.
            self.assertEqual(warm_residuals, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
