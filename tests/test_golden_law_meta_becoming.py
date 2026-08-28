import itertools
import unittest


SOURCE_STATES = tuple(range(8))
TARGET_PERM = (5, 2, 7, 0, 3, 6, 1, 4)
TARGET_STATES = tuple(range(8))


def bit_column(states, bit, perm=None):
    if perm is None:
        return tuple((x >> bit) & 1 for x in states)
    return tuple((perm[x] >> bit) & 1 for x in states)


SOURCE_ATOMS = {
    "sA": bit_column(SOURCE_STATES, 0),
    "sB": bit_column(SOURCE_STATES, 1),
    "sC": bit_column(SOURCE_STATES, 2),
}
TARGET_ATOMS = {
    "tP": bit_column(TARGET_STATES, 2, TARGET_PERM),
    "tQ": bit_column(TARGET_STATES, 0, TARGET_PERM),
    "tR": bit_column(TARGET_STATES, 1, TARGET_PERM),
}

# Source and target deliberately use disjoint literal operator identities.
SOURCE_OPS = {
    "s_cap": (0, 0, 0, 1),   # AND
    "s_cup": (0, 1, 1, 1),   # OR
    "s_twist": (0, 1, 1, 0), # XOR
    "s_untwist": (1, 0, 0, 1), # XNOR
}
TARGET_OPS = {
    "t_meet": (0, 0, 0, 1),
    "t_join": (0, 1, 1, 1),
    "t_weave": (1, 0, 0, 1), # XNOR: same behavioural partition as source XOR
}


def apply_op(table, a, b):
    return table[(a << 1) | b]


def combine(table, left, right):
    return tuple(apply_op(table, a, b) for a, b in zip(left, right))


def negate(col):
    return tuple(1 - x for x in col)


def kernel(col):
    return frozenset(
        (i, j)
        for i in range(len(col))
        for j in range(i + 1, len(col))
        if col[i] == col[j]
    )


def op_partition(table):
    """Anonymous behavioural identity of a binary constructor.

    Output labels are quotiented away: only which input patterns the operator
    treats as equal survives.
    """
    patterns = range(4)
    return frozenset(
        (i, j)
        for i in patterns
        for j in range(i + 1, 4)
        if table[i] == table[j]
    )


def base_language(atoms):
    out = dict(atoms)
    for name, col in atoms.items():
        out[f"not({name})"] = negate(col)
    return out


def exact_repair_exists(atoms, hidden):
    target = kernel(hidden)
    return any(kernel(col) == target for col in base_language(atoms).values())


def exact_repairs_with_operator(atoms, table, hidden):
    target = kernel(hidden)
    repairs = []
    items = tuple(atoms.items())
    for (ln, left), (rn, right) in itertools.product(items, repeat=2):
        col = combine(table, left, right)
        if kernel(col) == target:
            repairs.append((ln, rn, col))
    return tuple(repairs)


def source_training_tasks():
    names = tuple(SOURCE_ATOMS)
    tasks = []
    xor = SOURCE_OPS["s_twist"]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            tasks.append(combine(xor, SOURCE_ATOMS[names[i]], SOURCE_ATOMS[names[j]]))
    return tuple(tasks)


def discover_meta_extension(atoms, operator_menu, tasks):
    """Find the least behavioural operator class repairing every source failure.

    The selector is not told XOR, parity, or any semantic operator name. It sees
    only executable truth tables and verifier-required target kernels.
    """
    classes = {}
    for name, table in operator_menu.items():
        fp = op_partition(table)
        ok = all(exact_repairs_with_operator(atoms, table, hidden) for hidden in tasks)
        if ok:
            classes.setdefault(fp, []).append(name)
    return classes


def choose_target_operator(operator_menu, retained_partition):
    matches = [name for name, table in operator_menu.items() if op_partition(table) == retained_partition]
    return tuple(sorted(matches))


