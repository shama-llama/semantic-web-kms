import threading
import time
from unittest.mock import Mock, patch

import pytest

from app.core.rate_limiter import RateLimiter, create_limiter, get_gemini_limiter


class TestRateLimiter:
    """Test cases for RateLimiter class."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization with default values."""
        limiter = RateLimiter()
        assert limiter.requests_per_minute == 15
        assert limiter.max_retries == 3
        assert limiter.base_delay == 1.0
        assert limiter.max_delay == 60.0
        assert limiter.jitter is True
        assert limiter.min_delay == 4.0  # 60/15 = 4

    def test_rate_limiter_custom_initialization(self):
        """Test rate limiter initialization with custom values."""
        limiter = RateLimiter(
            requests_per_minute=10,
            max_retries=5,
            base_delay=2.0,
            max_delay=30.0,
            jitter=False,
        )
        assert limiter.requests_per_minute == 10
        assert limiter.max_retries == 5
        assert limiter.base_delay == 2.0
        assert limiter.max_delay == 30.0
        assert limiter.jitter is False
        assert limiter.min_delay == 6.0  # 60/10 = 6

    def test_wait_if_needed_no_wait(self):
        """Test that wait_if_needed doesn't wait when under limit."""
        limiter = RateLimiter(requests_per_minute=60)  # 1 request per second
        start_time = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start_time
        assert elapsed < 0.1  # Should be very fast

    def test_wait_if_needed_with_delay(self):
        """Test that wait_if_needed respects minimum delay between requests."""
        limiter = RateLimiter(requests_per_minute=30)  # 2 seconds between requests
        start_time = time.time()
        limiter.wait_if_needed()
        # First call should be fast
        elapsed1 = time.time() - start_time
        assert elapsed1 < 0.1

        # Second call should wait
        start_time2 = time.time()
        limiter.wait_if_needed()
        elapsed2 = time.time() - start_time2
        assert elapsed2 >= 1.5  # Should wait at least 1.5 seconds

    def test_rate_limit_detection(self):
        """Test rate limit error detection."""
        limiter = RateLimiter()

        # Test various rate limit error messages
        rate_limit_errors = [
            "429 Too Many Requests",
            "Rate limit exceeded",
            "Quota exceeded",
            "Resource exhausted",
            "Too many requests",
            "Throttled",
        ]

        for error_msg in rate_limit_errors:
            assert limiter._is_rate_limit_error(error_msg)

        # Test non-rate-limit errors
        non_rate_limit_errors = [
            "Invalid API key",
            "Network error",
            "Timeout",
            "Server error",
        ]

        for error_msg in non_rate_limit_errors:
            assert not limiter._is_rate_limit_error(error_msg)

    def test_retry_delay_calculation(self):
        """Test retry delay calculation from error messages."""
        limiter = RateLimiter(jitter=False)  # Disable jitter for predictable tests

        # Test extracting retry delay from error message
        error_with_delay = '{"retryDelay": "45s"}'
        delay = limiter._calculate_retry_delay(error_with_delay, 0)
        assert delay == 45.0

        # Test exponential backoff when no delay specified
        delay = limiter._calculate_retry_delay("Some error", 1)
        assert delay == 2.0  # base_delay * 2^1

        delay = limiter._calculate_retry_delay("Some error", 2)
        assert delay == 4.0  # base_delay * 2^2

    def test_call_with_retry_success(self):
        """Test successful API call with retry logic."""
        limiter = RateLimiter()
        mock_func = Mock(return_value="success")

        result = limiter.call_with_retry(mock_func, "arg1", kwarg1="value1")

        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")

    def test_call_with_retry_rate_limit_recovery(self):
        """Test API call that recovers from rate limit error."""
        limiter = RateLimiter(max_retries=2, jitter=False)
        mock_func = Mock()
        mock_func.side_effect = [
            ValueError("429 Rate limit exceeded"),
            ValueError("429 Rate limit exceeded"),
            "success",
        ]

        with patch("time.sleep") as mock_sleep:
            result = limiter.call_with_retry(mock_func)

        assert result == "success"
        assert mock_func.call_count == 3
        # Should have 2 sleep calls for retries plus 1 for initial rate limiting
        assert mock_sleep.call_count >= 2

    def test_call_with_retry_max_retries_exceeded(self):
        """Test API call that fails after max retries."""
        limiter = RateLimiter(max_retries=2)
        mock_func = Mock()
        mock_func.side_effect = [
            ValueError("429 Rate limit exceeded"),
            ValueError("429 Rate limit exceeded"),
            ValueError("429 Rate limit exceeded"),
        ]

        with patch("time.sleep"):
            with pytest.raises(ValueError, match="Rate limit exceeded after 2 retries"):
                limiter.call_with_retry(mock_func)

        assert mock_func.call_count == 3

    def test_call_with_retry_non_rate_limit_error(self):
        """Test API call that fails with non-rate-limit error."""
        limiter = RateLimiter(max_retries=2)
        mock_func = Mock()
        mock_func.side_effect = ValueError("Invalid API key")

        with pytest.raises(ValueError, match="Invalid API key"):
            limiter.call_with_retry(mock_func)

        # Should retry non-rate-limit errors with exponential backoff
        assert mock_func.call_count == 3

    def test_get_stats(self):
        """Test getting rate limiter statistics."""
        limiter = RateLimiter(requests_per_minute=10)

        # Make a few requests
        for _ in range(3):
            limiter.wait_if_needed()

        stats = limiter.get_stats()
        assert stats["requests_per_minute"] == 10
        assert stats["recent_requests"] == 3
        assert stats["available_requests"] == 7
        assert stats["min_delay"] == 6.0
        assert stats["max_retries"] == 3

    def test_thread_safety(self):
        """Test that rate limiter is thread-safe."""
        limiter = RateLimiter(requests_per_minute=100)  # High limit for testing
        results = []
        errors = []

        def make_request():
            try:
                limiter.wait_if_needed()
                results.append(threading.current_thread().name)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request, name=f"Thread-{i}")
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check that all threads completed successfully
        assert len(results) == 10
        assert len(errors) == 0


class TestRateLimiterFunctions:
    """Test cases for rate limiter utility functions."""

    def test_get_gemini_limiter(self):
        """Test getting the global Gemini rate limiter."""
        limiter = get_gemini_limiter()
        assert isinstance(limiter, RateLimiter)
        assert limiter.requests_per_minute == 15
        assert limiter.min_delay == 4.0

    def test_create_limiter(self):
        """Test creating a custom rate limiter."""
        limiter = create_limiter(
            requests_per_minute=20,
            max_retries=5,
            base_delay=3.0,
            max_delay=45.0,
            jitter=False,
        )
        assert isinstance(limiter, RateLimiter)
        assert limiter.requests_per_minute == 20
        assert limiter.max_retries == 5
        assert limiter.base_delay == 3.0
        assert limiter.max_delay == 45.0
        assert limiter.jitter is False
        assert limiter.min_delay == 3.0  # max(3.0, 60/20)
