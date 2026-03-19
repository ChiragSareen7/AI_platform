from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple

from langchain_groq import ChatGroq
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from config import settings
from metrics import log_interaction
from retriever import TOP_K, similarity_search_with_scores


SYSTEM_PROMPT = """You are an AI assistant for {company_name}, a company described as:
{company_tagline}

You answer questions using two modes:
- If relevant company documents are provided, you must prioritize them and ground your answers strictly in that context.
- If the documents are not relevant or not provided, you can answer using general world knowledge.

Guidelines:
- Be honest when the documents do not contain enough information.
- Do not invent or hallucinate company policies, contracts, or guarantees that are not in the documents.
- When you use the documents, clearly cite them in your answer, mentioning the source file name and any useful metadata.
- Keep answers clear, structured, and concise.
"""


_HISTORIES: Dict[str, List[Dict[str, str]]] = {}


def _get_history_text(session_id: str) -> str:
    turns = _HISTORIES.get(session_id, [])
    if not turns:
        return ""
    parts: List[str] = []
    for turn in turns:
        q = turn.get("question", "")
        a = turn.get("answer", "")
        parts.append(f"User: {q}\nAssistant: {a}")
    return "\n\n".join(parts)


def _append_history(session_id: str, question: str, answer: str) -> None:
    if session_id not in _HISTORIES:
        _HISTORIES[session_id] = []
    _HISTORIES[session_id].append({"question": question, "answer": answer})


def _format_sources(docs_with_scores: List[Tuple[Document, float]]) -> List[Dict[str, Any]]:
    formatted: List[Dict[str, Any]] = []
    for doc, score in docs_with_scores:
        meta = dict(doc.metadata or {})
        formatted.append(
            {
                "source": meta.get("source"),
                "page": meta.get("page"),
                "score": float(score) if score is not None else None,
                "metadata": meta,
            }
        )
    return formatted


def _build_llm(model_name: str | None = None) -> ChatGroq:
    return ChatGroq(
        groq_api_key=settings.groq_api_key,
        model=model_name or settings.groq_model_primary,
        temperature=0.3,
        max_tokens=800,
    )


def _build_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("system", "Conversation so far (if any):\n{history}"),
            ("human", "{question}"),
            ("system", "Context from documents (if any):\n\n{context}"),
        ]
    )


def _combine_context(docs_with_scores: List[Tuple[Document, float]]) -> str:
    parts: List[str] = []
    for doc, score in docs_with_scores:
        meta = doc.metadata or {}
        src = meta.get("source", "unknown")
        page = meta.get("page", "N/A")
        parts.append(
            f"[source: {src}, page: {page}, score: {score:.3f}]\n{doc.page_content}"
        )
    return "\n\n---\n\n".join(parts)


def chat_with_rag(question: str, *, session_id: str = "default") -> Dict[str, Any]:
    """
    Main entry point for answering a user question with RAG and conversation memory.
    """
    start_time = time.time()

    history_text = _get_history_text(session_id)
    llm = _build_llm()
    prompt = _build_prompt()

    docs_with_scores = similarity_search_with_scores(question, k=TOP_K)

    # Use all retrieved docs as context, letting the LLM decide relevance.
    use_rag = len(docs_with_scores) > 0
    context = _combine_context(docs_with_scores) if use_rag else ""

    chain = (
        {
            "question": RunnablePassthrough(),
            "history": lambda _: history_text,
            "context": lambda _: context,
            "company_name": lambda _: settings.company_name,
            "company_tagline": lambda _: settings.company_tagline,
        }
        | prompt
        | llm
    )

    result = chain.invoke(question)

    answer_text = result.content if hasattr(result, "content") else str(result)

    _append_history(session_id, question, answer_text)

    latency_ms = (time.time() - start_time) * 1000.0

    sources = _format_sources(docs_with_scores if use_rag else [])

    usage = getattr(result, "usage_metadata", None) or {}
    tokens_in = usage.get("input_tokens")
    tokens_out = usage.get("output_tokens")

    log_interaction(
        question=question,
        response=answer_text,
        sources=sources,
        latency_ms=latency_ms,
        model_name=settings.groq_model_primary,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )

    return {
        "response": answer_text,
        "sources": sources,
        "latency": latency_ms,
    }

