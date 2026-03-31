from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)


class QueryResponse(BaseModel):
    answer: str
    model: str


def _route_model(query: str) -> str:
    text = query.lower()
    if any(k in text for k in {"gita", "krishna", "arjuna", "dharma", "karma", "verse", "chapter"}):
        return "gita"
    if any(k in text for k in {"compound", "molecular", "boiling", "melting", "solubility", "toxicity", "benzene"}):
        return "organic"
    return "python"


def _load_model_bundle(model_dir: Path) -> Tuple[AutoTokenizer, AutoModelForSeq2SeqLM]:
    if not model_dir.exists():
        raise FileNotFoundError(f"Model path does not exist: {model_dir}")
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForSeq2SeqLM.from_pretrained(str(model_dir))
    model.eval()
    return tokenizer, model


def _prompt_for_model(model_key: str, query: str) -> str:
    q = query.strip()
    if model_key == "python":
        return f"task: python_faq; question: {q}"
    if model_key == "organic":
        return f"task: organic_props; question: {q}"
    if model_key == "gita":
        return f"task: gita_verse; question: {q}"
    return f"question: {q}"


def _generate_answer(
    tokenizer: AutoTokenizer,
    model: AutoModelForSeq2SeqLM,
    query: str,
    model_key: str,
    max_input_length: int = 256,
    max_output_length: int = 256,
) -> str:
    prompt = _prompt_for_model(model_key, query)
    encoded = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_input_length)
    with torch.no_grad():
        output_ids = model.generate(
            **encoded,
            max_new_tokens=max_output_length,
            do_sample=False,
            num_beams=1,
        )
    return tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()


app = FastAPI(title="Models QA API", version="1.0.0")

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATHS = {
    "python": ROOT / "python_model",
    "organic": ROOT / "organic_model",
    "gita": ROOT / "gita_model",
}
MODEL_REGISTRY: Dict[str, Tuple[AutoTokenizer, AutoModelForSeq2SeqLM]] = {}


@app.on_event("startup")
def startup_event() -> None:
    for key, path in MODEL_PATHS.items():
        try:
            MODEL_REGISTRY[key] = _load_model_bundle(path)
        except Exception as exc:
            print(f"[startup] failed to load {key} model: {exc}")


def _handle_request(model_key: str, request: QueryRequest) -> QueryResponse:
    bundle = MODEL_REGISTRY.get(model_key)
    if bundle is None:
        raise HTTPException(status_code=503, detail=f"Model '{model_key}' is not loaded.")
    tokenizer, model = bundle
    return QueryResponse(answer=_generate_answer(tokenizer, model, request.query, model_key), model=model_key)


@app.post("/python", response_model=QueryResponse)
def ask_python(request: QueryRequest) -> QueryResponse:
    return _handle_request("python", request)


@app.post("/organic", response_model=QueryResponse)
def ask_organic(request: QueryRequest) -> QueryResponse:
    return _handle_request("organic", request)


@app.post("/gita", response_model=QueryResponse)
def ask_gita(request: QueryRequest) -> QueryResponse:
    return _handle_request("gita", request)


@app.post("/ask", response_model=QueryResponse)
def ask_routed(request: QueryRequest) -> QueryResponse:
    return _handle_request(_route_model(request.query), request)

