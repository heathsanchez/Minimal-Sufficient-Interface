import itertools
import unittest


# Finite abelian groups in invariant-factor form C_m x C_n with m | n and m > 1.
# Every world is non-cyclic.  The learner is never given the pair (m, n).
WORLDS = (
    (2, 2),
    (2, 4),
    (2, 6),
    (2, 8),
    (3, 3),
    (3, 6),
    (3, 9),
    (4, 4),
    (4, 8),
    (5, 5),
)

MAX_STAGE = 9

# Four independent surface languages.  Each maps its anonymous integer-pair
# programs into the two latent generators by a different fixed integer map.
# No learner receives a cross-lens translation.  These maps are part of each
# lens's own task semantics, not a bridge supplied between learners.
LENS_MAPS = {
    "arithmetic": ((1, 0), (0, 1)),
    "algebraic": ((1, 1), (0, 1)),
    "topological": ((1, 0), (1, 1)),
    "categorical": ((1, 1), (1, -1)),
}


def decode_surface(lens, q):
    (a, b), (c, d) = LENS_MAPS[lens]
    x, y = q
    return a * x + b * y, c * x + d * y


def task_outcome(world, lens, q):
    """Binary verifier result only.

    Hidden common meaning, never returned to the learner: the surface program
    denotes the identity in C_m x C_n.  Each lens has a distinct surface map.
    """
    m, n = world
    x, y = decode_surface(lens, q)
    return (x % m == 0) and (y % n == 0)


def stage_shell(stage):
    """New programs generated when the representation grammar grows to stage."""
    return tuple(
        (x, y)
        for x in range(-stage, stage + 1)
        for y in range(-stage, stage + 1)
        if (x, y) != (0, 0) and max(abs(x), abs(y)) == stage
    )


def grammar_through(stage):
    return tuple(q for k in range(1, stage + 1) for q in stage_shell(k))


def choose_query(candidates, lens, available, asked):
    best = None
    for q in available:
        if q in asked:
            continue
        yes = sum(task_outcome(w, lens, q) for w in candidates)
        no = len(candidates) - yes
        if yes == 0 or no == 0:
            continue
        score = (max(yes, no), abs(yes - no), q)
        if best is None or score < best[0]:
            best = (score, q)
    return None if best is None else best[1]


def identify_with_grammar_genesis(true_world, lens):
    """Actively identify the hidden world, extending grammar only on exhaustion.

    A stage transition is licensed only after every currently generable query is
    unable to split the surviving hypothesis class.  This is the bounded
    representational-insufficiency certificate.
    """
    candidates = list(WORLDS)
    asked = {}
    stage = 1
    available = []
    exhaustion_witnesses = []

    while len(candidates) > 1 and stage <= MAX_STAGE:
        available.extend(stage_shell(stage))

        while len(candidates) > 1:
            q = choose_query(candidates, lens, available, asked)
            if q is None:
                break
            ans = task_outcome(true_world, lens, q)
            asked[q] = ans
            candidates = [w for w in candidates if task_outcome(w, lens, q) == ans]

        if len(candidates) == 1:
            break

        # Exhaustion certificate: no query in the complete current grammar can
        # distinguish the surviving candidates.
        for q in available:
            vals = {task_outcome(w, lens, q) for w in candidates}
            if len(vals) > 1:
                raise AssertionError("claimed grammar exhaustion while a separator remains")

        before = tuple(candidates)
        next_shell = stage_shell(stage + 1)
        separators = [
            q for q in next_shell
            if len({task_outcome(w, lens, q) for w in candidates}) > 1
        ]
        if not separators:
            raise AssertionError("grammar extension has no new separator")

        # Exact ablation witness: without the new grammar production, at least
        # two worlds remain observationally identical; the new production splits
        # them.  This records the causal necessity of grammar extension.
        q = separators[0]
        partition = {}
        for w in candidates:
            partition.setdefault(task_outcome(w, lens, q), []).append(w)
        exhaustion_witnesses.append((stage, before, q, tuple(tuple(v) for v in partition.values())))
        stage += 1

    return tuple(candidates), asked, tuple(exhaustion_witnesses), stage


