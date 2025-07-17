"""Rate limiting utilities for API calls."""

import logging
import threading
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, Optional

logger = logging.getLogger("rate_limiter")


class RateLimiter:
    """
    Rate limiter for API calls with retry and backoff logic.

    This class provides rate limiting functionality with configurable limits,
    automatic retry logic, and exponential backoff for failed requests.
    """

    def __init__(
        self,
        requests_per_minute: int = 15,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
    ):
        """
        Initialize the RateLimiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute
            max_retries: Maximum number of retry attempts for failed requests
            base_delay: Base delay between requests in seconds
            max_delay: Maximum delay for exponential backoff
            jitter: Whether to add random jitter to delays
        """
        self.requests_per_minute = requests_per_minute
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter

        # Thread safety
        self._lock = threading.Lock()
        self._request_times: Deque[float] = deque()
        self._last_request_time: float = 0.0

        # Calculate minimum delay between requests
        self.min_delay = max(base_delay, 60.0 / requests_per_minute)

        logger.info(
            f"Rate limiter initialized: {requests_per_minute} RPM, "
            f"min delay: {self.min_delay:.2f}s"
        )

    def wait_if_needed(self) -> None:
        """Wait if necessary to stay within rate limits."""
        with self._lock:
            current_time = time.time()

            # Remove requests older than 1 minute
            while self._request_times and current_time - self._request_times[0] > 60:
                self._request_times.popleft()

            # If we've hit the rate limit, wait
            if len(self._request_times) >= self.requests_per_minute:
                wait_time = 60 - (current_time - self._request_times[0]) + 1
                logger.warning(
                    f"Rate limit reached ({self.requests_per_minute} RPM). "
                    f"Waiting {wait_time:.2f} seconds..."
                )
                time.sleep(wait_time)
                current_time = time.time()

            # Ensure minimum delay between requests
            time_since_last = current_time - self._last_request_time
            if time_since_last < self.min_delay:
                delay = self.min_delay - time_since_last
                if self.jitter:
                    # Add small random jitter to prevent thundering herd
                    import secrets

                    delay += secrets.SystemRandom().uniform(0, 0.1)

                logger.debug(
                    f"Rate limiting: waiting {delay:.2f} seconds before API call"
                )
                time.sleep(delay)

            # Record this request
            self._request_times.append(current_time)
            self._last_request_time = float(current_time)

    def call_with_retry(
        self,
        func: Callable[..., Any],
        *args,
        error_handler: Optional[Callable[..., Any]] = None,
        **kwargs,
    ) -> Any:
        """
        Call a function with retry logic for rate limiting.

        Args:
            func: Function to call
            *args: Arguments to pass to the function
            error_handler: Optional function to handle specific errors
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Result of the function call

        Raises:
            Exception: If the function fails after max retries
        """
        for attempt in range(self.max_retries + 1):
            try:
                # Wait for rate limit
                self.wait_if_needed()

                # Make the API call
                result = func(*args, **kwargs)
                logger.debug(f"API call successful (attempt {attempt + 1})")
                return result

            except Exception as e:
                error_msg = str(e)
                logger.error(f"API call failed (attempt {attempt + 1}): {error_msg}")

                # Check if this is a rate limit error
                if self._is_rate_limit_error(error_msg):
                    if attempt < self.max_retries:
                        retry_delay = self._calculate_retry_delay(error_msg, attempt)
                        logger.warning(
                            f"Rate limit detected. Waiting {retry_delay:.2f} "
                            f"seconds before retry {attempt + 1}..."
                        )
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error("Max retries reached for rate limit. Giving up.")
                        raise ValueError(
                            f"Rate limit exceeded after {self.max_retries} retries: {error_msg}"
                        )

                # Handle other errors with custom handler if provided
                if error_handler:
                    try:
                        return error_handler(e, attempt)
                    except Exception as handler_error:
                        logger.error(f"Error handler failed: {handler_error}")

                # For non-rate-limit errors, don't retry unless it's the last attempt
                if attempt == self.max_retries:
                    raise

                # For other errors, retry with exponential backoff
                retry_delay = self._calculate_backoff_delay(attempt)
                logger.warning(f"Retrying in {retry_delay:.2f} seconds...")
                time.sleep(retry_delay)

        # This should never be reached
        raise ValueError("Unexpected error in rate-limited API call")

    def _is_rate_limit_error(self, error_msg: str) -> bool:
        """
        Check if an error is a rate limit error.

        Args:
            error_msg: Error message to check

        Returns:
            True if this is a rate limit error
        """
        rate_limit_keywords = [
            "rate",
            "limit",
            "429",
            "quota",
            "resource_exhausted",
            "too many requests",
            "throttled",
            "exhausted",
        ]
        return any(keyword in error_msg.lower() for keyword in rate_limit_keywords)

    def _calculate_retry_delay(self, error_msg: str, attempt: int) -> float:
        """
        Calculate the retry delay for rate limiting.

        Args:
            error_msg: Error message from API
            attempt: Current attempt number

        Returns:
            Delay in seconds
        """
        import re

        # Try to extract retry delay from error message
        retry_match = re.search(
            r'retryDelay["\']?\s*:\s*["\']?(\d+)s?["\']?', error_msg
        )
        if retry_match:
            return float(retry_match.group(1))

        # Use exponential backoff with jitter
        delay = min(self.base_delay * (2**attempt), self.max_delay)
        if self.jitter:
            import secrets

            delay += secrets.SystemRandom().uniform(0, delay * 0.1)

        return float(delay)

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """
        Calculate the backoff delay for rate limiting.

        Args:
            attempt: Current attempt number

        Returns:
            Delay in seconds
        """
        delay = min(self.base_delay * (2**attempt), self.max_delay)
        if self.jitter:
            import secrets

            delay += secrets.SystemRandom().uniform(0, delay * 0.1)
        return float(delay)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics for the rate limiter.

        Returns:
            Dictionary with rate limiter statistics
        """
        with self._lock:
            current_time = time.time()
            recent_requests = len(
                [t for t in self._request_times if current_time - t <= 60]
            )

            return {
                "requests_per_minute": self.requests_per_minute,
                "recent_requests": recent_requests,
                "available_requests": max(
                    0, self.requests_per_minute - recent_requests
                ),
                "min_delay": self.min_delay,
                "max_retries": self.max_retries,
            }


# Global rate limiter instances for different APIs
_gemini_limiter = RateLimiter(
    requests_per_minute=15,
    max_retries=3,
    base_delay=4.0,  # 60/15 = 4 seconds minimum
    max_delay=60.0,
)


def get_gemini_limiter() -> RateLimiter:
    """
    Get a rate limiter for Gemini API calls.

    Returns:
        RateLimiter instance configured for Gemini API
    """
    return _gemini_limiter


def create_limiter(
    requests_per_minute: int = 15,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
) -> RateLimiter:
    """
    Create a new rate limiter instance.

    Args:
        requests_per_minute: Maximum requests allowed per minute
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between requests in seconds
        max_delay: Maximum delay for exponential backoff
        jitter: Whether to add random jitter to delays

    Returns:
        Configured RateLimiter instance
    """
    return RateLimiter(
        requests_per_minute=requests_per_minute,
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        jitter=jitter,
    )
