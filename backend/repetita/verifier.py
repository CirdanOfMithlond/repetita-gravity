from __future__ import annotations

from collections import Counter

from .models import AnalysisResult, Disposition, DocumentModel, RecurrenceFamily


def verify_analysis(document: DocumentModel, families: list[RecurrenceFamily]) -> tuple[dict[str, bool], list[str], str]:
    unit_ids = [unit.unit_id for unit in document.units]
    decision_ids = [decision.unit_id for family in families for decision in family.decisions]
    warnings: list[str] = []

    invariant_results = {
        "stable_unique_unit_ids": len(unit_ids) == len(set(unit_ids)),
        "all_family_occurrences_have_one_decision": all(Counter(decision_ids)[uid] == 1 for uid in set(decision_ids)),
        "every_family_has_a_gravity_centre": all(bool(family.gravity_centre) for family in families),
        "protected_occurrences_are_not_removed": all(
            decision.disposition != Disposition.REMOVE_FULLY_REDUNDANT
            for family in families
            for decision in family.decisions
            if decision.local_function.value in {"structural", "evidentiary"}
        ),
        "uncertain_occurrences_fail_closed": all(
            decision.disposition == Disposition.HUMAN_REVIEW
            for family in families
            for decision in family.decisions
            if decision.semantic_relation.value in {"uncertain", "related_non_duplicate"}
        ),
        "no_automatic_deletion_before_rewrite_verification": all(
            decision.disposition != Disposition.REMOVE_FULLY_REDUNDANT
            for family in families
            for decision in family.decisions
        ),
    }
    review_count = sum(
        decision.disposition == Disposition.HUMAN_REVIEW
        for family in families
        for decision in family.decisions
    )
    if review_count:
        warnings.append(f"{review_count} occurrence decision(s) require human or model-assisted adjudication.")
    if not families:
        warnings.append("No recurrence family crossed the conservative candidate threshold.")
    if not all(invariant_results.values()):
        status = "NOT_VERIFIED"
        warnings.append("At least one structural invariant failed.")
    elif review_count:
        status = "ANALYSIS_COMPLETE_REWRITE_WITHHELD"
    else:
        status = "ANALYSIS_VERIFIED_REWRITE_NOT_YET_RUN"
    return invariant_results, warnings, status


def assemble_result(document: DocumentModel, families: list[RecurrenceFamily]) -> AnalysisResult:
    invariants, warnings, status = verify_analysis(document, families)
    return AnalysisResult(document=document, families=families, invariants=invariants, warnings=warnings, status=status)

