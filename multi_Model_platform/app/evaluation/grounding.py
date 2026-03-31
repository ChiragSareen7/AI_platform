from __future__ import annotations

import re
from typing import Sequence

from app.evaluation.embeddings import embed_texts, cosine_similarity_vec


_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def split_sentences(text: str, min_len: int = 12) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    parts = [p.strip() for p in _SPLIT_RE.split(text) if p and len(p.strip()) >= min_len]
    return parts if parts else [text]


def chunk_context(context: str, max_chars: int = 480) -> list[str]:
    ctx = (context or "").strip()
    if not ctx:
        return []
    blocks = [b.strip() for b in re.split(r"\n\s*\n", ctx) if b.strip()]
    chunks: list[str] = []
    for b in blocks:
        if len(b) <= max_chars:
            chunks.append(b)
        else:
            for i in range(0, len(b), max_chars):
                chunks.append(b[i : i + max_chars])
    return [c for c in chunks if c]


def groundedness_from_chunks(
    sentences: Sequence[str],
    context_chunks: Sequence[str],
    embedding_model: str,
    min_sim: float,
) -> tuple[float, list[str]]:
    if not sentences:
        return 1.0, []
    if not context_chunks:
        return 0.0, list(sentences)

    sent_embs = embed_texts(list(sentences), embedding_model)
    chunk_embs = embed_texts(list(context_chunks), embedding_model)
    unsupported: list[str] = []
    supported = 0
    for i, _ in enumerate(sentences):
        best = 0.0
        for j in range(len(context_chunks)):
            sim = cosine_similarity_vec(sent_embs[i], chunk_embs[j])
            if sim > best:
                best = sim
        if best >= min_sim:
            supported += 1
        else:
            unsupported.append(sentences[i])
    g = supported / len(sentences)
    return g, unsupported
