from __future__ import annotations


def generate_prompts(query: str) -> list[dict]:
    return [
        {"version": "v1", "text": f"Answer clearly and concisely: {query}"},
        {"version": "v2", "text": f"Explain in detail with useful context: {query}"},
        {"version": "v3", "text": f"Answer strictly with facts only. If uncertain, say uncertain: {query}"},
    ]
