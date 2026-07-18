from __future__ import annotations

import json
import unittest
from pathlib import Path

from repetita.pipeline import analyse_document


ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_json_schemas_parse(self) -> None:
        for path in (ROOT / "schemas").glob("*.json"):
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(data["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertFalse(data.get("additionalProperties", True))

    def test_transaction_schema_is_fail_closed(self) -> None:
        schema = json.loads((ROOT / "schemas" / "family-transaction.schema.json").read_text(encoding="utf-8"))
        states = schema["properties"]["state"]["enum"]
        self.assertIn("rolled_back", states)
        self.assertIn("human_review", states)

    def test_openai_strict_schemas_avoid_unsupported_unique_items_keyword(self) -> None:
        for name in (
            "family-adjudication.schema.json",
            "rewrite-proposal.schema.json",
            "semantic-verification.schema.json",
            "global-semantic-verification.schema.json",
        ):
            with self.subTest(schema=name):
                text = (ROOT / "schemas" / name).read_text(encoding="utf-8")
                self.assertNotIn("uniqueItems", text)

    def test_analysis_result_is_json_serializable(self) -> None:
        result = analyse_document("# Test\n\nA complete proposition remains available.")
        encoded = json.dumps(result.to_dict())
        self.assertIn("stable_unique_unit_ids", encoded)


if __name__ == "__main__":
    unittest.main()