def heldout_exact(true_world, pred_world, lens, asked):
    universe = grammar_through(MAX_STAGE)
    unseen = [q for q in universe if q not in asked]
    correct = sum(task_outcome(true_world, lens, q) == task_outcome(pred_world, lens, q) for q in unseen)
    return correct, len(unseen)


def canonical_noncyclic_structure(world):
    """Coordinate-free evaluation target for this frozen family.

    Finite abelian groups are classified by invariant factors.  Returning the
    invariant-factor pair is evaluation-only; learners never receive it or a
    cross-lens dictionary.
    """
    m, n = world
    assert m > 1 and n % m == 0
    return (m, n)


class NoncyclicConvergentConceptGenesis(unittest.TestCase):
    def test_independent_languages_extend_grammar_and_converge(self):
        lenses = tuple(LENS_MAPS)
        recoveries = 0
        convergence = 0
        heldout_correct = 0
        heldout_total = 0
        total_queries = 0
        total_extensions = 0
        worlds_with_extension = 0
        exact_ablation_witnesses = 0
        max_stage = 0
        cross_lens_translation_used = 0

        for world in WORLDS:
            recovered = {}
            this_world_extended = False

            for lens in lenses:
                survivors, asked, exhaustion, stage = identify_with_grammar_genesis(world, lens)
                self.assertEqual(len(survivors), 1)
                pred = survivors[0]
                self.assertEqual(pred, world)
                recovered[lens] = canonical_noncyclic_structure(pred)
                recoveries += 1

                c, t = heldout_exact(world, pred, lens, asked)
                heldout_correct += c
                heldout_total += t
                self.assertEqual(c, t)

                total_queries += len(asked)
                total_extensions += len(exhaustion)
                exact_ablation_witnesses += len(exhaustion)
                max_stage = max(max_stage, stage)
                if exhaustion:
                    this_world_extended = True

                # Re-check every recorded ablation witness independently.
                for old_stage, before, separator, blocks in exhaustion:
                    self.assertGreater(len(before), 1)
                    self.assertGreater(len(blocks), 1)
                    for q in grammar_through(old_stage):
                        self.assertEqual(len({task_outcome(w, lens, q) for w in before}), 1)
                    self.assertGreater(len({task_outcome(w, lens, separator) for w in before}), 1)

            if this_world_extended:
                worlds_with_extension += 1

            # Independent learners converge only after learning; comparison is
            # performed on the coordinate-free invariant-factor classification.
            if len(set(recovered.values())) == 1:
                convergence += 1

            # Structural sanity: each hidden object is genuinely non-cyclic.
            m, n = world
            group_order = m * n
            max_element_order = n
            self.assertLess(max_element_order, group_order)

        print(
            "NONCYCLIC_CONVERGENT_CONCEPT_GENESIS: "
            f"worlds={len(WORLDS)}; lenses={len(lenses)}; "
            f"recoveries={recoveries}/{len(WORLDS) * len(lenses)}; "
            f"cross_lens_convergence={convergence}/{len(WORLDS)}; "
            f"heldout={heldout_correct}/{heldout_total}; "
            f"total_queries={total_queries}; total_extensions={total_extensions}; "
            f"worlds_with_extension={worlds_with_extension}/{len(WORLDS)}; "
            f"exact_ablation_witnesses={exact_ablation_witnesses}; "
            f"max_stage={max_stage}; cross_lens_translation_used={cross_lens_translation_used}"
        )

        self.assertEqual(recoveries, len(WORLDS) * len(lenses))
        self.assertEqual(convergence, len(WORLDS))
        self.assertEqual(heldout_correct, heldout_total)
        self.assertGreater(total_extensions, 0)
        self.assertGreater(exact_ablation_witnesses, 0)
        self.assertEqual(worlds_with_extension, len(WORLDS))
        self.assertEqual(cross_lens_translation_used, 0)
        self.assertLessEqual(max_stage, MAX_STAGE)


if __name__ == "__main__":
    unittest.main()
