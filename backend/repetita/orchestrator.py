from __future__ import annotations

from typing import Any

from .global_semantic import OpenAIGlobalSemanticVerifier
from .global_verifier import verify_global_rewrite
from .openai_adapter import OpenAIAdapterError, OpenAIAdjudicator
from .openai_rewrite import OpenAISemanticVerifier, OpenAITransactionProposer
from .pass_controller import run_deterministic_safe_pass
from .pipeline import analyse_document
from .transaction import FamilyTransaction, apply_model_transaction


def _model_family_step(
    source: str,
    family_id: str,
    *,
    adjudicator: OpenAIAdjudicator,
    proposer: OpenAITransactionProposer,
    semantic_verifier: OpenAISemanticVerifier,
) -> tuple[dict[str, Any], FamilyTransaction | None]:
    analysis = analyse_document(source)
    family = next((item for item in analysis.families if item.family_id == family_id), None)
    if family is None:
        return (
            {
                "status": "NOT_FOUND",
                "family_id": family_id,
                "reason": "The requested recurrence family is not present in the current document.",
            },
            None,
        )
    if not all(adapter.available for adapter in (adjudicator, proposer, semantic_verifier)):
        return (
            {
                "status": "MODEL_UNAVAILABLE",
                "family_id": family_id,
                "reason": (
                    "OPENAI_API_KEY is not configured; deterministic analysis and exact-safe transactions remain "
                    "available."
                ),
            },
            None,
        )
    try:
        adjudication = adjudicator.adjudicate(analysis.document, family)
        if adjudication["unresolved_questions"] or any(
            occurrence["disposition"] == "human_review" for occurrence in adjudication["occurrences"]
        ):
            return (
                {
                    "status": "HUMAN_REVIEW",
                    "family_id": family_id,
                    "reason": "Semantic adjudication identified unresolved risk; no rewrite was attempted.",
                    "adjudication": adjudication,
                },
                None,
            )
        if all(occurrence["disposition"] == "preserve_in_place" for occurrence in adjudication["occurrences"]):
            return (
                {
                    "status": "PRESERVED",
                    "family_id": family_id,
                    "reason": "GPT-5.6 found intentional or functionally necessary recurrence; no text was changed.",
                    "resolved_unit_ids": list(family.unit_ids),
                    "adjudication": adjudication,
                },
                None,
            )
        proposal = proposer.propose(source, analysis.document, family, adjudication)
        verification = semantic_verifier.verify(analysis.document, family, proposal)
        transaction = apply_model_transaction(source, analysis.document, family, proposal, verification)
        return (
            {
                "status": "COMMITTED" if transaction.state == "committed" else "ROLLED_BACK",
                "family_id": family_id,
                "reason": (
                    "Model proposal passed family-level semantic and deterministic transaction gates."
                    if transaction.state == "committed"
                    else "The proposed rewrite failed at least one transaction gate and was rolled back."
                ),
                "adjudication": adjudication,
                "proposal": proposal,
                "semantic_verification": verification,
                "transaction": transaction.to_dict(),
                "revised_document": transaction.revised_document,
            },
            transaction,
        )
    except OpenAIAdapterError as error:
        return (
            {"status": "ROLLED_BACK", "family_id": family_id, "reason": str(error)},
            None,
        )


def run_model_family_transaction(
    source: str,
    family_id: str,
    *,
    adjudicator: OpenAIAdjudicator | None = None,
    proposer: OpenAITransactionProposer | None = None,
    semantic_verifier: OpenAISemanticVerifier | None = None,
) -> dict[str, Any]:
    adjudicator = adjudicator or OpenAIAdjudicator()
    proposer = proposer or OpenAITransactionProposer()
    semantic_verifier = semantic_verifier or OpenAISemanticVerifier()
    result, transaction = _model_family_step(
        source,
        family_id,
        adjudicator=adjudicator,
        proposer=proposer,
        semantic_verifier=semantic_verifier,
    )
    if transaction and transaction.state == "committed":
        result["global_verification"] = verify_global_rewrite(
            source,
            transaction.revised_document,
            [transaction],
        ).to_dict()
    return result


def _family_signature(analysis, family) -> tuple[tuple[str, str], ...]:
    by_id = {unit.unit_id: unit for unit in analysis.document.units}
    return tuple(
        sorted(
            (by_id[unit_id].location.section_title, by_id[unit_id].normalized_text)
            for unit_id in family.unit_ids
        )
    )


def _public_audit(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "revised_document"}


