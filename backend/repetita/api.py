from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .metrics import plan_complexity
from .orchestrator import run_hybrid_gravity_pass, run_model_family_transaction
from .pipeline import analyse_document

MAX_DOCUMENT_BYTES = 5_000_000


def _text(payload: dict[str, Any]) -> str:
    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("A non-empty text field is required")
    if len(text.encode("utf-8")) > MAX_DOCUMENT_BYTES:
        raise ValueError("Document exceeds the 5 MB MVP limit")
    return text


def analyse_payload(payload: dict[str, Any]) -> dict[str, Any]:
    text = _text(payload)
    context_limit = int(payload.get("context_limit", 1_050_000))
    safety_ratio = float(payload.get("safety_ratio", 0.60))
    result = analyse_document(text, context_limit=context_limit, safety_ratio=safety_ratio)
    return {"analysis": result.to_dict(), "complexity": asdict(plan_complexity(result))}


def safe_pass_payload(payload: dict[str, Any]) -> dict[str, Any]:
    text = _text(payload)
    return run_hybrid_gravity_pass(text)


def model_family_payload(payload: dict[str, Any]) -> dict[str, Any]:
    text = _text(payload)
    family_id = payload.get("family_id")
    if not isinstance(family_id, str) or not family_id:
        raise ValueError("A family_id field is required")
    return run_model_family_transaction(text, family_id)
