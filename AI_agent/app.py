import os
import time
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from rag_pipeline import chat_with_rag
from retriever import similarity_search_with_scores


os.environ.setdefault("LANGCHAIN_TRACING_V2", settings.langsmith_tracing_v2)
os.environ.setdefault("LANGCHAIN_API_KEY", settings.langsmith_api_key)
os.environ.setdefault("LANGCHAIN_PROJECT", settings.langsmith_project)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = "default"


class RetrieveRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    response: str
    sources: list[dict[str, Any]]
    latency: float


app = FastAPI(title="Nexora RAG Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/retrieve")
async def retrieve_endpoint(body: RetrieveRequest) -> Dict[str, Any]:
    """Return top-k context chunks only (no LLM). For deterministic pipeline: top_k=3, fixed."""
    if not body.query or not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    k = 3
    results = similarity_search_with_scores(body.query.strip(), k=k)
    context_chunks = []
    similarity_scores = []
    for doc, score in results:
        context_chunks.append({
            "content": doc.page_content,
            "source": doc.metadata.get("source"),
            "page": doc.metadata.get("page"),
            "category": doc.metadata.get("category"),
            "id": doc.metadata.get("source", "") + "_" + str(doc.metadata.get("page", 0)),
        })
        similarity_scores.append(float(score))
    return {"contextChunks": context_chunks, "similarityScores": similarity_scores}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest) -> Dict[str, Any]:
    if not body.message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    start = time.time()
    result = chat_with_rag(body.message, session_id=body.session_id or "default")
    end = time.time()

    latency = (end - start) * 1000.0
    result["latency"] = latency
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )

