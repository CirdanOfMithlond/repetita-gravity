from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FrontendContractTests(unittest.TestCase):
    def test_workflow_exposes_all_nine_ordered_stages(self) -> None:
        html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
        steps = [int(value) for value in re.findall(r'data-step="(\d+)"', html)]
        self.assertEqual(steps, list(range(1, 10)))

    def test_final_certification_is_not_hardcoded(self) -> None:
        html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("VERIFIED BY REPETITA GRAVITY", html)
        self.assertNotIn("VERIFIED BY REPETITA GRAVITY", script)

    def test_frontend_has_no_external_asset_dependencies(self) -> None:
        html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
        self.assertNotRegex(html, r'https?://')

    def test_static_assets_use_project_pages_relative_paths(self) -> None:
        html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="./styles.css', html)
        self.assertIn('src="./app.js', html)
        self.assertNotIn('href="/styles.css', html)
        self.assertNotIn('src="/app.js', html)

    def test_static_demo_has_fail_closed_offline_fallback(self) -> None:
        script = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
        self.assertIn("./demo-data.json", script)
        self.assertIn("certifies the bundled sample only", script)
        self.assertIn("GPT-5.6 REFERENCE AUDIT + PYTHON RE-VERIFICATION", script)

    def test_stage_status_and_three_axis_classification_are_visible(self) -> None:
        script = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
        self.assertIn("LEDGER INDEXED", script)
        self.assertIn("RECURRENCES MAPPED", script)
        self.assertIn("SEMANTIC RELATION", script)
        self.assertIn("LOCAL FUNCTION", script)
        self.assertIn("EDITORIAL DISPOSITION", script)


if __name__ == "__main__":
    unittest.main()
