"""
Markdown rendering for Strategic Build Plans
"""

from datetime import datetime
from typing import Any
from jinja2 import Environment


# --------------------
# Markdown Template (Jinja2)
# --------------------
JINJA_TEMPLATE = """# Strategic Build Plan — {{ project }} ({{ customer }})
**Rev:** {{ revision or '—' }}  
**Date:** {{ date }}

## Keys to the Project
{% if keys and keys|length > 0 -%}
{% for k in keys -%}
{{ loop.index }}. {{ k }}
{% endfor %}
{% elif summary -%}
{# If summary appears to contain newline-separated bullets, render as enumerated #}
{% set lines = summary.split('\n') %}
{% if lines|length > 1 %}
{% for k in lines %}
{{ loop.index }}. {{ k.strip() }}
{% endfor %}
{% else %}
{{ summary }}
{% endif %}
{% else -%}
1. Manufacturing priorities to be synthesized.
{% endif %}

### Quality Plan
{% if quality_plan -%}
- **Hold Points:** {% if quality_plan.hold_points %}{{ quality_plan.hold_points|join(', ') }}{% else %}None found{% endif %}
- **Critical Dimensions / Characteristics:** {% if quality_plan.ctqs %}{{ quality_plan.ctqs|join(', ') }}{% else %}None found{% endif %}
- **Welding Requirements:** {{ quality_plan.passivation|nn }}
- **Cleaning Requirements:** {{ quality_plan.cleanliness|nn }}
- **Test Fits:** TBD
- **Required Check / Punch Lists:** TBD
- **Required Tests:** {% if quality_plan.required_tests %}{{ quality_plan.required_tests|join(', ') }}{% else %}None found{% endif %}
- **Supplier Quality Manual:** None found
- **Other:** {% if quality_plan.documentation %}{{ quality_plan.documentation|join(', ') }}{% else %}None found{% endif %}
- **Opportunities to use Faro tracer, Leica, or Twyn:** {% if quality_plan.metrology %}{{ quality_plan.metrology|join(', ') }}{% else %}None found{% endif %}
{% else -%}
- **Hold Points:** None found
- **Critical Dimensions / Characteristics:** None found
- **Welding Requirements:** None found
- **Cleaning Requirements:** None found
- **Test Fits:** None found
- **Required Check / Punch Lists:** None found
- **Required Tests:** None found
- **Supplier Quality Manual:** None found
- **Other:** None found
- **Opportunities to use Faro tracer, Leica, or Twyn:** None found
{% endif %}

### Purchasing
{% if purchasing -%}
- **Country of Origin / Material Cert Requirements:** {{ purchasing.coo_mtr|nn }}
- **Long Lead Items:** {% if purchasing.long_leads %}
{% for item in purchasing.long_leads %}{% set _lead = (item.lead_time|nn) %}{% set _vendor = (item.vendor_hint|nn) %}{% if _lead == 'None found' %}{% set _lead = '' %}{% endif %}{% if _vendor == 'None found' %}{% set _vendor = '' %}{% endif %}  - {{ item.item|nn }}{% if _lead %} ({{ _lead }}){% endif %}{% if _vendor %} - {{ _vendor }}{% endif %}
{% endfor %}{% else %}None found{% endif %}
-- **Outsourced Items:** None found
-- **High Volume / Preordered Material:** None found
-- **Customer Supplied Items:** None found
- **Coatings:** {{ materials_finishes|default('', true)|nn }}
- **Alternates:** {% if purchasing.alternates %}{{ purchasing.alternates|length }} defined{% else %}None found{% endif %}
- **RFQs:** {% if purchasing.rfqs %}{{ purchasing.rfqs|length }} pending{% else %}None found{% endif %}
{% else -%}
- **Country of Origin / Material Cert Requirements:** None found
- **Long Lead Items:** None found
- **Outsourced Items:** None found
- **High Volume / Preordered Material:** None found
- **Customer Supplied Items:** None found
- **Coatings:** {{ materials_finishes|default('TBD', true) }}
{% endif %}

### Build Strategy
{{ process_flow|default('TBD', true) }}

### Execution Strategy
{{ tooling_fixturing|default('TBD', true) }}

### Release Plan
{{ schedule|default('TBD', true) }}

### Shipping
{{ pack_ship|default('TBD', true) }}

---

## Risks & Mitigations
{% for rk in risks -%}
- **Risk:** {{ rk.risk }}  
    Impact: {{ rk.impact or '—' }}  
    Mitigation: {{ rk.mitigation }}  
    Owner: {{ rk.owner or 'TBD' }}  Due: {{ rk.due_date or 'TBD' }}
{% endfor %}

{% if open_questions_curated and open_questions and open_questions|length > 0 -%}
## Open Questions
{% for q in open_questions -%}
{% if q is string %}- {{ q }}{% else %}- {{ q.question }}{% endif %}
{% endfor %}
{% endif %}

{% if cost_levers_curated and cost_levers and cost_levers|length > 0 -%}
## Cost Levers
{% for cl in cost_levers -%}
- {{ cl }}
{% endfor %}
{% endif %}

---

### Engineering Instructions
{% if engineering_instructions -%}
{% set ei = engineering_instructions %}
{% if ei.exceptional_steps and ei.exceptional_steps|length > 0 -%}
### Exceptional Steps (Non‑standard)
{% for step in ei.exceptional_steps -%}
1. {{ step.workcenter }}{% if step.sources and step.sources|length > 0 %} [^s:ex-{{ loop.index }}]{% endif %}
    {% if step.input %}- Input: {{ step.input }}{% endif %}
    {% if step.program %}- Program: {{ step.program }}{% endif %}
    {% if step.notes and step.notes|length > 0 %}- Notes: {{ step.notes|join('; ') }}{% endif %}
    {% if step.qc and step.qc|length > 0 %}- QC: {{ step.qc|join('; ') }}{% endif %}
{% endfor %}
{% endif %}

{% if ei.fixtures and ei.fixtures|length > 0 -%}
### Fixtures
{% for f in ei.fixtures -%}
- {{ f.id if f.id is defined else f.name if f.name is defined else 'Fixture' }}{% if f.type %} ({{ f.type }}){% endif %}{% if f.status %} — {{ f.status }}{% endif %}
{% endfor %}
{% endif %}

{% if ei.programs and ei.programs|length > 0 -%}
### Programs
{% for p in ei.programs -%}
- {{ p.machine }} — {{ p.file }}{% if p.rev %} (rev {{ p.rev }}){% endif %}
{% endfor %}
{% endif %}

{% if ei.quality_routing and ei.quality_routing|length > 0 -%}
### Quality Operation Placements
{% for q in ei.quality_routing -%}
1. {{ q.workcenter }}: {{ q.quality_operation }}{% if q.notes and q.notes|length > 0 %} — {{ q.notes|join('; ') }}{% endif %}{% if q.sources and q.sources|length > 0 %} [^s:qr-{{ loop.index }}]{% endif %}
{% endfor %}
{% endif %}

{% if ei.dfm_actions and ei.dfm_actions|length > 0 -%}
### DFM Actions to Carry Through in Design
{% for a in ei.dfm_actions -%}
- {{ a.action }}{% if a.target %} — Target: {{ a.target }}{% endif %}{% if a.rationale %} — Rationale: {{ a.rationale }}{% endif %}{% if a.sources and a.sources|length > 0 %} [^s:dfm-{{ loop.index }}]{% endif %}
{% endfor %}
{% endif %}

{% if ei.routing and ei.routing|length > 0 -%}
### Full Routing (if provided)
{% for step in ei.routing -%}
1. {{ step.workcenter }}{% if step.sources and step.sources|length > 0 %} [^s:rt-{{ loop.index }}]{% endif %}
    {% if step.input %}- Input: {{ step.input }}{% endif %}
    {% if step.program %}- Program: {{ step.program }}{% endif %}
    {% if step.notes and step.notes|length > 0 %}- Notes: {{ step.notes|join('; ') }}{% endif %}
    {% if step.qc and step.qc|length > 0 %}- QC: {{ step.qc|join('; ') }}{% endif %}
{% endfor %}
{% endif %}

{% if ei.ctqs_for_routing and ei.ctqs_for_routing|length > 0 -%}
### CTQs for Routing
{% for c in ei.ctqs_for_routing -%}
- {{ c }}
{% endfor %}
{% endif %}

{% if ei.open_items and ei.open_items|length > 0 -%}
### Open Items
{% for oi in ei.open_items -%}
- {{ oi }}
{% endfor %}
{% endif %}
{% else -%}
_Engineering instructions: TBD_
{% endif %}

---

_Sources used (for traceability):_
{% if context_sources and context_sources|length > 0 -%}
{% for s in context_sources -%}
- {{ s.id }} — {{ s.title }} ({{ s.kind }}; {{ s.authority }})
{% endfor %}
{% elif source_files_used and source_files_used|length > 0 -%}
{% for s in source_files_used -%}
- {{ s }}
{% endfor %}
{% else -%}
No sources listed.
{% endif %}

{# Footnotes for inline citations #}
{% if engineering_instructions and engineering_instructions.exceptional_steps and engineering_instructions.exceptional_steps|length > 0 -%}
{% for step in engineering_instructions.exceptional_steps -%}
{% if step.sources and step.sources|length > 0 %}
[^s:ex-{{ loop.index }}]: Sources: {{ step.sources | map(attribute='source_id') | join(', ') }}
{% endif %}
{% endfor %}
{% endif %}
{% if engineering_instructions and engineering_instructions.routing and engineering_instructions.routing|length > 0 -%}
{% for step in engineering_instructions.routing -%}
{% if step.sources and step.sources|length > 0 %}
[^s:rt-{{ loop.index }}]: Sources: {{ step.sources | map(attribute='source_id') | join(', ') }}
{% endif %}
{% endfor %}
{% endif %}
{% if engineering_instructions and engineering_instructions.quality_routing and engineering_instructions.quality_routing|length > 0 -%}
{% for item in engineering_instructions.quality_routing -%}
{% if item.sources and item.sources|length > 0 %}
[^s:qr-{{ loop.index }}]: Sources: {{ item.sources | map(attribute='source_id') | join(', ') }}
{% endif %}
{% endfor %}
{% endif %}
{% if engineering_instructions and engineering_instructions.dfm_actions and engineering_instructions.dfm_actions|length > 0 -%}
{% for item in engineering_instructions.dfm_actions -%}
{% if item.sources and item.sources|length > 0 %}
[^s:dfm-{{ loop.index }}]: Sources: {{ item.sources | map(attribute='source_id') | join(', ') }}
{% endif %}
{% endfor %}
{% endif %}
"""


def _nn(value: Any) -> str:
    if value is None:
        return "None found"
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value).strip()
    if not s:
        return "None found"
    upper = s.upper()
    if upper in {"UNKNOWN", "TBD", "T.B.D.", "NA", "N/A"}:
        return "None found"
    return s


def render_plan_md(plan_json: dict) -> str:
    """Render Strategic Build Plan JSON to Markdown"""
    # Don't trim newlines after Jinja blocks; bullet lines would otherwise merge
    env = Environment(autoescape=False, trim_blocks=False, lstrip_blocks=True)
    env.filters["nn"] = _nn
    tmpl = env.from_string(JINJA_TEMPLATE)
    plan_json["date"] = datetime.now().strftime("%Y-%m-%d")
    # Pass through context sources if available under common keys
    context_sources = []
    if isinstance(plan_json.get("context_pack"), dict):
        cp = plan_json.get("context_pack") or {}
        if isinstance(cp.get("sources"), list):
            context_sources = cp.get("sources")
    elif isinstance(plan_json.get("_context_sources"), list):
        context_sources = plan_json.get("_context_sources")
    ctx = dict(plan_json)
    ctx["context_sources"] = context_sources
    return tmpl.render(**ctx)
