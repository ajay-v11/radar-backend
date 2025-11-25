# Agents Overview

## System Architecture

The system uses a **two-phase workflow** with 5 LangGraph-based agents:

```
Phase 1: Company Analysis
    └─> Industry Detector Agent

Phase 2: Visibility Analysis (Orchestrated)
    └─> Visibility Orchestrator
        ├─> Query Generator Agent
        ├─> AI Model Tester Agent
        └─> Scorer Analyzer Agent
```

## Key Features

- **LangGraph Workflows**: All agents use LangGraph for modular, observable workflows
- **Category-Based Batching**: Visibility orchestrator processes queries by category with progressive results
- **Dynamic Classification**: No hardcoded industries - LLM generates specific classifications
- **Parallel Scraping**: Company and competitor pages scraped simultaneously
- **Slug-Based Caching**: Simple route-level caching (24hr TTL)
- **Hybrid Matching**: Exact + semantic mention detection using ChromaDB

---

## Agent 1: Industry Detector

**Module**: `agents/industry_detection_agent/`

**Purpose**: Analyzes company website with dynamic industry classification and generates custom query categories

**LangGraph Workflow** (9 nodes):

1. `scrape_company_pages` - Scrape homepage + about page (parallel)
2. `scrape_competitor_pages` - Scrape competitor homepages (parallel)
3. `combine_scraped_content` - Combine all scraped content
4. `classify_industry` - Dynamic LLM classification (no hardcoded list)
5. `generate_extraction_template` - Create industry-specific template
6. `extract_with_template` - Extract company data using template
7. `generate_query_categories` - Generate custom query categories
8. `enrich_competitors` - Enrich competitor data with scraped content
9. `finalize` - Mark workflow complete

**Key Features**:

- Parallel scraping (company + competitors simultaneously)
- Dynamic industry classification (e.g., "AI-Powered Meal Kit Delivery" not "food_services")
- Generates custom query categories per company
- Stores competitors in ChromaDB with rich embeddings

**Output**:

- `industry`, `broad_category`, `industry_description`
- `query_categories_template` (used by query generator)
- `company_name`, `company_description`, `company_summary`
- `competitors`, `competitors_data` (with products, positioning)
- `extraction_template`, `product_category`, `market_keywords`
- `target_audience`, `brand_positioning`, `buyer_intent_signals`

**Cache**: 24hr TTL (complete analysis cached by slug)

---

## Agent 2: Query Generator

**Module**: `agents/query_generator_agent/`

**Purpose**: Generates search queries using dynamic categories from Industry Detector

**LangGraph Workflow** (5 nodes):

1. `check_cache` - Check if queries already cached (skips generation if found)
2. `calculate_distribution` - Calculate weighted query distribution across categories
3. `generate_category_queries` - Generate queries for all categories using LLM
4. `cache_results` - Cache generated queries (no longer used - route-level caching)
5. `finalize` - Return final queries and categories

**Key Features**:

- Uses `query_categories_template` from Industry Detector (no hardcoded categories)
- Weighted distribution (e.g., comparison 30%, product selection 25%)
- LLM generates queries with company + competitor context
- Deduplication

**Output**:

- `queries`: List of 20-100 queries
- `query_categories`: Organized by category

**Cache**: No agent-level caching (route-level only)

---

## Agent 3: AI Model Tester

**Module**: `agents/ai_model_tester_agent/`

**Purpose**: Tests queries across multiple AI models

**LangGraph Workflow** (3 nodes):

1. `initialize_responses` - Initialize response storage for all models
2. `test_queries_batch` - Test all queries across all models (parallel per query)
3. `finalize` - Return model responses

**Supported Models**:

- ChatGPT (gpt-3.5-turbo)
- Gemini (gemini-2.5-flash-lite)
- Claude (claude-3-5-haiku)
- Llama (llama-3.1-8b-instant via Groq)
- Grok (via OpenRouter)
- DeepSeek (via OpenRouter)

**Output**:

- `model_responses`: Dict mapping model names to response lists

**Cache**: No agent-level caching (route-level only)

---

## Agent 4: Scorer Analyzer

**Module**: `agents/scorer_analyzer_agent/`

**Purpose**: Calculates visibility score using hybrid mention detection

**LangGraph Workflow** (4 nodes):

1. `initialize_analysis` - Build query-to-category mapping
2. `analyze_responses` - Analyze all responses using hybrid matching (exact + semantic)
3. `calculate_score` - Calculate visibility score and build detailed report
4. `finalize` - Return score and analysis report

**Scoring Formula**:

