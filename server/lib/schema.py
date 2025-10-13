"""
Shared JSON Schema and APQP Checklist for Strategic Build Planner
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Source(BaseModel):
    kind: Literal[
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
    authority: Literal["mandatory", "conditional", "reference", "internal"]
    precedence_rank: int
    scope: list[str]
    applies_if: Optional[dict[str, str]] = None
    rev: Optional[str] = None
    effective_date: Optional[str] = None
    id: str
    title: str
    customer: Optional[str] = None
    family: Optional[str] = None


class Citation(BaseModel):
    source_id: str
    page_ref: Optional[str] = None
    passage_sha: Optional[str] = None


class Fact(BaseModel):
    id: str
    claim: str
    topic: str
    citation: Citation
    authority: Literal["mandatory", "conditional", "reference", "internal"]
    precedence_rank: int
    applies_if: Optional[dict[str, str]] = None
    status: Literal["canonical", "proposed", "superseded"]
    confidence_model: Optional[float] = None


class ContextPack(BaseModel):
    project: Dict[str, Any]
    sources: list[Source]
    facts: list[Fact]
    precedence_policy: str = "lower rank overrides higher"


class AgentTask(BaseModel):
    name: str
    notes: Optional[str] = None
    owner_hint: Optional[str] = None
    due_date: Optional[str] = None
    source_hint: Optional[str] = None


class AgentConflict(BaseModel):
    topic: str
    issue: str
    citations: List[Dict[str, Optional[str]]] = Field(default_factory=list)


class AgentPatch(BaseModel):
    patch: Dict[str, Any] = Field(default_factory=dict)
    tasks: List[AgentTask] = Field(default_factory=list)
    conflicts: List[AgentConflict] = Field(default_factory=list)


class EMASourceRef(BaseModel):
    source_id: str
    page_ref: Optional[str] = None
    passage_sha: Optional[str] = None


class EMARoutingOp(BaseModel):
    op_no: int
    workcenter: str
    input: Optional[str] = None
    program: Optional[str] = None
    notes: List[str] = Field(default_factory=list)
    qc: List[str] = Field(default_factory=list)
    sources: List[EMASourceRef] = Field(default_factory=list)


class EngineeringFixture(BaseModel):
    id: str
    type: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    due: Optional[str] = None
    sources: List[EMASourceRef] = Field(default_factory=list)


class EngineeringProgram(BaseModel):
    machine: str
    file: str
    rev: Optional[str] = None
    notes: Optional[str] = None
    sources: List[EMASourceRef] = Field(default_factory=list)


class DFMAction(BaseModel):
    action: str
    target: Optional[str] = None
    rationale: Optional[str] = None
    sources: List[EMASourceRef] = Field(default_factory=list)


class QualityRoutingPlacement(BaseModel):
    op_no: int
    workcenter: str
    quality_operation: str
    notes: List[str] = Field(default_factory=list)
    sources: List[EMASourceRef] = Field(default_factory=list)


class EngineeringInstructions(BaseModel):
    routing: List[EMARoutingOp] = Field(default_factory=list)
    fixtures: List[EngineeringFixture] = Field(default_factory=list)
    programs: List[EngineeringProgram] = Field(default_factory=list)
    ctqs_for_routing: List[str] = Field(default_factory=list)
    open_items: List[str] = Field(default_factory=list)
    # New focused outputs for EMA
    exceptional_steps: List[EMARoutingOp] = Field(default_factory=list)
    dfm_actions: List[DFMAction] = Field(default_factory=list)
    quality_routing: List[QualityRoutingPlacement] = Field(default_factory=list)


class QualityPlan(BaseModel):
    ctqs: List[str] = Field(default_factory=list)
    inspection_levels: List[str] = Field(default_factory=list)
    passivation: Optional[str] = None
    cleanliness: Optional[str] = None
    hold_points: List[str] = Field(default_factory=list)
    required_tests: List[str] = Field(default_factory=list)
    documentation: List[str] = Field(default_factory=list)
    metrology: List[str] = Field(default_factory=list)


class PurchasingItem(BaseModel):
    item: str
    lead_time: Optional[str] = None
    vendor_hint: Optional[str] = None
    citations: List[Dict[str, Optional[str]]] = Field(default_factory=list)


class PurchasingAlternate(BaseModel):
    item: str
    alternate: str
    rationale: Optional[str] = None
    citations: List[Dict[str, Optional[str]]] = Field(default_factory=list)


class PurchasingRFQ(BaseModel):
    item: str
    vendor: Optional[str] = None
    due: Optional[str] = None
    citations: List[Dict[str, Optional[str]]] = Field(default_factory=list)


class PurchasingPlan(BaseModel):
    long_leads: List[PurchasingItem] = Field(default_factory=list)
    coo_mtr: Optional[str] = None
    alternates: List[PurchasingAlternate] = Field(default_factory=list)
    rfqs: List[PurchasingRFQ] = Field(default_factory=list)


class ScheduleMilestone(BaseModel):
    name: str
    start_hint: Optional[str] = None
    end_hint: Optional[str] = None
    owner: Optional[str] = None
    citations: List[Dict[str, Optional[str]]] = Field(default_factory=list)


class SchedulePlan(BaseModel):
    milestones: List[ScheduleMilestone] = Field(default_factory=list)
    do_early: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class ExecutionTimebox(BaseModel):
    window: str
    focus: str
    owner_hint: Optional[str] = None
    notes: List[str] = Field(default_factory=list)
    citations: List[Dict[str, Optional[str]]] = Field(default_factory=list)


class ExecutionStrategy(BaseModel):
    timeboxes: List[ExecutionTimebox] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)

# --------------------
# APQP Checklist for Stainless Sheet-Metal
# --------------------
APQP_CHECKLIST = [
    # Contract/Commercial
    "PO vs Quote deltas (qtys, release cadence, price breaks, payment terms, Incoterms)",
    "Customer quality flowdowns (ISO/AS, special certifications, PPAP level)",
    "Regulatory (RoHS/REACH), ITAR/EAR, cybersecurity/DFARS flowdowns if any",

    # Technical Requirements
    "Material grade/spec (304/316/321/etc), thickness, temper; mill certs & traceability",
    "Finish (e.g., #4, bead blast), passivation (ASTM A967/A380), heat tint removal)",
    "Weld symbols (AWS D1.6 / customer spec), weld sequences & distortion control",
    "Grain direction, bend allowances, minimum flange lengths, K-factor assumptions",
    "Critical GD&T features/tolerances; datum strategy; datum transfer across ops",
    "Tube vs flat differences (ovalization, cope, fishmouth, miters); tube laser cut quirk risks",
    "Fixturing requirements (tack, weld, inspection); modular vs dedicated",
    "CMM/laser scan vs gauges; sampling plans; first-article (FAI/PPAP) specifics",
    "Special processes (coatings, heat treat, passivation vendor requirements)",
    "Packaging/labeling/cleanliness (food/med device?), lot control, serialization",

    # Manufacturing Plan
    "Process flow (blank → form → trim → weld → finish → inspect → pack); routers",
    "Cell layout and bottlenecks; robotics availability; weld torch access/clearances",
    "Tooling: punches/dies, press brake tooling, locators; lead-time & buy/make decisions",
    "Capacity & takt assumptions; setup reduction (SMED) opportunities",
    "SPC/CPk on CTQs; gage R&R; control plan alignment with PFMEA",
    "Risk register (top 3 risks) + mitigations + owners + due dates",
    "Cost levers (material utilization, nesting, multi-op setups, fixture reuse, robot programs)",
    "Timeline & gates; long-lead items; first‑ship readiness checklist",
]

# --------------------
# Structured Output Schema
# --------------------
PLAN_SCHEMA = {
    "name": "StrategicBuildPlan",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "project": {"type": "string", "description": "Project / part family name"},
            "customer": {"type": "string"},
            "revision": {"type": "string"},
            "summary": {"type": "string"},
            "requirements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "topic": {"type": "string"},
                        "requirement": {"type": "string"},
                        "source_hint": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                    },
                    "required": ["topic", "requirement", "source_hint", "confidence"]
                }
            },
            "engineering_instructions": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "routing": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "op_no": {"type": "integer"},
                                "workcenter": {"type": "string"},
                                "input": {"type": ["string", "null"]},
                                "program": {"type": ["string", "null"]},
                                "notes": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "qc": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "sources": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "source_id": {"type": "string"},
                                            "page_ref": {"type": ["string", "null"]},
                                            "passage_sha": {"type": ["string", "null"]}
                                        },
                                        "required": ["source_id", "page_ref", "passage_sha"]
                                    }
                                }
                            },
                            "required": [
                                "op_no",
                                "workcenter",
                                "input",
                                "program",
                                "notes",
                                "qc",
                                "sources"
                            ]
                        }
                    },
                    "fixtures": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "id": {"type": "string"},
                                "type": {"type": ["string", "null"]},
                                "status": {"type": ["string", "null"]},
                                "owner": {"type": ["string", "null"]},
                                "due": {"type": ["string", "null"]},
                                "sources": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "source_id": {"type": "string"},
                                            "page_ref": {"type": ["string", "null"]},
                                            "passage_sha": {"type": ["string", "null"]}
                                        },
                                        "required": ["source_id", "page_ref", "passage_sha"]
                                    }
                                }
                            },
                            "required": ["id", "type", "status", "owner", "due", "sources"]
                        }
                    },
                    "programs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "machine": {"type": "string"},
                                "file": {"type": "string"},
                                "rev": {"type": ["string", "null"]},
                                "notes": {"type": ["string", "null"]},
                                "sources": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "source_id": {"type": "string"},
                                            "page_ref": {"type": ["string", "null"]},
                                            "passage_sha": {"type": ["string", "null"]}
                                        },
                                        "required": ["source_id", "page_ref", "passage_sha"]
                                    }
                                }
                            },
                            "required": ["machine", "file", "rev", "notes", "sources"]
                        }
                    },
                    "ctqs_for_routing": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "open_items": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "exceptional_steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "op_no": {"type": "integer"},
                                "workcenter": {"type": "string"},
                                "input": {"type": ["string", "null"]},
                                "program": {"type": ["string", "null"]},
                                "notes": {"type": "array", "items": {"type": "string"}},
                                "qc": {"type": "array", "items": {"type": "string"}},
                                "sources": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "source_id": {"type": "string"},
                                            "page_ref": {"type": ["string", "null"]},
                                            "passage_sha": {"type": ["string", "null"]}
                                        },
                                        "required": ["source_id", "page_ref", "passage_sha"]
                                    }
                                }
                            },
                            "required": [
                                "op_no",
                                "workcenter",
                                "input",
                                "program",
                                "notes",
                                "qc",
                                "sources"
                            ]
                        }
                    },
                    "dfm_actions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "action": {"type": "string"},
                                "target": {"type": ["string", "null"]},
                                "rationale": {"type": ["string", "null"]},
                                "sources": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "source_id": {"type": "string"},
                                            "page_ref": {"type": ["string", "null"]},
                                            "passage_sha": {"type": ["string", "null"]}
                                        },
                                        "required": ["source_id", "page_ref", "passage_sha"]
                                    }
                                }
                            },
                            "required": ["action", "target", "rationale", "sources"]
                        }
                    },
                    "quality_routing": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "op_no": {"type": "integer"},
                                "workcenter": {"type": "string"},
                                "quality_operation": {"type": "string"},
                                "notes": {"type": "array", "items": {"type": "string"}},
                                "sources": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "source_id": {"type": "string"},
                                            "page_ref": {"type": ["string", "null"]},
                                            "passage_sha": {"type": ["string", "null"]}
                                        },
                                        "required": ["source_id", "page_ref", "passage_sha"]
                                    }
                                }
                            },
                            "required": ["op_no", "workcenter", "quality_operation", "notes", "sources"]
                        }
                    }
                },
                "required": [
                    "routing",
                    "fixtures",
                    "programs",
                    "ctqs_for_routing",
                    "open_items",
                    "exceptional_steps",
                    "dfm_actions",
                    "quality_routing"
                ]
            },
            "quality_plan": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "ctqs": {"type": "array", "items": {"type": "string"}},
                    "inspection_levels": {"type": "array", "items": {"type": "string"}},
                    "passivation": {"type": ["string", "null"]},
                    "cleanliness": {"type": ["string", "null"]},
                    "hold_points": {"type": "array", "items": {"type": "string"}},
                    "required_tests": {"type": "array", "items": {"type": "string"}},
                    "documentation": {"type": "array", "items": {"type": "string"}},
                    "metrology": {"type": "array", "items": {"type": "string"}}
                },
                "required": [
                    "ctqs",
                    "inspection_levels",
                    "passivation",
                    "cleanliness",
                    "hold_points",
                    "required_tests",
                    "documentation",
                    "metrology"
                ]
            },
            "purchasing": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "long_leads": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "item": {"type": "string"},
                                "lead_time": {"type": ["string", "null"]},
                                "vendor_hint": {"type": ["string", "null"]},
                                "citations": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "source_id": {"type": "string"},
                                            "page_ref": {"type": ["string", "null"]},
                                            "passage_sha": {"type": ["string", "null"]}
                                        },
                                        "required": ["source_id", "page_ref", "passage_sha"]
                                    }
                                }
                            },
                            "required": ["item", "lead_time", "vendor_hint", "citations"]
                        }
                    },
                    "coo_mtr": {"type": ["string", "null"]},
                    "alternates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "item": {"type": "string"},
                                "alternate": {"type": "string"},
                                "rationale": {"type": ["string", "null"]},
                                "citations": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "source_id": {"type": "string"},
                                            "page_ref": {"type": ["string", "null"]},
                                            "passage_sha": {"type": ["string", "null"]}
                                        },
                                        "required": ["source_id", "page_ref", "passage_sha"]
                                    }
                                }
                            },
                            "required": ["item", "alternate", "rationale", "citations"]
                        }
                    },
                    "rfqs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "item": {"type": "string"},
                                "vendor": {"type": ["string", "null"]},
                                "due": {"type": ["string", "null"]},
                                "citations": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "source_id": {"type": "string"},
                                            "page_ref": {"type": ["string", "null"]},
                                            "passage_sha": {"type": ["string", "null"]}
                                        },
                                        "required": ["source_id", "page_ref", "passage_sha"]
                                    }
                                }
                            },
                            "required": ["item", "vendor", "due", "citations"]
                        }
                    }
                },
                "required": ["long_leads", "coo_mtr", "alternates", "rfqs"]
            },
            "release_plan": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "milestones": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "name": {"type": "string"},
                                "start_hint": {"type": ["string", "null"]},
                                "end_hint": {"type": ["string", "null"]},
                                "owner": {"type": ["string", "null"]},
                                "citations": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "source_id": {"type": "string"},
                                            "page_ref": {"type": ["string", "null"]},
                                            "passage_sha": {"type": ["string", "null"]}
                                        },
                                        "required": ["source_id", "page_ref", "passage_sha"]
                                    }
                                }
                            },
                            "required": ["name", "start_hint", "end_hint", "owner", "citations"]
                        }
                    },
                    "do_early": {"type": "array", "items": {"type": "string"}},
                    "risks": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["milestones", "do_early", "risks"]
            },
            "execution_strategy": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "timeboxes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "window": {"type": "string"},
                                "focus": {"type": "string"},
                                "owner_hint": {"type": ["string", "null"]},
                                "notes": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "citations": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "source_id": {"type": "string"},
                                            "page_ref": {"type": ["string", "null"]},
                                            "passage_sha": {"type": ["string", "null"]}
                                        },
                                        "required": ["source_id", "page_ref", "passage_sha"]
                                    }
                                }
                            },
                            "required": ["window", "focus", "owner_hint", "notes", "citations"]
                        }
                    },
                    "notes": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["timeboxes", "notes"]
            },
            "open_questions": {
                "type": "array",
                "items": {"type": "string"}
            },
            "cost_levers": {
                "type": "array",
                "items": {"type": "string"}
            },
            "pack_ship": {"type": ["string", "null"]},
            "source_files_used": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": [
            "project",
            "customer",
            "revision",
            "summary",
            "requirements",
            "engineering_instructions",
            "quality_plan",
            "purchasing",
            "release_plan",
            "execution_strategy",
            "open_questions",
            "cost_levers",
            "pack_ship",
            "source_files_used"
        ]
    },
    "strict": True
}

# --------------------
# QA Rubric Schema
# --------------------
QA_RUBRIC_SCHEMA = {
    "name": "QAGradeResult",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "overall_score": {"type": "number", "minimum": 0, "maximum": 100},
            "dimensions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "dimension": {"type": "string", "enum": ["Completeness", "Specificity", "Actionability", "Manufacturability", "Risk"]},
                        "score": {"type": "number", "minimum": 0, "maximum": 100},
                        "reasons": {"type": "array", "items": {"type": "string"}},
                        "fixes": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["dimension", "score", "reasons", "fixes"]
                }
            }
        },
        "required": ["overall_score", "dimensions"]
    },
    "strict": True
}
