from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class DiscourseRole(StrEnum):
    CLAIM = "claim"
    REASON = "reason"
    EVIDENCE = "evidence"
    FACT = "fact"
    QUALIFICATION = "qualification"
    LIMITATION = "limitation"
    EXCEPTION = "exception"
    CONSEQUENCE = "consequence"
    RECOMMENDATION = "recommendation"
    DEFINITION = "definition"
    CROSS_REFERENCE = "cross_reference"
    STRUCTURAL_FORMULA = "structural_formula"
    UNKNOWN = "unknown"


class SemanticRelation(StrEnum):
    EXACT_EQUIVALENT = "exact_equivalent"
    PARAPHRASE_EQUIVALENT = "paraphrase_equivalent"
    PARTIAL_OVERLAP = "partial_overlap"
    RELATED_NON_DUPLICATE = "related_non_duplicate"
    UNCERTAIN = "uncertain"


class LocalFunction(StrEnum):
    STRUCTURAL = "structural"
    SUMMARY = "summary"
    CONTEXT = "context"
    EVIDENTIARY = "evidentiary"
    ANALYTICAL = "analytical"
    RECOMMENDATORY = "recommendatory"
    CONCLUSIVE = "conclusive"
    DEFINITORY = "definitory"
    TRANSITIONAL = "transitional"
    UNKNOWN = "unknown"


class Disposition(StrEnum):
    PRESERVE_IN_PLACE = "preserve_in_place"
    TRANSFER_TO_CENTRE = "transfer_to_centre"
    MERGE_INTO_CENTRE = "merge_into_centre"
    CONVERT_TO_CROSS_REFERENCE = "convert_to_cross_reference"
    REMOVE_FULLY_REDUNDANT = "remove_fully_redundant"
    HUMAN_REVIEW = "human_review"


@dataclass(frozen=True)
class SourceLocation:
    section_id: str
    section_title: str
    paragraph_index: int
    sentence_index: int
    char_start: int
    char_end: int


@dataclass(frozen=True)
class HardAnchors:
    numbers: tuple[str, ...] = ()
    quotations: tuple[str, ...] = ()
    citations: tuple[str, ...] = ()
    defined_terms: tuple[str, ...] = ()


@dataclass
class SemanticUnit:
    unit_id: str
    text: str
    normalized_text: str
    location: SourceLocation
    discourse_role: DiscourseRole
    local_function: LocalFunction
    anchors: HardAnchors
    tokens: frozenset[str]


@dataclass(frozen=True)
class SimilarityEvidence:
    lexical_overlap: float
    concept_overlap: float
    anchor_overlap: float
    role_compatibility: float
    composite: float


@dataclass
class OccurrenceDecision:
    unit_id: str
    semantic_relation: SemanticRelation
    local_function: LocalFunction
    disposition: Disposition
    confidence: float
    rationale: str
    unique_residual_tokens: tuple[str, ...] = ()


@dataclass
class RecurrenceFamily:
    family_id: str
    label: str
    unit_ids: list[str]
    pair_evidence: dict[str, SimilarityEvidence]
    sections: list[str]
    risk_score: float = 0.0
    gravity_centre: str | None = None
    gravity_scores: dict[str, float] = field(default_factory=dict)
    competing_centre: str | None = None
    competing_score: float = 0.0
    gravity_rationale: str = ""
    decisions: list[OccurrenceDecision] = field(default_factory=list)


@dataclass(frozen=True)
class ResourcePlan:
    estimated_tokens: int
    configured_context_limit: int
    safe_input_budget: int
    context_pressure: float
    strategy: str
    overlapping_chunks: int
    initial_pass_cap: int
    rationale: str


@dataclass
class DocumentModel:
    title: str
    sections: list[dict[str, Any]]
    units: list[SemanticUnit]
    resource_plan: ResourcePlan


@dataclass
class AnalysisResult:
    document: DocumentModel
    families: list[RecurrenceFamily]
    invariants: dict[str, bool]
    warnings: list[str]
    status: str

    def to_dict(self) -> dict[str, Any]:
        def normalize(value: Any) -> Any:
            if isinstance(value, dict):
                return {str(key): normalize(item) for key, item in value.items()}
            if isinstance(value, (list, tuple, set, frozenset)):
                return [normalize(item) for item in value]
            if isinstance(value, StrEnum):
                return value.value
            return value

        return normalize(asdict(self))
