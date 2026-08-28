import itertools
import unittest


# Final-boss protocol:
# - hidden world is a finite thin category (a preorder category from a DAG closure);
# - arrow tokens are anonymously permuted;
# - verifier NEVER returns a composite token, source, target, type, identity, or object count;
# - verifier returns only binary task success/failure for an anonymous action sequence
#   under an anonymous terminal-task context;
# - learner identifies the hidden world from those binary outcomes and is scored on
#   held-out task queries plus recovery of the latent categorical structure afterward.


def transitive_closure(n, edges):
    reach = [[False] * n for _ in range(n)]
    for i in range(n):
        reach[i][i] = True
    for i, j in edges:
        reach[i][j] = True
    for k in range(n):
        for i in range(n):
            for j in range(n):
                reach[i][j] = reach[i][j] or (reach[i][k] and reach[k][j])
    return reach


def make_hidden_world(n, edge_mask, perm):
    possible = [(i, j) for i in range(n) for j in range(i + 1, n)]
    edges = [e for bit, e in enumerate(possible) if edge_mask & (1 << bit)]
    reach = transitive_closure(n, edges)
    arrows = [(i, j) for i in range(n) for j in range(n) if reach[i][j]]
    index = {a: k for k, a in enumerate(arrows)}
    if len(perm) != len(arrows):
        raise ValueError("bad permutation")
    inv = {tok: arrows[i] for i, tok in enumerate(perm)}
    tok_of = {arrows[i]: tok for i, tok in enumerate(perm)}

    def run_sequence(seq):
        if not seq:
            return None
        first = inv[seq[0]]
        src, dst = first
        for tok in seq[1:]:
            a, b = inv[tok]
            if dst != a:
                return None
            dst = b
        return src, dst

    # Anonymous task contexts are all non-trivial subsets of latent destination
    # objects, represented only by context indices.  The learner never sees them.
    contexts = [bits for bits in range(1, (1 << n) - 1)]

    def task_answer(seq, ctx_idx):
        out = run_sequence(seq)
        if out is None:
            return False
        _, dst = out
        mask = contexts[ctx_idx]
        return bool(mask & (1 << dst))

    return {
        "n": n,
        "arrows": tuple(arrows),
        "index": index,
        "inv": inv,
        "tok_of": tok_of,
        "contexts": tuple(contexts),
        "answer": task_answer,
    }


def canonical_signature(world):
    # Coordinate-free category signature used only after learning, never exposed
    # through the verifier. Thin categories are captured here by object count and
    # multiset of hom cardinalities plus degree profiles.
    n = world["n"]
    arrows = world["arrows"]
    hom = []
    outdeg = []
    indeg = []
    for i in range(n):
        outdeg.append(sum(1 for a, b in arrows if a == i and a != b))
        indeg.append(sum(1 for a, b in arrows if b == i and a != b))
        for j in range(n):
            hom.append(sum(1 for a, b in arrows if a == i and b == j))
    return (n, len(arrows), tuple(sorted(hom)), tuple(sorted(outdeg)), tuple(sorted(indeg)))


def observable_fingerprint(world, max_len=3):
    m = len(world["arrows"])
    c = len(world["contexts"])
    rows = []
    for length in range(1, max_len + 1):
        for seq in itertools.product(range(m), repeat=length):
            rows.append(tuple(world["answer"](seq, k) for k in range(c)))
    return tuple(rows)


def all_worlds():
    """Generate a bounded family with latent object count 2..4.

    To keep the census exhaustive but tractable, use all DAG edge masks on the
    natural order and a deterministic but diverse subset of anonymous token
    presentations: identity, reversal, rotations, and pair swaps. Extensional
    duplicates under the task-only verifier are quotiented before learning.
    """
    by_shape = {}
    for n in (2, 3, 4):
        edge_count = n * (n - 1) // 2
        for edge_mask in range(1 << edge_count):
            # Build canonical once to know arrow count.
            possible = [(i, j) for i in range(n) for j in range(i + 1, n)]
            edges = [e for bit, e in enumerate(possible) if edge_mask & (1 << bit)]
            reach = transitive_closure(n, edges)
            arrows = [(i, j) for i in range(n) for j in range(n) if reach[i][j]]
            m = len(arrows)
            perms = []
            base = tuple(range(m))
            perms.append(base)
            perms.append(tuple(reversed(base)))
            for r in range(1, min(m, 4)):
                perms.append(base[r:] + base[:r])
            if m >= 2:
                p = list(base); p[0], p[1] = p[1], p[0]; perms.append(tuple(p))
            if m >= 4:
                p = list(base); p[2], p[3] = p[3], p[2]; perms.append(tuple(p))

            for perm in dict.fromkeys(perms):
                w = make_hidden_world(n, edge_mask, perm)
                key = (m, len(w["contexts"]))
                fp = observable_fingerprint(w, max_len=3)
                by_shape.setdefault(key, {})[fp] = w
    return {k: tuple(v.values()) for k, v in by_shape.items()}


