import itertools
import unittest


def all_maps(n):
    return tuple(itertools.product(range(n), repeat=n))


def permutations(n):
    return tuple(m for m in all_maps(n) if len(set(m)) == n)


def apply_word(word, f, g, x):
    y = x
    for symbol in reversed(word):
        y = (f if symbol == 0 else g)[y]
    return y


def rows(fs, gs, n, verifier):
    return [
        (f, g, x, verifier(f, g, x))
        for f in fs
        for g in gs
        for x in range(n)
    ]


def fit_lookup(data, key_fn):
    table = {}
    for row in data:
        key = key_fn(row)
        y = row[3]
        if key in table and table[key] != y:
            return None
        table[key] = y
    return table


def generated_words(max_depth=2):
    out = []
    for d in range(1, max_depth + 1):
        out.extend(itertools.product((0, 1), repeat=d))
    return tuple(out)


def fit_generated_probe(data, max_depth=2):
    """Family 1: invent a new unary observation by composing existing actions."""
    survivors = []
    for word in generated_words(max_depth):
        table = fit_lookup(data, lambda r, w=word: apply_word(w, r[0], r[1], r[2]))
        if table is not None:
            survivors.append((word, table))
    if not survivors:
        return None
    return min(survivors, key=lambda z: (len(z[0]), z[0]))


def fit_binary_local(data):
    """Family 2: invent an arbitrary local binary constructor over F(x),G(x)."""
    table = fit_lookup(data, lambda r: (r[0][r[2]], r[1][r[2]]))
    return None if table is None else table


def fit_state_gated(data):
    """Family 3: invent a state-conditioned local constructor over x,F(x),G(x)."""
    table = fit_lookup(data, lambda r: (r[2], r[0][r[2]], r[1][r[2]]))
    return None if table is None else table


def choose_extension_family(data):
    """Choose the least structural extension that is verifier-sufficient.

    Crucially, the learner is not told which hidden world it is in. The same
    ordered portfolio is applied unchanged in every case:
      1) synthesize a new composite probe;
      2) if impossible, admit a binary local constructor;
      3) if still impossible, admit a state-conditioned constructor.

    This is a bounded meta-language experiment: the extension families are
    supplied, but the winning *kind* of extension is not.
    """
    probe = fit_generated_probe(data, 2)
    if probe is not None:
        return "generated_probe", probe

    binary = fit_binary_local(data)
    if binary is not None:
        return "binary_local", binary

    gated = fit_state_gated(data)
    if gated is not None:
        return "state_gated", gated

    return None, None


def predict(model_kind, model, row):
    f, g, x, _ = row
    if model_kind == "generated_probe":
        word, table = model
        return table[apply_word(word, f, g, x)]
    if model_kind == "binary_local":
        return model[(f[x], g[x])]
    if model_kind == "state_gated":
        return model[(x, f[x], g[x])]
    raise ValueError(model_kind)


class UnscriptedConstructorFamilyGenesis(unittest.TestCase):
    def test_same_meta_procedure_selects_three_different_extension_kinds(self):
        n = 3
        discovery = permutations(n)

        hidden_worlds = {
            # Needs a new composite observation; current x/F/G interface is not enough.
            "sequential": lambda f, g, x: f[g[x]],
            # Needs simultaneous access to two primitive outcomes.
            "pointwise": lambda f, g, x: min(f[x], g[x]),
            # Needs current state as an additional control coordinate.
            "gated": lambda f, g, x: f[x] if x == 0 else g[x],
        }
        expected = {
            "sequential": "generated_probe",
            "pointwise": "binary_local",
            "gated": "state_gated",
        }

        chosen = {}
        for name, verifier in hidden_worlds.items():
            data = rows(discovery, discovery, n, verifier)
            kind, model = choose_extension_family(data)
            self.assertIsNotNone(model)
            self.assertEqual(kind, expected[name])
            chosen[name] = kind

        self.assertEqual(
            chosen,
            {
                "sequential": "generated_probe",
                "pointwise": "binary_local",
                "gated": "state_gated",
            },
        )

    def test_selected_family_transfers_and_wrong_lower_families_are_exhausted(self):
        n = 3
        maps = all_maps(n)
        discovery = set(permutations(n))

        hidden_worlds = {
            "sequential": lambda f, g, x: f[g[x]],
            "pointwise": lambda f, g, x: min(f[x], g[x]),
            "gated": lambda f, g, x: f[x] if x == 0 else g[x],
        }

        summary = {}
        for name, verifier in hidden_worlds.items():
            discovery_rows = rows(tuple(discovery), tuple(discovery), n, verifier)
            kind, model = choose_extension_family(discovery_rows)
            self.assertIsNotNone(model)

            # Structural exhaustion checks: each selected family appears only
            # after every cheaper family in the fixed portfolio has failed.
            if kind == "binary_local":
                self.assertIsNone(fit_generated_probe(discovery_rows, 2))
            if kind == "state_gated":
                self.assertIsNone(fit_generated_probe(discovery_rows, 2))
                self.assertIsNone(fit_binary_local(discovery_rows))

            heldout = [
                r for r in rows(maps, maps, n, verifier)
                if not (r[0] in discovery and r[1] in discovery)
            ]
            failures = sum(predict(kind, model, r) != r[3] for r in heldout)
            self.assertEqual(failures, 0)

            # Exact causal ablation: revert to the original supplied interface
            # (x,F(x),G(x)); for worlds that required a genuine extension, the
            # verifier again sees unresolved collisions on held-out examples.
            old_table = fit_lookup(heldout, lambda r: (r[2], r[0][r[2]], r[1][r[2]]))
            if name == "sequential":
                self.assertIsNone(old_table)

            summary[name] = {
                "family": kind,
                "heldout": len(heldout),
                "failures": failures,
            }

        print(
            "unscripted constructor-family genesis: "
            + "; ".join(
                f"{name}={info['family']},heldout={info['heldout']},failures={info['failures']}"
                for name, info in summary.items()
            )
        )


if __name__ == "__main__":
    unittest.main()
