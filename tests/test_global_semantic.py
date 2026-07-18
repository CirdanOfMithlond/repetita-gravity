from __future__ import annotations

import json
import unittest
from pathlib import Path

from repetita.global_semantic import (
    OpenAIGlobalSemanticVerifier,
    validate_global_semantic_verification,
)
from repetita.global_verifier import verify_global_rewrite
from repetita.openai_adapter import OpenAIAdapterError
from repetita.orchestrator import run_hybrid_gravity_pass
from repetita.parser import parse_document


ROOT = Path(__file__).resolve().parents[1]


def passing_global_verification(text: str) -> dict:
    checks = [
        {
            "unit_id": unit.unit_id,
            "disposition_confirmed": True,
            "semantic_payload_preserved": True,
            "unique_content_preserved": True,
            "local_function_preserved": True,
            "hard_anchors_preserved": True,
            "rationale": "The immutable payload is present or formally reconciled to its destination.",
        }
        for unit in parse_document(text).units
    ]
    return {
        "unit_checks": checks,
        "evidence_preserved": True,
        "qualifications_preserved": True,
        "exceptions_preserved": True,
        "hard_anchors_preserved": True,
        "cross_references_resolve": True,
        "gravity_centres_coherent": True,
        "no_new_accidental_redundancy": True,
        "narrative_continuity": True,
        "overall": "passed",
        "failures": [],
    }


class PreserveAdjudicator:
    available = True
    model = "gpt-5.6"

    def adjudicate(self, document, family):
        by_id = {unit.unit_id: unit for unit in document.units}
        return {
            "family_id": family.family_id,
            "theme_label": family.label,
            "shared_payload": [family.label],
            "centre_section": family.gravity_centre,
            "centre_rationale": "The recurrence is functionally necessary and should remain unchanged.",
            "occurrences": [
                {
                    "unit_id": unit_id,
                    "semantic_relation": "related_non_duplicate",
                    "local_function": by_id[unit_id].local_function.value,
                    "disposition": "preserve_in_place",
                    "duplicated_payload": [],
                    "unique_residual_payload": [by_id[unit_id].text],
                    "hard_anchor_risk": [],
                    "rationale": "This occurrence has a distinct local function.",
                }
                for unit_id in family.unit_ids
            ],
            "unresolved_questions": [],
        }


class UnusedModelAdapter:
    available = True
    model = "gpt-5.6"

    def propose(self, *_args, **_kwargs):
        raise AssertionError("A preserve-only adjudication must not trigger rewriting")

    def verify(self, *_args, **_kwargs):
        raise AssertionError("A preserve-only adjudication must not trigger family rewrite verification")


class PassingGlobalVerifier:
    available = True
    model = "gpt-5.6"

    def verify(self, original_text, *_args, **_kwargs):
        return passing_global_verification(original_text)


class GlobalSemanticTests(unittest.TestCase):
    def test_request_uses_independent_strict_high_reasoning_review(self) -> None:
        text = "# Evidence\n\nThe measured log contains 418 events."
        formal = verify_global_rewrite(text, text, [])
        request = OpenAIGlobalSemanticVerifier(transport=lambda _: {}).build_verification_request(
            text,
            text,
            formal,
            [],
            [],
        )
        self.assertEqual(request["model"], "gpt-5.6")
        self.assertEqual(request["reasoning"]["effort"], "high")
        self.assertTrue(request["text"]["format"]["strict"])
        self.assertFalse(request["store"])

    def test_missing_original_unit_is_rejected(self) -> None:
        text = "# Evidence\n\nThe log contains 418 events. A qualification remains binding."
        verification = passing_global_verification(text)
        verification["unit_checks"].pop()
        expected = {unit.unit_id for unit in parse_document(text).units}
        with self.assertRaisesRegex(OpenAIAdapterError, "ledger mismatch"):
            validate_global_semantic_verification(verification, expected)

    def test_false_pass_claim_is_rejected(self) -> None:
        text = "# Evidence\n\nThe measured log contains 418 events."
        verification = passing_global_verification(text)
        verification["evidence_preserved"] = False
        expected = {unit.unit_id for unit in parse_document(text).units}
        with self.assertRaisesRegex(OpenAIAdapterError, "claimed pass"):
            validate_global_semantic_verification(verification, expected)

    def test_hybrid_certification_requires_both_model_layers(self) -> None:
        text = (ROOT / "sample-data" / "adversarial-professional.md").read_text(encoding="utf-8")
        result = run_hybrid_gravity_pass(
            text,
            adjudicator=PreserveAdjudicator(),
            proposer=UnusedModelAdapter(),
            semantic_verifier=UnusedModelAdapter(),
            global_semantic_verifier=PassingGlobalVerifier(),
        )
        self.assertEqual(result["global_semantic_verification"]["status"], "PASSED")
        self.assertTrue(result["certification"]["eligible"])
        self.assertEqual(result["certification"]["label"], "VERIFIED BY REPETITA GRAVITY")

    def test_no_api_key_keeps_certification_fail_closed(self) -> None:
        text = (ROOT / "sample-data" / "adversarial-professional.md").read_text(encoding="utf-8")
        result = run_hybrid_gravity_pass(text)
        self.assertEqual(result["model_status"], "MODEL_UNAVAILABLE")
        self.assertFalse(result["certification"]["eligible"])
        self.assertEqual(result["certification"]["label"], "NOT YET VERIFIED")


if __name__ == "__main__":
    unittest.main()
