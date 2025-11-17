import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Union

import aiohttp
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MAX_REQUESTS_PER_MINUTE = 30

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable not set")


class SummarizationError(Exception):
    """Base exception for summarization failures."""
    pass


class RetryableError(SummarizationError):
    """Errors that should trigger a retry (rate limits, timeouts, server errors)."""
    pass


class NonRetryableError(SummarizationError):
    """Errors that should not be retried (auth, validation, malformed)."""
    pass


class RateLimiter:
    """Token bucket rate limiter for API calls.
    
    Proactively spaces requests to stay under the rate limit.
    With 30 requests per 60 seconds, this enforces ~2 second spacing.
    """

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.min_interval = window_seconds / max_requests  # ~2 seconds for 30/60
        self.last_request_time: float = 0.0

    async def acquire(self):
        """Wait if necessary to stay under rate limit."""
        now = time.time()
        time_since_last = now - self.last_request_time
        
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            logger.debug("Rate limiting: waiting %.2f seconds", wait_time)
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()


# Global rate limiter
_summarizer_limiter = RateLimiter(max_requests=MAX_REQUESTS_PER_MINUTE, window_seconds=60)


async def summarize_text(text: str) -> Dict[str, Union[List[str], str]]:
    """Summarize *text* using structured output with async/await.

    The function returns a dictionary with two keys:
    * ``"summary"`` – the concise summary string (empty on error).
    * ``"ai_tags"`` – a list of extracted tags (empty list on error).

    Raises:
    * ``RetryableError`` for rate limits, timeouts, and server errors.
    * ``NonRetryableError`` for authentication and validation errors.
    """
    system_prompt = (
        "You are a helpful assistant that summarizes text content concisely and clearly. "
        "Based on the input, provide a clear and concise summary highlighting "
        "the key themes in 100 words or less. Extract relevant tags and include them. No Yapping!"
        """ Respond only with JSON using this format:
        {
            "tags": [
                "tag1",
                "tag2",
                "tag3"
            ],
            "summary": "Short and concise summary"
        }"""
    )

    api_url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

    payload = {
        "model": "openai/gpt-oss-120b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        "response_format": {"type": "json_object"},
    }

    # Apply rate limiting
    await _summarizer_limiter.acquire()

    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(api_url, headers=headers, json=payload) as response:
                # Handle 429 (rate limit) – retryable
                if response.status == 429:
                    raise RetryableError("Rate limit hit (429)")

                # Handle 5xx (server errors) – retryable
                if response.status >= 500:
                    raise RetryableError(f"Server error {response.status}")

                # Handle 401/403 (auth) – non-retryable
                if response.status in (401, 403):
                    raise NonRetryableError(f"Authentication error {response.status}")

                # Handle other 4xx (client errors) – non-retryable
                if response.status >= 400:
                    raise NonRetryableError(f"Client error {response.status}")

                try:
                    data = await response.json()
                except (json.JSONDecodeError, ValueError):
                    raise NonRetryableError("Invalid JSON response")

                # Validate response structure
                if not isinstance(data, dict) or "choices" not in data:
                    raise NonRetryableError("Unexpected response structure: missing 'choices'")

                if not isinstance(data["choices"], list) or len(data["choices"]) == 0:
                    raise NonRetryableError("Unexpected response structure: empty choices")

                choice = data["choices"][0]
                if not isinstance(choice, dict) or "message" not in choice:
                    raise NonRetryableError("Unexpected response structure: missing message")

                message = choice["message"]
                if not isinstance(message, dict) or "content" not in message:
                    raise NonRetryableError("Unexpected response structure: missing content")

                content_str = message["content"]
                try:
                    parsed = json.loads(content_str)
                except json.JSONDecodeError as e:
                    raise NonRetryableError(f"Invalid JSON in response content: {e}")

                summary = str(parsed.get("summary", "")).strip()
                tags = parsed.get("tags", []) or []

                # Validate tags is a list of strings
                if not isinstance(tags, list):
                    tags = []
                else:
                    tags = [str(t) for t in tags]

                return {"summary": summary, "ai_tags": tags}

    except asyncio.TimeoutError:
        raise RetryableError("Request timeout")
    except aiohttp.ClientError as e:
        raise RetryableError(f"Network error: {e}")


if __name__ == "__main__":
    async def main():
        test_text = "The quick brown fox jumps over the lazy dog. This is a test of the summarization function."
        try:
            result = await summarize_text(test_text)
            print("Summary:", result)
        except Exception as e:
            print(f"Error: {e}")

    asyncio.run(main())
