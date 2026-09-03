"""Attachment-aware candidate controller.

This is an A/B candidate over the verified DevelopmentalOperatingSystem.  It adds
one distinction only: ATTACHMENT, for cases where a verified local theorem has
not yet been shown to apply to the live global frontier.
"""
from __future__ import annotations
from developmental_operating_system import DevelopmentalOperatingSystem, Action


class AttachmentAwareDevelopmentalOS(DevelopmentalOperatingSystem):
    def classify_residual(self, residual: str):
        text = residual.lower()
        attachment_terms = (
            'attach', 'attachment', 'maps into the current frontier',
            'apply to the live frontier', 'live frontier', 'assumptions map',
            'assumptions of the local result', 'assumptions have not yet been shown',
            'shown to hold in the target reduction', 'hold in the target reduction',
            'lift the local theorem', 'local theorem to the global',
            'prove that this layer occurs', 'connect this theorem to',
        )
        attachment_score = sum(text.count(w) for w in attachment_terms)
        base_type, scores = super().classify_residual(residual)
        scores = dict(scores)
        scores['ATTACHMENT'] = attachment_score
        if attachment_score:
            return 'ATTACHMENT', scores
        return base_type, scores

    def wake_actions(self, state):
        # Preserve the entire baseline queue first.
        super().wake_actions(state)
        if state.residual_type == 'ATTACHMENT':
            triggers = tuple(p['id'] for p in state.provenance_graph[-8:])
            if 'act:attach' not in {a.id for a in state.action_queue}:
                state.action_queue.append(Action(
                    'act:attach', 'ATTACH',
                    'Prove or refute that the verified local theorem assumptions map into the live frontier before global promotion.',
                    triggers, 4.5, 4.5, 1.0,
                    residual_types=('ATTACHMENT',)
                ))
            # Attachment must outrank generic probing when attachment is the certified residual.
            state.action_queue.sort(key=lambda a: (0 if a.id == 'act:attach' else 1, -a.utility, a.id))
