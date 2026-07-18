from __future__ import annotations

import hashlib
import re

from .models import (
    DiscourseRole,
    DocumentModel,
    HardAnchors,
    LocalFunction,
    ResourcePlan,
    SemanticUnit,
    SourceLocation,
)

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")
NUMBER_RE = re.compile(r"(?<!\w)(?:[$€£]?\d[\d,.]*(?:%|\s*(?:USD|EUR|GBP))?)(?!\w)", re.I)
QUOTE_RE = re.compile(r'[“\"]([^”\"]{2,})[”\"]')
CITATION_RE = re.compile(r"(?:\[[^\]]+\]|\([^)]*\b(?:19|20)\d{2}[^)]*\))")
DEFINED_TERM_RE = re.compile(r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,4}\b")

ROLE_MARKERS: tuple[tuple[DiscourseRole, tuple[str, ...]], ...] = (
    (DiscourseRole.CROSS_REFERENCE, ("see ", "refer to", "as set out in", "as explained in")),
    (DiscourseRole.QUALIFICATION, ("provided that", "subject to", "only if", "unless")),
    (DiscourseRole.LIMITATION, ("however", "limited to", "does not", "cannot")),
    (DiscourseRole.EXCEPTION, ("except", "other than", "save for")),
    (DiscourseRole.EVIDENCE, ("evidence", "recorded", "measurement", "data show", "observed")),
    (DiscourseRole.RECOMMENDATION, ("recommend", "should", "must implement", "propose")),
    (DiscourseRole.CONSEQUENCE, ("therefore", "consequently", "as a result")),
    (DiscourseRole.DEFINITION, ("means", "is defined as", "refers to")),
    (DiscourseRole.REASON, ("because", "since", "owing to")),
)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s%$€£-]", " ", text.lower())).strip()


def stable_id(section_id: str, paragraph: int, sentence: int, text: str) -> str:
    payload = f"{section_id}|{paragraph}|{sentence}|{normalize_text(text)}"
    return "u_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def detect_role(text: str) -> DiscourseRole:
    lowered = text.lower()
    for role, markers in ROLE_MARKERS:
        if any(marker in lowered for marker in markers):
            return role
    return DiscourseRole.CLAIM


def detect_function(section_title: str, role: DiscourseRole) -> LocalFunction:
    title = section_title.lower()
    if any(x in title for x in ("executive summary", "summary", "overview", "abstract")):
        return LocalFunction.SUMMARY
    if any(x in title for x in ("analysis", "discussion", "assessment")):
        return LocalFunction.ANALYTICAL
    if any(x in title for x in ("recommendation", "remedy", "proposal")):
        return LocalFunction.RECOMMENDATORY
    if any(x in title for x in ("conclusion", "closing")):
        return LocalFunction.CONCLUSIVE
    if any(x in title for x in ("method", "procedure", "protocol")):
        return LocalFunction.STRUCTURAL
    if role == DiscourseRole.EVIDENCE or any(x in title for x in ("evidence", "record", "finding")):
        return LocalFunction.EVIDENTIARY
    if role == DiscourseRole.DEFINITION:
        return LocalFunction.DEFINITORY
    if role == DiscourseRole.CROSS_REFERENCE:
        return LocalFunction.CONTEXT
    return LocalFunction.CONTEXT


def extract_anchors(text: str) -> HardAnchors:
    return HardAnchors(
        numbers=tuple(NUMBER_RE.findall(text)),
        quotations=tuple(QUOTE_RE.findall(text)),
        citations=tuple(CITATION_RE.findall(text)),
        defined_terms=tuple(DEFINED_TERM_RE.findall(text)),
    )


def _resource_plan(text: str, section_count: int, context_limit: int, safety_ratio: float) -> ResourcePlan:
    estimated_tokens = max(1, round(len(text) / 4))
    safe_budget = max(1, round(context_limit * safety_ratio))
    pressure = estimated_tokens / safe_budget
    if pressure <= 0.55:
        strategy, chunks = "whole_document", 1
    elif pressure <= 1:
        strategy, chunks = "section_chunks_with_global_synthesis", max(2, section_count)
    else:
        strategy = "overlapping_structural_chunks_with_global_ledger"
        chunks = max(section_count, int(pressure) + 2)
    initial_pass_cap = min(5, max(1, 1 + int(pressure > 0.45) + int(pressure > 0.85)))
    rationale = (
        f"Estimated input uses {pressure:.1%} of the configured safe input budget; "
        f"selected {strategy}. The pass count is a safety cap, not a mandatory rewrite count."
    )
    return ResourcePlan(
        estimated_tokens=estimated_tokens,
        configured_context_limit=context_limit,
        safe_input_budget=safe_budget,
        context_pressure=round(pressure, 4),
        strategy=strategy,
        overlapping_chunks=chunks,
        initial_pass_cap=initial_pass_cap,
        rationale=rationale,
    )


def parse_document(text: str, *, context_limit: int = 1_000_000, safety_ratio: float = 0.60) -> DocumentModel:
    if not text or not text.strip():
        raise ValueError("Document input is empty")
    if context_limit < 1_000:
        raise ValueError("Configured context limit is implausibly small")

    matches = list(HEADING_RE.finditer(text))
    sections: list[dict] = []
    if not matches:
        sections.append({"id": "s_001", "title": "Document", "level": 1, "body": text, "start": 0})
    else:
        if text[: matches[0].start()].strip():
            sections.append({"id": "s_000", "title": "Preamble", "level": 1, "body": text[: matches[0].start()], "start": 0})
        for index, match in enumerate(matches):
            body_start = match.end()
            body_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            sections.append(
                {
                    "id": f"s_{index + 1:03d}",
                    "title": match.group(2).strip(),
                    "level": len(match.group(1)),
                    "body": text[body_start:body_end].strip(),
                    "start": body_start,
                }
            )

    units: list[SemanticUnit] = []
    for section in sections:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", section["body"]) if p.strip()]
        running_offset = section["start"]
        for paragraph_index, paragraph in enumerate(paragraphs):
            sentences = [s.strip() for s in SENTENCE_RE.split(paragraph) if s.strip()]
            for sentence_index, sentence in enumerate(sentences):
                char_start = text.find(sentence, running_offset)
                if char_start < 0:
                    char_start = running_offset
                char_end = char_start + len(sentence)
                running_offset = char_end
                role = detect_role(sentence)
                unit_id = stable_id(section["id"], paragraph_index, sentence_index, sentence)
                normalized = normalize_text(sentence)
                units.append(
                    SemanticUnit(
                        unit_id=unit_id,
                        text=sentence,
                        normalized_text=normalized,
                        location=SourceLocation(
                            section_id=section["id"],
                            section_title=section["title"],
                            paragraph_index=paragraph_index,
                            sentence_index=sentence_index,
                            char_start=char_start,
                            char_end=char_end,
                        ),
                        discourse_role=role,
                        local_function=detect_function(section["title"], role),
                        anchors=extract_anchors(sentence),
                        tokens=frozenset(normalized.split()),
                    )
                )

    title = matches[0].group(2).strip() if matches else "Untitled document"
    public_sections = [{k: v for k, v in section.items() if k not in {"body", "start"}} for section in sections]
    return DocumentModel(
        title=title,
        sections=public_sections,
        units=units,
        resource_plan=_resource_plan(text, len(sections), context_limit, safety_ratio),
    )
