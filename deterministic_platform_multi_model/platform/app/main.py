from __future__ import annotations  # allows modern type hint syntax on older Python

from pathlib import Path  # pathlib lets us work with file/folder paths in an OS-independent way

from fastapi import FastAPI  # FastAPI is the web framework — it handles incoming HTTP requests
from fastapi.responses import FileResponse  # FileResponse sends a file (like HTML) back to the browser
from fastapi.staticfiles import StaticFiles  # StaticFiles serves a whole folder of files (JS, CSS, HTML)
from fastapi.middleware.cors import CORSMiddleware  # CORS middleware allows browser frontends on different ports to call our API
from pydantic import BaseModel, Field  # BaseModel defines the shape of request/response data; Field adds validation rules

from app.services.orchestrator import run_query_pipeline  # the main pipeline function that runs all models
from app.services.logger import ensure_store_files  # makes sure the logs.json and model_performance.json files exist
from app.services.learning import generate_report  # generates a summary report of model performance over time


# ── Request Model ────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    # This class defines exactly what JSON the client must send in POST /query
    query: str = Field(..., min_length=1)  # 'query' is required (... means required), must be at least 1 character
    context: str | None = Field(None, description="Optional RAG/context text for semantic grounding")
    # 'context' is optional (None by default) — provide it if you have retrieved document chunks to ground the answer against
    ground_truth: str | None = Field(None, description="Optional reference answer for semantic accuracy")
    # 'ground_truth' is optional — provide a known correct answer so the system can compute accuracy as cosine similarity


# ── App Setup ────────────────────────────────────────────────────────────────
app = FastAPI(title="Multi Model Orchestration Platform", version="1.0.0")
# creates the FastAPI application object with a human-readable title shown in /docs

STATIC_DIR = Path(__file__).resolve().parent / "static"
# __file__ is the path to THIS file (main.py)
# .resolve() converts it to an absolute path
# .parent goes up one folder level (to the app/ folder)
# / "static" joins with the static subfolder — this is where index.html, app.js, styles.css live

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
# tells FastAPI: any request to /static/... should serve files from the static/ folder
# e.g. /static/styles.css → serves platform/app/static/styles.css


# ── CORS Configuration ───────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,  # CORS = Cross-Origin Resource Sharing — controls which websites can call our API
    allow_origins=[  # list of website origins (protocol + domain + port) allowed to make requests
        "http://127.0.0.1:5500",   # common VS Code Live Server port
        "http://localhost:5500",
        "http://[::]:5500",        # IPv6 version of localhost
        "http://127.0.0.1:5173",   # Vite dev server port
        "http://localhost:5173",
        "http://[::]:5173",
        "http://127.0.0.1:3000",   # React / Next.js default dev port
        "http://localhost:3000",
        "http://[::]:3000",
    ],
    allow_credentials=True,  # allows cookies and auth headers to be sent with cross-origin requests
    allow_methods=["*"],     # allows all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],     # allows all HTTP headers in requests
)


# ── Startup Event ─────────────────────────────────────────────────────────────
@app.on_event("startup")  # this function runs automatically when the server starts up
def startup() -> None:
    ensure_store_files()
    # makes sure store/logs.json and store/model_performance.json exist on disk
    # if they don't exist, it creates them with empty content ([] and {})


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")  # handles GET requests to the root URL "http://127.0.0.1:8020/"
def root() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))
    # sends the browser the index.html file (the visual dashboard UI)


@app.post("/query")  # handles POST requests to "http://127.0.0.1:8020/query"
def query_endpoint(request: QueryRequest) -> dict:
    # FastAPI automatically reads the JSON body and creates a QueryRequest object from it
    # then returns the pipeline result as JSON
    return run_query_pipeline(
        request.query,           # the user's question string
        context=request.context,       # optional context chunks for grounding
        ground_truth=request.ground_truth,  # optional correct answer for accuracy
    )


@app.get("/report")  # handles GET requests to "http://127.0.0.1:8020/report"
def report_endpoint() -> dict:
    return generate_report()
    # reads store/logs.json and store/model_performance.json and returns aggregate stats:
    # best model per domain, average latency, accuracy comparison, total queries count
