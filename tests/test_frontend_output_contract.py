from __future__ import annotations

import unittest
from pathlib import Path

from repetita.api import safe_pass_payload


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "sample-data" / "adversarial-professional.md"
FRONTEND_OUTPUT = ROOT / "frontend" / "output.js"
FRONTEND_INDEX = ROOT / "frontend" / "index.html"
OUTPUT_STYLES = ROOT / "frontend" / "output.css"


class DeliverableOutputContractTests(unittest.TestCase):
    def test_release_preserves_original_and_returns_revised_document(self) -> None:
        source = SAMPLE.read_text(encoding="utf-8")
        release = safe_pass_payload({"text": source})

        self.assertEqual(release["original_document"], source)
        self.assertTrue(release["revised_document"].strip())
        self.assertNotEqual(release["revised_document"], source)
        self.assertTrue(release["transactions"])
        self.assertTrue(release["certification"]["eligible"])

    def test_frontend_exposes_revised_compare_copy_and_download_controls(self) -> None:
        output = FRONTEND_OUTPUT.read_text(encoding="utf-8")
        index = FRONTEND_INDEX.read_text(encoding="utf-8")

        for required_token in (
            "COMPLETE REVISED DOCUMENT",
            'data-output-view="compare"',
            'data-output-view="original"',
            'data-output-action="copy"',
            'data-output-action="download"',
            "repetita-gravity-revised.txt",
        ):
            self.assertIn(required_token, output)

        self.assertIn("output.css", index)
        self.assertIn("output.js", index)
        self.assertTrue(OUTPUT_STYLES.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    unittest.main()
