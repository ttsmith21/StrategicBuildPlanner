from __future__ import annotations

from typing import Any, Dict, List

from ..lib.schema import AgentPatch

CANONICAL_OPEN_QUESTIONS: List[str] = [
    "Confirm customer-specific quality flowdowns (docs, certifications, special approvals).",
    "Confirm passivation/finish requirements and acceptance criteria (if any).",
    "Confirm any special fixturing or gaging requirements beyond standard work.",
    "Confirm material spec/grade and any CoO or mill cert requirements.",
    "Confirm packaging, labeling, cleanliness, and serialization/lot control requirements.",
    "Confirm delivery milestones and any hold points beyond shop QA gates.",
]


def run_open_questions(plan: Dict[str, Any]) -> AgentPatch:
    existing = plan.get("open_questions") or []
    if isinstance(existing, list) and len(existing) > 0:
        return AgentPatch(patch={}, tasks=[], conflicts=[])
    open_qs = [
        {"question": q, "requested_from": "CUSTOMER", "blocking": True}
        for q in CANONICAL_OPEN_QUESTIONS
    ]
    return AgentPatch(patch={"open_questions": open_qs, "open_questions_curated": True}, tasks=[], conflicts=[])
