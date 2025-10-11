#!/usr/bin/env python3
"""
Strategic Build Planner - APQP Assistant MVP

Uses OpenAI's Responses API with Vector Stores and Structured Outputs
to draft manufacturing-ready Strategic Build Plans for stainless sheet-metal fabrication.

Northern Manufacturing Co., Inc.
"""

import os, sys, json, argparse, tempfile, textwrap, time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth
from jinja2 import Template
from openai import OpenAI

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
            "process_flow": {"type": "string"},
            "tooling_fixturing": {"type": "string"},
            "quality_plan": {"type": "string"},
            "materials_finishes": {"type": "string"},
            "quality_plan_hold_points": {"type": "string"},
            "quality_plan_welding": {"type": "string"},
            "quality_plan_cleaning": {"type": "string"},
            "quality_plan_test_fits": {"type": "string"},
            "quality_plan_checklists": {"type": "string"},
            "quality_plan_tests": {"type": "string"},
            "supplier_quality_manual": {"type": "string"},
            "quality_plan_other": {"type": "string"},
            "metrology_opportunities": {"type": "string"},
            "purchasing_country_of_origin": {"type": "string"},
            "long_lead_items": {"type": "string"},
            "outsourced_items": {"type": "string"},
            "high_volume_material": {"type": "string"},
            "customer_supplied_items": {"type": "string"},
            "purchasing_coatings": {"type": "string"},
            "release_plan": {"type": "string"},
            "ctqs": {
                "type": "array",
                "items": {"type":"string"}
            },
            "risks": {
                "type": "array",
                "items": {
                    "type":"object",
                    "additionalProperties": False,
                    "properties": {
                        "risk": {"type":"string"},
                        "impact": {"type":"string"},
                        "mitigation": {"type":"string"},
                        "owner": {"type":"string"},
                        "due_date": {"type":"string"}
                    },
                    "required": ["risk", "impact", "mitigation", "owner", "due_date"]
                }
            },
            "open_questions": {
                "type":"array",
                "items":{"type":"string"}
            },
            "cost_levers": {"type":"array","items":{"type":"string"}},
            "pack_ship": {"type":"string"},
            "source_files_used": {"type":"array","items":{"type":"string"}}
        },
        "required": [
            "project", "customer", "revision", "summary", "requirements",
            "process_flow", "tooling_fixturing", "quality_plan", "materials_finishes",
            "quality_plan_hold_points", "quality_plan_welding", "quality_plan_cleaning",
            "quality_plan_test_fits", "quality_plan_checklists", "quality_plan_tests",
            "supplier_quality_manual", "quality_plan_other", "metrology_opportunities",
            "purchasing_country_of_origin", "long_lead_items", "outsourced_items",
            "high_volume_material", "customer_supplied_items", "purchasing_coatings",
            "release_plan", "ctqs", "risks", "open_questions", "cost_levers", "pack_ship",
            "source_files_used"
        ]
    },
    "strict": True
}

# --------------------
# Markdown Template (Jinja2)
# --------------------
JINJA_TEMPLATE = """# Strategic Build Plan — {{ project }} ({{ customer }})
**Rev:** {{ revision or '—' }}  
**Date:** {{ date }}

## Keys to the Project
{{ summary }}

### Key Requirements (curated)
{% for r in requirements -%}
- **{{ r.topic }}** — {{ r.requirement }}{% if r.source_hint %} _(source: {{ r.source_hint }})_{% endif %}{% if r.confidence is not none %} _(confidence: {{ '%.0f' % (100*r.confidence) }}%)_{% endif %}
{% endfor %}

### Quality Plan
- **Hold Points:** {{ quality_plan_hold_points|default('TBD', true) }}
- **Critical Dimensions / Characteristics:** {% if ctqs %}{{ ctqs|join(', ') }}{% else %}TBD{% endif %}
- **Welding Requirements:** {{ quality_plan_welding|default('TBD', true) }}
- **Cleaning Requirements:** {{ quality_plan_cleaning|default('TBD', true) }}
- **Test Fits:** {{ quality_plan_test_fits|default('TBD', true) }}
- **Required Check / Punch Lists:** {{ quality_plan_checklists|default('TBD', true) }}
- **Required Tests:** {{ quality_plan_tests|default('TBD', true) }}
- **Supplier Quality Manual:** {{ supplier_quality_manual|default('TBD', true) }}
- **Other:** {{ quality_plan_other|default('TBD', true) }}
- **Opportunities to use Faro tracer, Leica, or Twyn:** {{ metrology_opportunities|default('TBD', true) }}

### Purchasing
- **Country of Origin / Material Cert Requirements:** {{ purchasing_country_of_origin|default('TBD', true) }}
- **Long Lead Items:** {{ long_lead_items|default('TBD', true) }}
- **Outsourced Items:** {{ outsourced_items|default('TBD', true) }}
- **High Volume / Preordered Material:** {{ high_volume_material|default('TBD', true) }}
- **Customer Supplied Items:** {{ customer_supplied_items|default('TBD', true) }}
- **Coatings:** {{ purchasing_coatings|default(materials_finishes, true) }}

### Build Strategy
{{ process_flow|default('TBD', true) }}

### Execution Strategy
{{ tooling_fixturing|default('TBD', true) }}

### Release Plan
{{ release_plan|default('TBD', true) }}

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

## Open Questions
{% for q in open_questions -%}
- {{ q }}
{% endfor %}

## Cost Levers
{% for cl in cost_levers -%}
- {{ cl }}
{% endfor %}

---

_Sources used (for traceability):_
{% for s in source_files_used -%}
- {{ s }}
{% endfor %}
"""

