### Nexora Systems – RAG Conversational Agent

This project is a production-ready AI conversational agent built with:

- **Python + FastAPI** backend
- **LangChain + Groq (llama3)** for LLM and RAG
- **FAISS** vector store with **HuggingFaceEmbeddings**
- **PyPDFLoader + RecursiveCharacterTextSplitter** for PDF chunking
- **ConversationBufferMemory** for multi-turn chat
- **LangSmith tracing** (LangChain v2 tracing) enabled via env vars
- **Next.js** frontend chat UI

The agent answers questions using company PDFs from `data/` via Retrieval Augmented Generation (RAG), and falls back to general LLM knowledge when documents are not relevant. Each request is logged to a JSONL file for later analysis.

---

### 1. Project structure

```text
AI_agent/
  app.py
  config.py
  rag_pipeline.py
  retriever.py
  embeddings.py
  memory.py
  metrics.py
  requirements.txt
  .env

  data/
    (8 company PDFs – you provide these)

  vector_store/
    (created automatically to persist FAISS index)

  logs/
    requests.jsonl        # created automatically for metrics

  frontend/
    package.json
    next.config.mjs
    pages/
      index.js            # chat UI
```

---

### 2. Environment variables

Create `.env` in `AI_agent/` (you already did) with keys like:

```bash
# --- LLM / Groq ---
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL_PRIMARY=llama3-70b-8192
GROQ_MODEL_SECONDARY=llama3-8b-8192

# --- Embeddings / Hugging Face (optional but recommended) ---
HUGGINGFACEHUB_API_TOKEN=your_hf_token_here
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2

# --- LangSmith / LangChain observability ---
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGCHAIN_PROJECT=Nexora-Agent

# --- App / backend config ---
APP_HOST=0.0.0.0
APP_PORT=8000
FRONTEND_ORIGIN=http://localhost:3000

# --- Paths ---
DATA_DIR=./data
VECTOR_STORE_DIR=./vector_store
LOG_FILE_PATH=./logs/requests.jsonl

# --- Company info for prompt ---
COMPANY_NAME=Nexora Systems
COMPANY_TAGLINE=Nexora Systems is a global artificial intelligence infrastructure company focused on building monitoring, optimization, and governance platforms for large scale AI deployments.
```

---

### 3. Backend setup and run

1. **Create and activate a virtualenv** (optional but recommended):

```bash
cd AI_agent
python -m venv .venv
source .venv/bin/activate   # on macOS/Linux
# .venv\Scripts\activate    # on Windows
```

2. **Install Python dependencies**:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3. **Ensure your PDFs are in `data/`**:

- Place your 8 company PDF documents into `AI_agent/data/`.

4. **Run the FastAPI backend**:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

On first run, the backend will:

- Load PDFs from `data/`
- Chunk them (`chunk_size=1000`, `chunk_overlap=200`)
- Build FAISS embeddings
- Persist the index under `vector_store/faiss_index/`

Subsequent runs will **reuse** the existing FAISS index (no rebuild unless you delete it).

---

### 4. Frontend (Next.js) setup and run

1. **Install Node dependencies**:

```bash
cd AI_agent/frontend
npm install
```

2. **Run the Next.js dev server**:

```bash
npm run dev
```

3. **Open the chat UI**:

- Visit `http://localhost:3000` in your browser.
- The frontend will call the backend at `http://localhost:8000/chat`.

---

### 5. Using the agent

- Ask company-specific questions like:
  - “What does Nexora Systems do?”
  - “Who are Nexora’s clients?”
  - “What monitoring capabilities does Nexora’s platform provide?”
- The agent:
  - Retrieves top-4 similar chunks from FAISS (`search_type="similarity"`, `k=4`).
  - Uses them as context for the Groq LLM when relevance is high.
  - Falls back to general LLM knowledge when no relevant documents are found.
  - Maintains conversation history via `ConversationBufferMemory` so multi-turn questions keep context.
  - Returns sources used (file name, page, similarity score) with each answer.

---

### 6. Observability and metrics

- **LangSmith / LangChain tracing**:
  - Enabled automatically via `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`.
  - All LangChain chains, LLM calls, and retriever calls become traceable in LangSmith.

- **Agent-level metrics logging** (no dashboards):
  - On every `/chat` request the backend appends a JSON record to `logs/requests.jsonl` containing:
    - user question
    - retrieved documents (source + page + score)
    - model response
    - latency (ms)
    - model name
    - tokens in/out (when Groq metadata is available)

You can later load this JSONL file into any analytics or monitoring tool you like.

---

### 7. Implementation notes

- **RAG pipeline** (`rag_pipeline.py`):
  - Uses `FAISS` vector store and a custom `similarity_search_with_relevance_scores` helper.
  - Applies a relevance threshold so that if all scores are low, the system skips RAG context and answers using only the LLM.
  - System prompt instructs the assistant to prioritize company documents, avoid hallucinating policies, and cite sources.

- **Conversation memory** (`memory.py`):
  - Uses `ConversationBufferMemory` keyed by `session_id` (defaults to `"default"`).
  - `/chat` accepts an optional `session_id` to support multiple parallel conversations.

- **Retriever / vector store** (`retriever.py`):
  - Automatically discovers all `.pdf` files under `DATA_DIR`.
  - Uses `PyPDFLoader` and `RecursiveCharacterTextSplitter` with:
    - `chunk_size=1000`
    - `chunk_overlap=200`

- **Frontend UX**:
  - Simple chat-style interface with:
    - chat bubbles for user and assistant
    - scrollable chat area
    - loading indicator (“Thinking…”)
    - visible latency and document sources for each assistant reply.

---

### 8. Next steps / customization

- Add support for switching between multiple Groq models per request (e.g. query parameter or UI toggle).
- Extend the prompt with additional company guidelines or safety policies.
- Implement user-level authentication, session management, or role-based prompts.
- Attach your own monitoring / dashboards by consuming the JSONL logs and LangSmith traces.

