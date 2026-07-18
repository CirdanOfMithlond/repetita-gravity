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


def apply_model_transaction(
    source: str,
    document: DocumentModel,
    family: RecurrenceFamily,
    proposal: dict,
    semantic_verification: dict,
) -> FamilyTransaction:
    """Validate and atomically apply a model proposal, or return a rollback."""
    from .openai_rewrite import validate_rewrite_proposal, validate_semantic_verification

    validate_rewrite_proposal(proposal, document, family)
    validate_semantic_verification(semantic_verification, family)
    by_id = {unit.unit_id: unit for unit in document.units}
    failures: list[str] = []
    if proposal["unresolved_questions"]:
        failures.append("Rewrite proposal contains unresolved questions")
    if any(donor["disposition"] == "human_review" for donor in proposal["donors"]):
        failures.append("At least one donor requires human review")
    if semantic_verification["overall"] != "passed":
        failures.extend(semantic_verification["failures"] or ["Independent semantic verification did not pass"])

    records_by_id = {donor["unit_id"]: donor for donor in proposal["donors"]}
    receiver = proposal["receiver"]
    edits: list[tuple[int, int, str, str]] = []
    for donor in proposal["donors"]:
        unit = by_id[donor["unit_id"]]
        edits.append((unit.location.char_start, unit.location.char_end, donor["proposed_repair"], unit.unit_id))
        if donor["disposition"] == "convert_to_cross_reference" and proposal["centre_section"].lower() not in donor["proposed_repair"].lower():
            failures.append(f"{unit.unit_id}: cross-reference does not name the gravity centre")
    receiver_unit = by_id[receiver["unit_id"]]
    if receiver["proposed_text"] != receiver["original_text"]:
        edits.append(
            (
                receiver_unit.location.char_start,
                receiver_unit.location.char_end,
                receiver["proposed_text"],
                receiver_unit.unit_id,
            )
        )

    spans = sorted((start, end) for start, end, _replacement, _unit_id in edits)
    if any(left_end > right_start for (_left_start, left_end), (right_start, _right_end) in zip(spans, spans[1:])):
        failures.append("Proposed mutation spans overlap")

    revised = source
    for start, end, replacement, unit_id in sorted(edits, reverse=True):
        if source[start:end] != by_id[unit_id].text:
            failures.append(f"{unit_id}: immutable source span no longer matches")
            continue
        revised = revised[:start] + replacement + revised[end:]

    original_anchor_values = {
        anchor
        for unit_id in family.unit_ids
        for anchor in _all_anchor_values(by_id[unit_id])
    }
    missing_anchors = sorted(anchor for anchor in original_anchor_values if anchor not in revised)
    if missing_anchors:
        failures.append(f"Hard anchors missing after rewrite: {missing_anchors}")

    provenance_ids = {
        item["source_unit_id"]
        for item in receiver["provenance"]
    }
    incoming_donor_ids = {
        donor["unit_id"]
        for donor in proposal["donors"]
        if donor["duplicated_payload"] or donor["unique_residual_payload"]
    }
    if not incoming_donor_ids.issubset(provenance_ids):
        failures.append("Receiver provenance does not cover every incoming donor")

    centre_resolves = proposal["centre_section"] in {section["title"] for section in document.sections}
    checks_pass = all(
        check["original_payload_covered"]
        and check["unique_residual_covered"]
        and check["local_function_preserved"]
        and check["hard_anchors_preserved"]
        for check in semantic_verification["unit_checks"]
    )
    verification = TransactionVerification(
        ledger_reconciled=len(semantic_verification["unit_checks"]) == len(family.unit_ids) and checks_pass,
        anchors_preserved=not missing_anchors,
        scope_isolated=not any("span" in failure for failure in failures),
        cross_references_resolve=centre_resolves and not any("cross-reference" in failure for failure in failures),
        new_duplication_absent=semantic_verification["no_new_duplication"],
        semantic_adjudication=semantic_verification["overall"],
        failures=tuple(failures),
    )
    passed = all(
        (
            verification.ledger_reconciled,
            verification.anchors_preserved,
            verification.scope_isolated,
            verification.cross_references_resolve,
            verification.new_duplication_absent,
            semantic_verification["no_meaning_shift"],
            semantic_verification["narrative_continuity"],
            not failures,
        )
    )
    if not passed:
        revised = source
    base_hash = document_hash(source)
    transaction_id = "tx_" + hashlib.sha256(f"{base_hash}|{family.family_id}|model".encode()).hexdigest()[:12]
    return FamilyTransaction(
        transaction_id=transaction_id,
        family_id=family.family_id,
        base_document_hash=base_hash,
        state="committed" if passed else "rolled_back",
        centre=proposal["centre_section"],
        donors=tuple(proposal["donors"]),
        receiver=proposal["receiver"],
        changed_unit_ids=tuple(proposal["changed_unit_ids"]),
        verification=verification,
        revised_document=revised,
    )
