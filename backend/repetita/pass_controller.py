from __future__ import annotations

from dataclasses import asdict, dataclass

from .pipeline import analyse_document
from .transaction import FamilyTransaction, prepare_exact_transaction


@dataclass
class PassResult:
    original_document: str
    revised_document: str
    transactions: list[FamilyTransaction]
    eligible_families_remaining: int
    stop_reason: str

    def to_dict(self) -> dict:
        return {
            "transactions": [transaction.to_dict() for transaction in self.transactions],
            "eligible_families_remaining": self.eligible_families_remaining,
            "stop_reason": self.stop_reason,
        }


def run_deterministic_safe_pass(source: str, *, max_transactions: int = 50) -> PassResult:
    """Commit exact, whole-sentence duplicate transactions one family at a time."""
    original = source
    working = source
    committed: list[FamilyTransaction] = []
    attempted_family_signatures: set[tuple[str, ...]] = set()

    for _ in range(max_transactions):
        analysis = analyse_document(working)
        candidate = None
        for family in analysis.families:
            signature = tuple(sorted(family.unit_ids))
            if signature in attempted_family_signatures:
                continue
            attempted_family_signatures.add(signature)
            transaction = prepare_exact_transaction(working, analysis.document, family)
            if transaction and transaction.state == "committed":
                candidate = transaction
                break
        if candidate is None:
            remaining = sum(
                prepare_exact_transaction(working, analysis.document, family) is not None
                for family in analysis.families
            )
            return PassResult(
                original_document=original,
                revised_document=working,
                transactions=committed,
                eligible_families_remaining=remaining,
                stop_reason=(
                    "No further deterministic exact-duplicate transaction is justified; "
                    "semantic or partial-overlap families require model adjudication or human review."
                ),
            )
        working = candidate.revised_document
        committed.append(candidate)

    return PassResult(
        original_document=original,
        revised_document=working,
        transactions=committed,
        eligible_families_remaining=0,
        stop_reason="Safety transaction cap reached; further processing is withheld.",
    )

