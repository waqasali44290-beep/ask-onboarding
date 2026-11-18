"""Ollama client: streams an answer from the local LLM, token by token."""
import json
from collections.abc import Callable, Iterator

import httpx

from app.config import settings

# (system prompt, user message) -> stream of text pieces. Tests pass a fake with this shape.
StreamChat = Callable[[str, str], Iterator[str]]


class LLMError(RuntimeError):
    """The LLM could not be reached or failed mid-answer."""


def stream_chat(system: str, user: str) -> Iterator[str]:
    request = {
        "model": settings.llm_model,
        "stream": True,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "options": {
            "temperature": 0,  # same question + same sources -> same answer; no creative guessing
            "num_predict": settings.llm_max_tokens,
            "num_ctx": settings.llm_context_tokens,
        },
    }
    # Short connect timeout so "Ollama is down" is reported quickly; long read
    # timeout because a CPU-only model can pause for a while before the first token.
    timeout = httpx.Timeout(10, read=180)
    try:
        with httpx.stream("POST", f"{settings.ollama_url}/api/chat", json=request, timeout=timeout) as response:
            response.raise_for_status()
            # Ollama streams one JSON object per line.
            for line in response.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                if "error" in data:
                    raise LLMError(data["error"])
                if text := data.get("message", {}).get("content"):
                    yield text
                if data.get("done"):
                    return
    except httpx.HTTPError as exc:
        raise LLMError(f"Could not reach the language model: {exc}") from exc
