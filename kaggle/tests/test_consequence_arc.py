import unittest

from metalogic_arc3.consequence_arc import (
    EffectProjectionAdapter,
    RelationalEffect,
    RelationalObservation,
    SemanticAction,
    TerminalWarrant,
    WarrantedEffectExample,
    compile_projection,
)
from metalogic_arc3.future_arc import macro_effect
from metalogic_arc3.protected_future import UnknownResidual


CODE_R = (0, 1, 0, 0, 0, 0)
CODE_U = (1, 0, 0, 0, 0, 0)


def fixture_observation():
    return RelationalObservation.build(
        objects={"source"},
        relations={("source", "visible")},
    )


def point_frame(row, col, *, background=0, foreground=7):
    grid = [[background for _ in range(7)] for _ in range(7)]
    grid[row][col] = foreground
    return grid


def example_with_features(level, features, output):
    observation = fixture_observation()
    return WarrantedEffectExample.build(
        before=observation,
        intervention=SemanticAction("program-slot", (features.get("name", "probe"),)),
        after=observation,
        effect=RelationalEffect.build(
            {name: value for name, value in features.items() if name != "name"}
        ),
        intermediates=(),
        output=output,
        slot_index=0,
        terminal_warrant=TerminalWarrant("PROGRESS", f"run:{level}"),
        lineage=(level,),
    )


def example(level, operator, output):
    return example_with_features(
        level,
        {"name": operator, "trace.occupancy@1": (operator,)},
        output,
    )


class ConsequenceObjects(unittest.TestCase):
    def test_example_identity_ignores_construction_order(self):
        before = RelationalObservation.build(
            objects={"b", "a"},
            relations={("a", "left", "b")},
        )
        after = RelationalObservation.build(
            objects={"a", "b"},
            relations={("a", "aligned", "b")},
        )
        left = WarrantedEffectExample.build(
            before=before,
            intervention=SemanticAction("move", ("R",)),
            after=after,
            effect=RelationalEffect.build(
                {"trace.occupancy@1": ((0, 0), (0, 1))}
            ),
            intermediates=(),
            output=(0, 1, 0, 0, 0, 0),
            slot_index=0,
            terminal_warrant=TerminalWarrant("PROGRESS", "run:1"),
            lineage=("G3",),
        )
        right = WarrantedEffectExample.build(
            before=before,
            intervention=SemanticAction("move", ("R",)),
            after=after,
            effect=RelationalEffect.build(
                {"trace.occupancy@1": ((0, 0), (0, 1))}
            ),
            intermediates=(),
            output=(0, 1, 0, 0, 0, 0),
            slot_index=0,
            terminal_warrant=TerminalWarrant("PROGRESS", "run:1"),
            lineage=("G3",),
        )

        self.assertEqual(left.example_id, right.example_id)

    def test_observation_and_effect_identity_ignore_input_order(self):
        first_observation = RelationalObservation.build(
            objects=("a", "b"),
            relations=(("a", "left", "b"), ("a", "above", "b")),
        )
        second_observation = RelationalObservation.build(
            objects=("b", "a"),
            relations=(("a", "above", "b"), ("a", "left", "b")),
        )
        first_effect = RelationalEffect.build(
            {"trace.roles@1": (1, 2), "action.arity@1": 1}
        )
        second_effect = RelationalEffect.build(
            {"action.arity@1": 1, "trace.roles@1": (1, 2)}
        )

        self.assertEqual(
            (first_observation.observation_id, first_effect.effect_id),
            (second_observation.observation_id, second_effect.effect_id),
        )

    def test_unwarranted_example_is_rejected(self):
        observation = fixture_observation()

        with self.assertRaisesRegex(ValueError, "terminal_warrant_required"):
            WarrantedEffectExample.build(
                before=observation,
                intervention=SemanticAction("move", ("R",)),
                after=observation,
                effect=RelationalEffect.build({"trace.occupancy@1": ()}),
                intermediates=(),
                output=(0,),
                slot_index=0,
                terminal_warrant=TerminalWarrant("UNKNOWN", "none"),
                lineage=("G3",),
            )


