from __future__ import annotations

import os
from typing import Sequence

import numpy as np

_model = None
_model_name: str | None = None


def _get_model(name: str):
    global _model, _model_name
    if _model is None or _model_name != name:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(name, device=os.getenv("EVAL_EMBEDDING_DEVICE", "cpu"))
        _model_name = name
    return _model


def embed_texts(texts: Sequence[str], model_name: str) -> np.ndarray:
    if not texts:
        return np.zeros((0, 1), dtype=np.float32)
    m = _get_model(model_name)
    arr = m.encode(list(texts), convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(arr, dtype=np.float32)


def cosine_similarity_vec(a: np.ndarray, b: np.ndarray) -> float:
    if a.size == 0 or b.size == 0:
        return 0.0
    a = np.asarray(a).flatten()
    b = np.asarray(b).flatten()
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom < 1e-12:
        return 0.0
    return float(np.dot(a, b) / denom)


def relevance_query_response(query: str, response: str, model_name: str) -> float:
    q, r = query.strip(), response.strip()
    if not q or not r:
        return 0.0
    emb = embed_texts([q, r], model_name)
    return cosine_similarity_vec(emb[0], emb[1])


def semantic_similarity_pair(a: str, b: str, model_name: str) -> float:
    a, b = a.strip(), b.strip()
    if not a or not b:
        return 0.0
    emb = embed_texts([a, b], model_name)
    return cosine_similarity_vec(emb[0], emb[1])
