from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from .models import DocumentModel, RecurrenceFamily

API_ENDPOINT = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-5.6"
DEFAULT_REASONING_EFFORT = "high"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "family-adjudication.schema.json"

Transport = Callable[[dict[str, Any]], dict[str, Any]]


class OpenAIAdapterError(RuntimeError):
    pass


def load_adjudication_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _extract_output_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for part in item.get("content", []):
            if part.get("type") == "refusal":
                raise OpenAIAdapterError(f"Model refusal: {part.get('refusal', 'unspecified')}")
            if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                return part["text"]
    raise OpenAIAdapterError("Responses API returned no structured output text")


def validate_adjudication(data: dict[str, Any], expected_unit_ids: set[str]) -> None:
    required = {
        "family_id",
        "theme_label",
        "shared_payload",
        "centre_section",
        "centre_rationale",
        "occurrences",
        "unresolved_questions",
    }
    if set(data) != required:
        raise OpenAIAdapterError("Adjudication keys do not match the strict contract")
    occurrence_ids = [item.get("unit_id") for item in data["occurrences"]]
    if len(occurrence_ids) != len(set(occurrence_ids)):
        raise OpenAIAdapterError("Adjudication contains duplicate occurrence IDs")
    if set(occurrence_ids) != expected_unit_ids:
        missing = expected_unit_ids - set(occurrence_ids)
        extra = set(occurrence_ids) - expected_unit_ids
        raise OpenAIAdapterError(f"Adjudication ledger mismatch; missing={sorted(missing)}, extra={sorted(extra)}")
    for occurrence in data["occurrences"]:
        if occurrence["disposition"] == "remove_fully_redundant" and occurrence["unique_residual_payload"]:
            raise OpenAIAdapterError("Model proposed full removal while unique residual payload remains")
        if occurrence["hard_anchor_risk"] and occurrence["disposition"] not in {"preserve_in_place", "human_review"}:
            raise OpenAIAdapterError("Risked hard anchors require preservation or human review")


class OpenAIAdjudicator:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        transport: Transport | None = None,
        timeout_seconds: int = 120,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
        self.reasoning_effort = os.getenv("OPENAI_REASONING_EFFORT", DEFAULT_REASONING_EFFORT)
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    @property
    def available(self) -> bool:
        return bool(self.api_key or self._transport)

    def build_request(self, document: DocumentModel, family: RecurrenceFamily) -> dict[str, Any]:
        by_id = {unit.unit_id: unit for unit in document.units}
        occurrences = []
        for unit_id in family.unit_ids:
            unit = by_id[unit_id]
            occurrences.append(
                {
                    "unit_id": unit.unit_id,
                    "text": unit.text,
                    "section": unit.location.section_title,
                    "paragraph_index": unit.location.paragraph_index,
                    "deterministic_role": unit.discourse_role.value,
                    "deterministic_function": unit.local_function.value,
                    "hard_anchors": {
                        "numbers": list(unit.anchors.numbers),
                        "quotations": list(unit.anchors.quotations),
                        "citations": list(unit.anchors.citations),
                        "defined_terms": list(unit.anchors.defined_terms),
                    },
                }
            )
        evidence = {key: value.__dict__ for key, value in family.pair_evidence.items()}
        user_payload = {
            "document_title": document.title,
            "family_id": family.family_id,
            "deterministic_label": family.label,
            "candidate_centre": family.gravity_centre,
            "candidate_centre_scores": family.gravity_scores,
            "occurrences": occurrences,
            "pair_evidence": evidence,
        }
        instructions = (
            "Adjudicate one candidate recurrence family for conservative semantic consolidation. "
            "Separate semantic relation, local function, and editorial disposition. Similarity is evidence, not proof. "
            "Never authorise full removal if any unique proposition, fact, evidence, number, quotation, citation, "
            "qualification, exception, limitation, consequence, local function, or grammatical dependency remains. "
            "Preserve intentional structural recurrence and evidence that belongs locally. Use human_review whenever "
            "equivalence, residual payload, centre selection, or anchor safety is uncertain. Return only the schema."
        )
        schema = load_adjudication_schema()
        return {
            "model": self.model,
            "store": False,
            "reasoning": {"effort": self.reasoning_effort},
            "input": [
                {"role": "developer", "content": instructions},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "repetita_family_adjudication",
                    "strict": True,
                    "schema": {key: value for key, value in schema.items() if key not in {"$schema", "$id", "title"}},
                }
            },
        }

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise OpenAIAdapterError("OPENAI_API_KEY is not configured")
        request = urllib.request.Request(
            API_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise OpenAIAdapterError(f"Responses API error {error.code}: {body[:500]}") from error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise OpenAIAdapterError(f"Responses API transport failure: {error}") from error

    def adjudicate(self, document: DocumentModel, family: RecurrenceFamily) -> dict[str, Any]:
        if not self.available:
            raise OpenAIAdapterError("GPT-5.6 adjudication is unavailable; deterministic analysis remains active")
        payload = self.build_request(document, family)
        response = self._transport(payload) if self._transport else self._post(payload)
        try:
            adjudication = json.loads(_extract_output_text(response))
        except json.JSONDecodeError as error:
            raise OpenAIAdapterError("Structured output was not valid JSON") from error
        validate_adjudication(adjudication, set(family.unit_ids))
        if adjudication["family_id"] != family.family_id:
            raise OpenAIAdapterError("Adjudication returned the wrong family ID")
        valid_sections = {section["title"] for section in document.sections}
        if adjudication["centre_section"] not in valid_sections:
            raise OpenAIAdapterError("Adjudication selected a gravity centre that does not exist")
        by_id = {unit.unit_id: unit for unit in document.units}
        if not any(
            by_id[unit_id].location.section_title == adjudication["centre_section"]
            for unit_id in family.unit_ids
        ):
            raise OpenAIAdapterError("Adjudication selected a gravity centre with no family occurrence")
        return adjudication
