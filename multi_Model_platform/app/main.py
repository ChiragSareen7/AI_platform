from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.services.orchestrator import run_query_pipeline
from app.services.logger import ensure_store_files
from app.services.learning import generate_report


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    context: str | None = Field(None, description="Optional RAG/context text for semantic grounding")
    ground_truth: str | None = Field(None, description="Optional reference answer for semantic accuracy")


app = FastAPI(title="Multi Model Orchestration Platform", version="1.0.0")
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://[::]:5500",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://[::]:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://[::]:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    ensure_store_files()


@app.get("/")
def root() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.post("/query")
def query_endpoint(request: QueryRequest) -> dict:
    return run_query_pipeline(
        request.query,
        context=request.context,
        ground_truth=request.ground_truth,
    )


@app.get("/report")
def report_endpoint() -> dict:
    return generate_report()
