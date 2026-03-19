# AI Observability and Control Platform

Node.js + Express backend that monitors, evaluates, and automatically optimizes an external AI agent (e.g. the LangChain RAG agent in `../AI_agent`).

## Setup

1. Install dependencies (none required beyond Node.js 18+).
2. Ensure the AI agent backend is running (e.g. `uvicorn app:app --port 8000` in `AI_agent`).
3. Set env if needed:
   - `AGENT_URL` – agent base URL (default `http://localhost:8000`)
   - `PORT` – platform port (default `3001`)

## Run

```bash
node app.js
```

Or: `npm start`

## API

- **POST /query**  
  Body: `{ "query": "Your question here" }`  
  Returns: `{ final_answer, attempts, final_metrics, final_prompt_version, config_used }`

- **GET /health**  
  Returns: `{ status: "ok" }`

## Store

- `store/logs.json` – per-query logs and attempts
- `store/metrics.json` – aggregated metrics
- `store/prompts.json` – prompt versions and performance

## Flow

1. Request hits **POST /query**.
2. Platform calls the external agent with the current prompt version and config.
3. Response is **evaluated** (relevance, accuracy, hallucination, toxicity).
4. **Metrics** are recorded (latency, tokens, cost, quality, stability).
5. If **qualityScore < threshold** (default 0.6) and retries remain, **control** adjusts config/prompt and **retries** (max 3).
6. All attempts are stored; final answer and metrics are returned.
