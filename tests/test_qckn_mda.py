import unittest

from msi import Interface
from qckn import CertifiedSubstitution, NewContextDefect, assess_operation
from qckn.mda import (
    Intervention,
    admissible_interventions,
    choose_intervention,
)
from qckn.outcomes import CertificateInvalid, Unknown


class TestTypedMDA(unittest.TestCase):
    def _defect(self):
        interface = Interface(
            (0, 1, 2),
            ("v",),
            lambda x, _c: {0: 0, 1: 0, 2: 1}[x],
        )
        action = lambda x: {0: 0, 1: 2, 2: 0}[x]
        result = assess_operation(interface, ("v",), action)
        self.assertIsInstance(result, NewContextDefect)
        return result

    def test_defect_choice_is_cost_sensitive_not_semantically_hardcoded(self):
        defect = self._defect()

        cheap_split = choose_intervention(
            defect,
            lambda i: {
                Intervention.SPLIT: 1,
                Intervention.EXPAND: 5,
                Intervention.RESTRUCTURE: 6,
                Intervention.CONSTRUCT: 7,
                Intervention.VERIFY: 8,
            }.get(i, 100),
        )
        self.assertEqual(cheap_split.primary, Intervention.SPLIT)

        cheap_expand = choose_intervention(
            defect,
            lambda i: 1 if i is Intervention.EXPAND else 10,
        )
        self.assertEqual(cheap_expand.primary, Intervention.EXPAND)

    def test_certified_substitution_has_only_compile_as_next_action(self):
        certified = CertifiedSubstitution(basis=("v",), classes=((0,),))
        self.assertEqual(
            admissible_interventions(certified),
            (Intervention.COMPILE,),
        )

    def test_invalid_certificate_cannot_compile(self):
        options = admissible_interventions(CertificateInvalid("bad-proof"))
        self.assertNotIn(Intervention.COMPILE, options)
        self.assertIn(Intervention.REVOKE, options)
        self.assertIn(Intervention.VERIFY, options)

    def test_unknown_requests_evidence_or_construction(self):
        options = admissible_interventions(Unknown("insufficient-evidence"))
        self.assertEqual(
            options,
            (Intervention.VERIFY, Intervention.CONSTRUCT),
        )


if __name__ == "__main__":
    unittest.main()
