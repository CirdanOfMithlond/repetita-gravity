from __future__ import annotations

from collections import defaultdict

from .models import (
    Disposition,
    DocumentModel,
    LocalFunction,
    OccurrenceDecision,
    RecurrenceFamily,
    SemanticRelation,
)
from .similarity import STOPWORDS

PROTECTED_FUNCTIONS = {LocalFunction.STRUCTURAL, LocalFunction.EVIDENTIARY}
CENTER_FIT: dict[LocalFunction, float] = {
    LocalFunction.ANALYTICAL: 1.00,
    LocalFunction.DEFINITORY: 0.95,
    LocalFunction.RECOMMENDATORY: 0.90,
    LocalFunction.CONTEXT: 0.65,
    LocalFunction.CONCLUSIVE: 0.45,
    LocalFunction.SUMMARY: 0.35,
    LocalFunction.EVIDENTIARY: 0.30,
    LocalFunction.STRUCTURAL: 0.20,
    LocalFunction.TRANSITIONAL: 0.20,
    LocalFunction.UNKNOWN: 0.10,
}


def _relation(score: float) -> SemanticRelation:
    if score >= 0.92:
        return SemanticRelation.EXACT_EQUIVALENT
    if score >= 0.68:
        return SemanticRelation.PARAPHRASE_EQUIVALENT
    if score >= 0.50:
        return SemanticRelation.PARTIAL_OVERLAP
    if score >= 0.43:
        return SemanticRelation.UNCERTAIN
    return SemanticRelation.RELATED_NON_DUPLICATE


def plan_families(document: DocumentModel, families: list[RecurrenceFamily]) -> list[RecurrenceFamily]:
    by_id = {unit.unit_id: unit for unit in document.units}
    for family in families:
        section_units: dict[str, list] = defaultdict(list)
        for unit_id in family.unit_ids:
            section_units[by_id[unit_id].location.section_title].append(by_id[unit_id])

        for section, units in section_units.items():
            role_fit = max(CENTER_FIT[unit.local_function] for unit in units)
            completeness = min(1.0, sum(len(unit.tokens) for unit in units) / 45)
            evidence_proximity = 1.0 if any(unit.local_function == LocalFunction.EVIDENTIARY for unit in units) else 0.45
            coherence = 1.0 if len(units) > 1 else 0.65
            disruption = 1.0 / (1 + max(0, len(family.sections) - 1))
            score = 0.35 * role_fit + 0.25 * completeness + 0.15 * evidence_proximity + 0.15 * coherence + 0.10 * disruption
            family.gravity_scores[section] = round(score, 4)
        family.gravity_centre = max(family.gravity_scores, key=family.gravity_scores.get)

        pair_scores_by_unit: dict[str, list[float]] = defaultdict(list)
        for pair, evidence in family.pair_evidence.items():
            left, right = pair.split("|")
            pair_scores_by_unit[left].append(evidence.composite)
            pair_scores_by_unit[right].append(evidence.composite)

        family.decisions = []
        for unit_id in family.unit_ids:
            unit = by_id[unit_id]
            average = sum(pair_scores_by_unit[unit_id]) / max(1, len(pair_scores_by_unit[unit_id]))
            relation = _relation(average)
            own_content = {token for token in unit.tokens if len(token) > 2 and token not in STOPWORDS}
            other_content = set().union(
                *(
                    {token for token in by_id[other_id].tokens if len(token) > 2 and token not in STOPWORDS}
                    for other_id in family.unit_ids
                    if other_id != unit_id
                )
            )
            unique_residual = tuple(sorted(own_content - other_content))
            if (
                relation == SemanticRelation.PARAPHRASE_EQUIVALENT
                and unit.normalized_text not in {by_id[other_id].normalized_text for other_id in family.unit_ids if other_id != unit_id}
                and len(unique_residual) >= 3
            ):
                relation = SemanticRelation.PARTIAL_OVERLAP
            at_centre = unit.location.section_title == family.gravity_centre
            if unit.local_function in PROTECTED_FUNCTIONS:
                disposition = Disposition.PRESERVE_IN_PLACE
                rationale = "Protected structural or evidentiary function remains local."
            elif relation in {SemanticRelation.UNCERTAIN, SemanticRelation.RELATED_NON_DUPLICATE}:
                disposition = Disposition.HUMAN_REVIEW
                rationale = "Semantic equivalence is not strong enough for automatic consolidation."
            elif at_centre:
                disposition = Disposition.PRESERVE_IN_PLACE
                rationale = "Occurrence is located at the selected logical gravity centre."
            elif unit.local_function in {LocalFunction.SUMMARY, LocalFunction.CONCLUSIVE}:
                disposition = Disposition.PRESERVE_IN_PLACE
                rationale = "Necessary functional echo is retained outside the canonical treatment."
            elif relation == SemanticRelation.PARTIAL_OVERLAP:
                disposition = Disposition.HUMAN_REVIEW
                rationale = "Partial overlap contains potential unique residual payload; removal is forbidden."
            else:
                disposition = Disposition.MERGE_INTO_CENTRE
                rationale = "Probable redundant payload may be merged, subject to donor and coverage verification."
            family.decisions.append(
                OccurrenceDecision(
                    unit_id=unit_id,
                    semantic_relation=relation,
                    local_function=unit.local_function,
                    disposition=disposition,
                    confidence=round(average, 4),
                    rationale=rationale,
                    unique_residual_tokens=unique_residual,
                )
            )

        section_spread = len(family.sections) / max(1, len(document.sections))
        unique_density = sum(1 for d in family.decisions if d.semantic_relation == SemanticRelation.PARTIAL_OVERLAP) / len(family.decisions)
        ambiguity = sum(1 for d in family.decisions if d.disposition == Disposition.HUMAN_REVIEW) / len(family.decisions)
        centrality = min(1.0, len(family.unit_ids) / max(2, len(document.units)))
        family.risk_score = round(0.30 * unique_density + 0.25 * section_spread + 0.25 * ambiguity + 0.20 * centrality, 4)

    return sorted(families, key=lambda family: (family.risk_score, len(family.unit_ids)))
