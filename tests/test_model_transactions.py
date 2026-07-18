from __future__ import annotations

import hashlib
import unittest

from repetita.pipeline import analyse_document
from repetita.transaction import apply_model_transaction


def bound(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def fixture():
    source = (
        "# Background\n\nThe archive preserves every original record.\n\n"
        "# Analysis\n\nThe archive preserves every original record and supports later verification."
    )
    analysis = analyse_document(source)
    family = analysis.families[0]
    units = {unit.unit_id: unit for unit in analysis.document.units}
    background = next(unit for unit in units.values() if unit.location.section_title == "Background")
    receiver = next(unit for unit in units.values() if unit.location.section_title == "Analysis")
    proposal = {
        "family_id": family.family_id,
        "centre_section": "Analysis",
        "donors": [
            {
                "unit_id": background.unit_id,
                "source_text_sha256": bound(background.text),
                "original_text": background.text,
                "duplicated_payload": ["The archive preserves every original record."],
                "unique_residual_payload": [],
                "local_function": "context",
                "grammatical_dependencies": [],
                "hard_anchors": [],
                "disposition": "convert_to_cross_reference",
                "proposed_repair": "See Analysis for the archive-preservation treatment.",
            }
        ],
        "receiver": {
            "unit_id": receiver.unit_id,
            "source_text_sha256": bound(receiver.text),
            "original_text": receiver.text,
            "incoming_payload": ["The archive preserves every original record."],
            "proposed_text": receiver.text,
            "provenance": [
                {"source_unit_id": background.unit_id, "integrated_payload": ["The archive preserves every original record."]}
            ],
        },
        "changed_unit_ids": [background.unit_id],
        "unresolved_questions": [],
    }
    checks = [
        {
            "unit_id": unit_id,
            "original_payload_covered": True,
            "unique_residual_covered": True,
            "local_function_preserved": True,
            "hard_anchors_preserved": True,
            "rationale": "Payload remains at the receiver or resolves through the cross-reference.",
        }
        for unit_id in family.unit_ids
    ]
    verification = {
        "family_id": family.family_id,
        "unit_checks": checks,
        "receiver_complete": True,
        "no_new_duplication": True,
        "no_meaning_shift": True,
        "narrative_continuity": True,
        "overall": "passed",
        "failures": [],
    }
    return source, analysis, family, proposal, verification


class ModelTransactionTests(unittest.TestCase):
    def test_verified_proposal_commits_atomically(self) -> None:
        source, analysis, family, proposal, verification = fixture()
        transaction = apply_model_transaction(source, analysis.document, family, proposal, verification)
        self.assertEqual(transaction.state, "committed")
        self.assertIn("See Analysis", transaction.revised_document)
        self.assertTrue(transaction.verification.ledger_reconciled)

    def test_unresolved_proposal_rolls_back(self) -> None:
        source, analysis, family, proposal, verification = fixture()
        proposal["unresolved_questions"] = ["The donor may have an intentional rhetorical function."]
        transaction = apply_model_transaction(source, analysis.document, family, proposal, verification)
        self.assertEqual(transaction.state, "rolled_back")
        self.assertEqual(transaction.revised_document, source)

    def test_failed_semantic_verification_rolls_back(self) -> None:
        source, analysis, family, proposal, verification = fixture()
        verification["overall"] = "failed"
        verification["failures"] = ["Local function was not preserved."]
        verification["unit_checks"][0]["local_function_preserved"] = False
        transaction = apply_model_transaction(source, analysis.document, family, proposal, verification)
        self.assertEqual(transaction.state, "rolled_back")
        self.assertEqual(transaction.revised_document, source)


if __name__ == "__main__":
    unittest.main()

