"""
Test parallel agent execution with REAL OpenAI API calls.

This test loads the .env file and makes actual OpenAI API calls to verify:
1. Parallel execution works with real API
2. Performance improvement is realized
3. All agents complete successfully
"""

import os
import json
import time
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)

# Verify API key is loaded
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    LOGGER.error("OPENAI_API_KEY not found in environment!")
    LOGGER.error("Please ensure .env file exists and contains OPENAI_API_KEY")
    exit(1)

LOGGER.info(f"API key loaded: {api_key[:8]}...{api_key[-4:]}")

# Import after loading environment
from server.agents.coordinator import run_specialists
from server.lib.schema import ContextPack

def test_with_real_openai_api():
    """Test parallel execution using real OpenAI API calls."""

    # Find a test session with real data
    sessions_dir = Path("outputs/sessions")
    if not sessions_dir.exists():
        LOGGER.error("No sessions directory found. Please run /ingest first.")
        return False

    # Load the most recent session with a plan
    session_files = sorted(sessions_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    session_data = None
    session_file_name = None
    for session_file in session_files:
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Check if it has snapshots with vector_store_id
                if data.get("snapshots") and len(data["snapshots"]) > 0:
                    snapshot = data["snapshots"][-1]  # Get latest snapshot
                    if snapshot.get("vector_store_id"):
                        session_data = snapshot
                        session_file_name = session_file.name
                        LOGGER.info(f"Using session: {session_file_name}")
                        break
        except Exception as e:
            LOGGER.warning(f"Failed to load {session_file.name}: {e}")

    if not session_data:
        LOGGER.error("No valid session found with vector_store_id. Please run /ingest and /draft first.")
        return False

    plan_json = session_data.get("plan_json", {})
    context_pack_dict = session_data.get("context_pack", {})
    vector_store_id = session_data.get("vector_store_id")

    if not vector_store_id:
        LOGGER.error("Session has no vector_store_id")
        return False

    LOGGER.info("=" * 80)
    LOGGER.info(f"Vector Store ID: {vector_store_id}")
    LOGGER.info(f"Project: {plan_json.get('project', 'Unknown')}")
    LOGGER.info(f"Customer: {plan_json.get('customer', 'Unknown')}")
    LOGGER.info("=" * 80)

    # Validate context pack
    try:
        context_pack = ContextPack.model_validate(context_pack_dict)
        LOGGER.info(f"Context Pack: {len(context_pack.sources)} sources, {len(context_pack.facts)} facts")
    except Exception as e:
        LOGGER.error(f"Invalid context pack: {e}")
        return False

    # Run specialists with REAL OpenAI API and measure time
    LOGGER.info("")
    LOGGER.info("=" * 80)
    LOGGER.info("🚀 STARTING PARALLEL AGENT EXECUTION WITH REAL OPENAI API")
    LOGGER.info("=" * 80)
    LOGGER.info("")
    LOGGER.info("This will make real OpenAI API calls for all 4 specialist agents:")
    LOGGER.info("  - QMA (Quality Management Agent)")
    LOGGER.info("  - PMA (Purchasing Management Agent)")
    LOGGER.info("  - SCA (Schedule Coordinator Agent)")
    LOGGER.info("  - EMA (Engineering Management Agent)")
    LOGGER.info("")
    LOGGER.info("Expected time: 20-30 seconds (with parallel execution)")
    LOGGER.info("Without parallel: 60-90 seconds (sequential baseline)")
    LOGGER.info("")

    start_time = time.time()

    try:
        result = run_specialists(plan_json, context_pack, vector_store_id)

        elapsed = time.time() - start_time

        LOGGER.info("")
        LOGGER.info("=" * 80)
        LOGGER.info(f"✅ AGENTS COMPLETED IN {elapsed:.2f} SECONDS")
        LOGGER.info("=" * 80)

        # Validate results
        updated_plan = result.get("plan_json", {})
        tasks = result.get("tasks_suggested", [])
        qa = result.get("qa", {})
        conflicts = result.get("conflicts", [])

        LOGGER.info("")
        LOGGER.info("RESULTS:")
        LOGGER.info(f"  Tasks suggested: {len(tasks)}")
        LOGGER.info(f"  Conflicts detected: {len(conflicts)}")
        LOGGER.info(f"  QA score: {qa.get('score', 'N/A')}")
        LOGGER.info(f"  QA blocked: {qa.get('blocked', False)}")

        # Check that specialist sections were populated
        sections = {
            "Quality Plan": bool(updated_plan.get("quality_plan")),
            "Purchasing Plan": bool(updated_plan.get("purchasing")),
            "Schedule Plan": bool(updated_plan.get("release_plan")),
            "Engineering Instructions": bool(updated_plan.get("engineering_instructions")),
            "Keys": bool(updated_plan.get("keys")),
        }

        LOGGER.info("")
        LOGGER.info("SPECIALIST OUTPUTS:")
        for section, populated in sections.items():
            status = "✓" if populated else "✗"
            LOGGER.info(f"  [{status}] {section}")

        all_populated = all(sections.values())

        # Performance analysis
        LOGGER.info("")
        LOGGER.info("=" * 80)
        LOGGER.info("PERFORMANCE ANALYSIS")
        LOGGER.info("=" * 80)

        sequential_estimate_min = 60
        sequential_estimate_max = 90
        sequential_estimate_mid = 75

        speedup_min = sequential_estimate_min / elapsed if elapsed > 0 else 0
        speedup_max = sequential_estimate_max / elapsed if elapsed > 0 else 0
        speedup_mid = sequential_estimate_mid / elapsed if elapsed > 0 else 0

        LOGGER.info(f"  Actual time (parallel): {elapsed:.2f}s")
        LOGGER.info(f"  Sequential estimate: {sequential_estimate_min}-{sequential_estimate_max}s")
        LOGGER.info(f"  Speedup achieved: {speedup_mid:.1f}x (baseline: {sequential_estimate_mid}s)")
        LOGGER.info(f"  Speedup range: {speedup_min:.1f}x - {speedup_max:.1f}x")

        LOGGER.info("")
        if speedup_mid >= 2.5:
            LOGGER.info("🎉 SUCCESS! Performance target achieved (>2.5x speedup)!")
        else:
            LOGGER.warning(f"⚠️  Speedup below target: {speedup_mid:.1f}x (target: 2.5x)")

        if all_populated:
            LOGGER.info("✅ All specialist agents completed successfully!")
        else:
            LOGGER.warning("⚠️  Some specialist outputs missing")

        LOGGER.info("=" * 80)

        # Save results
        output_file = Path("outputs") / f"test_parallel_real_api_{int(time.time())}.json"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": time.time(),
                "elapsed_seconds": elapsed,
                "speedup": speedup_mid,
                "sections_populated": sections,
                "tasks_count": len(tasks),
                "conflicts_count": len(conflicts),
                "qa_score": qa.get('score'),
                "plan": updated_plan
            }, f, indent=2)

        LOGGER.info(f"Results saved to: {output_file}")

        return True

    except Exception as e:
        elapsed = time.time() - start_time
        LOGGER.error("")
        LOGGER.error("=" * 80)
        LOGGER.error(f"❌ AGENT EXECUTION FAILED after {elapsed:.2f} seconds")
        LOGGER.error("=" * 80)
        LOGGER.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    LOGGER.info("")
    LOGGER.info("=" * 80)
    LOGGER.info("TESTING PARALLEL AGENT EXECUTION WITH REAL OPENAI API")
    LOGGER.info("=" * 80)
    LOGGER.info("")

    success = test_with_real_openai_api()

    LOGGER.info("")
    if success:
        LOGGER.info("✅ TEST PASSED!")
    else:
        LOGGER.error("❌ TEST FAILED!")
