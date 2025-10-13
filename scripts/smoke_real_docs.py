import os, json, sys
from pathlib import Path
import requests

API = os.getenv("SBP_API", "http://localhost:8001")

ROOT = Path(r"C:\Users\tsmith\OneDrive - Northern Manufacturing Co., Inc\Documents\GitHub\StrategicBuildPlanner")
inputs = ROOT / "inputs"
drawing = inputs / "DenCo 2025 U PP Demo TNMC 9-18-2025 Rev 0.pdf"
meeting = inputs / "F4892 - ASME QUALIFICATION Oct 10, 2025 9_56 AM _ Transcription Export.md"


def fail(msg, r=None):
    print(f"ERROR: {msg}")
    if r is not None:
        print(f"Status: {r.status_code}\nBody: {r.text[:1000]}")
    sys.exit(1)


def ingest(project_name: str):
    # files_meta must be a dict keyed by lowercase filename for server overrides to apply
    files_meta = {
        drawing.name.lower(): {
            "doc_type": "drawing",
            "authority": "mandatory",
            "precedence_rank": "high",
        },
        meeting.name.lower(): {
            "doc_type": "meeting_notes",
            "authority": "internal",
            "precedence_rank": "high",
        },
    }
    with open(drawing, "rb") as f1, open(meeting, "rb") as f2:
        files = [
            ("files", (drawing.name, f1, "application/pdf")),
            ("files", (meeting.name, f2, "text/markdown")),
        ]
        data = {
            "project_name": project_name,
            "files_meta": json.dumps(files_meta),
            "cql": "id=638648330",
        }
        r = requests.post(f"{API}/ingest", files=files, data=data, timeout=180)
    if r.status_code != 200:
        fail("ingest failed", r)
    body = r.json()
    session_id = body.get("session_id")
    vector_store_id = body.get("vector_store_id") or body.get("vsid")
    context_pack = body.get("context_pack") or {}
    if not vector_store_id:
        fail("no vector_store_id in ingest response")
    return session_id, vector_store_id, context_pack


def run_agents_with_session(session_id: str):
    payload = {"session_id": session_id}
    r = requests.post(f"{API}/agents/run", json=payload, timeout=360)
    if r.status_code != 200:
        fail("agents/run failed", r)
    return r.json()


def qa_grade(plan_json, context_pack):
    r = requests.post(f"{API}/qa/grade", json={"plan_json": plan_json, "context_pack": context_pack}, timeout=180)
    if r.status_code != 200:
        fail("qa/grade failed", r)
    return r.json()


def main():
    # Pre-flight
    try:
        rh = requests.get(f"{API}/health", timeout=10)
        rh.raise_for_status()
    except Exception as e:
        fail(f"health failed: {e}")

    title = "F4982 - NORTHERNMFG ASME"
    if not drawing.exists() or not meeting.exists():
        fail("Input files not found in /inputs folder")

    print(f"Ingesting: {drawing.name}, {meeting.name}")
    session_id, vsid, ctx = ingest(title)
    print(f"session_id={session_id} vector_store_id={vsid}")

    print("Running agents… (this can take 1–3 min)")
    agents_out = run_agents_with_session(session_id)
    plan = agents_out.get("plan_json", {})

    ei = plan.get("engineering_instructions", {}) or {}
    exc = len(ei.get("exceptional_steps", []) or [])
    dfm = len(ei.get("dfm_actions", []) or [])
    qrt = len(ei.get("quality_routing", []) or [])
    qa_embed = agents_out.get("qa", {}) or {}
    print(f"Engineering: exceptional={exc}, dfm={dfm}, quality_routing={qrt}")
    if qa_embed:
        print(f"QA (embed): score={qa_embed.get('score')} blocked={qa_embed.get('blocked')}")

    print("Grading QA…")
    qa = qa_grade(plan, ctx)
    print(f"QA grade: score={qa.get('score')} blocked={qa.get('blocked')} reasons={len(qa.get('reasons', []))}")

    # Save artifacts
    outdir = ROOT / "outputs"
    outdir.mkdir(exist_ok=True)
    (outdir / "agents_run.json").write_text(json.dumps(agents_out, indent=2))
    (outdir / "plan.md").write_text(agents_out.get("plan_markdown", ""), encoding="utf-8")
    print(f"Saved outputs to: {outdir}")


if __name__ == "__main__":
    main()
