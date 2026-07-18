from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .models import DocumentModel, RecurrenceFamily
from .openai_adapter import OpenAIAdapterError, OpenAIAdjudicator, _extract_output_text

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"


def _load_schema(name: str) -> dict[str, Any]:
    schema = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
    return {key: value for key, value in schema.items() if key not in {"$schema", "$id", "title"}}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _anchors(unit) -> list[str]:
    return sorted(set(unit.anchors.numbers + unit.anchors.quotations + unit.anchors.citations + unit.anchors.defined_terms))


def _strict_response(
    model: str,
    schema_name: str,
    schema_file: str,
    developer: str,
    user_payload: dict,
    *,
    reasoning_effort: str = "high",
) -> dict:
    return {
        "model": model,
        "store": False,
        "reasoning": {"effort": reasoning_effort},
        "input": [
            {"role": "developer", "content": developer},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": True,
                "schema": _load_schema(schema_file),
            }
        },
    }


class OpenAITransactionProposer(OpenAIAdjudicator):
    def build_proposal_request(
        self,
        source: str,
        document: DocumentModel,
        family: RecurrenceFamily,
        adjudication: dict[str, Any],
    ) -> dict[str, Any]:
        by_id = {unit.unit_id: unit for unit in document.units}
        units = []
        for unit_id in family.unit_ids:
            unit = by_id[unit_id]
            context_start = max(0, unit.location.char_start - 300)
            context_end = min(len(source), unit.location.char_end + 300)
            units.append(
                {
                    "unit_id": unit_id,
                    "text": unit.text,
                    "source_text_sha256": _sha(unit.text),
                    "section": unit.location.section_title,
                    "local_context": source[context_start:context_end],
                    "hard_anchors": _anchors(unit),
                }
            )
        payload = {
            "family_id": family.family_id,
            "centre_section": adjudication["centre_section"],
            "adjudication": adjudication,
            "source_units": units,
        }
        prompt = (
            "Propose one isolated donor-repair and receiver-accretion transaction. Copy every original_text and its "
            "SHA-256 exactly. Do not edit preserved occurrences. For each donor, separate duplicated from unique "
            "residual payload before writing. The repair must remain grammatical, preserve local function and every "
            "hard anchor, and may become a precise cross-reference. The receiver must integrate every incoming unique "
            "payload with provenance rather than concatenate sentences. changed_unit_ids must be exactly the texts that "
            "change. If any safe repair is uncertain, use human_review and explain it in unresolved_questions."
        )
        return _strict_response(
            self.model,
            "repetita_rewrite_proposal",
            "rewrite-proposal.schema.json",
            prompt,
            payload,
            reasoning_effort=self.reasoning_effort,
        )

    def propose(self, source: str, document: DocumentModel, family: RecurrenceFamily, adjudication: dict[str, Any]) -> dict:
        payload = self.build_proposal_request(source, document, family, adjudication)
        response = self._transport(payload) if self._transport else self._post(payload)
        try:
            proposal = json.loads(_extract_output_text(response))
        except json.JSONDecodeError as error:
            raise OpenAIAdapterError("Rewrite proposal was not valid JSON") from error
        validate_rewrite_proposal(proposal, document, family)
        return proposal