def all_queries(m, c):
    # Tasks contain only an anonymous action sequence and anonymous binary goal
    # context. No direct composition query exists.
    for length in (1, 2, 3):
        for seq in itertools.product(range(m), repeat=length):
            for ctx in range(c):
                yield (seq, ctx)


def response(world, q):
    seq, ctx = q
    return world["answer"](seq, ctx)


def choose_query(candidates, queries, asked):
    best = None
    for q in queries:
        if q in asked:
            continue
        yes = sum(1 for w in candidates if response(w, q))
        no = len(candidates) - yes
        if yes == 0 or no == 0:
            continue
        score = (max(yes, no), abs(yes - no), len(q[0]), q)
        if best is None or score < best[0]:
            best = (score, q)
    return None if best is None else best[1]


def identify(true_world, universe):
    m = len(true_world["arrows"])
    c = len(true_world["contexts"])
    queries = tuple(all_queries(m, c))
    candidates = list(universe)
    asked = {}
    while len(candidates) > 1:
        q = choose_query(candidates, queries, asked)
        if q is None:
            break
        r = response(true_world, q)
        asked[q] = r
        candidates = [w for w in candidates if response(w, q) == r]
    return candidates, asked, queries


class FinalBossTaskOnlyCategoryGenesis(unittest.TestCase):
    def test_binary_task_residuals_force_latent_category(self):
        worlds_by_shape = all_worlds()
        worlds = 0
        exact_observable_recoveries = 0
        structural_recoveries = 0
        heldout_tasks = 0
        total_queries = 0
        max_queries = 0
        ambiguity_worlds = 0

        for shape, universe in sorted(worlds_by_shape.items()):
            m, c = shape
            self.assertGreater(len(universe), 0)
            for true_world in universe:
                worlds += 1
                survivors, asked, queries = identify(true_world, universe)
                total_queries += len(asked)
                max_queries = max(max_queries, len(asked))

                true_fp = observable_fingerprint(true_world, max_len=3)
                survivor_fps = {observable_fingerprint(w, max_len=3) for w in survivors}
                if survivor_fps == {true_fp}:
                    exact_observable_recoveries += 1
                else:
                    ambiguity_worlds += 1

                # Held-out prediction: every unasked task must be predicted
                # identically by every surviving hypothesis.
                unseen = [q for q in queries if q not in asked]
                self.assertGreater(len(unseen), 0)
                heldout_tasks += len(unseen)
                for q in unseen:
                    vals = {response(w, q) for w in survivors}
                    self.assertEqual(vals, {response(true_world, q)})

                # Scientific target: even though coordinates/presentations may
                # remain non-identifiable, task-equivalent survivors must agree
                # on the coordinate-free latent category structure.
                sigs = {canonical_signature(w) for w in survivors}
                if sigs == {canonical_signature(true_world)}:
                    structural_recoveries += 1

                self.assertLess(len(asked), len(queries))

        print(
            "FINAL_BOSS_TASK_ONLY_CATEGORY_GENESIS: "
            f"worlds={worlds}; exact_observable={exact_observable_recoveries}; "
            f"structural={structural_recoveries}; ambiguity={ambiguity_worlds}; "
            f"heldout_tasks={heldout_tasks}; total_queries={total_queries}; "
            f"max_queries={max_queries}"
        )

        self.assertGreater(worlds, 0)
        self.assertEqual(exact_observable_recoveries, worlds)
        self.assertEqual(structural_recoveries, worlds)
        self.assertEqual(ambiguity_worlds, 0)


if __name__ == "__main__":
    unittest.main()
