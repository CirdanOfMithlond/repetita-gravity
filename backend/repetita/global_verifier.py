from __future__ import annotations

from dataclasses import asdict, dataclass

from .models import DiscourseRole, Disposition
from .parser import normalize_text, parse_document
from .pipeline import analyse_document
from .transaction import FamilyTransaction


@dataclass(frozen=True)
class LedgerDisposition:
    unit_id: str
    disposition: str
    destination: str


@dataclass(frozen=True)
class GlobalVerificationReport:
    original_unit_count: int
    accounted_unit_count: int
    ledger_coverage: float
    dispositions: tuple[LedgerDisposition, ...]
    missing_unit_ids: tuple[str, ...]
    missing_hard_anchors: tuple[str, ...]
    unresolved_occurrences: int
    newly_introduced_family_count: int
    all_transactions_committed: bool
    all_transaction_checks_passed: bool
    status: str
    failures: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def _anchor_values(document) -> set[str]:
    return {
        value
        for unit in document.units
        for value in (
            unit.anchors.numbers
            + unit.anchors.quotations
            + unit.anchors.citations
            + unit.anchors.defined_terms
        )
    }


def verify_global_rewrite(
    original_text: str,
    revised_text: str,
    transactions: list[FamilyTransaction],
) -> GlobalVerificationReport:
    original = parse_document(original_text)
    revised_result = analyse_document(revised_text)
    revised = revised_result.document
    revised_ids = {unit.unit_id for unit in revised.units}
    transaction_by_unit = {
        unit_id: transaction
        for transaction in transactions
        for unit_id in transaction.changed_unit_ids
    }

    dispositions: list[LedgerDisposition] = []
    missing: list[str] = []
    for unit in original.units:
        if unit.unit_id in revised_ids:
            dispositions.append(LedgerDisposition(unit.unit_id, "preserved_in_place", unit.location.section_title))
            continue
        transaction = transaction_by_unit.get(unit.unit_id)
        if transaction and transaction.state == "committed" and transaction.verification.ledger_reconciled:
            donor_ids = {donor["unit_id"] for donor in transaction.donors}
            disposition = "donor_repaired" if unit.unit_id in donor_ids else "receiver_accreted"
            dispositions.append(LedgerDisposition(unit.unit_id, disposition, transaction.centre))
            continue
        missing.append(unit.unit_id)

    missing_anchors = sorted(anchor for anchor in _anchor_values(original) if anchor not in revised_text)
    unresolved = sum(
        decision.disposition == Disposition.HUMAN_REVIEW
        for family in revised_result.families
        for decision in family.decisions
    )

    original_family_text_sets = {
        frozenset(
            original_unit.normalized_text
            for original_unit in original.units
            if original_unit.unit_id in family.unit_ids
        )
        for family in analyse_document(original_text).families
    }
    revised_by_id = {unit.unit_id: unit for unit in revised.units}
    revised_family_text_sets = []
    for family in revised_result.families:
        family_units = [revised_by_id[unit_id] for unit_id in family.unit_ids]
        # A generated cross-reference and its canonical target are an intended
        # orbit, not newly introduced accidental redundancy.
        if any(unit.discourse_role == DiscourseRole.CROSS_REFERENCE for unit in family_units):
            continue
        revised_family_text_sets.append(frozenset(unit.normalized_text for unit in family_units))
    newly_introduced = sum(
        not any(revised_set.issubset(original_set) for original_set in original_family_text_sets)
        for revised_set in revised_family_text_sets
    )

    all_committed = all(transaction.state == "committed" for transaction in transactions)
    all_checks = all(
        transaction.verification.ledger_reconciled
        and transaction.verification.anchors_preserved
        and transaction.verification.scope_isolated
        and transaction.verification.cross_references_resolve
        and transaction.verification.new_duplication_absent
        and transaction.verification.semantic_adjudication == "passed"
        and not transaction.verification.failures
        for transaction in transactions
    )
    failures: list[str] = []
    if missing:
        failures.append(f"{len(missing)} original semantic unit(s) have no reconciled destination")
    if missing_anchors:
        failures.append(f"Hard anchors are missing: {missing_anchors}")
    if not all_committed:
        failures.append("At least one family transaction was not committed")
    if not all_checks:
        failures.append("At least one transaction verification did not pass")
    if newly_introduced:
        failures.append(f"{newly_introduced} newly introduced candidate recurrence family/families detected")

    coverage = len(dispositions) / max(1, len(original.units))
    if failures or coverage < 1.0:
        status = "NOT_VERIFIED"
    elif unresolved:
        status = "FORMAL_GATES_PASSED_UNRESOLVED_SEMANTICS"
    else:
        status = "FORMAL_GATES_PASSED_GLOBAL_SEMANTIC_REVIEW_PENDING"
    return GlobalVerificationReport(
        original_unit_count=len(original.units),
        accounted_unit_count=len(dispositions),
        ledger_coverage=round(coverage, 4),
        dispositions=tuple(dispositions),
        missing_unit_ids=tuple(missing),
        missing_hard_anchors=tuple(missing_anchors),
        unresolved_occurrences=unresolved,
        newly_introduced_family_count=newly_introduced,
        all_transactions_committed=all_committed,
        all_transaction_checks_passed=all_checks,
        status=status,
        failures=tuple(failures),
    )
