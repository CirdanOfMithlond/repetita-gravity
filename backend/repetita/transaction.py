from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass

from .models import (
    Disposition,
    DocumentModel,
    RecurrenceFamily,
    SemanticRelation,
)
from .parser import normalize_text


@dataclass(frozen=True)
class TransactionVerification:
    ledger_reconciled: bool
    anchors_preserved: bool
    scope_isolated: bool
    cross_references_resolve: bool
    new_duplication_absent: bool
    semantic_adjudication: str
    failures: tuple[str, ...]


@dataclass(frozen=True)
class FamilyTransaction:
    transaction_id: str
    family_id: str
    base_document_hash: str
    state: str
    centre: str
    donors: tuple[dict, ...]
    receiver: dict
    changed_unit_ids: tuple[str, ...]
    verification: TransactionVerification
    revised_document: str

    def to_dict(self) -> dict:
        data = asdict(self)
        data.pop("revised_document")
        return data


def document_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _all_anchor_values(unit) -> set[str]:
    return set(unit.anchors.numbers + unit.anchors.quotations + unit.anchors.citations + unit.anchors.defined_terms)


def prepare_exact_transaction(source: str, document: DocumentModel, family: RecurrenceFamily) -> FamilyTransaction | None:
    """Apply only the narrowest provably safe transformation.

    The deterministic engine can replace a whole-sentence exact duplicate with a
    resolving cross-reference. Partial overlap and model-dependent repair remain
    outside this function and fail closed.
    """
    by_id = {unit.unit_id: unit for unit in document.units}
    decisions = {decision.unit_id: decision for decision in family.decisions}
    centre_units = [
        by_id[unit_id]
        for unit_id in family.unit_ids
        if by_id[unit_id].location.section_title == family.gravity_centre
        and decisions[unit_id].disposition == Disposition.PRESERVE_IN_PLACE
    ]
    donors = [
        by_id[unit_id]
        for unit_id in family.unit_ids
        if decisions[unit_id].disposition == Disposition.MERGE_INTO_CENTRE
        and decisions[unit_id].semantic_relation == SemanticRelation.EXACT_EQUIVALENT
        and not decisions[unit_id].unique_residual_tokens
    ]
    if not centre_units or not donors:
        return None

    receiver = max(centre_units, key=lambda unit: len(unit.tokens))
    eligible = [unit for unit in donors if normalize_text(unit.text) == normalize_text(receiver.text)]
    if not eligible:
        return None

    base_hash = document_hash(source)
    failures: list[str] = []
    edits: list[tuple[int, int, str, str]] = []
    donor_records: list[dict] = []
    receiver_anchors = _all_anchor_values(receiver)
    for donor in eligible:
        donor_anchors = _all_anchor_values(donor)
        if not donor_anchors.issubset(receiver_anchors):
            failures.append(f"{donor.unit_id}: donor hard anchors are not present at the receiver")
            continue
        replacement = f"See {family.gravity_centre} for the canonical treatment of {family.label}."
        edits.append((donor.location.char_start, donor.location.char_end, replacement, donor.unit_id))
        donor_records.append(
            {
                "unit_id": donor.unit_id,
                "original_text": donor.text,
                "duplicated_payload": [donor.text],
                "unique_residual_payload": [],
                "local_function": donor.local_function.value,
                "hard_anchors": sorted(donor_anchors),
                "proposed_repair": replacement,
            }
        )

    if not edits:
        return None
    revised = source
    for start, end, replacement, _unit_id in sorted(edits, reverse=True):
        if revised[start:end] != source[start:end]:
            failures.append("Mutation offsets no longer match the immutable base document")
            break
        revised = revised[:start] + replacement + revised[end:]

    centre_resolves = bool(family.gravity_centre) and family.gravity_centre in {section["title"] for section in document.sections}
    ledger_reconciled = len(donor_records) == len(edits) and all(record["unique_residual_payload"] == [] for record in donor_records)
    anchors_preserved = not any("hard anchors" in failure for failure in failures)
    scope_isolated = not any("offsets" in failure for failure in failures)
    new_duplication_absent = all(normalize_text(record["original_text"]) not in normalize_text(record["proposed_repair"]) for record in donor_records)
    verification = TransactionVerification(
        ledger_reconciled=ledger_reconciled,
        anchors_preserved=anchors_preserved,
        scope_isolated=scope_isolated,
        cross_references_resolve=centre_resolves,
        new_duplication_absent=new_duplication_absent,
        semantic_adjudication="passed",
        failures=tuple(failures),
    )
    passed = all(
        (
            verification.ledger_reconciled,
            verification.anchors_preserved,
            verification.scope_isolated,
            verification.cross_references_resolve,
            verification.new_duplication_absent,
            not verification.failures,
        )
    )
    state = "committed" if passed else "rolled_back"
    if not passed:
        revised = source
    transaction_id = "tx_" + hashlib.sha256(f"{base_hash}|{family.family_id}".encode()).hexdigest()[:12]
    return FamilyTransaction(
        transaction_id=transaction_id,
        family_id=family.family_id,
        base_document_hash=base_hash,
        state=state,
        centre=family.gravity_centre or "",
        donors=tuple(donor_records),
        receiver={
            "original_text": receiver.text,
            "incoming_payload": [record["original_text"] for record in donor_records],
            "proposed_text": receiver.text,
            "provenance": [
                {"source_unit_id": record["unit_id"], "target_span": receiver.text}
                for record in donor_records
            ],
        },
        changed_unit_ids=tuple(record["unit_id"] for record in donor_records),
        verification=verification,
        revised_document=revised,
    )

