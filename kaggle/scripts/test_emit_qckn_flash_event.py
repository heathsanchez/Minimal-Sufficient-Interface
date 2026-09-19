import hashlib
import json
import unittest

from emit_qckn_flash_event import build_event, canonical


class ArcFlashEventEmitterTests(unittest.TestCase):
    def test_refutation_event_is_bound_to_qualified_evidence(self):
        evidence, event = build_event(
            source_commit="0123456789abcdef0123456789abcdef01234567"
        )
        evidence_text = canonical(evidence)
        self.assertEqual(event["event_kind"], "obstruction_admission")
        self.assertEqual(
            event["source_evidence_sha256"],
            hashlib.sha256(evidence_text.encode()).hexdigest(),
        )
        self.assertEqual(
            event["payload_sha256"],
            hashlib.sha256(canonical(event["payload"]).encode()).hexdigest(),
        )
        self.assertEqual(evidence["online_refutation"]["verifier_calls_before"], 8)
        self.assertEqual(evidence["online_refutation"]["verifier_calls_after"], 1)
        self.assertEqual(evidence["online_refutation"]["eliminated"], 7)
        self.assertFalse(evidence["online_refutation"]["upfront_blocked"])
        self.assertEqual(
            event["payload"]["obstruction"]["actual_output"],
            "refuted-transfer",
        )
        self.assertEqual(
            event["payload"]["obstruction"]["provenance"],
            "run:35404864326/artifact:10571982632",
        )
        text = canonical(event)
        self.assertEqual(text, canonical(json.loads(text)))

    def test_source_commit_must_be_full_sha(self):
        with self.assertRaises(ValueError):
            build_event(source_commit="bad")


if __name__ == "__main__":
    unittest.main()
