from __future__ import annotations

import unittest

from repetita.pass_controller import run_deterministic_safe_pass
from repetita.pipeline import analyse_document
from repetita.transaction import document_hash, prepare_exact_transaction


class TransactionTests(unittest.TestCase):
    def test_exact_duplicate_commits_as_resolving_cross_reference(self) -> None:
        source = (
            "# Background\n\nThe archive preserves every original record.\n\n"
            "# Analysis\n\nThe archive preserves every original record."
        )
        analysis = analyse_document(source)
        transaction = prepare_exact_transaction(source, analysis.document, analysis.families[0])
        self.assertIsNotNone(transaction)
        assert transaction is not None
        self.assertEqual(transaction.state, "committed")
        self.assertIn("See Analysis", transaction.revised_document)
        self.assertEqual(transaction.base_document_hash, document_hash(source))
        self.assertTrue(transaction.verification.ledger_reconciled)
        self.assertTrue(transaction.verification.scope_isolated)

    def test_evidence_duplicate_is_not_deterministically_moved(self) -> None:
        source = (
            "# Evidence\n\nThe measured record contains 418 events.\n\n"
            "# Analysis\n\nThe measured record contains 418 events."
        )
        analysis = analyse_document(source)
        transaction = prepare_exact_transaction(source, analysis.document, analysis.families[0])
        self.assertIsNone(transaction)

    def test_partial_overlap_is_not_transaction_eligible(self) -> None:
        source = (
            "# Background\n\nThe archive preserves every original record.\n\n"
            "# Analysis\n\nThe archive retains every original record, but temporary traces expire after 30 days."
        )
        analysis = analyse_document(source)
        self.assertTrue(analysis.families)
        transaction = prepare_exact_transaction(source, analysis.document, analysis.families[0])
        self.assertIsNone(transaction)

    def test_pass_reanalyses_after_each_atomic_commit(self) -> None:
        source = (
            "# Background\n\nThe archive preserves every original record.\n\n"
            "# Analysis\n\nThe archive preserves every original record.\n\n"
            "# Recommendations\n\nThe archive preserves every original record."
        )
        result = run_deterministic_safe_pass(source)
        self.assertGreaterEqual(len(result.transactions), 1)
        self.assertIn("See Analysis", result.revised_document)
        self.assertNotEqual(result.original_document, result.revised_document)


if __name__ == "__main__":
    unittest.main()