def run_hybrid_gravity_pass(
    source: str,
    *,
    adjudicator: OpenAIAdjudicator | None = None,
    proposer: OpenAITransactionProposer | None = None,
    semantic_verifier: OpenAISemanticVerifier | None = None,
    global_semantic_verifier: OpenAIGlobalSemanticVerifier | None = None,
    max_model_families: int = 20,
) -> dict[str, Any]:
    """Run exact-safe work, then bounded GPT family work, and certify only after a second global review."""
    deterministic = run_deterministic_safe_pass(source)
    working = deterministic.revised_document
    transactions = list(deterministic.transactions)
    resolved_unit_ids: set[str] = set()
    family_audits: list[dict[str, Any]] = []
    attempted_signatures: set[tuple[tuple[str, str], ...]] = set()

    adjudicator = adjudicator or OpenAIAdjudicator()
    proposer = proposer or OpenAITransactionProposer()
    semantic_verifier = semantic_verifier or OpenAISemanticVerifier()
    global_semantic_verifier = global_semantic_verifier or OpenAIGlobalSemanticVerifier()
    family_model_available = all(
        adapter.available for adapter in (adjudicator, proposer, semantic_verifier)
    )

    if family_model_available:
        for _ in range(max_model_families):
            analysis = analyse_document(working)
            candidate = next(
                (
                    family
                    for family in analysis.families
                    if any(decision.disposition.value == "human_review" for decision in family.decisions)
                    and _family_signature(analysis, family) not in attempted_signatures
                ),
                None,
            )
            if candidate is None:
                break
            attempted_signatures.add(_family_signature(analysis, candidate))
            result, transaction = _model_family_step(
                working,
                candidate.family_id,
                adjudicator=adjudicator,
                proposer=proposer,
                semantic_verifier=semantic_verifier,
            )
            family_audits.append(_public_audit(result))
            if result["status"] == "PRESERVED":
                resolved_unit_ids.update(result["resolved_unit_ids"])
            elif transaction and transaction.state == "committed":
                transactions.append(transaction)
                working = transaction.revised_document
    else:
        family_audits.append(
            {
                "status": "MODEL_UNAVAILABLE",
                "family_id": "",
                "reason": (
                    "No server-side OPENAI_API_KEY is configured. Ambiguous recurrence families remain fail-closed."
                ),
            }
        )

    formal_report = verify_global_rewrite(
        source,
        working,
        transactions,
        semantically_resolved_unit_ids=resolved_unit_ids,
    )
    formal_passed = formal_report.ledger_coverage == 1.0 and not formal_report.failures
    global_semantic: dict[str, Any]
    original_plan = analyse_document(source).document.resource_plan
    if not formal_passed:
        global_semantic = {
            "status": "NOT_RUN",
            "reason": "Formal conservation failed; semantic certification is blocked.",
        }
    elif formal_report.unresolved_occurrences:
        global_semantic = {
            "status": "NOT_RUN",
            "reason": (
                f"{formal_report.unresolved_occurrences} occurrence(s) remain unresolved after family adjudication."
            ),
        }
    elif original_plan.strategy != "whole_document":
        global_semantic = {
            "status": "WITHHELD",
            "reason": (
                "Whole-document semantic certification is withheld because this input requires structural chunking; "
                "the hackathon MVP does not yet run the required cross-chunk synthesis verifier."
            ),
        }
    elif not global_semantic_verifier.available:
        global_semantic = {
            "status": "MODEL_UNAVAILABLE",
            "reason": "A server-side OPENAI_API_KEY is required for independent global semantic review.",
        }
    else:
        try:
            verification = global_semantic_verifier.verify(
                source,
                working,
                formal_report,
                transactions,
                family_audits,
            )
            global_semantic = {
                "status": verification["overall"].upper(),
                "model": global_semantic_verifier.model,
                "verification": verification,
            }
        except OpenAIAdapterError as error:
            global_semantic = {"status": "FAILED", "reason": str(error)}

    eligible = formal_passed and not formal_report.unresolved_occurrences and global_semantic["status"] == "PASSED"
    reasons: list[str] = []
    reasons.extend(formal_report.failures)
    if formal_report.unresolved_occurrences:
        reasons.append(f"{formal_report.unresolved_occurrences} occurrence(s) still require semantic adjudication")
    elif global_semantic["status"] != "PASSED":
        reasons.append(global_semantic.get("reason", f"Global semantic review status: {global_semantic['status']}"))
    if eligible:
        stop_reason = (
            "The reconstructed document passed formal conservation and independent whole-document semantic review; "
            "no further pass is justified."
        )
    elif any(audit["status"] == "HUMAN_REVIEW" for audit in family_audits):
        stop_reason = "Automation stopped because at least one family exceeds the acceptable semantic-risk threshold."
    else:
        stop_reason = deterministic.stop_reason

    model_status = (
        "MODEL_UNAVAILABLE"
        if not family_model_available
        else "COMPLETE"
        if not formal_report.unresolved_occurrences
        else "HUMAN_REVIEW"
    )
    return {
        "original_document": source,
        "revised_document": working,
        "transactions": [transaction.to_dict() for transaction in transactions],
        "stop_reason": stop_reason,
        "eligible_families_remaining": deterministic.eligible_families_remaining,
        "family_audits": family_audits,
        "model_status": model_status,
        "global_verification": formal_report.to_dict(),
        "global_semantic_verification": global_semantic,
        "certification": {
            "eligible": eligible,
            "label": "VERIFIED BY REPETITA GRAVITY" if eligible else "NOT YET VERIFIED",
            "reasons": reasons,
        },
        "revised_analysis": analyse_document(working).to_dict(),
    }
