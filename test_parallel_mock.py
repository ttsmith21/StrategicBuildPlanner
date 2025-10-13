"""
Mock test to verify parallel execution timing and behavior.

This test simulates OpenAI API calls with time delays to verify:
1. Agents actually run in parallel (not sequentially)
2. ThreadPoolExecutor is working correctly
3. Timing confirms concurrent execution
"""

import asyncio
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)

def simulate_openai_call(agent_name: str, delay: float = 5.0):
    """Simulate an OpenAI API call that takes time."""
    LOGGER.info(f"{agent_name}: Starting (simulated API call)")
    time.sleep(delay)  # Simulate network + processing time
    LOGGER.info(f"{agent_name}: Completed")
    return {"agent": agent_name, "completed": True}

def test_sequential_execution():
    """Test sequential execution - should take 4 * delay seconds."""
    LOGGER.info("=" * 60)
    LOGGER.info("TEST 1: Sequential Execution")
    LOGGER.info("=" * 60)

    delay = 2.0  # 2 seconds per agent
    agents = ["QMA", "PMA", "SCA", "EMA"]

    start_time = time.time()
    results = []

    for agent in agents:
        result = simulate_openai_call(agent, delay)
        results.append(result)

    elapsed = time.time() - start_time
    expected = delay * len(agents)

    LOGGER.info(f"Sequential: {elapsed:.2f}s (expected ~{expected:.1f}s)")
    assert elapsed >= expected * 0.95, f"Too fast! Expected ~{expected}s, got {elapsed:.2f}s"

    return elapsed

def test_parallel_execution():
    """Test parallel execution - should take ~delay seconds (not 4 * delay)."""
    LOGGER.info("=" * 60)
    LOGGER.info("TEST 2: Parallel Execution (ThreadPoolExecutor)")
    LOGGER.info("=" * 60)

    delay = 2.0  # 2 seconds per agent
    agents = ["QMA", "PMA", "SCA", "EMA"]

    start_time = time.time()

    # Use ThreadPoolExecutor like our implementation
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(simulate_openai_call, agent, delay) for agent in agents]
        results = [future.result() for future in futures]

    elapsed = time.time() - start_time
    max_allowed = delay * 1.5  # Should be ~delay, allow 50% margin

    LOGGER.info(f"Parallel: {elapsed:.2f}s (expected ~{delay:.1f}s)")
    assert elapsed < max_allowed, f"Too slow! Expected ~{delay}s, got {elapsed:.2f}s"
    assert len(results) == 4, "Should have 4 results"

    return elapsed

def test_parallel_with_asyncio():
    """Test parallel execution using asyncio (like our implementation)."""
    LOGGER.info("=" * 60)
    LOGGER.info("TEST 3: Parallel Execution (asyncio + ThreadPoolExecutor)")
    LOGGER.info("=" * 60)

    delay = 2.0
    agents = ["QMA", "PMA", "SCA", "EMA"]

    async def run_agents_parallel():
        loop = asyncio.get_event_loop()

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                loop.run_in_executor(executor, simulate_openai_call, agent, delay)
                for agent in agents
            ]
            results = await asyncio.gather(*futures)

        return results

    start_time = time.time()
    results = asyncio.run(run_agents_parallel())
    elapsed = time.time() - start_time

    max_allowed = delay * 1.5

    LOGGER.info(f"Async+Parallel: {elapsed:.2f}s (expected ~{delay:.1f}s)")
    assert elapsed < max_allowed, f"Too slow! Expected ~{delay}s, got {elapsed:.2f}s"
    assert len(results) == 4, "Should have 4 results"

    return elapsed

def test_actual_coordinator_integration():
    """Test the actual coordinator with mocked agent functions."""
    LOGGER.info("=" * 60)
    LOGGER.info("TEST 4: Real Coordinator Integration (Mocked Agents)")
    LOGGER.info("=" * 60)

    # Import after setting up environment
    from server.lib.schema import ContextPack, AgentPatch
    from server.agents.coordinator import _run_specialists_parallel

    # Create minimal test data
    plan = {"project": "Test", "customer": "Test", "revision": "A"}
    context_pack = ContextPack(sources=[], facts=[], project={})
    vector_store_id = "test_vs_id"

    delay = 1.0  # 1 second per agent

    def mock_agent(plan, context_pack, vector_store_id):
        """Mock agent that simulates work."""
        agent_name = "TEST"
        LOGGER.info(f"{agent_name}: Starting")
        time.sleep(delay)
        LOGGER.info(f"{agent_name}: Completed")
        return AgentPatch(patch={}, tasks=[], conflicts=[])

    # Patch all agent functions
    with patch('server.agents.coordinator.run_qma', side_effect=mock_agent), \
         patch('server.agents.coordinator.run_pma', side_effect=mock_agent), \
         patch('server.agents.coordinator.run_sca', side_effect=mock_agent), \
         patch('server.agents.coordinator.run_ema', side_effect=mock_agent):

        start_time = time.time()

        # Run the actual parallel function
        patches, conflicts = asyncio.run(
            _run_specialists_parallel(plan, context_pack, vector_store_id)
        )

        elapsed = time.time() - start_time

    max_allowed = delay * 1.5  # Should be ~delay, not 4*delay

    LOGGER.info(f"Coordinator: {elapsed:.2f}s (expected ~{delay:.1f}s)")
    LOGGER.info(f"Patches returned: {len(patches)}")

    assert elapsed < max_allowed, f"Too slow! Expected ~{delay}s, got {elapsed:.2f}s"
    assert len(patches) == 4, f"Expected 4 patches, got {len(patches)}"

    return elapsed

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PARALLEL EXECUTION TIMING TESTS")
    print("=" * 60 + "\n")

    try:
        # Test 1: Sequential (baseline)
        seq_time = test_sequential_execution()
        print()

        # Test 2: Parallel with ThreadPoolExecutor
        par_time = test_parallel_execution()
        print()

        # Test 3: Parallel with asyncio
        async_time = test_parallel_with_asyncio()
        print()

        # Test 4: Real coordinator integration
        coord_time = test_actual_coordinator_integration()
        print()

        # Calculate speedups
        print("=" * 60)
        print("RESULTS SUMMARY")
        print("=" * 60)
        print(f"Sequential execution:     {seq_time:.2f}s")
        print(f"Parallel (ThreadPool):    {par_time:.2f}s ({seq_time/par_time:.1f}x speedup)")
        print(f"Parallel (asyncio):       {async_time:.2f}s ({seq_time/async_time:.1f}x speedup)")
        print(f"Coordinator (real code):  {coord_time:.2f}s ({seq_time/coord_time:.1f}x speedup)")
        print("=" * 60)

        # Verify we got significant speedup
        min_speedup = 3.0
        coord_speedup = seq_time / coord_time

        if coord_speedup >= min_speedup:
            print(f"✅ SUCCESS! Achieved {coord_speedup:.1f}x speedup (target: {min_speedup}x)")
            print("✅ Parallel execution is working correctly!")
        else:
            print(f"❌ FAILED! Only {coord_speedup:.1f}x speedup (target: {min_speedup}x)")
            print("❌ Parallel execution may not be working correctly")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
