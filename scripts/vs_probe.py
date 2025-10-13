import json, os, sys
from pathlib import Path
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "agents_run.json"

def main():
    if not OUT.exists():
        print("agents_run.json not found; run scripts/smoke_real_docs.py first")
        sys.exit(1)
    data = json.loads(OUT.read_text(encoding="utf-8"))
    vsid = data.get("vector_store_id") or data.get("context_pack",{}).get("project",{}).get("vector_store_id")
    sources = [s.get("title") for s in (data.get("context_pack",{}).get("sources") or [])]
    if not vsid:
        print("No vector_store_id in agents_run.json")
        sys.exit(1)

    client = OpenAI()
    prompt = {
        "instruction": "List the filenames in the attached vector store and return one 200-character excerpt from the most substantial file.",
        "format": {"files": ["string"], "excerpt": "string"}
    }
    try:
        resp = client.responses.create(
            model=os.getenv("OPENAI_MODEL_PLAN", "gpt-4o-mini"),
            input=[
                {"role": "system", "content": "You are a helpful assistant. Return strict JSON with keys files and excerpt."},
                {"role": "user", "content": json.dumps(prompt)},
            ],
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_ids": [vsid]}},
            temperature=0.0,
        )
    except Exception as e:
        print(f"OpenAI responses.create failed: {e}")
        sys.exit(1)

    # Try to parse JSON back from response
    payload = None
    try:
        for block in getattr(resp, "output", []) or []:
            for item in getattr(block, "content", []) or []:
                if getattr(item, "type", None) == "text":
                    txt = getattr(item, "text", None)
                    if txt and getattr(txt, "value", None):
                        payload = json.loads(txt.value)
                        break
        if payload is None and getattr(resp, "output_text", None):
            payload = json.loads(resp.output_text)
    except Exception:
        payload = None
    print(json.dumps({
        "vector_store_id": vsid,
        "sources": sources,
        "probe": payload,
    }, indent=2))

if __name__ == "__main__":
    main()
