from __future__ import annotations

import unittest

from repetita.global_verifier import verify_global_rewrite
from repetita.pipeline import analyse_document
from repetita.transaction import prepare_exact_transaction


class GlobalVerifierTests(unittest.TestCase):
    def test_transaction_accounts_for_transformed_donor(self) -> None:
        source = (
            "# Background\n\nThe archive preserves every original record.\n\n"
            "# Analysis\n\nThe archive preserves every original record."
        )
        analysis = analyse_document(source)
        transaction = prepare_exact_transaction(source, analysis.document, analysis.families[0])
        assert transaction is not None
        report = verify_global_rewrite(source, transaction.revised_document, [transaction])
        self.assertEqual(report.ledger_coverage, 1.0)
        self.assertFalse(report.missing_unit_ids)
        self.assertTrue(report.all_transactions_committed)

    def test_silent_unique_sentence_loss_fails(self) -> None:
        source = "# Evidence\n\nThe log contains 418 events. A unique qualification remains binding."
        revised = "# Evidence\n\nThe log contains 418 events."
        report = verify_global_rewrite(source, revised, [])
        self.assertEqual(report.status, "NOT_VERIFIED")
        self.assertLess(report.ledger_coverage, 1.0)
        self.assertTrue(report.missing_unit_ids)

    def test_hard_anchor_loss_fails_even_when_words_are_similar(self) -> None:
        source = "# Evidence\n\nThe measured log contains 418 events."
        revised = "# Evidence\n\nThe measured log contains many events."
        report = verify_global_rewrite(source, revised, [])
        self.assertEqual(report.status, "NOT_VERIFIED")
        self.assertIn("418", report.missing_hard_anchors)


if __name__ == "__main__":
    unittest.main()

