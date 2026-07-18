from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .global_verifier import verify_global_rewrite
from .openai_adapter import OpenAIAdapterError, OpenAIAdjudicator
from .openai_rewrite import OpenAISemanticVerifier, OpenAITransactionProposer
from .pipeline import analyse_document
from .transaction import apply_model_transaction


def run_model_family_transaction(
    source: str,
    family_id: str,
    *,
    adjudicator: OpenAIAdjudicator | None = None,
    proposer: OpenAITransactionProposer | None = None,
    semantic_verifier: OpenAISemanticVerifier | None = None,
) -> dict[str, Any]:
    analysis = analyse_document(source)
    family = next((item for item in analysis.families if item.family_id == family_id), None)
    if family is None:
        return {"status": "NOT_FOUND", "reason": "The requested recurrence family is not present in the current document."}
    adjudicator = adjudicator or OpenAIAdjudicator()
    proposer = proposer or OpenAITransactionProposer()
    semantic_verifier = semantic_verifier or OpenAISemanticVerifier()
    if not all(adapter.available for adapter in (adjudicator, proposer, semantic_verifier)):
        return {
            "status": "MODEL_UNAVAILABLE",
            "reason": "OPENAI_API_KEY is not configured; deterministic analysis and exact-safe transactions remain available.",
        }
    try:
        adjudication = adjudicator.adjudicate(analysis.document, family)
        if adjudication["unresolved_questions"] or any(
            occurrence["disposition"] == "human_review" for occurrence in adjudication["occurrences"]
        ):
            return {
                "status": "HUMAN_REVIEW",
                "reason": "Semantic adjudication identified unresolved risk; no rewrite was attempted.",
                "adjudication": adjudication,
            }
        proposal = proposer.propose(source, analysis.document, family, adjudication)
        verification = semantic_verifier.verify(analysis.document, family, proposal)
        transaction = apply_model_transaction(source, analysis.document, family, proposal, verification)
        global_report = verify_global_rewrite(source, transaction.revised_document, [transaction])
        return {
            "status": "COMMITTED" if transaction.state == "committed" else "ROLLED_BACK",
            "adjudication": adjudication,
            "proposal": proposal,
            "semantic_verification": verification,
            "transaction": transaction.to_dict(),
            "revised_document": transaction.revised_document,
            "global_verification": global_report.to_dict(),
        }
    except OpenAIAdapterError as error:
        return {"status": "ROLLED_BACK", "reason": str(error)}

