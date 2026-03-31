# How Metrics Are Calculated — AI Optimization Platform

This document explains every metric produced by each service, the exact formulas used, and where the code lives.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [multi_Model_platform Metrics](#2-multi_model_platform-metrics-port-8020)
3. [Platform (Observability) Metrics](#3-platform-observability-metrics-port-3001)
4. [Deterministic Pipeline Metrics](#4-deterministic-pipeline-metrics-port-3002)
5. [AI_agent Logging Metrics](#5-ai_agent-logging-metrics-port-8000)
6. [Shared Primitives](#6-shared-primitives)
7. [Configuration & Tuning](#7-configuration--tuning)

---

## 1. Architecture Overview

```
                    ┌──────────────────────────┐
                    │  multi_Model_platform     │
                    │  Lexical + Semantic Eval   │
                    │  + BLUE Metrics + Ranking  │
                    └────────────┬─────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
   ┌─────▼─────┐          ┌─────▼─────┐          ┌─────▼─────┐
   │  Platform  │          │Deterministic│         │  AI_agent  │
   │  5 metric  │          │  Validation │         │  JSONL     │
   │  groups    │          │  Metrics    │         │  Logging   │
   └───────────┘          └─────────────┘         └───────────┘
```

Each service computes its own metrics independently. There is no shared metrics bus — each service uses its own evaluation logic suited to its role.

---

## 2. multi_Model_platform Metrics (port 8020)

This service runs the most sophisticated evaluation. For every query, it executes **all ranked models × 3 prompt variants**, evaluates each response, ranks them, and returns the best.

### 2.1 Lexical Metrics (per response)

**File:** `multi_Model_platform/app/services/evaluator.py`  
**Function:** `_legacy_lexical_metrics(query, response, latency, token_usage)`

| Metric | Formula | Range |
|--------|---------|-------|
| **relevanceScore** | `keyword_overlap(query, response)` = \|query_tokens ∩ response_tokens\| / \|query_tokens\| | 0–1 |
| **accuracyScore** | `min(1.0, 0.65 × relevance + 0.35 × jaccard)` where jaccard = \|tokens_A ∩ tokens_B\| / \|tokens_A ∪ tokens_B\| | 0–1 |
| **hallucinationScore** | `max(0.0, 1.0 − accuracy + 0.1 if low_quality_marker)` | 0–1 |
| **confidenceScore** | `accuracy − (latency / 40000) − 0.15 if low_quality_marker`, clamped [0,1] | 0–1 |
| **tokenUsage** | `len(text) // 4` (rough heuristic: ~4 chars per token) | int |
| **cost** | `token_usage × 0.000002` | float |
| **toxicityScore** | Always 0.0 (no bad-word check at this layer) | 0 |
| **errorRate** | 1.0 if model returned an error, else 0.0 | 0 or 1 |

**Low quality markers:** `"i don't know"`, `"uncertain"`, `"not sure"`, `"cannot determine"` — if found in response, accuracy is penalized and hallucination inflated.

### 2.2 Semantic Metrics (per response)

**Files:** `multi_Model_platform/app/evaluation/pipeline.py`, `embeddings.py`, `grounding.py`, `nli.py`, `llm_judge.py`  
**Function:** `run_semantic_evaluation(query, response, context, ground_truth, thresholds)`  
**Enabled when:** `EVAL_ENABLE_SEMANTIC=true` (default: true)

These use **sentence-transformers** (`all-MiniLM-L6-v2`) for real embedding-based evaluation.

#### 2.2.1 Relevance

```
relevance = cosine_similarity(embed(query), embed(response))
```

- Embeds query and response into 384-dim vectors using the sentence transformer
- Computes cosine similarity between them
- **File:** `app/evaluation/embeddings.py → relevance_query_response()`

#### 2.2.2 Groundedness

```
For each sentence in response:
    best_sim = max(cosine_similarity(embed(sentence), embed(chunk)) for chunk in context_chunks)
    if best_sim >= grounding_min_sim (default 0.75):
        sentence is "supported"
    else:
        sentence is "unsupported"

groundedness = supported_count / total_sentences
```

- Context is split into chunks of max 480 chars (by paragraph boundaries)
- Each response sentence is compared against every context chunk
- **File:** `app/evaluation/grounding.py → groundedness_from_chunks()`
- If **no context provided**, groundedness falls back to the relevance score

#### 2.2.3 Hallucination (Semantic)

```
hallucination = unsupported_sentences / total_sentences
```

- Directly derived from the grounding check
- If NLI is enabled, contradicted sentences also count as hallucinated:
  ```
  hallucination = max(grounding_hallucination, contradiction_count / total_sentences)
  ```

#### 2.2.4 NLI (Natural Language Inference) — Optional

**Enabled when:** `EVAL_ENABLE_NLI=true` (default: false)  
**Model:** `cross-encoder/nli-MiniLM-L6-H-6`

```
For each response sentence:
    label, confidence = cross_encoder.predict(context, sentence)
    label ∈ {entailment, neutral, contradiction}
    
    score = 1.0 if entailment, 0.5 if neutral, 0.0 if contradiction

entailment_avg = mean(scores)
```

- Sentences labeled "contradiction" are added to the unsupported list
- **File:** `app/evaluation/nli.py → entailment_mean_score()`

#### 2.2.5 Accuracy (Semantic)

Two modes:

```
if ground_truth is provided:
    accuracy = cosine_similarity(embed(response), embed(ground_truth))
else:
    accuracy = groundedness × relevance
```

- When you pass a reference answer via the `ground_truth` field, accuracy is a direct semantic comparison
- Otherwise it's a product of how grounded and relevant the response is

#### 2.2.6 Confidence (Semantic)

Weighted combination of all signals:

```
if NLI enabled:
    confidence = (w_groundedness × groundedness + w_relevance × relevance + w_entailment × entailment_avg) / (w_g + w_r + w_e)
else:
    confidence = (w_groundedness × groundedness + w_relevance × relevance) / (w_g + w_r)
```

Default weights: `groundedness=0.35, relevance=0.35, entailment=0.30`

If **LLM Judge** is enabled (`EVAL_ENABLE_LLM_JUDGE=true`), confidence is blended:
```
confidence = 0.5 × confidence + 0.5 × judge_correctness
```

#### 2.2.7 LLM Judge — Optional

**Enabled when:** `EVAL_ENABLE_LLM_JUDGE=true` (default: false)  
**File:** `app/evaluation/llm_judge.py`

Sends query + context + response to Groq and asks for a JSON verdict:
```json
{"correctness": 0-1, "relevance": 0-1, "hallucination": 0-1}
```

The `correctness` score is blended into confidence (50/50 with computed confidence).

### 2.3 BLUE Metrics (aggregate across all responses)

**File:** `multi_Model_platform/app/services/orchestrator.py → _blue_metrics()`

These summarize the entire query run (all models × all prompts):

| Metric | Formula |
|--------|---------|
| **behaviorStability** | For each model, compute `average_pairwise_jaccard` of its responses across the 3 prompts. Then average across models. |
| **latency** | Mean latency across all model×prompt responses |
| **usageCost** | Sum of all individual costs |
| **errorRate** | Mean error rate across all responses |

### 2.4 Ranking

**File:** `multi_Model_platform/app/services/ranker.py`

Responses are sorted by a tuple key (lower is better):

```
if USE_SEMANTIC_RANKING=true (default):
    sort by: (-semantic.accuracy, +semantic.hallucination, +latency, -semantic.confidence)
else:
    sort by: (-accuracyScore, +hallucinationScore, +latency, -confidenceScore)
```

The first response after sorting is the **best answer**.

---

## 3. Platform (Observability) Metrics (port 3001)

The Platform wraps the AI_agent's `/chat` endpoint and evaluates every response. It produces **5 metric groups**.

### 3.1 Evaluation Scores

**File:** `Platform/src/services/evaluation.service.js → evaluate()`

| Metric | Formula | Range |
|--------|---------|-------|
| **relevanceScore** | `min(1, (matching_words / query_words) × 1.2)` — keyword overlap between query and response | 0–1 |
| **accuracyScore** | For each word in response (>2 chars), check if it appears in context. `found / total_words` | 0–1 |
| **hallucinationScore** | Split response into sentences. For each sentence, check if any keyword (>3 chars) appears in context. `not_found / total_sentences` | 0–1 |
| **toxicityScore** | Count of response words in a bad-words list × 0.25 | 0–1 |
| **qualityScore** | `0.25 × relevance + 0.35 × accuracy + 0.25 × (1−hallucination) + 0.15 × (1−toxicity)` | 0–1 |

### 3.2 System Metrics

**File:** `Platform/src/services/metrics.service.js → buildMetrics()`

| Metric | Source |
|--------|--------|
| **latencyMs** | Wall-clock time for the AI_agent `/chat` round-trip |
| **tokenUsage** | `{input, output, total}` estimated as `ceil(chars / 4)` per text |
| **costPerRequest** | `(input_tokens / 1000) × costPer1kInput + (output_tokens / 1000) × costPer1kOutput` |

### 3.3 Stability Metrics

| Metric | Formula |
|--------|---------|
| **retryRate** | `retryCount / (retryCount + 1)` — 0 if first attempt succeeded |
| **errorRate** | 1 if any attempt threw an error, else 0 |
| **behaviorStability** | Jaccard similarity × length ratio between all response attempts. Computed via `similarity.js → behaviorStability()` |

### 3.4 Safety Metrics

| Metric | Source |
|--------|--------|
| **toxicityScore** | From evaluation (bad-words check) |
| **groundingScore** | `1 − hallucinationScore` (computed from hallucinationScore) |

### 3.5 User Metrics

| Metric | Source |
|--------|--------|
| **clarityScore** | Derived from relevance + accuracy heuristics |
| **helpfulnessScore** | Derived from quality score composite |

### 3.6 Retry Logic

If `qualityScore < qualityThreshold` (default 0.6), the Platform:
1. Adjusts config (temperature, maxTokens, prompt version)
2. Retries up to `maxRetries` times
3. Each retry is logged as a separate attempt with its own metrics
4. Final metrics include stability across all attempts

---

## 4. Deterministic Pipeline Metrics (port 3002)

The deterministic service focuses on **hallucination prevention** through strict validation.

### 4.1 Validation Metrics

**File:** `deterministic/src/services/validation.service.js`

The pipeline works as follows:

```
1. Split LLM answer into sentences (by . ! ? boundaries, min 10 chars)
2. For each sentence:
     best_sim = max(
         calculateSimilarity(sentence, full_joined_context),
         max(calculateSimilarity(sentence, chunk) for chunk in chunks)
     )
3. If best_sim < MIN_SIMILARITY (0.10): sentence is "unsupported"
```

| Metric | Formula | Range |
|--------|---------|-------|
| **hallucinationScore** | `unsupported_count / total_sentences` | 0–1 |
| **similarityScore** | `1 − hallucinationScore` | 0–1 |
| **validationScore** | Mean of best similarity scores across all sentences | 0–1 |
| **confidence** | 1 if all sentences pass, else 0 (binary) | 0 or 1 |

### 4.2 Similarity Function

**File:** `deterministic/src/utils/similarity.js → calculateSimilarity()`

```
calculateSimilarity(text1, text2) = (jaccard + cosine) / 2

where:
    jaccard = |set(words_1) ∩ set(words_2)| / |set(words_1) ∪ set(words_2)|
    cosine  = dot(tf_vector_1, tf_vector_2) / (|tf_vector_1| × |tf_vector_2|)
```

- Tokenization: lowercase, strip punctuation, split on whitespace
- tf = term-frequency (word count per document)
- This is a **lexical** (word-overlap) metric, not semantic

### 4.3 Rejection Logic

```
if hallucinationScore > 0:
    answer = "Answer could not be verified from documents."
    confidence = 0
```

This is strict by design — **every** sentence must pass the similarity threshold, or the entire answer is rejected.

---

## 5. AI_agent Logging Metrics (port 8000)

The AI_agent itself doesn't compute quality metrics. It logs raw interaction data to JSONL.

**File:** `AI_agent/metrics.py → log_interaction()`

| Field | Source |
|-------|--------|
| **timestamp** | `time.time()` at log write |
| **question** | User's query |
| **response** | LLM-generated answer |
| **sources** | Retrieved document chunks with similarity scores |
| **latency_ms** | Wall-clock time for the full RAG pipeline |
| **model_name** | Groq model used (e.g. `llama-3.3-70b-versatile`) |
| **tokens_in** | Input token count (from Groq response metadata) |
| **tokens_out** | Output token count (from Groq response metadata) |

The retrieval endpoint (`/retrieve`) returns:
- **contextChunks**: Document content, source file, page, category
- **similarityScores**: Pinecone cosine similarity scores (384-dim `all-MiniLM-L6-v2` embeddings)

---

## 6. Shared Primitives

### 6.1 Jaccard Similarity

Used by: multi_Model_platform, Platform, Deterministic

```
jaccard(A, B) = |tokens(A) ∩ tokens(B)| / |tokens(A) ∪ tokens(B)|
```

### 6.2 Cosine Similarity (Lexical / TF)

Used by: Deterministic

```
cosine(A, B) = Σ(tfA[w] × tfB[w]) / (||tfA|| × ||tfB||)
```

Where `tf[w]` = count of word `w` in the document.

### 6.3 Cosine Similarity (Embedding / Semantic)

Used by: multi_Model_platform semantic evaluation

```
cosine(A, B) = dot(embed(A), embed(B)) / (||embed(A)|| × ||embed(B)||)
```

Where `embed()` = sentence-transformer output (384-dim normalized vector).

### 6.4 Token Estimation

Used by: Platform, multi_Model_platform

```
tokens ≈ ceil(len(text) / 4)
```

Rough heuristic: ~4 characters per token for English text.

---

## 7. Configuration & Tuning

### multi_Model_platform

Set in `.env` or `app/evaluation/config.py`:

| Variable | Default | Effect |
|----------|---------|--------|
| `EVAL_ENABLE_SEMANTIC` | `true` | Enable/disable embedding-based evaluation |
| `EVAL_ENABLE_NLI` | `false` | Enable cross-encoder NLI (entailment/contradiction) |
| `EVAL_ENABLE_LLM_JUDGE` | `false` | Enable Groq-based LLM judge |
| `EVAL_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model for semantic eval |
| `EVAL_NLI_MODEL` | `cross-encoder/nli-MiniLM-L6-H-6` | Cross-encoder for NLI |
| `EVAL_GROUNDING_MIN_SIM` | `0.75` | Minimum embedding similarity for a sentence to be "grounded" |
| `EVAL_W_GROUNDEDNESS` | `0.35` | Weight for groundedness in confidence |
| `EVAL_W_RELEVANCE` | `0.35` | Weight for relevance in confidence |
| `EVAL_W_ENTAILMENT` | `0.30` | Weight for NLI entailment in confidence |
| `USE_SEMANTIC_RANKING` | `true` | Use semantic scores for ranking (vs lexical) |

### Deterministic

| Variable | Default | Effect |
|----------|---------|--------|
| `MIN_SIMILARITY` | `0.10` | Minimum Jaccard+Cosine score for a sentence to pass validation |

### Platform

| Variable | Default | Effect |
|----------|---------|--------|
| `qualityThreshold` | `0.6` | Minimum qualityScore before retry |
| `maxRetries` | `2` | Maximum number of retry attempts |
| `costPer1kInput` | `0.0015` | Cost per 1k input tokens |
| `costPer1kOutput` | `0.002` | Cost per 1k output tokens |

---

## Summary: Metrics at a Glance

```
┌───────────────────────────────────────────────────────────────┐
│                    METRICS PIPELINE                            │
├───────────────┬───────────────────────────────────────────────┤
│               │  Lexical Layer (word overlap)                  │
│  multi_Model  │  ├─ relevance (keyword overlap)               │
│  _platform    │  ├─ accuracy (0.65×relevance + 0.35×jaccard)  │
│               │  ├─ hallucination (1 − accuracy + penalty)    │
│               │  └─ confidence (accuracy − latency penalty)   │
│               │                                               │
│               │  Semantic Layer (embeddings)                   │
│               │  ├─ relevance (cosine: query ↔ response)      │
│               │  ├─ groundedness (sentence ↔ context chunks)  │
│               │  ├─ hallucination (unsupported/total)         │
│               │  ├─ accuracy (response ↔ ground_truth OR      │
│               │  │            groundedness × relevance)        │
│               │  └─ confidence (weighted avg of above)        │
│               │                                               │
│               │  BLUE Metrics (aggregate)                     │
│               │  ├─ behaviorStability (pairwise jaccard)      │
│               │  ├─ latency (mean)                            │
│               │  ├─ usageCost (sum)                           │
│               │  └─ errorRate (mean)                          │
├───────────────┼───────────────────────────────────────────────┤
│  Platform     │  system: latency, tokens, cost                │
│  (Observ.)    │  aiQuality: relevance, accuracy, hallucination│
│               │  stability: retryRate, errorRate, behavior    │
│               │  safety: toxicity, grounding                  │
│               │  user: clarity, helpfulness                   │
├───────────────┼───────────────────────────────────────────────┤
│ Deterministic │  hallucinationScore (sentence validation)     │
│               │  similarityScore (1 − hallucination)          │
│               │  validationScore (mean similarity)            │
│               │  confidence (binary: all pass or reject)      │
├───────────────┼───────────────────────────────────────────────┤
│  AI_agent     │  latency_ms, tokens_in, tokens_out            │
│               │  similarity_scores (Pinecone cosine)          │
└───────────────┴───────────────────────────────────────────────┘
```
