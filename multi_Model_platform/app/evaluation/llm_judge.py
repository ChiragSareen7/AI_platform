from __future__ import annotations

import json
import os
import re
from typing import Any, Callable, Protocol

import httpx


class JudgeProvider(Protocol):
    def __call__(self, query: str, response: str, context: str) -> dict[str, Any] | None: ...


def default_groq_judge(query: str, response: str, context: str) -> dict[str, Any] | None:
    key = os.getenv("GROQ_API_KEY") or os.getenv("EVAL_JUDGE_API_KEY")
    if not key:
        return None
    base = os.getenv("EVAL_JUDGE_BASE_URL", os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"))
    model = os.getenv("EVAL_JUDGE_MODEL", os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"))
    system = (
        "You are an evaluation judge. Reply with ONLY valid JSON, no markdown: "
        '{"correctness":0-1,"relevance":0-1,"hallucination":0-1} '
        "where hallucination is degree of unsupported/fabricated content (higher=worse)."
    )
    user = f"query:\n{query}\n\ncontext:\n{context[:6000]}\n\nresponse:\n{response[:8000]}"
    try:
        with httpx.Client(timeout=45.0) as client:
            r = client.post(
                f"{base.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[^{}]+\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return None


def make_judge(provider: Callable[..., dict[str, Any] | None] | None) -> JudgeProvider | None:
    if provider is not None:
        return provider
    return default_groq_judge
