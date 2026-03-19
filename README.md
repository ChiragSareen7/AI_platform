# AI Optimization Workspace

This repository contains three connected applications:

- `AI_agent` - the Python RAG backend (FastAPI) that loads PDFs, builds vectors, and serves retrieval/chat APIs.
- `deterministic` - the deterministic execution + validation layer (Node/Express) that calls `AI_agent` retrieval and enforces strict output controls.
- `Platform` - a UI/control app for observability/tuning (separate from deterministic runtime path).

The main production flow for deterministic responses is:

1. User calls `deterministic` API/UI.
2. `deterministic` calls `AI_agent` `/retrieve` for grounded context.
3. `deterministic` runs strict prompt + LLM + validation + cache.
4. Final structured response is returned with scores and metadata.

---

## Folder-by-folder overview

### `AI_agent/`

Python FastAPI service providing RAG retrieval and chat.

- `app.py`
  - `POST /retrieve`: returns top context chunks + scores (used by `deterministic`).
  - `POST /chat`: conversational RAG endpoint.
- `retriever.py`
  - PDF loading, chunking, vector build/load.
  - rule-based query category routing.
  - filtered retrieval + fallback retrieval.
  - supports vector provider selection (`qdrant` or `faiss`).
- `embeddings.py`
  - embedding model setup (`sentence-transformers/all-MiniLM-L6-v2`, normalized vectors).
- `rag_pipeline.py`
  - LLM chain for `/chat`.
- `config.py`
  - all env-driven runtime settings.
- `data/`
  - source PDF knowledge base.
- `vector_store/`
  - persisted vector data (`faiss_index/` and/or local qdrant files).
- `logs/`
  - request/interaction logs.
- `frontend/`
  - Next.js chat UI for direct `AI_agent` testing.

### `deterministic/`

Node/Express app for strict deterministic execution and verification.

- `app.js`
  - server bootstrap and routes.
- `src/routes/deterministic.routes.js`
  - `POST /deterministic-query`.
- `src/controllers/deterministic.controller.js`
  - orchestrates request execution, optional determinism test, and logging.
- `src/services/`
  - `inputNormalizer.service.js`: deterministic input normalization.
  - `queryClassifier.service.js`: rule-based category classification.
  - `retrieval.service.js`: calls `AI_agent` `/retrieve`.
  - `prompt.service.js`: strict anti-hallucination prompt template.
  - `llm.service.js`: LLM call with deterministic config.
  - `validation.service.js`: verifies answer support against context.
  - `cache.service.js`: stable hash-based cache keying.
  - `pipeline.service.js`: end-to-end deterministic pipeline.
  - `test.service.js`: runs same query repeatedly for consistency checks.
- `src/utils/similarity.js`
  - Jaccard + cosine similarity functions.
- `public/deterministic.html`
  - deterministic dashboard UI.
- `store/`
  - runtime logs and cached outputs.

### `Platform/`

Separate control/observability interface and related services/stores.
Useful for experimentation and metrics, but not the critical path of the deterministic API.

---

## How components connect

### Runtime integration

- `deterministic` -> `AI_agent` via:
  - `AGENT_RETRIEVE_URL=http://localhost:8000/retrieve`
- `AI_agent` returns:
  - `contextChunks[]` with `content`, `source`, `page`, `category`, `id`
  - `similarityScores[]`
- `deterministic` uses this context to enforce grounded generation.

### Determinism contract

Determinism is achieved by fixing:

- normalized input rules
- rule-based classification
- retrieval top-k and routing logic
- prompt template
- LLM params (`temperature=0`, fixed seed, fixed max tokens)
- validation rules
- cache key construction from normalized query + versions + context IDs

---

## Qdrant and vectorization details

### What vectorization means here

1. **Load docs** (`PyPDFLoader`): each PDF page becomes a document.
2. **Attach metadata**:
   - `source` (file name)
   - `category` (`hiring`, `products`, `policies`, `security`, `general`)
3. **Chunk text** (`RecursiveCharacterTextSplitter`):
   - `chunk_size=1200`
   - `chunk_overlap=300`
4. **Embed chunks** with sentence-transformers:
   - model: `sentence-transformers/all-MiniLM-L6-v2`
   - normalized embeddings for stable cosine behavior
5. **Store vectors** in Qdrant collection (cosine distance).

### How Qdrant retrieval works

- Query -> embedding vector.
- Detect category from query (rule-based).
- Search Qdrant with metadata filter on `metadata.category`.
- Return top `k=3`.
- Fallback to unfiltered all-doc search when:
  - no category-filtered results, or
  - best score below threshold.

This improves latency and relevance by avoiding unnecessary cross-document searches.

---

## RAG flow (end-to-end)

### `AI_agent` retrieval flow

`query -> detect category -> vector search (filtered) -> fallback (optional) -> top chunks`

### deterministic flow

`query -> normalize -> classify -> retrieve context -> strict prompt -> LLM -> validate -> similarity checks -> cache -> final JSON`

Validation rejects unsupported claims and can replace unverified output with safe fallback text.

---

## Environment configuration

Do not commit real secrets. Use `.env` locally.

### `AI_agent/.env` important keys

- LLM: `GROQ_API_KEY`, `GROQ_MODEL_PRIMARY`
- embeddings: `EMBEDDING_MODEL_NAME`
- vector provider:
  - `VECTOR_DB_PROVIDER=qdrant` (recommended)
  - `QDRANT_COLLECTION_NAME`
  - local mode: `QDRANT_PATH`
  - remote mode: `QDRANT_URL`, `QDRANT_API_KEY`
- one-time rebuild switch:
  - `FORCE_REBUILD_VECTOR_STORE=true` (rebuild)
  - then set back to `false`

### `deterministic/.env` important keys

- `GROQ_API_KEY`
- `GROQ_MODEL`
- `AGENT_RETRIEVE_URL` (points to `AI_agent` `/retrieve`)
- `PORT` (default `3002`)

---

## Run order (recommended)

1. Start `AI_agent`:
   - `cd AI_agent`
   - `source ../.venv/bin/activate` (if using shared venv)
   - first-time rebuild (optional):  
     `FORCE_REBUILD_VECTOR_STORE=true uvicorn app:app --host 0.0.0.0 --port 8000 --reload`
   - subsequent runs:  
     `uvicorn app:app --host 0.0.0.0 --port 8000 --reload`

2. Start deterministic service:
   - `cd deterministic`
   - `npm install`
   - `node app.js`

3. Open deterministic dashboard:
   - `http://localhost:3002/deterministic.html`

---

## Quick verification checklist

- `POST http://localhost:8000/retrieve` returns context chunks and scores.
- `POST http://localhost:3002/deterministic-query` returns strict JSON fields.
- Category-targeted queries return relevant source docs:
  - acquisitions -> acquisition/product docs
  - hiring -> hiring/recruitment docs
  - products -> product/platform docs
- deterministic dashboard shows context, scores, cache state, and determinism checks.

---

## Notes

- If remote Qdrant is unreachable, current retrieval logic can fall back to local Qdrant path.
- If local Qdrant storage is accessed by multiple processes, run a dedicated Qdrant server for concurrent access.
- If LLM calls fail in `deterministic`, retrieval can still work; verify Groq key/quota/model.
