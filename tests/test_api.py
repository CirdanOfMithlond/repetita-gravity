from __future__ import annotations

import unittest

from repetita.api import analyse_payload, safe_pass_payload


class ApiTests(unittest.TestCase):
    def test_analyse_payload_returns_measurement_and_complexity(self) -> None:
        result = analyse_payload({"text": "# Note\n\nA unique complete statement remains."})
        self.assertIn("analysis", result)
        self.assertIn("complexity", result)
        self.assertEqual(result["analysis"]["document"]["title"], "Note")

    def test_empty_payload_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty"):
            analyse_payload({"text": ""})

    def test_safe_pass_returns_revised_document_and_global_report(self) -> None:
        text = (
            "# Background\n\nAccess reviews occur every 90 days.\n\n"
            "# Recommendations\n\nAccess reviews occur every 90 days."
        )
        result = safe_pass_payload({"text": text})
        self.assertIn("See Recommendations", result["revised_document"])
        self.assertEqual(result["global_verification"]["ledger_coverage"], 1.0)


if __name__ == "__main__":
    unittest.main()

