"""
Ollama LLM client.

Sends prompts to a local Ollama instance and parses structured JSON responses.
Used by all agent workflows for sentiment analysis and signal generation.
"""

import json
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger("smv.ollama")

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """Lazy-init the HTTP client for Ollama."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=120.0,  # LLM inference can be slow
        )
    return _client


async def close_client() -> None:
    """Close the HTTP client. Called on app shutdown."""
    global _client
    if _client:
        await _client.aclose()
        _client = None


async def generate(
    prompt: str,
    system: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """
    Generate a text completion from Ollama.
    Returns raw text response.
    """
    client = _get_client()

    payload: dict[str, Any] = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if system:
        payload["system"] = system

    try:
        resp = await client.post("/api/generate", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "")
    except httpx.HTTPStatusError as e:
        logger.error(f"Ollama API error {e.response.status_code}: {e.response.text[:200]}")
        return ""
    except httpx.RequestError as e:
        logger.error(f"Ollama request failed: {e}")
        return ""


async def generate_json(
    prompt: str,
    system: str | None = None,
    temperature: float = 0.2,
) -> dict | list | None:
    """
    Generate a structured JSON response from Ollama.
    Attempts to parse the LLM output as JSON. Returns None on parse failure.
    """
    # Enhance system prompt to request JSON output
    json_system = (system or "") + (
        "\n\nIMPORTANT: You MUST respond with valid JSON only. "
        "No markdown, no code fences, no explanatory text. Just raw JSON."
    )

    raw = await generate(prompt=prompt, system=json_system.strip(), temperature=temperature)

    if not raw:
        return None

    # Try to extract JSON from the response
    text = raw.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (fences)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON within the text
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start = text.find(start_char)
            end = text.rfind(end_char)
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    continue

        logger.warning(f"Failed to parse Ollama JSON response: {text[:200]}")
        return None


async def check_health() -> bool:
    """Check if Ollama is running and the model is available."""
    client = _get_client()
    try:
        resp = await client.get("/api/tags")
        resp.raise_for_status()
        data = resp.json()
        models = [m.get("name", "") for m in data.get("models", [])]
        model_available = any(settings.ollama_model in m for m in models)
        if not model_available:
            logger.warning(
                f"Ollama running but model '{settings.ollama_model}' not found. "
                f"Available: {models}. Pull it with: ollama pull {settings.ollama_model}"
            )
        return True
    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        return False
