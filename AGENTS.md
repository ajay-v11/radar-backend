# AI Visibility Scoring System - Agents Overview

## System Architecture

The system uses a **two-phase workflow** with 4 specialized agents:

```
Phase 1: Company Analysis
    └─> Industry Detector Agent

Phase 2: Complete Visibility Flow
    ├─> Industry Detector Agent (reuses Phase 1 cache)
    ├─> Query Generator Agent
    ├─> AI Model Tester Agent
    └─> Scorer Analyzer Agent
```

## Workflow State

All agents share a common state that flows through the pipeline:

```python
{
    "company_url": str,
    "company_name": str,
    "company_description": str,
    "industry": str,
    "competitors": List[str],
    "queries": List[str],
    "model_responses": Dict[str, List[str]],
    "visibility_score": float,
    "analysis_report": Dict,
    "errors": List[str]
}
```

---

## Agent 1: Industry Detector

**File**: `agents/industry_detector.py`

**Purpose**: Scrapes company website, detects industry, identifies competitors

**Process**:

1. Check cache (24hr TTL)
2. Scrape website with Firecrawl
3. Analyze with LLM (gpt-4-mini)
4. Extract: industry, company info, competitors
5. Store in ChromaDB with embeddings

**Industries**: technology, retail, healthcare, finance, food_services, other

**Output**:

- `industry`: Classification
- `company_name`, `company_description`, `company_summary`
- `competitors`: List of competitor names
- `competitors_data`: Rich metadata (description, products, positioning)

**Features**:

- Redis caching (90% faster on repeated URLs)
- Retry logic (2 attempts)
- Fallback to keyword matching if AI fails
- Stores competitors with rich embeddings for semantic search

---

## Agent 2: Query Generator

**File**: `agents/query_generator.py`

**Purpose**: Generates industry-specific search queries using LLM

**Process**:

1. Check cache (24hr TTL)
2. Select industry-specific categories (weighted)
3. Generate queries with LLM for each category
4. Incorporate company + competitor context
5. Deduplicate and cache results

**Categories** (example for food_services):

- Comparison (30%): "HelloFresh vs Blue Apron"
- Product Selection (25%): "best meal kits for families"
- Dietary Needs (20%): "keto meal delivery"
- Best-of Lists (15%): "top 10 meal delivery 2025"
- How-to (10%): "how meal kits work"

**Output**:

- `queries`: List of 20-100 queries
- `query_categories`: Organized by category

**Features**:

- Industry-specific templates
- Weighted distribution across categories
- Company + competitor context in queries
- Redis caching (instant on repeated requests)

---

## Agent 3: AI Model Tester

**File**: `agents/ai_model_tester.py`

**Purpose**: Tests queries across multiple AI models

**Supported Models**:

- ChatGPT (gpt-3.5-turbo)
- Gemini (gemini-2.5-flash-lite)
- Claude (claude-3-haiku)
- Llama (llama-3.1-8b-instant via Groq - FREE)
- Grok (via OpenRouter)
- DeepSeek (via OpenRouter)

**Process**:

1. For each query:
   - Check cache (1hr TTL)
   - Query each model
   - Cache response
   - Store in model_responses

**Output**:

- `model_responses`: Dict mapping model names to response lists

**Features**:

- Response caching (70% cost reduction)
- Graceful error handling
- Empty response on failure (non-blocking)

---

## Agent 4: Scorer Analyzer

**File**: `agents/scorer_analyzer.py`

**Purpose**: Calculates visibility score using hybrid mention detection

**Scoring Formula**:

```
visibility_score = (total_mentions / (num_queries × num_models)) × 100
```

**Mention Detection** (Hybrid):

1. **Exact String Matching**: Fast, high-precision company name search
2. **Semantic Matching**: RAG-based competitor detection via ChromaDB
   - Catches variations: "meal kit service" → HelloFresh
   - Similarity threshold: 0.70
   - Uses rich embeddings (name + description + products + positioning)

**Output**:

- `visibility_score`: 0-100 score
- `analysis_report`: Detailed breakdown with:
  - Per-model metrics
  - Competitor mention tracking
  - Sample mentions with context

**Interpretation**:

- 90-100%: Excellent visibility
- 70-89%: Good visibility
- 50-69%: Moderate visibility
- 30-49%: Low visibility
- 0-29%: Very low visibility

---

## Two-Phase Workflow

### Phase 1: Company Analysis

**Endpoint**: `POST /analyze/company`

**Purpose**: Isolated company analysis (higher failure rate, reusable results)

**Cache**: 24hr TTL on complete analysis

**Response**:

- Cached: Instant JSON (~10-50ms)
- Not cached: SSE stream with progress

### Phase 2: Visibility Analysis

**Endpoint**: `POST /analyze/visibility`

**Prerequisites**: Must run Phase 1 first

**Purpose**: Generate queries, test AI models, calculate visibility score

**Cache Layers**:

1. Industry analysis (24hr) - from Phase 1
2. Queries (24hr) - per company+industry+count
3. Model responses (1hr) - per query+model
4. Complete flow (24hr) - per all parameters

**Cache Behavior**:

- Same everything → Instant cached results
- Only models changed → Reuses queries, re-runs tests
- Only num_queries changed → Reuses industry, regenerates queries

**Response**:

- Cached: Instant JSON
- Not cached: SSE stream with real-time progress

---

## Smart Caching Strategy

### Multi-Level Caching

```
Level 1: Industry Analysis (24hr)
  → Instant company data on repeated requests

Level 2: Queries (24hr)
  → Reuses queries when only models change

Level 3: Model Responses (1hr)
  → 70% cost reduction on repeated queries

Level 4: Complete Flow (24hr)
  → Instant results when all parameters match
```

### Performance

**Cold Cache**: 35-70 seconds
**Warm Cache**: 20-100ms (instant)
**Cost Savings**: 70% with caching

---

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
FIRECRAWL_API_KEY=...

# Optional (for additional models)
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...
GROK_API_KEY=...
OPEN_ROUTER_API_KEY=...

# Databases
CHROMA_HOST=localhost
CHROMA_PORT=8001
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Model Settings

```python
# config/settings.py
INDUSTRY_ANALYSIS_MODEL = "gpt-4-mini"
CHATGPT_MODEL = "gpt-3.5-turbo"
GEMINI_MODEL = "gemini-2.5-flash-lite"
CLAUDE_MODEL = "claude-3-haiku-20240307"

DEFAULT_MODELS = ["chatgpt", "gemini"]
MIN_QUERIES = 20
MAX_QUERIES = 100
```

---

## Error Handling

All agents follow consistent principles:

1. **Non-Blocking**: Agents continue on errors
2. **Graceful Degradation**: Fallback strategies
3. **Error Logging**: Errors stored in `state["errors"]`
4. **State Preservation**: Partial results still returned

---

## Database Architecture

### ChromaDB (Vector Store)

- Port: 8001
- Collections: `companies`, `competitors`
- Usage: Semantic search, competitor matching

### Redis (Cache)

- Port: 6379
- TTL: 24hr (scrapes/analysis), 1hr (responses)
- Usage: Multi-level caching, rate limiting

### RAG Store (In-Memory)

- Query templates by industry (25+ per category)
- Loaded on startup

---

## Quick Start

### 1. Start Services

```bash
docker-compose up -d
```

### 2. Run Server

```bash
python run_server.py
```

### 3. Use API

```bash
# Phase 1: Analyze company
curl -X POST http://localhost:8000/analyze/company \
  -H "Content-Type: application/json" \
  -d '{"company_url": "https://hellofresh.com"}'

# Phase 2: Visibility analysis
curl -X POST http://localhost:8000/analyze/visibility \
  -H "Content-Type: application/json" \
  -d '{
    "company_url": "https://hellofresh.com",
    "num_queries": 20,
    "models": ["chatgpt", "gemini"]
  }'
```

---

## Documentation

For detailed documentation, see:

- **Architecture**: `docs/ARCHITECTURE.md` - System design and data flow
- **Orchestration**: `docs/ORCHESTRATION.md` - Workflow coordination
- **API Reference**: `docs/API_ENDPOINTS.md` - Complete API docs
- **Agent Details**:
  - `docs/AGENT_INDUSTRY_DETECTOR.md`
  - `docs/AGENT_QUERY_GENERATOR.md`
  - `docs/AGENT_AI_MODEL_TESTER.md`
  - `docs/AGENT_SCORER_ANALYZER.md`

---

## Key Features

✅ **Multi-Level Caching**: 4 cache layers for optimal performance
✅ **Hybrid Matching**: Exact + semantic mention detection
✅ **Smart Caching**: Granular cache keys for maximum reuse
✅ **Parallel Processing**: Batch testing for efficiency
✅ **Cost Optimized**: 70% cost reduction with caching
✅ **Streaming Updates**: Real-time progress via SSE
✅ **Graceful Degradation**: Continues on partial failures