def validate_rewrite_proposal(proposal: dict, document: DocumentModel, family: RecurrenceFamily) -> None:
    required = {"family_id", "centre_section", "donors", "receiver", "changed_unit_ids", "unresolved_questions"}
    if set(proposal) != required or proposal["family_id"] != family.family_id:
        raise OpenAIAdapterError("Rewrite proposal does not match the family contract")
    by_id = {unit.unit_id: unit for unit in document.units}
    family_ids = set(family.unit_ids)
    donor_ids = [donor["unit_id"] for donor in proposal["donors"]]
    if len(donor_ids) != len(set(donor_ids)) or not set(donor_ids).issubset(family_ids):
        raise OpenAIAdapterError("Rewrite proposal contains invalid or duplicate donor IDs")
    receiver = proposal["receiver"]
    if receiver["unit_id"] not in family_ids:
        raise OpenAIAdapterError("Rewrite receiver is outside the recurrence family")
    if by_id[receiver["unit_id"]].location.section_title != proposal["centre_section"]:
        raise OpenAIAdapterError("Rewrite receiver is outside the selected gravity centre")
    records = proposal["donors"] + [receiver]
    for record in records:
        unit = by_id[record["unit_id"]]
        if record["original_text"] != unit.text or record["source_text_sha256"] != _sha(unit.text):
            raise OpenAIAdapterError(f"Source binding failed for {unit.unit_id}")
    for donor in proposal["donors"]:
        if sorted(donor["hard_anchors"]) != _anchors(by_id[donor["unit_id"]]):
            raise OpenAIAdapterError(f"Hard-anchor inventory mismatch for {donor['unit_id']}")
        if donor["disposition"] == "remove_fully_redundant" and donor["unique_residual_payload"]:
            raise OpenAIAdapterError("Full removal is forbidden while residual payload remains")
    expected_changed = set(donor_ids)
    if receiver["proposed_text"] != receiver["original_text"]:
        expected_changed.add(receiver["unit_id"])
    if set(proposal["changed_unit_ids"]) != expected_changed:
        raise OpenAIAdapterError("changed_unit_ids does not match the actual proposal scope")


class OpenAISemanticVerifier(OpenAIAdjudicator):
    def build_verification_request(
        self,
        document: DocumentModel,
        family: RecurrenceFamily,
        proposal: dict[str, Any],
    ) -> dict[str, Any]:
        by_id = {unit.unit_id: unit for unit in document.units}
        original = [
            {
                "unit_id": unit_id,
                "text": by_id[unit_id].text,
                "section": by_id[unit_id].location.section_title,
                "local_function": by_id[unit_id].local_function.value,
                "hard_anchors": _anchors(by_id[unit_id]),
            }
            for unit_id in family.unit_ids
        ]
        payload = {"family_id": family.family_id, "original_occurrences": original, "rewrite_proposal": proposal}
        prompt = (
            "Independently verify a proposed recurrence-family rewrite. Do not assume the prior adjudication is correct. "
            "For every original unit, test whether its full payload, unique residual payload, local function and hard "
            "anchors survive in the donor repair, receiver or preserved occurrence. Test for changed meaning, broken "
            "narrative continuity and new duplication. A single material uncertainty requires human_review; a failed "
            "check requires failed. Return one check for every original unit ID and only the strict schema."
        )
        return _strict_response(
            self.model,
            "repetita_semantic_verification",
            "semantic-verification.schema.json",
            prompt,
            payload,
            reasoning_effort=self.reasoning_effort,
        )

    def verify(self, document: DocumentModel, family: RecurrenceFamily, proposal: dict[str, Any]) -> dict:
        payload = self.build_verification_request(document, family, proposal)
        response = self._transport(payload) if self._transport else self._post(payload)
        try:
            verification = json.loads(_extract_output_text(response))
        except json.JSONDecodeError as error:
            raise OpenAIAdapterError("Semantic verification was not valid JSON") from error
        validate_semantic_verification(verification, family)
        return verification


def validate_semantic_verification(verification: dict, family: RecurrenceFamily) -> None:
    required = {
        "family_id",
        "unit_checks",
        "receiver_complete",
        "no_new_duplication",
        "no_meaning_shift",
        "narrative_continuity",
        "overall",
        "failures",
    }
    if set(verification) != required or verification["family_id"] != family.family_id:
        raise OpenAIAdapterError("Semantic verification does not match the family contract")
    check_ids = [check["unit_id"] for check in verification["unit_checks"]]
    if set(check_ids) != set(family.unit_ids) or len(check_ids) != len(set(check_ids)):
        raise OpenAIAdapterError("Semantic verification does not reconcile every family unit exactly once")
    booleans = [
        verification["receiver_complete"],
        verification["no_new_duplication"],
        verification["no_meaning_shift"],
        verification["narrative_continuity"],
    ]
    booleans.extend(
        value
        for check in verification["unit_checks"]
        for key, value in check.items()
        if key in {"original_payload_covered", "unique_residual_covered", "local_function_preserved", "hard_anchors_preserved"}
    )
    if verification["overall"] == "passed" and (not all(booleans) or verification["failures"]):
        raise OpenAIAdapterError("Semantic verifier claimed pass despite a failed check")
