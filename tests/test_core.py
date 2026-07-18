from __future__ import annotations

import unittest

from repetita.models import Disposition, LocalFunction
from repetita.parser import extract_anchors, parse_document
from repetita.pipeline import analyse_document
from repetita.similarity import compare_units, detect_families


class ParserTests(unittest.TestCase):
    def test_empty_input_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "empty"):
            parse_document("  \n")

    def test_malformed_heading_falls_back_to_one_document_section(self) -> None:
        document = parse_document("#Not a heading\n\nA complete sentence remains available.")
        self.assertEqual(document.sections[0]["title"], "Document")
        self.assertEqual(len(document.units), 2)

    def test_stable_ids_are_deterministic(self) -> None:
        text = "# Test\n\nA stable proposition remains here."
        first = parse_document(text).units[0].unit_id
        second = parse_document(text).units[0].unit_id
        self.assertEqual(first, second)

    def test_hard_anchors_are_extracted(self) -> None:
        anchors = extract_anchors('The "Control Record" retained 418 events (Smith 2026).')
        self.assertIn("418", anchors.numbers)
        self.assertIn("Control Record", anchors.quotations)
        self.assertIn("(Smith 2026)", anchors.citations)


class ResourcePlanningTests(unittest.TestCase):
    def test_short_document_uses_whole_document_strategy(self) -> None:
        plan = parse_document("A short complete sentence.", context_limit=10_000).resource_plan
        self.assertEqual(plan.strategy, "whole_document")
        self.assertEqual(plan.initial_pass_cap, 1)

    def test_long_document_uses_structural_chunks(self) -> None:
        text = "# Long\n\n" + ("A substantive sentence contains several important words. " * 2000)
        plan = parse_document(text, context_limit=3_000, safety_ratio=0.50).resource_plan
        self.assertEqual(plan.strategy, "overlapping_structural_chunks_with_global_ledger")
        self.assertLessEqual(plan.initial_pass_cap, 5)


class RecurrenceTests(unittest.TestCase):
    def test_exact_repetition_forms_a_family(self) -> None:
        document = parse_document(
            "# One\n\nThe archive preserves every original record.\n\n"
            "# Two\n\nThe archive preserves every original record."
        )
        families = detect_families(document.units)
        self.assertEqual(len(families), 1)
        evidence = next(iter(families[0].pair_evidence.values()))
        self.assertGreaterEqual(evidence.composite, 0.92)

    def test_related_but_distinct_function_is_not_automatically_deleted(self) -> None:
        result = analyse_document(
            "# Evidence\n\nThe measured log contains 418 events and the archive preserves every original record.\n\n"
            "# Analysis\n\nThe archive preserves every original record so reviewers can reconstruct the transformation."
        )
        decisions = [decision for family in result.families for decision in family.decisions]
        self.assertTrue(decisions)
        evidence_decision = next(d for d in decisions if d.local_function == LocalFunction.EVIDENTIARY)
        self.assertEqual(evidence_decision.disposition, Disposition.PRESERVE_IN_PLACE)

    def test_intentional_method_recurrence_is_protected(self) -> None:
        result = analyse_document(
            "# Method\n\nAt every checkpoint the reviewer records the source transformation and result. "
            "At every checkpoint the reviewer records the source transformation and result."
        )
        decisions = [decision for family in result.families for decision in family.decisions]
        self.assertTrue(decisions)
        self.assertTrue(all(d.disposition == Disposition.PRESERVE_IN_PLACE for d in decisions))

    def test_partial_overlap_is_withheld_for_review(self) -> None:
        result = analyse_document(
            "# Background\n\nThe archive preserves every original record.\n\n"
            "# Analysis\n\nThe archive retains every original record, but temporary diagnostic traces expire after 30 days."
        )
        decisions = [decision for family in result.families for decision in family.decisions]
        self.assertTrue(decisions)
        self.assertIn(Disposition.HUMAN_REVIEW, {decision.disposition for decision in decisions})

    def test_weak_transitive_bridge_does_not_force_one_family(self) -> None:
        document = parse_document(
            "# Test\n\n"
            "The archive preserves every original record for verification. "
            "The archive keeps every record and evidence item for review. "
            "Evidence items support the final recommendation."
        )
        families = detect_families(document.units, candidate_threshold=0.38)
        self.assertTrue(all(len(family.unit_ids) <= 2 for family in families))


class VerificationTests(unittest.TestCase):
    def test_analysis_never_claims_final_rewrite_certification(self) -> None:
        result = analyse_document(
            "# One\n\nThe archive preserves every original record.\n\n"
            "# Two\n\nThe archive preserves every original record."
        )
        self.assertNotEqual(result.status, "VERIFIED_BY_REPETITA_GRAVITY")
        self.assertTrue(all(result.invariants.values()))


if __name__ == "__main__":
    unittest.main()
