"""Quality Manager Agent wrapper for specialist workflow."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI
from pydantic import BaseModel, Field

from ..lib.context_pack import ContextPack
from ..lib.schema import AgentConflict, AgentPatch, AgentTask, QualityPlan
from .prompts import QMA_SYSTEM
from .base_threads import run_json_schema_thread

LOGGER = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models for QMA Structured Output
# ============================================================================

class Citation(BaseModel):
    """Source citation for traceability"""
    source_id: str = Field(description="Document identifier")
    page_ref: Optional[str] = Field(default=None, description="Page/section reference or [INFERRED]")
    quote: Optional[str] = Field(default=None, description="Verbatim text from source")


class WeldingRequirements(BaseModel):
    """Welding and fabrication process standards"""
    pressure_vessel_stamp: Optional[str] = Field(default=None, description="ASME U/R stamp requirements")
    process_piping_codes: List[str] = Field(default_factory=list, description="ASME B31.1/B31.3, etc.")
    aws_references: List[str] = Field(default_factory=list, description="AWS D1.1, D1.6, D1.2, etc.")
    weld_process_restrictions: List[str] = Field(default_factory=list, description="Welding process restrictions")
    other_directives: List[str] = Field(default_factory=list, description="Other fabrication quality directives")
    citations: List[Citation] = Field(default_factory=list)


class CriticalDimensionsCharacteristics(BaseModel):
    """Critical dimensions and tolerances"""
    general_tolerances: Optional[str] = Field(default=None, description="General dimensional tolerance standards")
    machining_surface_finish: List[str] = Field(default_factory=list, description="Machining or surface finish requirements")
    critical_features: List[str] = Field(default_factory=list, description="Specific CTQ dimensions with tolerances")
    citations: List[Citation] = Field(default_factory=list)


class CleaningFinishingRequirements(BaseModel):
    """Cleaning and finishing requirements"""
    passivation: Optional[str] = Field(default=None, description="Passivation requirements (e.g., ASTM A967)")
    pickling: Optional[str] = Field(default=None, description="Pickling requirements (e.g., ASTM A380)")
    electropolishing: Optional[str] = Field(default=None, description="Electropolishing requirements")
    other_stainless_finishing: List[str] = Field(default_factory=list, description="Other stainless steel finishing")
    carbon_steel_finishing: Optional[str] = Field(default=None, description="Paint, galvanize, powder coat, etc.")
    cleaning_requirements: List[str] = Field(default_factory=list, description="Degreasing, solvent cleaning, etc.")
    other_finishing: List[str] = Field(default_factory=list, description="Other finishing requirements")
    citations: List[Citation] = Field(default_factory=list)


class RequiredTestsInspections(BaseModel):
    """Required tests and inspections"""
    inspection_levels: List[str] = Field(default_factory=list, description="FAI, PPAP Level X, AQL, sampling plans")
    certificate_of_conformance: Optional[str] = Field(default=None, description="COC requirements")
    inspection_test_plan: Optional[str] = Field(default=None, description="ITP or Quality Plan references")
    liquid_penetrant: Optional[str] = Field(default=None, description="PT requirements")
    radiography: Optional[str] = Field(default=None, description="RT requirements")
    mtr_traceability: Optional[str] = Field(default=None, description="MTR traceability requirements")
    weld_mapping: Optional[str] = Field(default=None, description="Weld mapping requirements")
    pressure_testing: Optional[str] = Field(default=None, description="Hydrostatic, pneumatic, leak testing")
    pmi_testing: Optional[str] = Field(default=None, description="PMI requirements")
    ferrite_testing: Optional[str] = Field(default=None, description="Ferrite content testing")
    visual_weld_inspection: Optional[str] = Field(default=None, description="Visual inspection, CWI")
    ultrasound_magnetic: Optional[str] = Field(default=None, description="UT or MT inspection")
    trial_fits: List[str] = Field(default_factory=list, description="Trial fit or assembly requirements")
    functional_tests: List[str] = Field(default_factory=list, description="Functional testing requirements")
    other_inspections: List[str] = Field(default_factory=list, description="Other specified tests")
    citations: List[Citation] = Field(default_factory=list)


class QualityPlanDetailed(BaseModel):
    """QMA's detailed structured output"""
    welding_requirements: WeldingRequirements = Field(default_factory=WeldingRequirements)
    critical_dimensions: CriticalDimensionsCharacteristics = Field(default_factory=CriticalDimensionsCharacteristics)
    cleaning_finishing: CleaningFinishingRequirements = Field(default_factory=CleaningFinishingRequirements)
    tests_inspections: RequiredTestsInspections = Field(default_factory=RequiredTestsInspections)
    
    # Summary fields for template compatibility
    hold_points: List[str] = Field(
        default_factory=list,
        description="Inspection hold points (e.g., 'After welding', 'Before passivation', 'Final inspection')"
    )
    metrology: List[str] = Field(
        default_factory=list,
        description="Metrology opportunities (CMM, Faro arm, laser scan, etc.)"
    )


