"""
Retry logic with exponential backoff for OpenAI API calls.

Handles transient failures gracefully with configurable retry policies.
"""

import time
import logging
from typing import TypeVar, Callable, Optional, Type, Tuple
from functools import wraps

LOGGER = logging.getLogger(__name__)

T = TypeVar('T')


class RetryExhausted(Exception):
    """Raised when all retry attempts have been exhausted"""
    pass


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int, float], None]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to retry a function with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        exceptions: Tuple of exception types to catch (default: all exceptions)
        on_retry: Optional callback(exception, attempt, delay) called before each retry

    Returns:
        Decorated function that retries on failure

    Example:
        @retry_with_backoff(max_attempts=3, initial_delay=1.0)
        def call_openai_api():
            return client.chat.completions.create(...)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            attempt = 1
            delay = initial_delay

            while attempt <= max_attempts:
                try:
                    result = func(*args, **kwargs)

                    # Log success if this wasn't the first attempt
                    if attempt > 1:
                        LOGGER.info(
                            f"{func.__name__} succeeded on attempt {attempt}/{max_attempts}"
                        )

                    return result

                except exceptions as e:
                    if attempt >= max_attempts:
                        LOGGER.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise RetryExhausted(
                            f"Failed after {max_attempts} attempts: {e}"
                        ) from e

                    # Calculate next delay with exponential backoff
                    current_delay = min(delay, max_delay)

                    LOGGER.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )

                    # Call optional callback
                    if on_retry:
                        try:
                            on_retry(e, attempt, current_delay)
                        except Exception as callback_error:
                            LOGGER.error(f"Retry callback failed: {callback_error}")

                    # Sleep before retry
                    time.sleep(current_delay)

                    # Update for next iteration
                    attempt += 1
                    delay *= exponential_base

            # Should never reach here, but just in case
            raise RetryExhausted(f"Exhausted {max_attempts} attempts")

        return wrapper

    return decorator


def should_retry_openai_error(exception: Exception) -> bool:
    """
    Determine if an OpenAI error should be retried.

    Transient errors (rate limits, timeouts, server errors) should be retried.
    Client errors (invalid requests, authentication) should not.
    """
    error_str = str(exception).lower()

    # Retry on rate limit errors
    if 'rate limit' in error_str or '429' in error_str:
        return True

    # Retry on server errors (5xx)
    if '500' in error_str or '502' in error_str or '503' in error_str or '504' in error_str:
        return True

    # Retry on timeout errors
    if 'timeout' in error_str or 'timed out' in error_str:
        return True

    # Retry on connection errors
    if 'connection' in error_str or 'network' in error_str:
        return True

    # Don't retry on client errors (4xx except 429)
    if '400' in error_str or '401' in error_str or '403' in error_str or '404' in error_str:
        return False

    # Default: retry for unknown errors (conservative approach)
    return True


def create_openai_retry_decorator(max_attempts: int = 3, initial_delay: float = 2.0):
    """
    Create a retry decorator specifically for OpenAI API calls.

    Args:
        max_attempts: Maximum retry attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 2.0)

    Returns:
        Retry decorator configured for OpenAI API calls

    Example:
        retry_openai = create_openai_retry_decorator(max_attempts=3)

        @retry_openai
        def run_agent():
            return client.beta.threads.runs.create_and_poll(...)
    """

    def on_retry_callback(exception: Exception, attempt: int, delay: float):
        """Log OpenAI-specific retry information"""
        should_retry = should_retry_openai_error(exception)
        if not should_retry:
            LOGGER.warning(
                f"OpenAI error appears non-retryable but retrying anyway: {exception}"
            )

    return retry_with_backoff(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        max_delay=30.0,  # Cap at 30 seconds for OpenAI
        exponential_base=2.0,
        exceptions=(Exception,),  # Catch all exceptions, filter in callback
        on_retry=on_retry_callback,
    )
