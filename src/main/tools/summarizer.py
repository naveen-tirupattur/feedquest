import json
import requests
import time
from typing import Dict, List, Union

# Rate limiter for free tier (Groq: max 30 requests per minute)
_request_times = []  # Track timestamps of recent requests
MAX_REQUESTS_PER_MINUTE = 30

def summarize_text(text: str) -> Dict[str, Union[List[str], str]]:
    """Summarize *text* using structured output.

    The function returns a dictionary with two keys:
    * ``"summary"`` – the concise summary string (empty on error).
    * ``"ai_tags"`` – a list of extracted tags (empty list on error).
    """
    system_prompt = (
        "You are a helpful assistant that summarizes text content concisely and clearly. "
        "Based on the input, provide a clear and concise summary highlighting "
        "the key themes in 100 words or less. Extract relevant tags and include them. No Yapping!"
    )
    api_url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": "Bearer ",
    }

    payload = {
        "model": "openai/gpt-oss-120b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
    }
    summary = ""
    tags = []

    try:
        # Rate limiting: keep total requests under 30 per minute
        global _request_times
        current_time = time.time()

        # Remove requests older than 1 minute
        _request_times = [t for t in _request_times if current_time - t < 60]

        # If we've hit the limit, wait until the oldest request is outside the window
        if len(_request_times) >= MAX_REQUESTS_PER_MINUTE:
            wait_time = 60 - (current_time - _request_times[0])
            print(f"Rate limit approaching (30/min). Waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
            # Recalculate after waiting
            current_time = time.time()
            _request_times = [t for t in _request_times if current_time - t < 60]

        _request_times.append(current_time)
        response = requests.post(api_url, headers=headers, json=payload)

        # Don't retry on 429, just return empty
        if response.status_code == 429:
            print("Rate limit hit (429). Returning empty summary.")
            return {"summary": "", "ai_tags": []}

        response.raise_for_status()

        try:
            data = response.json()
        except ValueError:
            print("Error during summarization: invalid JSON response")
            return {"summary": "", "ai_tags": []}

        # Extract structured output from OpenAI/Groq format: choices[0].message.content
        if not (isinstance(data, dict) and "choices" in data and
                isinstance(data["choices"], list) and len(data["choices"]) > 0):
            print("Error during summarization: unexpected response structure")
            return {"summary": "", "ai_tags": []}

        choice = data["choices"][0]
        if not (isinstance(choice, dict) and "message" in choice):
            print("Error during summarization: missing message in response")
            return {"summary": "", "ai_tags": []}

        message = choice["message"]
        if not (isinstance(message, dict) and "content" in message):
            print("Error during summarization: missing content in message")
            return {"summary": "", "ai_tags": []}

        # Parse the JSON structured output
        content_str = message["content"]
        try:
            parsed = json.loads(content_str)
            summary = str(parsed.get("summary", "")).strip()
            tags = parsed.get("tags", []) or []
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Error parsing structured output: {e}")
            return {"summary": "", "ai_tags": []}

    except requests.RequestException as e:
        print(f"Error during summarization: {e}")
        return {"summary": "", "ai_tags": []}

    # Ensure tags is a list of strings
    if not isinstance(tags, list):
        tags = []
    return {"summary": summary, "ai_tags": tags}

if __name__ == "__main__":
    test_text = "The quick brown fox jumps over the lazy dog. This is a test of the summarization function."
    result = summarize_text(test_text)
    print("Summary:", result)