class QMATaskOutput(BaseModel):
    """A suggested QA task"""
    name: str
    notes: Optional[str] = None
    owner_hint: Optional[str] = "QA"
    due_date: Optional[str] = None
    source_hint: Optional[str] = None


class QMAConflictOutput(BaseModel):
    """A conflict between requirements"""
    topic: str
    issue: str
    citations: List[Dict[str, Optional[str]]] = Field(default_factory=list)


class QMAResponse(BaseModel):
    """Complete QMA agent response with structured outputs"""
    quality_plan: QualityPlanDetailed
    tasks: List[QMATaskOutput] = Field(default_factory=list)
    conflicts: List[QMAConflictOutput] = Field(default_factory=list)
    open_items: List[str] = Field(
        default_factory=list,
        description="Missing information or questions needing resolution"
    )


# Generate JSON Schema from Pydantic model with strict mode fixes
def _make_strict_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively fix schema for OpenAI strict mode requirements:
    1. Add additionalProperties: false to all objects
    2. Ensure 'required' array includes all properties
    """
    if isinstance(schema, dict):
        # Fix object types
        if schema.get("type") == "object":
            # Add additionalProperties: false
            if "additionalProperties" not in schema:
                schema["additionalProperties"] = False

            # Ensure 'required' array includes all properties
            if "properties" in schema:
                all_props = list(schema["properties"].keys())
                if "required" not in schema:
                    schema["required"] = all_props
                else:
                    # Make sure all properties are in required
                    for prop in all_props:
                        if prop not in schema["required"]:
                            schema["required"].append(prop)

        # Recursively process nested schemas
        for key, value in schema.items():
            if isinstance(value, dict):
                _make_strict_schema(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        _make_strict_schema(item)

    return schema

_base_schema = QMAResponse.model_json_schema()
_QUALITY_PATCH_SCHEMA: Dict[str, Any] = {
    "name": "QMAResponse",
    "strict": True,
    "schema": _make_strict_schema(_base_schema)
}


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    return OpenAI(api_key=api_key)


def _blank_patch() -> AgentPatch:
    return AgentPatch(patch={"quality_plan": QualityPlan().model_dump()}, tasks=[], conflicts=[])


def _summarize_context(plan_json: Dict[str, Any], context_pack: ContextPack) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "project": plan_json.get("project"),
        "customer": plan_json.get("customer"),
        "revision": plan_json.get("revision"),
        "existing_quality_plan": plan_json.get("quality_plan"),
        "purchasing": plan_json.get("purchasing"),
        "release_plan": plan_json.get("release_plan"),
        "execution_strategy": plan_json.get("execution_strategy"),
        "facts": [fact.model_dump() for fact in context_pack.facts],
    }
    return summary


def _extract_json(response: Any) -> Dict[str, Any]:
    """Extract JSON from OpenAI Responses API output"""
    if response is None:
        return {}
    if isinstance(response, dict):
        return response
    
    # Try to extract from response.output blocks
    output_blocks = getattr(response, "output", None)
    if output_blocks:
        for block in output_blocks:
            content = getattr(block, "content", None) or (block.get("content") if isinstance(block, dict) else None)
            if not content:
                continue
            for item in content:
                item_type = getattr(item, "type", None) or (item.get("type") if isinstance(item, dict) else None)
                if item_type == "output_json":
                    data = getattr(item, "json", None)
                    if data is None and isinstance(item, dict):
                        data = item.get("json")
                    if isinstance(data, dict):
                        return data
                if item_type == "text":
                    text_value = getattr(item, "text", None) or (item.get("text") if isinstance(item, dict) else None)
                    if isinstance(text_value, str):
                        try:
                            return json.loads(text_value)
                        except json.JSONDecodeError:
                            LOGGER.debug("QMA text block not JSON: %s", text_value)
    
    # Try output_text attribute
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        try:
            return json.loads(output_text)
        except json.JSONDecodeError:
            LOGGER.debug("QMA output_text not JSON: %s", output_text)
    
    # Try model_dump if available
    dump_method = getattr(response, "model_dump", None)
    if callable(dump_method):
        dumped = dump_method()
        if isinstance(dumped, dict):
            return dumped
    
    return {}


def _normalize_patch(qma_response: QMAResponse) -> Dict[str, Any]:
    """Convert detailed QMA response to template-compatible quality_plan format"""
    qp = qma_response.quality_plan
    
    # Build passivation summary from welding requirements
    passivation_parts = []
    if qp.welding_requirements.pressure_vessel_stamp:
        passivation_parts.append(qp.welding_requirements.pressure_vessel_stamp)
    if qp.welding_requirements.aws_references:
        passivation_parts.append(", ".join(qp.welding_requirements.aws_references))
    if qp.welding_requirements.process_piping_codes:
        passivation_parts.append(", ".join(qp.welding_requirements.process_piping_codes))
    if qp.welding_requirements.weld_process_restrictions:
        passivation_parts.append("; ".join(qp.welding_requirements.weld_process_restrictions))
    passivation_summary = "; ".join(passivation_parts) if passivation_parts else None
    
    # Build CTQs list from critical dimensions
    ctqs = []
    if qp.critical_dimensions.general_tolerances:
        ctqs.append(f"General tolerances: {qp.critical_dimensions.general_tolerances}")
    ctqs.extend(qp.critical_dimensions.machining_surface_finish)
    ctqs.extend(qp.critical_dimensions.critical_features)
    
    # Build cleanliness summary from cleaning/finishing
    cleanliness_parts = []
    if qp.cleaning_finishing.passivation:
        cleanliness_parts.append(f"Passivation: {qp.cleaning_finishing.passivation}")
    if qp.cleaning_finishing.pickling:
        cleanliness_parts.append(f"Pickling: {qp.cleaning_finishing.pickling}")
    if qp.cleaning_finishing.electropolishing:
        cleanliness_parts.append(f"Electropolishing: {qp.cleaning_finishing.electropolishing}")
    cleanliness_parts.extend(qp.cleaning_finishing.other_stainless_finishing)
    if qp.cleaning_finishing.carbon_steel_finishing:
        cleanliness_parts.append(qp.cleaning_finishing.carbon_steel_finishing)
    cleanliness_parts.extend(qp.cleaning_finishing.cleaning_requirements)
    cleanliness_parts.extend(qp.cleaning_finishing.other_finishing)
    cleanliness_summary = "; ".join(cleanliness_parts) if cleanliness_parts else None
    
    # Build required tests list
    required_tests = []
    ti = qp.tests_inspections
    if ti.liquid_penetrant: required_tests.append(f"PT: {ti.liquid_penetrant}")
    if ti.radiography: required_tests.append(f"RT: {ti.radiography}")
    if ti.pressure_testing: required_tests.append(ti.pressure_testing)
    if ti.pmi_testing: required_tests.append(f"PMI: {ti.pmi_testing}")
    if ti.ferrite_testing: required_tests.append(f"Ferrite: {ti.ferrite_testing}")
    if ti.visual_weld_inspection: required_tests.append(f"Visual: {ti.visual_weld_inspection}")
    if ti.ultrasound_magnetic: required_tests.append(ti.ultrasound_magnetic)
    required_tests.extend(ti.trial_fits)
    required_tests.extend(ti.functional_tests)
    required_tests.extend(ti.other_inspections)
    
    # Build documentation list
    documentation = []
    documentation.extend(ti.inspection_levels)  # FAI, PPAP Level 3, etc.
    if ti.certificate_of_conformance: documentation.append("COC")
    if ti.inspection_test_plan: documentation.append("ITP")
    if ti.mtr_traceability: documentation.append("MTR traceability")
    if ti.weld_mapping: documentation.append("Weld map")
    
    # Return normalized quality_plan matching schema
    normalized = QualityPlan(**{
        "ctqs": ctqs,
        "inspection_levels": ti.inspection_levels,
        "passivation": passivation_summary,
        "cleanliness": cleanliness_summary,
        "hold_points": qp.hold_points,
        "required_tests": required_tests,
        "documentation": documentation,
        "metrology": qp.metrology,
    }).model_dump()
    
    return normalized


def run_qma(
    plan_json: Dict[str, Any],
    context_pack: ContextPack,
    vector_store_id: str | None,
) -> AgentPatch:
    """Execute the Quality Manager Agent and return its patch."""

    if not vector_store_id:
        LOGGER.info("run_qma invoked without vector store; returning blank patch.")
        return _blank_patch()

    model = os.getenv("OPENAI_MODEL_QMA", os.getenv("OPENAI_MODEL_PLAN", "gpt-5"))
    payload = {
        "plan_snapshot": plan_json,
        "context_pack": _summarize_context(plan_json, context_pack),
        "instructions": "Analyze the uploaded documents and extract quality planning requirements. Fill the quality_plan structure with detailed information from the documents. Use citations for traceability.",
    }

    try:
        LOGGER.info("QMA: Calling OpenAI Threads API...")
        data = run_json_schema_thread(
            model=model,
            system_prompt=QMA_SYSTEM,
            user_prompt=payload,
            json_schema=_QUALITY_PATCH_SCHEMA,
            vector_store_id=vector_store_id,
            temperature=0.1,
        )
        LOGGER.info("QMA: Got response from OpenAI Threads")
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.exception("QMA threads call failed: %s", exc)
        return _blank_patch()
    LOGGER.info("QMA: Extracted JSON data type=%s", type(data))
    if not isinstance(data, dict):
        LOGGER.warning("QMA returned non-dict payload; defaulting to blank patch.")
        return _blank_patch()

    # Parse the structured response
    try:
        qma_response = QMAResponse(**data)
        LOGGER.info("QMA: Successfully parsed QMAResponse with %d tasks, %d conflicts", 
                   len(qma_response.tasks), len(qma_response.conflicts))
    except Exception as exc:
        LOGGER.warning("Failed to parse QMA response as QMAResponse: %s", exc)
        LOGGER.debug("Raw response data: %s", data)
        return _blank_patch()

    # Convert detailed structure to template-compatible format
    patch_dict = _normalize_patch(qma_response)
    
    # Convert tasks
    tasks = [
        AgentTask(
            name=task.name,
            notes=task.notes,
            owner_hint=task.owner_hint or "QA",
            due_date=task.due_date,
            source_hint=task.source_hint,
        )
        for task in qma_response.tasks
    ]
    
    # Convert conflicts
    conflicts = [
        AgentConflict(
            topic=conflict.topic,
            issue=conflict.issue,
            citations=conflict.citations,
        )
        for conflict in qma_response.conflicts
    ]

    return AgentPatch(patch={"quality_plan": patch_dict}, tasks=tasks, conflicts=conflicts)
