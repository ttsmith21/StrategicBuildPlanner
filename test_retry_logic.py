"""
Test retry logic with simulated failures.

Verifies that transient errors are retried with exponential backoff.
"""

import time
import logging
from server.lib.retry import retry_with_backoff, RetryExhausted, should_retry_openai_error

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)


class SimulatedOpenAIError(Exception):
    """Simulate an OpenAI API error"""
    pass


def test_retry_success_after_failures():
    """Test that function succeeds after retries"""
    print("\n" + "=" * 60)
    print("TEST 1: Success after 2 failures")
    print("=" * 60)

    attempt_count = {"count": 0}

    @retry_with_backoff(max_attempts=3, initial_delay=0.5, exceptions=(SimulatedOpenAIError,))
    def flaky_function():
        attempt_count["count"] += 1
        if attempt_count["count"] < 3:
            raise SimulatedOpenAIError(f"Simulated failure #{attempt_count['count']}")
        return "success"

    start = time.time()
    result = flaky_function()
    elapsed = time.time() - start

    assert result == "success", f"Expected 'success', got '{result}'"
    assert attempt_count["count"] == 3, f"Expected 3 attempts, got {attempt_count['count']}"
    print(f"✓ Function succeeded after {attempt_count['count']} attempts in {elapsed:.2f}s")


def test_retry_exhausted():
    """Test that RetryExhausted is raised after max attempts"""
    print("\n" + "=" * 60)
    print("TEST 2: Retry exhausted after max attempts")
    print("=" * 60)

    attempt_count = {"count": 0}

    @retry_with_backoff(max_attempts=3, initial_delay=0.5, exceptions=(SimulatedOpenAIError,))
    def always_failing_function():
        attempt_count["count"] += 1
        raise SimulatedOpenAIError(f"Simulated failure #{attempt_count['count']}")

    try:
        always_failing_function()
        assert False, "Should have raised RetryExhausted"
    except RetryExhausted as e:
        print(f"✓ RetryExhausted raised after {attempt_count['count']} attempts: {e}")
        assert attempt_count["count"] == 3, f"Expected 3 attempts, got {attempt_count['count']}"


def test_exponential_backoff():
    """Test that delays follow exponential backoff"""
    print("\n" + "=" * 60)
    print("TEST 3: Exponential backoff timing")
    print("=" * 60)

    attempt_times = []

    def on_retry_callback(exception, attempt, delay):
        attempt_times.append((attempt, delay, time.time()))

    attempt_count = {"count": 0}

    @retry_with_backoff(
        max_attempts=4,
        initial_delay=0.5,
        exponential_base=2.0,
        exceptions=(SimulatedOpenAIError,),
        on_retry=on_retry_callback
    )
    def failing_function():
        attempt_count["count"] += 1
        raise SimulatedOpenAIError(f"Failure #{attempt_count['count']}")

    try:
        failing_function()
    except RetryExhausted:
        pass

    # Verify exponential backoff delays
    print(f"✓ Attempt times recorded: {len(attempt_times)}")
    for i, (attempt, delay, timestamp) in enumerate(attempt_times):
        expected_delay = 0.5 * (2.0 ** i)
        print(f"  Attempt {attempt}: delay={delay:.2f}s (expected ~{expected_delay:.2f}s)")
        assert abs(delay - expected_delay) < 0.01, f"Delay mismatch at attempt {attempt}"

    print("✓ Exponential backoff verified")


def test_should_retry_openai_error():
    """Test OpenAI error classification"""
    print("\n" + "=" * 60)
    print("TEST 4: OpenAI error classification")
    print("=" * 60)

    # Should retry
    retryable_errors = [
        Exception("Rate limit exceeded (429)"),
        Exception("Server error 500"),
        Exception("Server error 502"),
        Exception("Server error 503"),
        Exception("Connection timeout"),
        Exception("Network error"),
    ]

    for error in retryable_errors:
        assert should_retry_openai_error(error), f"Should retry: {error}"
        print(f"✓ Retryable: {error}")

    # Should not retry
    non_retryable_errors = [
        Exception("Invalid request 400"),
        Exception("Unauthorized 401"),
        Exception("Forbidden 403"),
        Exception("Not found 404"),
    ]

    for error in non_retryable_errors:
        assert not should_retry_openai_error(error), f"Should not retry: {error}"
        print(f"✓ Non-retryable: {error}")

    print("✓ Error classification correct")


def test_retry_callback():
    """Test that retry callback is called"""
    print("\n" + "=" * 60)
    print("TEST 5: Retry callback invocation")
    print("=" * 60)

    callback_calls = []

    def on_retry_callback(exception, attempt, delay):
        callback_calls.append((str(exception), attempt, delay))

    attempt_count = {"count": 0}

    @retry_with_backoff(
        max_attempts=3,
        initial_delay=0.5,
        exceptions=(SimulatedOpenAIError,),
        on_retry=on_retry_callback
    )
    def failing_function():
        attempt_count["count"] += 1
        raise SimulatedOpenAIError(f"Failure #{attempt_count['count']}")

    try:
        failing_function()
    except RetryExhausted:
        pass

    # Callback should be called for attempts 1 and 2 (not 3 because that's the last)
    assert len(callback_calls) == 2, f"Expected 2 callback calls, got {len(callback_calls)}"
    print(f"✓ Callback called {len(callback_calls)} times")

    for i, (error, attempt, delay) in enumerate(callback_calls):
        print(f"  Call {i+1}: attempt={attempt}, delay={delay:.2f}s, error={error}")

    print("✓ Callback invocation verified")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTING RETRY LOGIC WITH EXPONENTIAL BACKOFF")
    print("=" * 60)

    try:
        test_retry_success_after_failures()
        test_retry_exhausted()
        test_exponential_backoff()
        test_should_retry_openai_error()
        test_retry_callback()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
