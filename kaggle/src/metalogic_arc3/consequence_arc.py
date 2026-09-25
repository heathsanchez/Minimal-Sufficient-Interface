from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Hashable, Iterable, Mapping

from .protected_future import UnknownResidual, canonical_digest


@dataclass(frozen=True)
class RelationalObservation:
    objects: tuple[Hashable, ...]
    relations: tuple[Hashable, ...]
    observation_id: str

    @classmethod
    def build(
        cls,
        *,
        objects: Iterable[Hashable],
        relations: Iterable[Hashable],
    ) -> RelationalObservation:
        canonical_objects = tuple(sorted(set(objects), key=canonical_digest))
        canonical_relations = tuple(sorted(set(relations), key=canonical_digest))
        meaning = (
            "relational-observation@1",
            canonical_objects,
            canonical_relations,
        )
        return cls(
            canonical_objects,
            canonical_relations,
            canonical_digest(meaning),
        )


@dataclass(frozen=True)
class SemanticAction:
    family: str
    controls: tuple[Hashable, ...]


@dataclass(frozen=True)
class RelationalEffect:
    features: tuple[tuple[str, Hashable], ...]
    effect_id: str

    @classmethod
    def build(cls, features: Mapping[str, Hashable]) -> RelationalEffect:
        normalized = tuple(sorted(features.items()))
        meaning = ("relational-effect@1", normalized)
        return cls(normalized, canonical_digest(meaning))

    def project(self, families: Iterable[str]) -> tuple[tuple[str, Hashable], ...]:
        selected = set(families)
        return tuple(
            (name, value)
            for name, value in self.features
            if name in selected
        )


@dataclass(frozen=True)
class TerminalWarrant:
    consequence: str
    evidence_ref: str


@dataclass(frozen=True)
class WarrantedEffectExample:
    before: RelationalObservation
    intervention: SemanticAction
    intermediates: tuple[RelationalObservation, ...]
    after: RelationalObservation
    effect: RelationalEffect
    output: tuple[int, ...]
    slot_index: int
    terminal_warrant: TerminalWarrant
    lineage: tuple[str, ...]
    example_id: str

    @classmethod
    def build(
        cls,
        *,
        before: RelationalObservation,
        intervention: SemanticAction,
        after: RelationalObservation,
        effect: RelationalEffect,
        intermediates: Iterable[RelationalObservation],
        output: Iterable[int],
        slot_index: int,
        terminal_warrant: TerminalWarrant,
        lineage: Iterable[str],
    ) -> WarrantedEffectExample:
        if terminal_warrant.consequence not in {"PROGRESS", "WIN"}:
            raise ValueError("terminal_warrant_required")
        canonical_intermediates = tuple(intermediates)
        canonical_output = tuple(output)
        canonical_lineage = tuple(lineage)
        meaning = (
            "warranted-effect-example@1",
            before,
            intervention,
            canonical_intermediates,
            after,
            effect,
            canonical_output,
            slot_index,
            terminal_warrant,
            canonical_lineage,
        )
        return cls(
            before,
            intervention,
            canonical_intermediates,
            after,
            effect,
            canonical_output,
            slot_index,
            terminal_warrant,
            canonical_lineage,
            canonical_digest(meaning),
        )


@dataclass(frozen=True)
class EffectClass:
    class_id: str
    signature: tuple[tuple[str, Hashable], ...]
    effect_ids: tuple[str, ...]
    output: tuple[int, ...]
    evidence_ids: tuple[str, ...]
    source_levels: tuple[str, ...]