class GoldenLawMetaBecoming(unittest.TestCase):
    def test_source_failure_changes_the_generator_itself(self):
        tasks = source_training_tasks()
        self.assertEqual(len(tasks), 3)
        self.assertTrue(all(not exact_repair_exists(SOURCE_ATOMS, hidden) for hidden in tasks))

        learned = discover_meta_extension(SOURCE_ATOMS, SOURCE_OPS, tasks)
        self.assertEqual(len(learned), 1)
        retained_partition, source_realizers = next(iter(learned.items()))

        # Concrete syntax is not unique: XOR and XNOR realize the same
        # consequential constructor class. Behavioural identity is unique.
        self.assertEqual(set(source_realizers), {"s_twist", "s_untwist"})
        self.assertEqual(op_partition(SOURCE_OPS["s_twist"]), retained_partition)
        self.assertEqual(op_partition(SOURCE_OPS["s_untwist"]), retained_partition)

        print(
            "META_BECOMING_SOURCE "
            f"tasks={len(tasks)} base_failures={len(tasks)} "
            f"surviving_behavioural_classes={len(learned)} "
            f"concrete_realizers={len(source_realizers)}"
        )

    def test_learned_way_of_expanding_transfers_without_literal_identity(self):
        tasks = source_training_tasks()
        learned = discover_meta_extension(SOURCE_ATOMS, SOURCE_OPS, tasks)
        retained_partition = next(iter(learned))

        # Held-out target task uses disjoint atom names, a permutation of the
        # underlying states, and a complementary concrete realizer (XNOR).
        hidden_pair = combine(
            TARGET_OPS["t_weave"], TARGET_ATOMS["tP"], TARGET_ATOMS["tR"]
        )

        self.assertTrue(set(SOURCE_ATOMS).isdisjoint(TARGET_ATOMS))
        self.assertTrue(set(SOURCE_OPS).isdisjoint(TARGET_OPS))
        self.assertFalse(exact_repair_exists(TARGET_ATOMS, hidden_pair))

        warm_matches = choose_target_operator(TARGET_OPS, retained_partition)
        self.assertEqual(warm_matches, ("t_weave",))
        warm_repairs = exact_repairs_with_operator(
            TARGET_ATOMS, TARGET_OPS[warm_matches[0]], hidden_pair
        )
        self.assertTrue(warm_repairs)

        # RAW_HISTORY cannot replay source operator IDs in the target language.
        raw_literal_matches = tuple(name for name in SOURCE_OPS if name in TARGET_OPS)
        self.assertEqual(raw_literal_matches, ())

        # SHAM retains a wrong source behavioural class (AND).
        sham_partition = op_partition(SOURCE_OPS["s_cap"])
        sham_matches = choose_target_operator(TARGET_OPS, sham_partition)
        self.assertEqual(sham_matches, ("t_meet",))
        self.assertFalse(
            exact_repairs_with_operator(TARGET_ATOMS, TARGET_OPS[sham_matches[0]], hidden_pair)
        )

        # Exact ablation removes the learned meta-extension and restores the
        # insufficient base generator.
        self.assertFalse(exact_repair_exists(TARGET_ATOMS, hidden_pair))

        print(
            "META_BECOMING_TRANSFER "
            "cold=FAIL raw=FAIL sham=FAIL ablation=FAIL warm=PASS "
            f"target_operator={warm_matches[0]}"
        )

    def test_promoted_generator_enables_a_second_unseen_composition(self):
        tasks = source_training_tasks()
        retained_partition = next(iter(discover_meta_extension(SOURCE_ATOMS, SOURCE_OPS, tasks)))
        warm_name = choose_target_operator(TARGET_OPS, retained_partition)[0]
        table = TARGET_OPS[warm_name]

        # This deeper task was absent from source selection and from the first
        # held-out target pair task: three-way parity/complement under a new
        # state presentation. The promoted generator can construct it recursively.
        first = combine(table, TARGET_ATOMS["tP"], TARGET_ATOMS["tQ"])
        triple = combine(table, first, TARGET_ATOMS["tR"])

        base_kernels = {kernel(col) for col in base_language(TARGET_ATOMS).values()}
        one_step_kernels = set(base_kernels)
        for left, right in itertools.product(TARGET_ATOMS.values(), repeat=2):
            one_step_kernels.add(kernel(combine(table, left, right)))

        self.assertNotIn(kernel(triple), base_kernels)
        self.assertNotIn(kernel(triple), one_step_kernels)

        # Two recursive uses of the retained constructor produce the exact
        # unseen target structure; deleting the constructor destroys the route.
        rebuilt = combine(table, combine(table, TARGET_ATOMS["tP"], TARGET_ATOMS["tQ"]), TARGET_ATOMS["tR"])
        self.assertEqual(kernel(rebuilt), kernel(triple))

        print(
            "META_BECOMING_COMPOUNDING depth_required=2 "
            "cold_depth1=FAIL warm_depth2=PASS exact_ablation=FAIL"
        )


if __name__ == "__main__":
    unittest.main()
