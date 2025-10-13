"""Utilities for constructing source registries and freezing context packs."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, cast, Literal

try:
    from .schema import Citation, ContextPack, Fact, Source
except ImportError:  # pragma: no cover - script execution fallback
    import os
    import sys

    sys.path.append(os.path.dirname(__file__))
    from schema import Citation, ContextPack, Fact, Source


SourceKind = Literal[
    "drawing",
    "po",
    "quote",
    "itp",
    "customer_spec",
    "generic_spec",
    "supplier_qm",
    "email",
    "lessons_learned",
    "sow_spec",
    "meeting_notes",
    "other",
]

SourceAuthority = Literal["mandatory", "conditional", "reference", "internal"]


_KNOWN_KIND_PRECEDENCE: Dict[SourceKind, int] = {
    "drawing": 1,
    "po": 1,
    "quote": 2,
    "itp": 2,
    "sow_spec": 2,
    "customer_spec": 3,
    "supplier_qm": 4,
    "generic_spec": 5,
    "meeting_notes": 6,
    "email": 20,
    "lessons_learned": 6,
    "other": 10,
}
_DEFAULT_PRECEDENCE = 10

_KNOWN_KIND_AUTHORITY: Dict[SourceKind, SourceAuthority] = {
    "drawing": "mandatory",
    "po": "mandatory",
    "quote": "conditional",
    "itp": "mandatory",
    "sow_spec": "mandatory",
    "customer_spec": "mandatory",
    "supplier_qm": "conditional",
    "generic_spec": "reference",
    "meeting_notes": "mandatory",
    "email": "internal",
    "lessons_learned": "internal",
    "other": "reference",
}
_DEFAULT_AUTHORITY: SourceAuthority = "reference"


def _collect_text_fields(entry: Dict[str, Any], keys: Iterable[str]) -> str:
    pieces: List[str] = []
    for key in keys:
        value = entry.get(key)
        if isinstance(value, str):
            pieces.append(value)
    # Normalize: replace underscores with spaces, then lowercase
    # This ensures "Purchase_Order" becomes "purchase order"
    text = " ".join(pieces).replace("_", " ").lower()
    return text


def _collect_labels(entry: Dict[str, Any]) -> List[str]:
    raw_labels = entry.get("labels") or []
    if isinstance(raw_labels, dict):
        raw_labels = raw_labels.values()
    labels: List[str] = []
    for label in raw_labels:
        if isinstance(label, str):
            labels.append(label.lower())
        elif isinstance(label, dict):
            name = label.get("name")
            if isinstance(name, str):
                labels.append(name.lower())
    return labels


def _detect_kind(entry: Dict[str, Any]) -> SourceKind:
    text = _collect_text_fields(entry, ("filename", "name", "title", "path"))
    labels = _collect_labels(entry)
    label_text = " ".join(labels)

    def has(keyword: str) -> bool:
        return keyword in text or keyword in label_text

    # Order matters! Check longer/more-specific patterns first to avoid substring matches
    # E.g., "proposal" before "po" (to avoid matching "po" in "proposal")

    if has("lessons") or has("retro"):
        return cast(SourceKind, "lessons_learned")
    if has("weld") and has("plan"):
        return cast(SourceKind, "generic_spec")
    if has("drawing") or has("print") or any(text.endswith(ext) for ext in (".dwg", ".dxf")):
        return cast(SourceKind, "drawing")

    # Check "purchase order" and "proposal" before "po" to avoid substring matches
    if has("purchase order"):
        return cast(SourceKind, "po")
    if has("quote") or has("proposal"):
        return cast(SourceKind, "quote")
    # Now check "po" last for PO-specific matches
    if has("po"):
        return cast(SourceKind, "po")

    if has("itp") or has("inspection") or has("test plan"):
        return cast(SourceKind, "itp")
    if has("sow") or has("statement of work") or has("project spec") or has("project standard"):
        return cast(SourceKind, "sow_spec")
    if has("customer spec") or ("customer" in labels and "spec" in labels):
        return cast(SourceKind, "customer_spec")
    if has("supplier") and has("qm"):
        return cast(SourceKind, "supplier_qm")
    if has("email") or has("mail"):
        return cast(SourceKind, "email")
    if has("meeting") or has("minutes") or has("notes"):
        return cast(SourceKind, "meeting_notes")
    if has("spec"):
        return cast(SourceKind, "generic_spec")
    return cast(SourceKind, "other")


def _coerce_scope(entry: Dict[str, Any]) -> List[str]:
    scope: List[str] = []
    raw_scope = entry.get("scope")
    if isinstance(raw_scope, (list, tuple, set)):
        for item in raw_scope:
            if isinstance(item, str):
                scope.append(item)
    labels = _collect_labels(entry)
    for label in labels:
        if label not in scope:
            scope.append(label)
    return scope


def _coerce_applies_if(entry: Dict[str, Any]) -> Optional[Dict[str, str]]:
    raw = entry.get("applies_if")
    if not isinstance(raw, dict):
        return None
    filtered: Dict[str, str] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, str):
            filtered[key] = value
    return filtered or None


def _resolve_precedence(kind: SourceKind) -> int:
    return _KNOWN_KIND_PRECEDENCE.get(kind, _DEFAULT_PRECEDENCE)


def _resolve_authority(kind: SourceKind) -> SourceAuthority:
    return _KNOWN_KIND_AUTHORITY.get(kind, _DEFAULT_AUTHORITY)


def _coerce_precedence_override(value: Any, fallback: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text.isdigit():
            return int(text)
        # allow simple keywords
        keyword_map = {
            "highest": 1,
            "very_high": 1,
            "high": 2,
            "medium": 5,
            "low": 10,
        }
        return keyword_map.get(text, fallback)
    return fallback


def _coerce_authority_override(value: Any, fallback: SourceAuthority) -> SourceAuthority:
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"mandatory", "conditional", "reference", "internal"}:
            return cast(SourceAuthority, text)
        # allow synonyms
        synonym_map: Dict[str, SourceAuthority] = {
            "must": "mandatory",
            "shall": "mandatory",
            "should": "conditional",
            "guidance": "reference",
            "info": "reference",
            "internal": "internal",
        }
        return synonym_map.get(text, fallback)
    return fallback


def build_source_registry(
    uploaded_files: List[Dict[str, Any]],
    confluence_pages: List[Dict[str, Any]],
    files_meta: Optional[Dict[str, Any]] = None,
) -> List[Source]:
    entries = [dict(item, source_type="file") for item in uploaded_files] + [
        dict(item, source_type="confluence") for item in confluence_pages
    ]
    sources: List[Source] = []
    files_meta = files_meta or {}
    for entry in entries:
        # Allow optional user-provided overrides from ingest metadata
        filename_key = str(entry.get("filename") or entry.get("title") or entry.get("name") or "").lower()
        meta = files_meta.get(filename_key) if isinstance(files_meta, dict) else None
        kind = cast(SourceKind, meta.get("doc_type")) if isinstance(meta, dict) and isinstance(meta.get("doc_type"), str) else _detect_kind(entry)
        source_id = str(entry.get("id") or entry.get("name") or entry.get("title") or entry.get("path") or entry.get("filename") or len(sources) + 1)
        title = str(entry.get("title") or entry.get("name") or entry.get("filename") or source_id)
        source = Source(
            kind=kind,
            authority=_coerce_authority_override(meta.get("authority"), _resolve_authority(kind)) if isinstance(meta, dict) else _resolve_authority(kind),
            precedence_rank=_coerce_precedence_override(meta.get("precedence_rank"), _resolve_precedence(kind)) if isinstance(meta, dict) else _resolve_precedence(kind),
            scope=_coerce_scope(entry),
            applies_if=_coerce_applies_if(entry),
            rev=entry.get("rev") or entry.get("revision"),
            effective_date=entry.get("effective_date") or entry.get("date"),
            id=source_id,
            title=title,
            customer=entry.get("customer"),
            family=entry.get("family"),
        )
        sources.append(source)
    return sources


def _fact_in_scope(fact: Fact, project: Dict[str, Any]) -> bool:
    if not fact.applies_if:
        return True
    for key, expected in fact.applies_if.items():
        actual = project.get(key)
        if actual != expected:
            return False
    return True


def freeze_context_pack(
    sources: List[Source],
    candidate_facts: List[Fact],
    project: Dict[str, Any],
) -> ContextPack:
    scoped_facts: List[Fact] = []
    for fact in candidate_facts:
        if _fact_in_scope(fact, project):
            scoped_facts.append(fact.model_copy(deep=True))

    facts_by_topic: Dict[str, List[Fact]] = defaultdict(list)
    for fact in scoped_facts:
        facts_by_topic[fact.topic].append(fact)

    for topic, facts in facts_by_topic.items():
        canonical_candidates = sorted(
            (f for f in facts if f.authority in {"mandatory", "conditional"}),
            key=lambda f: (f.precedence_rank, f.id),
        )
        canonical: Optional[Fact] = canonical_candidates[0] if canonical_candidates else None
        if canonical:
            canonical.status = "canonical"
            for fact in canonical_candidates[1:]:
                fact.status = "superseded"
            for fact in facts:
                if fact is canonical:
                    continue
                if fact.authority in {"reference", "internal"}:
                    fact.status = "proposed"
                elif fact.status != "superseded":
                    fact.status = "superseded"
        else:
            reference_like = sorted(
                (f for f in facts if f.authority in {"reference", "internal"}),
                key=lambda f: (f.precedence_rank, f.id),
            )
            if reference_like:
                head = reference_like[0]
                head.status = "canonical"
                for fact in reference_like[1:]:
                    fact.status = "proposed"

    packed = ContextPack(project=project, sources=sources, facts=scoped_facts)
    return packed


if __name__ == "__main__":
    demo_files = [
        {"id": "DRAW-001", "filename": "ACME_bracket_drawing.pdf", "labels": ["drawing"]},
        {"id": "PO-1001", "filename": "PO_1001.pdf", "labels": ["po"], "customer": "ACME"},
    ]
    demo_pages = [
        {"id": "CONF-42", "title": "Customer Spec 9001", "labels": ["customer", "spec"]},
        {"id": "CONF-99", "title": "Lessons Learned - Bracket Program", "labels": ["lessons_learned"]},
    ]
    registry = build_source_registry(demo_files, demo_pages)

    source_lookup = {source.title: source.id for source in registry}

    demo_facts = [
        Fact(
            id="F-1",
            claim="Use 316L stainless steel sheet",
            topic="Materials",
            citation=Citation(source_id=source_lookup["ACME_bracket_drawing.pdf"], page_ref="1", passage_sha=None),
            authority="mandatory",
            precedence_rank=1,
            applies_if={"customer": "ACME"},
            status="proposed",
            confidence_model=0.95,
        ),
        Fact(
            id="F-2",
            claim="Use 304 stainless as alternative",
            topic="Materials",
            citation=Citation(source_id=source_lookup["Customer Spec 9001"], page_ref="4", passage_sha=None),
            authority="mandatory",
            precedence_rank=3,
            applies_if={"customer": "ACME"},
            status="proposed",
            confidence_model=0.7,
        ),
        Fact(
            id="F-3",
            claim="Historical weld setup guidance",
            topic="Weld Setup",
            citation=Citation(source_id=source_lookup["Lessons Learned - Bracket Program"], page_ref=None, passage_sha=None),
            authority="internal",
            precedence_rank=99,
            applies_if=None,
            status="proposed",
            confidence_model=0.6,
        ),
        Fact(
            id="F-4",
            claim="Preferred weld sequence per customer spec",
            topic="Weld Setup",
            citation=Citation(source_id=source_lookup["Customer Spec 9001"], page_ref="7", passage_sha=None),
            authority="mandatory",
            precedence_rank=2,
            applies_if={"platform": "Bracket"},
            status="proposed",
            confidence_model=0.8,
        ),
    ]

    project_context = {"customer": "ACME", "platform": "Bracket"}
    frozen_pack = freeze_context_pack(registry, demo_facts, project_context)

    for fact in frozen_pack.facts:
        print(f"{fact.id} ({fact.topic}): {fact.status}")