@dataclass(frozen=True)
class EffectProjectionAdapter:
    interface_id: str
    families: tuple[str, ...]
    classes: tuple[EffectClass, ...]
    preserves: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    adapter_id: str
    warrant_id: str

    @classmethod
    def build(
        cls,
        examples: Iterable[WarrantedEffectExample],
    ) -> EffectProjectionAdapter | UnknownResidual:
        examples = tuple(examples)
        if not examples:
            return UnknownResidual("target.projection@1", "empty_training_set")

        by_effect: dict[str, list[WarrantedEffectExample]] = {}
        for example in examples:
            by_effect.setdefault(example.effect.effect_id, []).append(example)
        for group in by_effect.values():
            if len({item.output for item in group}) != 1:
                return UnknownResidual(
                    "target.projection@1",
                    "conflicting_warranted_outputs",
                    tuple(sorted(item.example_id for item in group)),
                )

        available = tuple(
            sorted(
                set.intersection(
                    *(
                        {name for name, _ in example.effect.features}
                        for example in examples
                    )
                )
            )
        )
        candidates = []
        for size in range(len(available) + 1):
            for families in combinations(available, size):
                grouped: dict[
                    tuple[tuple[str, Hashable], ...],
                    list[WarrantedEffectExample],
                ] = {}
                for example in examples:
                    signature = example.effect.project(families)
                    grouped.setdefault(signature, []).append(example)
                if all(
                    len({item.output for item in group}) == 1
                    for group in grouped.values()
                ):
                    partition = tuple(
                        sorted(
                            tuple(sorted(item.example_id for item in group))
                            for group in grouped.values()
                        )
                    )
                    candidates.append(
                        (len(grouped), size, partition, families, grouped)
                    )

        if not candidates:
            return UnknownResidual(
                "target.projection@1",
                "no_output_preserving_interface",
            )
        candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
        class_count, family_count, _, families, grouped = candidates[0]
        tied_partitions = {
            item[2]
            for item in candidates
            if (item[0], item[1]) == (class_count, family_count)
        }
        if len(tied_partitions) != 1:
            return UnknownResidual(
                "target.projection@1",
                "ambiguous_minimal_preserving_interface",
                tuple(
                    canonical_digest(partition)
                    for partition in sorted(tied_partitions)
                ),
            )

        classes = tuple(
            EffectClass(
                class_id=canonical_digest(
                    ("effect-class@1", signature, group[0].output)
                ),
                signature=signature,
                effect_ids=tuple(
                    sorted({item.effect.effect_id for item in group})
                ),
                output=group[0].output,
                evidence_ids=tuple(
                    sorted(item.example_id for item in group)
                ),
                source_levels=tuple(
                    sorted({item.lineage[0] for item in group})
                ),
            )
            for signature, group in sorted(
                grouped.items(),
                key=lambda item: canonical_digest(item[0]),
            )
        )
        preserves = ("effect.relational@1", "target.column@1")
        evidence_ids = tuple(sorted(item.example_id for item in examples))
        semantic_classes = tuple(
            (block.class_id, block.signature, block.output)
            for block in classes
        )
        meaning = (
            "effect-projection-adapter@1",
            families,
            semantic_classes,
            preserves,
        )
        adapter_id = canonical_digest(meaning)
        warrant_id = canonical_digest(
            (
                "effect-projection-warrant@1",
                adapter_id,
                evidence_ids,
                tuple(
                    (
                        block.class_id,
                        block.evidence_ids,
                        block.source_levels,
                    )
                    for block in classes
                ),
            )
        )
        return cls(
            "target.projection@1",
            families,
            classes,
            preserves,
            evidence_ids,
            adapter_id,
            warrant_id,
        )

    def project(
        self,
        effect: RelationalEffect,
    ) -> tuple[int, ...] | UnknownResidual:
        signature = effect.project(self.families)
        for block in self.classes:
            if signature == block.signature:
                if not self.families and effect.effect_id not in block.effect_ids:
                    break
                if len(block.source_levels) < 2:
                    return UnknownResidual(
                        "target.projection@1",
                        "untransported_effect_class",
                        (block.class_id,),
                    )
                return block.output
        return UnknownResidual(
            "target.projection@1",
            "unseen_effect_class",
            (effect.effect_id,),
        )


def compile_projection(
    effects: Iterable[RelationalEffect],
    adapter: EffectProjectionAdapter,
) -> tuple[tuple[int, ...], ...] | UnknownResidual:
    outputs = []
    unknown_ids = []
    for effect in effects:
        result = adapter.project(effect)
        if isinstance(result, UnknownResidual):
            unknown_ids.extend(result.evidence or (effect.effect_id,))
        else:
            outputs.append(result)
    if unknown_ids:
        return UnknownResidual(
            "target.projection@1",
            "unseen_or_ambiguous_effect_class",
            tuple(unknown_ids),
        )
    return tuple(outputs)
