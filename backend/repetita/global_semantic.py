from __future__ import annotations

import json
from typing import Any

from .global_verifier import GlobalVerificationReport
from .openai_adapter import OpenAIAdapterError, OpenAIAdjudicator, _extract_output_text
from .openai_rewrite import _anchors, _strict_response
from .parser import parse_document
from .transaction import FamilyTransaction


GLOBAL_SCHEMA = "global-semantic-verification.schema.json"


def validate_global_semantic_verification(verification: dict[str, Any], expected_unit_ids: set[str]) -> None:
    required = {
        "unit_checks",
        "evidence_preserved",
        "qualifications_preserved",
        "exceptions_preserved",
        "hard_anchors_preserved",
        "cross_references_resolve",
        "gravity_centres_coherent",
        "no_new_accidental_redundancy",
        "narrative_continuity",
        "overall",
        "failures",
    }
    if set(verification) != required:
        raise OpenAIAdapterError("Global semantic verification keys do not match the strict contract")
    check_ids = [check.get("unit_id") for check in verification["unit_checks"]]
    if len(check_ids) != len(set(check_ids)) or set(check_ids) != expected_unit_ids:
        missing = expected_unit_ids - set(check_ids)
        extra = set(check_ids) - expected_unit_ids
        raise OpenAIAdapterError(
            f"Global semantic ledger mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
        )
    document_checks = [
        verification["evidence_preserved"],
        verification["qualifications_preserved"],
        verification["exceptions_preserved"],
        verification["hard_anchors_preserved"],
        verification["cross_references_resolve"],
        verification["gravity_centres_coherent"],
        verification["no_new_accidental_redundancy"],
        verification["narrative_continuity"],
    ]
    unit_checks = [
        value
        for check in verification["unit_checks"]
        for key, value in check.items()
        if key
        in {
            "disposition_confirmed",
            "semantic_payload_preserved",
            "unique_content_preserved",
            "local_function_preserved",
            "hard_anchors_preserved",
        }
    ]
    if verification["overall"] == "passed" and (
        not all(document_checks + unit_checks) or verification["failures"]
    ):
        raise OpenAIAdapterError("Global semantic verifier claimed pass despite a failed check")


class OpenAIGlobalSemanticVerifier(OpenAIAdjudicator):
    """A second, whole-document model review that cannot mutate the document."""

    def build_verification_request(
        self,
        original_text: str,
        revised_text: str,
        formal_report: GlobalVerificationReport,
        transactions: list[FamilyTransaction],
        family_audits: list[dict[str, Any]],
    ) -> dict[str, Any]:
        original = parse_document(original_text)
        disposition_by_id = {item.unit_id: item for item in formal_report.dispositions}
        ledger = [
            {
                "unit_id": unit.unit_id,
                "original_text": unit.text,
                "section": unit.location.section_title,
                "discourse_role": unit.discourse_role.value,
                "local_function": unit.local_function.value,
                "hard_anchors": _anchors(unit),
                "formal_disposition": disposition_by_id[unit.unit_id].disposition,
                "formal_destination": disposition_by_id[unit.unit_id].destination,
            }
            for unit in original.units
        ]
        audits = [
            {
                "family_id": audit.get("family_id", ""),
                "status": audit.get("status", ""),
                "adjudication": audit.get("adjudication"),
                "semantic_verification": audit.get("semantic_verification"),
            }
            for audit in family_audits
        ]
        payload = {
            "immutable_original_document": original_text,
            "reconstructed_document": revised_text,
            "conservation_ledger": ledger,
            "committed_transactions": [transaction.to_dict() for transaction in transactions],
            "family_semantic_audits": audits,
            "formal_verification": formal_report.to_dict(),
        }
        prompt = (
            "Perform an independent final whole-document semantic review. You did not authorise the edits and must "
            "not trust the earlier family adjudications. Reconcile every immutable source unit exactly once against "
            "its formal disposition and the reconstructed document. Verify full semantic payload, unique content, "
            "local function, evidence, qualifications, limitations, exceptions, numbers, quotations, citations, "
            "cross-references, gravity-centre coherence, narrative continuity and absence of newly introduced "
            "accidental redundancy. Formal ledger coverage is necessary but not sufficient. Any material ambiguity "
            "requires human_review; any loss or meaning shift requires failed. Return only the strict schema."
        )
        return _strict_response(
            self.model,
            "repetita_global_semantic_verification",
            GLOBAL_SCHEMA,
            prompt,
            payload,
            reasoning_effort=self.reasoning_effort,
        )

    def verify(
        self,
        original_text: str,
        revised_text: str,
        formal_report: GlobalVerificationReport,
        transactions: list[FamilyTransaction],
        family_audits: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not self.available:
            raise OpenAIAdapterError("GPT-5.6 global semantic verification is unavailable")
        payload = self.build_verification_request(
            original_text,
            revised_text,
            formal_report,
            transactions,
            family_audits,
        )
        response = self._transport(payload) if self._transport else self._post(payload)
        try:
            verification = json.loads(_extract_output_text(response))
        except json.JSONDecodeError as error:
            raise OpenAIAdapterError("Global semantic verification was not valid JSON") from error
        expected_ids = {unit.unit_id for unit in parse_document(original_text).units}
        validate_global_semantic_verification(verification, expected_ids)
        return verification
