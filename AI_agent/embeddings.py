from typing import Any

from langchain_huggingface import HuggingFaceEmbeddings

from config import settings


def get_embedding_model() -> Any:
    """
    Create and return the embedding model used for RAG.
    """
    model_kwargs = {"device": "cpu"}
    encode_kwargs = {"normalize_embeddings": True}

    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs,
    )

