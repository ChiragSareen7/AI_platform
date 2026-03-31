from __future__ import annotations

import os
import time
from typing import Any

import httpx

from app.services.tracing import traceable_if_enabled
from app.utils.token_estimator import estimate_tokens

MODELS_API_BASE_URL = os.getenv("MODELS_API_BASE_URL", "http://127.0.0.1:8010")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "25"))

MODEL_ENDPOINT_MAP = {
    "organic_model": "/organic",
    "python_model": "/python",
    "gita_model": "/gita",
}


@traceable_if_enabled(run_type="chain", name="execute-model-call")
def execute_model(model_name: str, original_query: str, prompt_text: str) -> dict[str, Any]:
    started = time.perf_counter()
    error = None
    text = ""

    try:
        if model_name == "groq_model":
            text = _execute_groq(prompt_text)
        else:
            endpoint = MODEL_ENDPOINT_MAP[model_name]
            payload = {"query": prompt_text}
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                resp = client.post(f"{MODELS_API_BASE_URL}{endpoint}", json=payload)
                resp.raise_for_status()
                body = resp.json()
                text = body.get("answer", "")
    except Exception as exc:
        error = str(exc)

    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    tokens = estimate_tokens(prompt_text + " " + text)

    return {
        "model": model_name,
        "query": original_query,
        "response": text,
        "error": error,
        "latency": latency_ms,
        "tokenUsage": tokens,
    }


def _execute_groq(prompt_text: str) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("Missing GROQ_API_KEY")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.1,
    }

    with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        resp = client.post(f"{GROQ_BASE_URL}/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
        body = resp.json()
        return body["choices"][0]["message"]["content"].strip()
