from __future__ import annotations

from .models import AnalysisResult
from .parser import parse_document
from .planner import plan_families
from .similarity import detect_families
from .verifier import assemble_result


def analyse_document(
    text: str,
    *,
    context_limit: int = 1_000_000,
    safety_ratio: float = 0.60,
    candidate_threshold: float = 0.43,
) -> AnalysisResult:
    document = parse_document(text, context_limit=context_limit, safety_ratio=safety_ratio)
    families = detect_families(document.units, candidate_threshold=candidate_threshold)
    planned = plan_families(document, families)
    return assemble_result(document, planned)