```
visibility_score = (total_mentions / (num_queries × num_models)) × 100
```

**Hybrid Mention Detection**:

1. **Exact matching**: Fast company name search
2. **Semantic matching**: RAG-based via ChromaDB (threshold: 0.70)
   - Catches variations: "meal kit service" → HelloFresh
   - Uses rich embeddings from Industry Detector

**Output**:

- `visibility_score`: 0-100 score
- `analysis_report`: Per-model metrics, competitor mentions, samples

---

## Agent 5: Visibility Orchestrator

**Module**: `agents/visibility_orchestrator/`

**Purpose**: Orchestrates Query Generator → AI Model Tester → Scorer Analyzer with category-based batching

**LangGraph Workflow** (7 nodes with conditional looping):

1. `initialize_categories` - Initialize all categories and distribution
2. `select_next_category` - Pick next category to process
3. `generate_category_queries` - Generate queries for current category
4. `test_category_models` - Test queries across all models (parallel)
5. `analyze_category_results` - Analyze results for current category
6. `aggregate_category_results` - Aggregate into running totals, stream progress
7. **Conditional**: More categories? → Loop to step 2, else → `finalize_results`

**Category-Based Batching**:

- Processes one category at a time
- Streams progressive results after each category
- Provides partial scores and per-model breakdowns
- Allows early visibility into results

**Output**:

- `queries`, `query_categories`, `model_responses`
- `visibility_score`, `analysis_report`
- Progressive updates via callback

---

## Two-Phase Workflow

### Phase 1: Company Analysis

**Endpoint**: `POST /analyze/company`

- Runs Industry Detector agent
- Cache: 24hr TTL (slug-based)
- Response: SSE stream (instant if cached)

### Phase 2: Visibility Analysis

**Endpoint**: `POST /analyze/visibility`

- Runs Visibility Orchestrator (chains 3 agents)
- Requires Phase 1 data (via company_slug_id)
- Cache: 24hr TTL (slug-based, complete results)
- Response: SSE stream with category-based progress updates

---

## Caching Strategy

**4 Cache Levels**:

1. Scraping (24hr) - Raw website content
2. Industry Analysis (24hr) - Complete company profile
3. Queries (24hr) - Generated queries per company+count
4. Model Responses (1hr) - Per query+model

**Performance**:

- Cold: 30-60 seconds
- Warm (cached): 10-50ms
- Cost savings: 70%

---

## Configuration

### Environment Variables

```bash
# LLM Providers
INDUSTRY_ANALYSIS_PROVIDER=openai  # claude, gemini, llama, openai, grok, deepseek
QUERY_GENERATION_PROVIDER=claude

# API Keys
ANTHROPIC_API_KEY=...  # Claude (Recommended)
GEMINI_API_KEY=...     # Gemini
GROK_API_KEY=...       # Llama via Groq (FREE)
OPEN_ROUTER_API_KEY=...  # Grok/DeepSeek
OPENAI_API_KEY=...     # OpenAI
FIRECRAWL_API_KEY=...  # Required

# Databases
CHROMA_HOST=localhost
CHROMA_PORT=8001
REDIS_HOST=localhost
REDIS_PORT=6379
```

See `docs/LLM_PROVIDER_CONFIGURATION.md` for details.

---

## Error Handling

All agents use LangGraph with consistent error handling:

- Non-blocking: Errors logged, workflow continues
- Errors stored in `state["errors"]`
- Partial results returned on failure

---

## Databases

**ChromaDB** (Port 8001):

- Collections: `companies`, `competitors`
- Usage: Semantic search for mention detection

**Redis** (Port 6379):

- Slug-based caching (route-level)
- TTL: 24hr per route

---

## Quick Start

```bash
# 1. Start services
docker-compose up -d

# 2. Run server
python run_server.py

# 3. Phase 1: Analyze company
curl -X POST http://localhost:8000/analyze/company \
  -H "Content-Type: application/json" \
  -d '{"company_url": "https://hellofresh.com"}'

# 4. Phase 2: Visibility analysis
curl -X POST http://localhost:8000/analyze/visibility \
  -H "Content-Type: application/json" \
  -d '{"company_url": "https://hellofresh.com", "num_queries": 20, "models": ["chatgpt", "gemini"]}'
```

---

## Documentation

- `docs/ARCHITECTURE.md` - System design and data flow
- `docs/API_ENDPOINTS.md` - API reference with examples
- `docs/LLM_PROVIDER_CONFIGURATION.md` - LLM provider setup
- `docs/LANGGRAPH_MIGRATION.md` - LangGraph migration notes
