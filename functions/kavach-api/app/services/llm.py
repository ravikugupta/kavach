from __future__ import annotations
"""
Optional LLM enhancement layer.

The prototype works fully offline using the rule-based NLU in `nlu.py`.
If you want richer natural-language understanding (especially for Kannada
free-text and complex multi-hop questions), you can plug in:

  1. Ollama (local LLM) -- set OLLAMA_HOST and OLLAMA_MODEL env vars.
  2. Anthropic Claude API -- set ANTHROPIC_API_KEY env var.

Both are optional. If neither is configured, `enhance_response` is a no-op.
"""

import os
import json

OLLAMA_HOST = os.environ.get("OLLAMA_HOST")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


def llm_available() -> bool:
    return bool(OLLAMA_HOST or ANTHROPIC_API_KEY or GEMINI_API_KEY)


def _call_ollama(prompt: str) -> str | None:
    try:
        import requests
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as exc:
        print(f"[llm] Ollama call failed: {exc}")
        return None


def _call_anthropic(prompt: str) -> str | None:
    try:
        import requests
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        parts = [c["text"] for c in data.get("content", []) if c.get("type") == "text"]
        return "\n".join(parts).strip()
    except Exception as exc:
        print(f"[llm] Anthropic call failed: {exc}")
        return None


def _call_gemini(prompt: str) -> str | None:
    try:
        import requests
        model = "gemini-1.5-flash"
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 400},
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "").strip()
        return None
    except Exception as exc:
        print(f"[llm] Gemini call failed: {exc}")
        return None


def enhance_response(user_query: str, structured_result: dict) -> str | None:
    """
    Given the user's raw query and the structured result already produced by
    the rule-based pipeline, ask an LLM to write a more natural answer.
    Returns None if no LLM is configured or the call fails.
    """
    if not llm_available():
        return None

    prompt = (
        "You are Kavach, a crime intelligence assistant for the Karnataka State Police. "
        "Rewrite the following structured analysis result as a concise, natural-language "
        "answer for an investigator. Do NOT invent any facts beyond what is given. "
        "Always keep specific IDs, names and numbers exactly as given.\n\n"
        f"User question: {user_query}\n\n"
        f"Structured result (JSON):\n{json.dumps(structured_result, default=str, indent=2)[:4000]}\n\n"
        "Answer:"
    )

    if OLLAMA_HOST:
        return _call_ollama(prompt)
    if ANTHROPIC_API_KEY:
        return _call_anthropic(prompt)
    if GEMINI_API_KEY:
        return _call_gemini(prompt)
    return None