class RelationalEffects(unittest.TestCase):
    def test_intermediate_relation_separates_equal_endpoints(self):
        origin = point_frame(3, 3)
        clockwise = macro_effect(
            (origin, point_frame(2, 3), origin),
            ("U", "D"),
        )
        horizontal = macro_effect(
            (origin, point_frame(3, 4), origin),
            ("R", "L"),
        )

        self.assertNotEqual(clockwise.effect.effect_id, horizontal.effect.effect_id)

    def test_macro_rejects_frame_control_arity_mismatch(self):
        with self.assertRaisesRegex(ValueError, "macro_frame_control_arity"):
            macro_effect((point_frame(1, 1), point_frame(1, 2)), ("R", "R"))


class EffectProjectionContracts(unittest.TestCase):
    def test_equal_effects_with_equal_outputs_share_one_class(self):
        adapter = EffectProjectionAdapter.build(
            (example("G3", "R", CODE_R), example("G4", "R", CODE_R))
        )

        self.assertEqual(len(adapter.classes), 1)
        self.assertEqual(
            adapter.project(example("G3", "R", CODE_R).effect),
            CODE_R,
        )

    def test_conflicting_warranted_outputs_fail_closed(self):
        result = EffectProjectionAdapter.build(
            (example("G3", "R", CODE_R), example("G4", "R", CODE_U))
        )

        self.assertIsInstance(result, UnknownResidual)
        self.assertEqual(result.reason, "conflicting_warranted_outputs")

    def test_unseen_effect_is_unknown(self):
        adapter = EffectProjectionAdapter.build((example("G3", "R", CODE_R),))

        result = adapter.project(example("G6", "novel", CODE_U).effect)

        self.assertEqual(result.missing_interface, "target.projection@1")

    def test_single_level_class_is_not_transport_authority(self):
        witnessed = example("G3", "R", CODE_R)
        adapter = EffectProjectionAdapter.build((witnessed,))

        result = adapter.project(witnessed.effect)

        self.assertEqual(result.reason, "untransported_effect_class")

    def test_nuisance_feature_does_not_block_cross_level_projection(self):
        g3_r = example_with_features(
            "G3",
            {
                "trace.occupancy@1": ("right",),
                "support.context@1": ("wide",),
            },
            CODE_R,
        )
        g4_r = example_with_features(
            "G4",
            {
                "trace.occupancy@1": ("right",),
                "support.context@1": ("tall",),
            },
            CODE_R,
        )
        g3_u = example_with_features(
            "G3",
            {
                "trace.occupancy@1": ("up",),
                "support.context@1": ("wide",),
            },
            CODE_U,
        )
        g4_u = example_with_features(
            "G4",
            {
                "trace.occupancy@1": ("up",),
                "support.context@1": ("tall",),
            },
            CODE_U,
        )
        adapter = EffectProjectionAdapter.build((g3_r, g4_r, g3_u, g4_u))
        transported = RelationalEffect.build(
            {
                "trace.occupancy@1": ("right",),
                "support.context@1": ("novel",),
            }
        )

        self.assertEqual(adapter.project(transported), CODE_R)

    def test_example_order_does_not_change_adapter_identity(self):
        examples = (
            example("G3", "R", CODE_R),
            example("G4", "U", CODE_U),
        )

        self.assertEqual(
            EffectProjectionAdapter.build(examples).adapter_id,
            EffectProjectionAdapter.build(tuple(reversed(examples))).adapter_id,
        )

    def test_new_equivalent_evidence_changes_warrant_not_semantics(self):
        first = EffectProjectionAdapter.build((example("G3", "R", CODE_R),))
        reinforced = EffectProjectionAdapter.build(
            (example("G3", "R", CODE_R), example("G4", "R", CODE_R))
        )

        self.assertEqual(first.adapter_id, reinforced.adapter_id)
        self.assertNotEqual(first.warrant_id, reinforced.warrant_id)

    def test_compile_projection_writes_nothing_when_one_slot_is_unknown(self):
        adapter = EffectProjectionAdapter.build(
            (example("G3", "R", CODE_R), example("G4", "R", CODE_R))
        )
        known = example("G3", "R", CODE_R).effect
        novel = example("G6", "novel", CODE_U).effect

        result = compile_projection((known, novel), adapter)

        self.assertIsInstance(result, UnknownResidual)
        self.assertEqual(result.evidence, (novel.effect_id,))


if __name__ == "__main__":
    unittest.main()
