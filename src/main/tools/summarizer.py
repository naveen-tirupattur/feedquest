import json
import requests
from typing import Dict, List, Union


def summarize_text(text: str, timeout: float = 5.0) -> Dict[str, Union[List[str], str]]:
    """Summarize *text* using the local Ollama model.

    The function now returns a dictionary with two keys:

    * ``"summary"`` – the concise summary string (empty on error).
    * ``"ai_tags"`` – a list of extracted tags (empty list on error).
    """
    # Default to a local Ollama daemon running on the standard port.
    system_prompt = (
        "You are a helpful assistant that summarizes text content concisely and clearly. "
        "Based on the input, provide a clear and concise summary highlighting"
        "the key themes in 100 words or less. Extract tags and include them in output json. No Yapping!"
    )
    api_url = "http://localhost:11434/api/generate"

    payload = {
        "model": "deepseek-v3.1:671b-cloud",
        "system": system_prompt,
        "prompt": text,
        "stream": False,
        "format": "json",

    }
    try:
        response = requests.post(api_url, json=payload, timeout=timeout)
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError:
            print("Error during summarization: invalid JSON response")
            return {"summary": "", "ai_tags": []}

        # The model may return a direct dict with ``summary`` and ``tags``
        # or a ``response`` field containing a JSON string.
        summary: str = ""
        tags: List[str] = []

        if isinstance(data, dict):
            if "summary" in data:
                summary = str(data.get("summary", "")).strip()
                tags = data.get("tags", []) or []
            elif "response" in data and isinstance(data["response"], str):
                # Attempt to parse the inner JSON string.
                try:
                    inner = json.loads(data["response"]).get("summary", "")
                    summary = str(inner).strip()
                    inner_tags = json.loads(data["response"]).get("tags", [])
                    tags = inner_tags or []
                except Exception:
                    # Fallback to raw string as summary.
                    summary = data["response"].strip()
            else:
                # Unexpected shape – serialize to string for summary.
                summary = json.dumps(data)
        elif isinstance(data, str):
            summary = data.strip()

        # Ensure tags is a list of strings.
        if not isinstance(tags, list):
            tags = []
        return {"summary": summary, "ai_tags": tags}
    except requests.RequestException as e:
        print(f"Error during summarization: {e}")
        return {"summary": "", "ai_tags": []}

if __name__ == "__main__":
    test_text = "The quick brown fox jumps over the lazy dog. This is a test of the summarization function."
    summary = summarize_text(test_text)
    print("Summary:", summary)
