from __future__ import annotations

import json
import unittest

from repetita.openai_adapter import OpenAIAdapterError, OpenAIAdjudicator
from repetita.parser import parse_document
from repetita.planner import plan_families
from repetita.similarity import detect_families


def sample_family():
    document = parse_document(
        "# Background\n\nThe archive preserves every original record.\n\n"
        "# Analysis\n\nThe archive preserves every original record."
    )
    family = plan_families(document, detect_families(document.units))[0]
    return document, family


class OpenAIAdapterTests(unittest.TestCase):
    def test_request_uses_gpt_5_6_strict_schema_and_no_storage(self) -> None:
        document, family = sample_family()
        request = OpenAIAdjudicator(transport=lambda _: {}).build_request(document, family)
        self.assertEqual(request["model"], "gpt-5.6")
        self.assertFalse(request["store"])
        self.assertTrue(request["text"]["format"]["strict"])
        self.assertEqual(request["text"]["format"]["type"], "json_schema")

    def test_complete_structured_adjudication_is_accepted(self) -> None:
        document, family = sample_family()
        occurrences = []
        for index, unit_id in enumerate(family.unit_ids):
            occurrences.append(
                {
                    "unit_id": unit_id,
                    "semantic_relation": "exact_equivalent",
                    "local_function": "analytical" if index else "context",
                    "disposition": "preserve_in_place" if index else "merge_into_centre",
                    "duplicated_payload": ["The archive preserves every original record."],
                    "unique_residual_payload": [],
                    "hard_anchor_risk": [],
                    "rationale": "Exact duplicate in a lower-fit section." if not index else "Canonical treatment.",
                }
            )
        answer = {
            "family_id": family.family_id,
            "theme_label": "record preservation",
            "shared_payload": ["Every original record is preserved."],
            "centre_section": "Analysis",
            "centre_rationale": "Analysis has the stronger functional fit.",
            "occurrences": occurrences,
            "unresolved_questions": [],
        }

        def transport(_payload):
            return {"output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(answer)}]}]}

        result = OpenAIAdjudicator(transport=transport).adjudicate(document, family)
        self.assertEqual(result["family_id"], family.family_id)

    def test_missing_ledger_unit_is_rejected(self) -> None:
        document, family = sample_family()
        answer = {
            "family_id": family.family_id,
            "theme_label": "record preservation",
            "shared_payload": [],
            "centre_section": "Analysis",
            "centre_rationale": "Candidate only.",
            "occurrences": [],
            "unresolved_questions": [],
        }
        transport = lambda _: {"output_text": json.dumps(answer)}
        with self.assertRaisesRegex(OpenAIAdapterError, "ledger mismatch"):
            OpenAIAdjudicator(transport=transport).adjudicate(document, family)

    def test_unique_payload_blocks_full_removal(self) -> None:
        document, family = sample_family()
        occurrences = []
        for unit_id in family.unit_ids:
            occurrences.append(
                {
                    "unit_id": unit_id,
                    "semantic_relation": "partial_overlap",
                    "local_function": "context",
                    "disposition": "remove_fully_redundant",
                    "duplicated_payload": ["record preservation"],
                    "unique_residual_payload": ["a qualification"],
                    "hard_anchor_risk": [],
                    "rationale": "Unsafe proposal.",
                }
            )
        answer = {
            "family_id": family.family_id,
            "theme_label": "record preservation",
            "shared_payload": [],
            "centre_section": "Analysis",
            "centre_rationale": "Candidate only.",
            "occurrences": occurrences,
            "unresolved_questions": [],
        }
        transport = lambda _: {"output_text": json.dumps(answer)}
        with self.assertRaisesRegex(OpenAIAdapterError, "full removal"):
            OpenAIAdjudicator(transport=transport).adjudicate(document, family)


if __name__ == "__main__":
    unittest.main()