# --------------------
# Config & helpers
# --------------------
def load_env():
    load_dotenv()
    cfg = {
        "openai_key": os.getenv("OPENAI_API_KEY"),
    "openai_model_plan": os.getenv("OPENAI_MODEL_PLAN", "gpt-4.1-mini"),
        "openai_model_transcribe": os.getenv("OPENAI_MODEL_TRANSCRIBE", "whisper-1"),
        "confluence_base": os.getenv("CONFLUENCE_BASE_URL"),
        "confluence_email": os.getenv("CONFLUENCE_EMAIL"),
        "confluence_token": os.getenv("CONFLUENCE_API_TOKEN"),
        "confluence_space": os.getenv("CONFLUENCE_SPACE_KEY"),
        "confluence_parent": os.getenv("CONFLUENCE_PARENT_PAGE_ID"),
    }
    return cfg

# --------------------
# Confluence helpers (Cloud REST API v1 + v2)
# --------------------
def get_space_id_by_key(base, email, token, space_key: str):
    """Get spaceId from space key using v2 API"""
    url = f"{base}/wiki/api/v2/spaces"
    resp = requests.get(url, params={"keys": space_key},
                        auth=HTTPBasicAuth(email, token))
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])
    if not results:
        raise ValueError(f"Space with key '{space_key}' not found")
    return results[0]["id"]

def cql_search(base, email, token, cql: str, limit=50):
    """v1 search with CQL"""
    url = f"{base}/wiki/rest/api/search"
    resp = requests.get(url, params={"cql": cql, "limit": limit},
                        auth=HTTPBasicAuth(email, token))
    resp.raise_for_status()
    data = resp.json()
    results = []
    for it in data.get("results", []):
        content = it.get("content", {})
        if content.get("id"):
            results.append({
                "id": content["id"],
                "title": content.get("title", "Untitled")
            })
    return results

def get_page_storage(base, email, token, page_id: str):
    """v2 pages with body-format=storage"""
    url = f"{base}/wiki/api/v2/pages/{page_id}"
    resp = requests.get(url, params={"body-format": "storage"},
                        auth=HTTPBasicAuth(email, token))
    resp.raise_for_status()
    js = resp.json()
    title = js.get("title", "Untitled")
    body_html = js.get("body", {}).get("storage", {}).get("value", "")
    # Quick HTML → text conversion (improve with BeautifulSoup if needed)
    text = body_html.replace("<br/>", "\n").replace("<p>", "\n").replace("</p>", "\n")
    return title, text

def create_confluence_page(base, email, token, space_key, parent_id, title, storage_html):
    """Create a new Confluence page using v2 API with spaceId (required)"""
    # Get spaceId from space key (required for v2 API)
    space_id = get_space_id_by_key(base, email, token, space_key)
    
    url = f"{base}/wiki/api/v2/pages"
    payload = {
        "spaceId": space_id,  # Required
        "status": "current",
        "title": title,
        "body": {
            "representation": "storage",
            "value": storage_html
        }
    }
    
    # Add parentId if provided
    if parent_id:
        payload["parentId"] = parent_id
    
    resp = requests.post(url, json=payload,
                         auth=HTTPBasicAuth(email, token))
    resp.raise_for_status()
    return resp.json()

# --------------------
# OpenAI helpers (Responses API + Vector Stores)
# --------------------
def create_vector_store_and_upload(client: OpenAI, name: str, file_paths):
    """Create a vector store and upload files for file search"""
    vs = client.vector_stores.create(name=name)
    streams = []
    for p in file_paths:
        streams.append(open(p, "rb"))
    try:
        batch = client.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vs.id,
            files=streams
        )
    finally:
        for s in streams:
            s.close()
    return vs, batch

