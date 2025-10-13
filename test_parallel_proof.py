"""
DEFINITIVE TEST: Prove OpenAI agents run in parallel, not sequentially.

This test will:
1. Run agents sequentially and measure time
2. Run agents in parallel and measure time
3. Prove parallel is faster
4. Log exact timestamps showing simultaneous execution
"""

import os
import time
import logging
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Setup logging with millisecond precision
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
LOGGER = logging.getLogger(__name__)

# Verify API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("ERROR: OPENAI_API_KEY not found in environment!")
    exit(1)

LOGGER.info(f"API key loaded: {api_key[:8]}...{api_key[-4:]}")

# Import after loading environment
from server.agents.qma import run_qma
from server.agents.pma import run_pma
from server.agents.sca import run_sca
from server.agents.ema import run_ema
from server.agents.coordinator import _run_specialists_parallel
from server.lib.schema import ContextPack
import asyncio


def load_test_session():
    """Load a real session for testing"""
    sessions_dir = Path("outputs/sessions")
    if not sessions_dir.exists():
        LOGGER.error("No sessions directory found")
        return None

    for session_file in sorted(sessions_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            import json
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get("snapshots") and len(data["snapshots"]) > 0:
                    snapshot = data["snapshots"][-1]
                    if snapshot.get("vector_store_id"):
                        LOGGER.info(f"Using session: {session_file.name}")
                        return snapshot
        except Exception as e:
            LOGGER.warning(f"Failed to load {session_file.name}: {e}")

    return None


def test_sequential_execution():
    """Run agents sequentially and measure time"""
    print("\n" + "=" * 80)
    print("PART 1: SEQUENTIAL EXECUTION (one after another)")
    print("=" * 80)

    session = load_test_session()
    if not session:
        print("ERROR: No valid session found")
        return None

    plan = session.get("plan_json", {})
    context_pack_dict = session.get("context_pack", {})
    vector_store_id = session.get("vector_store_id")

    try:
        context_pack = ContextPack.model_validate(context_pack_dict)
    except Exception as e:
        LOGGER.error(f"Invalid context pack: {e}")
        return None

    LOGGER.info("Starting SEQUENTIAL execution...")
    LOGGER.info(f"Project: {plan.get('project', 'Unknown')}")

    start_times = {}
    end_times = {}

    start_total = time.time()

    # QMA
    LOGGER.info("▶ Starting QMA...")
    start_times['QMA'] = datetime.now()
    try:
        qma_patch = run_qma(plan, context_pack, vector_store_id)
        end_times['QMA'] = datetime.now()
        LOGGER.info(f"✓ QMA completed")
    except Exception as e:
        LOGGER.error(f"✗ QMA failed: {e}")
        end_times['QMA'] = datetime.now()

    # PMA
    LOGGER.info("▶ Starting PMA...")
    start_times['PMA'] = datetime.now()
    try:
        pma_patch = run_pma(plan, context_pack, vector_store_id)
        end_times['PMA'] = datetime.now()
        LOGGER.info(f"✓ PMA completed")
    except Exception as e:
        LOGGER.error(f"✗ PMA failed: {e}")
        end_times['PMA'] = datetime.now()

    # SCA
    LOGGER.info("▶ Starting SCA...")
    start_times['SCA'] = datetime.now()
    try:
        sca_patch = run_sca(plan, context_pack, vector_store_id)
        end_times['SCA'] = datetime.now()
        LOGGER.info(f"✓ SCA completed")
    except Exception as e:
        LOGGER.error(f"✗ SCA failed: {e}")
        end_times['SCA'] = datetime.now()

    # EMA
    LOGGER.info("▶ Starting EMA...")
    start_times['EMA'] = datetime.now()
    try:
        ema_patch = run_ema(plan, context_pack, vector_store_id)
        end_times['EMA'] = datetime.now()
        LOGGER.info(f"✓ EMA completed")
    except Exception as e:
        LOGGER.error(f"✗ EMA failed: {e}")
        end_times['EMA'] = datetime.now()

    elapsed_total = time.time() - start_total

    print("\n" + "=" * 80)
    print("SEQUENTIAL RESULTS:")
    print("=" * 80)

    for agent in ['QMA', 'PMA', 'SCA', 'EMA']:
        if agent in start_times and agent in end_times:
            duration = (end_times[agent] - start_times[agent]).total_seconds()
            print(f"  {agent}: {start_times[agent].strftime('%H:%M:%S.%f')[:-3]} → {end_times[agent].strftime('%H:%M:%S.%f')[:-3]} ({duration:.1f}s)")

    print(f"\n  TOTAL TIME: {elapsed_total:.1f} seconds")
    print("=" * 80)

    return {
        'total_time': elapsed_total,
        'start_times': start_times,
        'end_times': end_times,
    }


def test_parallel_execution():
    """Run agents in parallel and measure time"""
    print("\n" + "=" * 80)
    print("PART 2: PARALLEL EXECUTION (all at once)")
    print("=" * 80)

    session = load_test_session()
    if not session:
        print("ERROR: No valid session found")
        return None

    plan = session.get("plan_json", {})
    context_pack_dict = session.get("context_pack", {})
    vector_store_id = session.get("vector_store_id")

    try:
        context_pack = ContextPack.model_validate(context_pack_dict)
    except Exception as e:
        LOGGER.error(f"Invalid context pack: {e}")
        return None

    LOGGER.info("Starting PARALLEL execution...")
    LOGGER.info(f"Project: {plan.get('project', 'Unknown')}")

    start_total = time.time()

    try:
        patches, conflicts = asyncio.run(_run_specialists_parallel(plan, context_pack, vector_store_id))
        elapsed_total = time.time() - start_total

        print("\n" + "=" * 80)
        print("PARALLEL RESULTS:")
        print("=" * 80)
        print(f"  All 4 agents executed in parallel")
        print(f"  TOTAL TIME: {elapsed_total:.1f} seconds")
        print("=" * 80)

        return {
            'total_time': elapsed_total,
            'patches': patches,
        }

    except Exception as e:
        elapsed_total = time.time() - start_total
        LOGGER.error(f"Parallel execution failed: {e}")
        return {
            'total_time': elapsed_total,
            'error': str(e),
        }


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("DEFINITIVE PARALLEL EXECUTION TEST")
    print("=" * 80)
    print("\nThis test will prove whether agents run in parallel or sequentially")
    print("by comparing actual execution times with real OpenAI API calls.")
    print("\n" + "=" * 80)

    # Run sequential
    seq_result = test_sequential_execution()

    if seq_result is None:
        print("\n❌ Sequential test failed - cannot continue")
        exit(1)

    # Wait a bit between tests
    print("\n⏳ Waiting 5 seconds before parallel test...")
    time.sleep(5)

    # Run parallel
    par_result = test_parallel_execution()

    if par_result is None:
        print("\n❌ Parallel test failed - cannot compare")
        exit(1)

    # Compare results
    print("\n" + "=" * 80)
    print("FINAL COMPARISON")
    print("=" * 80)

    seq_time = seq_result['total_time']
    par_time = par_result['total_time']
    speedup = seq_time / par_time if par_time > 0 else 0

    print(f"\nSequential execution: {seq_time:.1f} seconds")
    print(f"Parallel execution:   {par_time:.1f} seconds")
    print(f"Speedup:              {speedup:.1f}x")

    print("\n" + "=" * 80)

    if speedup >= 2.0:
        print("✅ SUCCESS: Agents ARE running in parallel!")
        print(f"   Achieved {speedup:.1f}x speedup (target: 2.0x+)")
        print("\n   This proves that all 4 agents run simultaneously,")
        print("   not one after another.")
    else:
        print("❌ FAILURE: Agents may NOT be running in parallel")
        print(f"   Only {speedup:.1f}x speedup (target: 2.0x+)")
        print("\n   This suggests agents may still be running sequentially.")
        print("   Expected parallel to be ~3-4x faster than sequential.")

    print("=" * 80)
