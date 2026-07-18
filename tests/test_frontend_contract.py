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


if __name__ == "__main__":
    unittest.main()

