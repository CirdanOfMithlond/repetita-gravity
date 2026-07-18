from __future__ import annotations

from dataclasses import asdict, dataclass
from difflib import SequenceMatcher

from .models import AnalysisResult, Disposition


@dataclass(frozen=True)
class ComplexityMetrics:
    context_pressure: float
    section_complexity: float
    repetition_density: float
    thematic_dispersion: float
    cross_section_dependency: float
    complexity_index: float
    planned_passes: int
    rationale: str


@dataclass(frozen=True)
class PassMetrics:
    pass_number: int
    repetition_burden: float
    substantive_ledger_coverage: float
    thematic_dispersion: float
    pass_instability: float
    unresolved_occurrences: int
    critical_failures: tuple[str, ...]


@dataclass(frozen=True)
class ContinuationDecision:
    action: str
    passes_completed: int
    passes_initially_planned: int
    estimated_passes_remaining: int
    reason: str


def plan_complexity(result: AnalysisResult) -> ComplexityMetrics:
    document = result.document
    section_count = len(document.sections)
    unit_count = max(1, len(document.units))
    family_occurrences = sum(len(family.unit_ids) for family in result.families)
    context_pressure = min(1.0, document.resource_plan.context_pressure)
    section_complexity = min(1.0, max(0, section_count - 1) / 20)
    repetition_density = min(1.0, family_occurrences / unit_count)
    if result.families and section_count > 1:
        thematic_dispersion = sum(
            max(0, len(family.sections) - 1) / (section_count - 1)
            for family in result.families
        ) / len(result.families)
    else:
        thematic_dispersion = 0.0
    unit_family_counts: dict[str, int] = {}
    for family in result.families:
        for unit_id in family.unit_ids:
            unit_family_counts[unit_id] = unit_family_counts.get(unit_id, 0) + 1
    shared = sum(count > 1 for count in unit_family_counts.values())
    cross_dependency = min(1.0, shared / unit_count)

    # Defaults are transparent configuration values pending labelled-corpus
    # calibration; the protocol does not present them as universal constants.
    index = (
        0.30 * context_pressure
        + 0.20 * section_complexity
        + 0.25 * repetition_density
        + 0.15 * thematic_dispersion
        + 0.10 * cross_dependency
    )
    if index <= 0.20:
        passes = 1
    elif index <= 0.40:
        passes = 2
    elif index <= 0.60:
        passes = 3
    elif index <= 0.80:
        passes = 4
    else:
        passes = 5
    rationale = (
        f"Initial cap {passes}: context pressure {context_pressure:.1%}, section complexity "
        f"{section_complexity:.1%}, recurrence density {repetition_density:.1%}, thematic "
        f"dispersion {thematic_dispersion:.1%}, cross-family dependency {cross_dependency:.1%}. "
        "The cap is adaptive and may stop early; it is never a mandatory rewrite count."
    )
    return ComplexityMetrics(
        context_pressure=round(context_pressure, 4),
        section_complexity=round(section_complexity, 4),
        repetition_density=round(repetition_density, 4),
        thematic_dispersion=round(thematic_dispersion, 4),
        cross_section_dependency=round(cross_dependency, 4),
        complexity_index=round(index, 4),
        planned_passes=passes,
        rationale=rationale,
    )


def measure_pass(
    result: AnalysisResult,
    *,
    pass_number: int,
    previous_document: str,
    current_document: str,
    accounted_original_units: int,
    total_original_units: int,
    critical_failures: tuple[str, ...] = (),
) -> PassMetrics:
    total_mass = max(1, sum(len(unit.tokens) for unit in result.document.units))
    redundant_mass = 0
    unresolved = 0
    for family in result.families:
        by_id = {unit.unit_id: unit for unit in result.document.units}
        for decision in family.decisions:
            if decision.disposition in {Disposition.MERGE_INTO_CENTRE, Disposition.REMOVE_FULLY_REDUNDANT}:
                redundant_mass += len(by_id[decision.unit_id].tokens)
            if decision.disposition == Disposition.HUMAN_REVIEW:
                unresolved += 1
    dispersion = plan_complexity(result).thematic_dispersion
    instability = 1.0 - SequenceMatcher(None, previous_document, current_document).ratio()
    coverage = accounted_original_units / max(1, total_original_units)
    return PassMetrics(
        pass_number=pass_number,
        repetition_burden=round(redundant_mass / total_mass, 4),
        substantive_ledger_coverage=round(coverage, 4),
        thematic_dispersion=dispersion,
        pass_instability=round(instability, 4),
        unresolved_occurrences=unresolved,
        critical_failures=critical_failures,
    )


def decide_continuation(
    current: PassMetrics,
    *,
    initially_planned: int,
    previous: PassMetrics | None = None,
    conservation_risk: float = 0.0,
    expected_benefit: float = 1.0,
) -> ContinuationDecision:
    completed = current.pass_number
    planned = min(5, max(1, initially_planned))
    if current.critical_failures or current.substantive_ledger_coverage < 1.0:
        return ContinuationDecision(
            "STOP_NOT_VERIFIED",
            completed,
            planned,
            0,
            "A critical invariant or ledger-coverage check failed; the document must roll back or enter human review.",
        )
    if conservation_risk >= expected_benefit:
        return ContinuationDecision(
            "STOP_HUMAN_REVIEW",
            completed,
            planned,
            0,
            "Expected consolidation benefit no longer exceeds the measured conservation risk.",
        )
    if current.unresolved_occurrences == 0 and current.repetition_burden == 0:
        return ContinuationDecision(
            "STOP_STABLE",
            completed,
            planned,
            0,
            "No material accidental recurrence remains and the complete ledger is reconciled.",
        )
    if previous is not None:
        improvement = previous.repetition_burden - current.repetition_burden
        if current.pass_instability < 0.02 and improvement < 0.01:
            return ContinuationDecision(
                "STOP_STABLE",
                completed,
                planned,
                0,
                "Change instability is below 2% and marginal burden improvement is below 1%.",
            )
    if completed >= 5:
        return ContinuationDecision(
            "STOP_SAFETY_CAP",
            completed,
            planned,
            0,
            "The absolute five-pass safety cap was reached with unresolved work; certification is withheld.",
        )
    if completed >= planned and (current.unresolved_occurrences > 0 or current.repetition_burden > 0):
        planned = min(5, planned + 1)
        return ContinuationDecision(
            "ADD_PASS",
            completed,
            planned,
            planned - completed,
            "Unresolved dispersion remains after the initial plan; one bounded pass was added.",
        )
    return ContinuationDecision(
        "CONTINUE",
        completed,
        planned,
        max(0, planned - completed),
        "Material recurrence remains, ledger coverage is complete, and expected benefit exceeds conservation risk.",
    )

