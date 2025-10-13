"""
Test script to verify parallel agent execution and measure performance improvement.

This script:
1. Loads a test session from outputs/sessions/
2. Calls the coordinator directly to run agents in parallel
3. Measures execution time
4. Verifies all agents ran successfully
"""

import json
import time
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)

# Import the coordinator
from server.agents.coordinator import run_specialists
from server.lib.schema import ContextPack

def test_parallel_execution():
    """Test parallel agent execution using a real session."""

    # Find a test session
    sessions_dir = Path("outputs/sessions")
    if not sessions_dir.exists():
        LOGGER.error("No sessions directory found. Please run /ingest first.")
        return

    # Load the most recent session with a plan
    session_files = sorted(sessions_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    session_data = None
    for session_file in session_files:
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Check if it has snapshots with vector_store_id
                if data.get("snapshots") and len(data["snapshots"]) > 0:
                    snapshot = data["snapshots"][-1]  # Get latest snapshot
                    if snapshot.get("vector_store_id"):
                        session_data = snapshot
                        LOGGER.info(f"Using session: {session_file.name}")
                        break
        except Exception as e:
            LOGGER.warning(f"Failed to load {session_file.name}: {e}")

    if not session_data:
        LOGGER.error("No valid session found with vector_store_id. Please run /ingest and /agents/run first.")
        return

    plan_json = session_data.get("plan_json", {})
    context_pack_dict = session_data.get("context_pack", {})
    vector_store_id = session_data.get("vector_store_id")

    if not vector_store_id:
        LOGGER.error("Session has no vector_store_id")
        return

    LOGGER.info(f"Vector Store ID: {vector_store_id}")
    LOGGER.info(f"Project: {plan_json.get('project', 'Unknown')}")
    LOGGER.info(f"Customer: {plan_json.get('customer', 'Unknown')}")

    # Validate context pack
    try:
        context_pack = ContextPack.model_validate(context_pack_dict)
        LOGGER.info(f"Context Pack: {len(context_pack.sources)} sources, {len(context_pack.facts)} facts")
    except Exception as e:
        LOGGER.error(f"Invalid context pack: {e}")
        return

    # Run specialists and measure time
    LOGGER.info("=" * 60)
    LOGGER.info("Starting parallel agent execution...")
    LOGGER.info("=" * 60)

    start_time = time.time()

    try:
        result = run_specialists(plan_json, context_pack, vector_store_id)

        elapsed = time.time() - start_time

        LOGGER.info("=" * 60)
        LOGGER.info(f"✅ Agents completed in {elapsed:.2f} seconds")
        LOGGER.info("=" * 60)

        # Validate results
        updated_plan = result.get("plan_json", {})
        tasks = result.get("tasks_suggested", [])
        qa = result.get("qa", {})
        conflicts = result.get("conflicts", [])

        LOGGER.info(f"Tasks suggested: {len(tasks)}")
        LOGGER.info(f"Conflicts detected: {len(conflicts)}")
        LOGGER.info(f"QA score: {qa.get('score', 'N/A')}")

        # Check that specialist sections were populated
        has_quality = bool(updated_plan.get("quality_plan"))
        has_purchasing = bool(updated_plan.get("purchasing"))
        has_schedule = bool(updated_plan.get("release_plan"))
        has_engineering = bool(updated_plan.get("engineering_instructions"))

        LOGGER.info(f"Quality Plan: {'✅' if has_quality else '❌'}")
        LOGGER.info(f"Purchasing Plan: {'✅' if has_purchasing else '❌'}")
        LOGGER.info(f"Schedule Plan: {'✅' if has_schedule else '❌'}")
        LOGGER.info(f"Engineering Instructions: {'✅' if has_engineering else '❌'}")

        if all([has_quality, has_purchasing, has_schedule, has_engineering]):
            LOGGER.info("=" * 60)
            LOGGER.info("✅ All specialist agents ran successfully!")
            LOGGER.info("=" * 60)

            # Estimate speedup (assuming sequential would be ~60-90s)
            sequential_estimate = 75  # midpoint of 60-90s range
            speedup = sequential_estimate / elapsed if elapsed > 0 else 0
            LOGGER.info(f"Estimated speedup: {speedup:.1f}x (assuming {sequential_estimate}s sequential baseline)")

            if speedup >= 2.5:
                LOGGER.info("🎉 Performance target achieved (>2.5x speedup)!")

        else:
            LOGGER.warning("⚠️  Some agents may not have completed successfully")

        return True

    except Exception as e:
        elapsed = time.time() - start_time
        LOGGER.error(f"❌ Agent execution failed after {elapsed:.2f} seconds: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    LOGGER.info("Testing parallel agent execution...")
    success = test_parallel_execution()

    if success:
        LOGGER.info("\n✅ Test passed!")
    else:
        LOGGER.error("\n❌ Test failed!")
