"""Quality Delta Detector agent utilities."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, TypedDict

from ..lib.context_pack import ContextPack

LOGGER = logging.getLogger(__name__)


class CitationDict(TypedDict, total=False):
    source_id: str
    page_ref: Optional[str]
    passage_sha: Optional[str]


class NonStandardDelta(TypedDict):
    topic: str
    delta_type: Literal["additional", "stricter", "conflict", "ambiguous"]
    delta_summary: str
    recommended_action: str
    cost_impact: str
    schedule_impact: str
    citation: CitationDict


def _load_baseline(path: str | Path) -> Dict[str, Dict[str, Any]]:
    base_path = Path(path)
    if not base_path.is_absolute():
        base_path = Path(__file__).resolve().parent.parent / path
    if not base_path.exists():
        LOGGER.warning("Baseline file missing at %s; returning empty baseline.", base_path)
        return {}
    try:
        data = json.loads(base_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.error("Failed to read baseline JSON: %s", exc)
        return {}

    if isinstance(data, dict):
        normalized: Dict[str, Dict[str, Any]] = {}
        for topic, entry in data.items():
            if isinstance(entry, dict):
                normalized[str(topic)] = entry
            else:
                normalized[str(topic)] = {"requirement": str(entry)}
        return normalized

    LOGGER.warning("Unexpected baseline format; expected object, got %s", type(data).__name__)
    return {}


def _impact_estimate(fact_authority: str, delta_type: str) -> tuple[str, str]:
    authority = fact_authority.lower()
    cost = "MEDIUM"
    schedule = "MEDIUM"
    if authority == "mandatory":
        cost = "HIGH"
        schedule = "HIGH" if delta_type != "additional" else "MEDIUM"
    elif authority == "conditional":
        cost = "MEDIUM"
        schedule = "MEDIUM"
    elif authority == "reference":
        cost = "LOW"
        schedule = "LOW"
    elif authority == "internal":
        cost = "LOW"
        schedule = "LOW"
    return cost, schedule


def _classify_delta(claim: str, baseline_requirement: Optional[str]) -> Literal["additional", "stricter", "conflict", "ambiguous"]:
    if not baseline_requirement:
        return "additional"
    claim_lower = claim.lower()
    baseline_lower = baseline_requirement.lower()
    if claim_lower == baseline_lower:
        return "ambiguous"
    if "no " in baseline_lower or "not required" in baseline_lower:
        if "no " in claim_lower or "not required" in claim_lower:
            return "ambiguous"
        return "additional"
    if claim_lower in baseline_lower:
        return "ambiguous"
    if baseline_lower in claim_lower:
        return "ambiguous"
    if any(word in claim_lower for word in ("must", "shall", "required", "per " )) and not any(
        word in baseline_lower for word in ("must", "shall", "required")
    ):
        return "stricter"
    if any(word in baseline_lower for word in ("must", "shall", "required")) and any(
        phrase in claim_lower for phrase in ("not required", "optional", "may")
    ):
        return "conflict"
    return "ambiguous"


def run_qdd(context_pack: ContextPack, baseline_path: str | Path = "server/lib/baseline_quality.json") -> List[NonStandardDelta]:
    baseline = _load_baseline(baseline_path)
    if not context_pack.facts:
        return []

    deltas: List[NonStandardDelta] = []
    for fact in context_pack.facts:
        if fact.status == "superseded":
            continue
        baseline_entry = baseline.get(fact.topic)
        baseline_requirement = None
        if baseline_entry:
            baseline_requirement = str(baseline_entry.get("requirement", ""))

        delta_type = _classify_delta(fact.claim, baseline_requirement)
        if delta_type == "ambiguous":
            continue

        summary_parts = []
        if baseline_requirement:
            summary_parts.append(f"Baseline: {baseline_requirement}")
        summary_parts.append(f"Customer: {fact.claim}")
        delta_summary = " | ".join(summary_parts)

        recommended_action = "Review with quality engineering to confirm routing impacts."
        if delta_type == "additional":
            recommended_action = "Integrate requirement into routing/CTQ plan and update control plan."
        elif delta_type == "stricter":
            recommended_action = "Update process sheets to meet stricter requirement; coordinate with production." 
        elif delta_type == "conflict":
            recommended_action = "Escalate to customer for clarification; hold affected operations until resolved."

        cost_impact, schedule_impact = _impact_estimate(fact.authority, delta_type)

        citation: CitationDict = {
            "source_id": fact.citation.source_id,
            "page_ref": fact.citation.page_ref,
            "passage_sha": fact.citation.passage_sha,
        }

        deltas.append(
            NonStandardDelta(
                topic=fact.topic,
                delta_type=delta_type,
                delta_summary=delta_summary,
                recommended_action=recommended_action,
                cost_impact=cost_impact,
                schedule_impact=schedule_impact,
                citation=citation,
            )
        )

    deltas.sort(key=lambda d: (d["topic"], d["delta_type"]))
    return deltas
