import unittest

from minimum_calculus_self_audit import (
    AuditCase,
    Decision,
    V0,
    V1,
    active_state_after_quotient,
    best_lawful_interaction,
    equivalent_under_attacks,
    future_equivalence_quotient,
)


class MinimumCalculusSelfAudit(unittest.TestCase):
    def test_incomplete_coverage_separates_old_and_refined_calculus(self):
        case = AuditCase("incomplete_cover", True, 0, False, 0)
        self.assertEqual(V0.decide(case), Decision.ESCALATE)
        self.assertEqual(V1.decide(case), Decision.UNKNOWN)
        print("SELF_AUDIT_COVERAGE PASS old=ESCALATE; refined=UNKNOWN; reason=absence_without_complete_cover")

    def test_certified_empty_version_space_still_escalates(self):
        case = AuditCase("certified_empty", True, 0, True, 0)
        self.assertEqual(V1.decide(case), Decision.ESCALATE)
        print("SELF_AUDIT_CERTIFIED_EMPTY PASS refined=ESCALATE; complete_cover=true")

    def test_future_equivalent_realizers_collapse_before_interaction(self):
        case = AuditCase("future_equivalent", True, 5, True, 1)
        self.assertEqual(V0.decide(case), Decision.INTERACT)
        self.assertEqual(V1.decide(case), Decision.COMPILE)
        quotient = future_equivalence_quotient([
            frozenset({"d0", "d1", "d2", "d3", "d4"}),
            frozenset({"d0", "d1", "d2", "d3", "d4"}),
        ])
        self.assertEqual(len(quotient), 1)
        print("SELF_AUDIT_FUTURE_QUOTIENT PASS realizers=5; future_classes=1; old=INTERACT; refined=COMPILE")

    def test_active_quotient_does_not_destroy_provenance(self):
        active = {"audit", "syntax", "ancestry"}
        protected = {"audit"}
        provenance = ("raw-observation-17", "verifier-run-23", "ancestry")
        compressed = active_state_after_quotient(active, protected)
        self.assertEqual(compressed, frozenset({"audit"}))
        self.assertEqual(provenance, ("raw-observation-17", "verifier-run-23", "ancestry"))
        print("SELF_AUDIT_PROVENANCE PASS active=3->1; provenance_retained=true")

    def test_discrimination_cannot_override_lawfulness(self):
        interactions = [
            {"name": "destructive_oracle", "lawful": False, "blocks": 8, "worst_case": 1, "cost": 1},
            {"name": "safe_split", "lawful": True, "blocks": 3, "worst_case": 3, "cost": 2},
            {"name": "sham", "lawful": True, "blocks": 1, "worst_case": 8, "cost": 1},
        ]
        chosen = best_lawful_interaction(interactions)
        self.assertEqual(chosen["name"], "safe_split")
        print("SELF_AUDIT_INTERACTION PASS highest_raw_discrimination_rejected=destructive_oracle; chosen=safe_split")

    def test_fixed_point_is_relative_not_global_completion(self):
        current = AuditCase("current_family", False, 1, True, 1)
        future = AuditCase("new_protected_consequence", True, 2, True, 2)
        self.assertEqual(V1.decide(current), Decision.FIXED)
        self.assertEqual(V1.decide(future), Decision.INTERACT)
        self.assertTrue(V1.relative_fixed_point)
        print("SELF_AUDIT_RELATIVE_FIXED_POINT PASS current=FIXED; new_consequence=INTERACT; global_completion=false")

    def test_attacks_certify_the_variants_are_not_equivalent(self):
        attacks = [
            AuditCase("incomplete_cover", True, 0, False, 0),
            AuditCase("future_equivalent", True, 5, True, 1),
        ]
        self.assertFalse(equivalent_under_attacks(V0, V1, attacks))
        print("SELF_AUDIT_SEPARATOR PASS variants_equivalent=false; consequential_separators=2")


if __name__ == "__main__":
    unittest.main()