def render_plan_md(plan: dict):
    """Render the JSON plan to Markdown using Jinja2"""
    t = Template(JINJA_TEMPLATE)
    return t.render(date=datetime.now().strftime("%Y-%m-%d"), **plan)

# --------------------
# Main flow
# --------------------
def run(project_name, local_files, confluence_cql, meeting_transcripts=None, publish_to_confluence=False):
    cfg = load_env()
    
    if not cfg["openai_key"]:
        print("❌ Error: OPENAI_API_KEY not set in .env file")
        sys.exit(1)
    
    client = OpenAI(api_key=cfg["openai_key"])

    print(f"\n{'='*70}")
    print(f"  Strategic Build Planner — {project_name}")
    print(f"{'='*70}\n")

    # 1) Gather inputs: local docs + Confluence pages (optional)
    tmp_files = []
    all_inputs = list(local_files)

    if confluence_cql and cfg["confluence_base"]:
        print(f"[Confluence] Searching with CQL: {confluence_cql}")
        try:
            hits = cql_search(cfg["confluence_base"], cfg["confluence_email"], 
                            cfg["confluence_token"], confluence_cql, limit=25)
            for h in hits:
                title, text = get_page_storage(cfg["confluence_base"], cfg["confluence_email"], 
                                              cfg["confluence_token"], h["id"])
                # Save as a temp .txt to feed into vector store
                tf = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w', encoding='utf-8')
                tf.write(f"# {title}\n\n{text}")
                tf.flush()
                tf.close()
                tmp_files.append(tf.name)
                print(f"  ✓ Fetched: {title}")
        except Exception as e:
            print(f"  ⚠ Confluence error: {e}")
    
    # 2) Add meeting transcripts if provided
    if meeting_transcripts:
        for meeting_path in meeting_transcripts:
            print(f"[Meeting] Adding transcript from: {meeting_path}")
            tf = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w', encoding='utf-8')
            with open(meeting_path, 'r', encoding='utf-8') as src:
                filename = Path(meeting_path).name
                tf.write(f"# Meeting Transcript: {filename}\n\n{src.read()}")
            tf.flush()
            tf.close()
            tmp_files.append(tf.name)

    all_inputs += tmp_files
    if not all_inputs:
        print("❌ No inputs found. Provide at least one file or Confluence CQL.")
        sys.exit(1)

    print(f"\n[Inputs] Processing {len(all_inputs)} file(s)...")
    for f in all_inputs:
        print(f"  - {Path(f).name}")

    # 3) Read file contents to include in prompt
    print("\n[OpenAI] Reading file contents...")
    documents_content = ""
    for file_path in all_inputs:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                filename = Path(file_path).name
                documents_content += f"\n\n=== {filename} ===\n{content}\n"
                print(f"  ✓ Read: {filename} ({len(content)} chars)")
        except Exception as e:
            print(f"  ⚠ Error reading {file_path}: {e}")

    # 4) Ask model for a Strategic Build Plan with structured outputs
    checklist_text = "\n".join([f"- {i}" for i in APQP_CHECKLIST])
    system_prompt = f"""
You are Northern Manufacturing's APQP/Contract-Review assistant.
You read procurement documents (POs/specs/quotes/drawings) and lessons learned (Confluence).
Produce a precise, **manufacturing-ready Strategic Build Plan** for stainless sheet-metal fabrication.

Rules:
- If a required item is missing, mark it as UNKNOWN and add to open_questions.
- Use conservative assumptions only if essential; call them out explicitly.
- Prefer specifics from sources over generic best-practices.
- Cite a source filename or page title when possible in source_hint.

Coverage checklist (use as a guide to build the plan; fill gaps if missing):
{checklist_text}
""".strip()

    user_task = f"""Draft the Strategic Build Plan for project '{project_name}'. 
Extract CTQs and weld/finish requirements precisely.

SOURCE DOCUMENTS:
{documents_content}
"""

    print("\n[OpenAI] Generating Strategic Build Plan with structured outputs...")
    try:
        # Use the standard chat completions API with structured outputs
        response = client.chat.completions.create(
            model="gpt-4o",  # Use GPT-4o for structured outputs
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_task
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": PLAN_SCHEMA
            },
            temperature=0.3
        )
    except Exception as e:
        print(f"❌ Error calling OpenAI API: {e}")
        sys.exit(3)

    # Extract JSON result from structured output
    plan_json = None
    try:
        # Chat completions with structured outputs return JSON in message content
        content = response.choices[0].message.content
        if content:
            plan_json = json.loads(content)
    except (json.JSONDecodeError, AttributeError, IndexError) as e:
        print(f"❌ Error parsing response: {e}")
        print("Raw response:", response)
        sys.exit(4)

    if not plan_json:
        print("❌ Model returned no structured plan. Raw response:\n", response)
        sys.exit(4)

    print(f"  ✓ Generated plan for: {plan_json.get('project', 'Unknown')}")
    print(f"  ✓ Customer: {plan_json.get('customer', 'Unknown')}")
    print(f"  ✓ Requirements: {len(plan_json.get('requirements', []))}")
    print(f"  ✓ Risks: {len(plan_json.get('risks', []))}")
    print(f"  ✓ Open Questions: {len(plan_json.get('open_questions', []))}")

    # 5) Render Markdown and save outputs to ./outputs/
    md = render_plan_md(plan_json)
    
    # Create outputs directory if it doesn't exist
    out_dir = Path("./outputs")
    out_dir.mkdir(exist_ok=True)
    
    # Generate filenames with project name
    safe_project_name = project_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    out_md = out_dir / f"Strategic_Build_Plan__{safe_project_name}.md"
    out_json = out_dir / f"Strategic_Build_Plan__{safe_project_name}.json"
    
    # Write Markdown file
    out_md.write_text(md, encoding="utf-8")
    print(f"\n[Output] ✓ Wrote Markdown: {out_md.resolve()}")
    
    # Write JSON file
    out_json.write_text(json.dumps(plan_json, indent=2), encoding="utf-8")
    print(f"[Output] ✓ Wrote JSON: {out_json.resolve()}")

    # 6) (Optional) publish to Confluence as a page
    page_url = None
    if publish_to_confluence and cfg["confluence_base"]:
        print("\n[Confluence] Publishing to Confluence...")
        if not cfg["confluence_space"]:
            print("  ⚠ Warning: CONFLUENCE_SPACE_KEY not set, skipping publish")
        else:
            try:
                # Convert Markdown to basic HTML (simple approach)
                storage_html = "<p>" + "</p><p>".join(line for line in md.splitlines()) + "</p>"
                title = f"Strategic Build Plan — {project_name}"
                
                # Create page with spaceId (required) and parentId (optional)
                res = create_confluence_page(
                    cfg["confluence_base"],
                    cfg["confluence_email"],
                    cfg["confluence_token"],
                    cfg["confluence_space"],
                    cfg["confluence_parent"],
                    title,
                    storage_html
                )
                
                page_id = res.get('id', '?')
                # Build page URL from response
                page_links = res.get('_links', {})
                web_ui = page_links.get('webui', '')
                if web_ui:
                    page_url = f"{cfg['confluence_base']}{web_ui}"
                else:
                    # Fallback URL construction
                    page_url = f"{cfg['confluence_base']}/wiki/spaces/{cfg['confluence_space']}/pages/{page_id}"
                
                print(f"  ✓ Created page: {res.get('title','(unknown)')}")
                print(f"  ✓ Page ID: {page_id}")
                print(f"  ✓ URL: {page_url}")
                
            except Exception as e:
                print(f"  ⚠ Confluence publish error: {e}")
                import traceback
                traceback.print_exc()

    # Cleanup temp files
    for f in tmp_files:
        try: 
            os.unlink(f)
        except: 
            pass

    print(f"\n{'='*70}")
    print("  ✅ Strategic Build Plan Complete!")
    print(f"{'='*70}\n")
    
    return page_url  # Return the Confluence page URL if published

if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="APQP Strategic Build Plan MVP - Northern Manufacturing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          # With local files only
          python apqp_starter.py --project "ACME Bracket Rev B" --files ./inputs/*.pdf
          
          # With Confluence context
          python apqp_starter.py --project "XYZ Enclosure" \\
            --files ./inputs/PO.pdf ./inputs/Drawing.pdf \\
            --cql 'space = KB AND label = "customer-acme" AND type = page'
          
          # With meeting transcript and publish
          python apqp_starter.py --project "Project Alpha" \\
            --files ./inputs/*.pdf \\
            --meeting ./meetings/kickoff-transcript.txt \\
            --publish
        """)
    )
    p.add_argument("--project", required=True, help="Project/part or PO identifier")
    p.add_argument("--files", nargs="*", default=[], help="Local files to include (PDF, DOCX, TXT, etc.)")
    p.add_argument("--cql", default="", help="Confluence CQL query for customer + family-of-parts pages")
    p.add_argument("--meeting", nargs="*", default=[], help="Path(s) to meeting transcript text file(s)")
    p.add_argument("--publish", action="store_true", help="Publish plan to Confluence")
    args = p.parse_args()
    
    run(args.project, args.files, args.cql, args.meeting, args.publish)
