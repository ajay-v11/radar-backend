# Documentation

## Overview

Two-phase workflow with LangGraph agents for analyzing company visibility across AI models.

## Quick Start

### 1. Start Services

```bash
docker-compose up -d
```

This starts:

- **ChromaDB** on port 8001 (vector database)
- **Redis** on port 6379 (cache)

### 2. Configure Environment

Copy `.env.example` to `.env` and add your API keys:

```bash
# Required
OPENAI_API_KEY=sk-...
FIRECRAWL_API_KEY=...

# Optional (for additional AI models)
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...
GROK_API_KEY=...
OPEN_ROUTER_API_KEY=...
```

### 3. Run Server

```bash
python run_server.py
```

Or with auto-reload:

```bash
uvicorn src.app:app --reload
```

### 4. Access API

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Documentation Structure

| Document                                                         | Description                                |
| ---------------------------------------------------------------- | ------------------------------------------ |
| [ARCHITECTURE.md](./ARCHITECTURE.md)                             | System design, data flow, caching strategy |
| [API_ENDPOINTS.md](./API_ENDPOINTS.md)                           | API reference with examples                |
| [LLM_PROVIDER_CONFIGURATION.md](./LLM_PROVIDER_CONFIGURATION.md) | LLM provider setup                         |
| [API_STREAMING_STRUCTURE.md](./API_STREAMING_STRUCTURE.md)       | SSE streaming format                       |
| [CSV_EXPORT.md](./CSV_EXPORT.md)                                 | CSV export feature                         |

## System Architecture

### Two-Phase Workflow

```
Phase 1: Company Analysis
    └─> Industry Detector Agent (LangGraph - 9 nodes)

Phase 2: Visibility Analysis
    └─> Visibility Orchestrator (7 nodes with looping)
        ├─> Query Generator (per category)
        ├─> AI Model Tester (parallel)
        └─> Scorer Analyzer (hybrid matching)
```

### Key Features

- **LangGraph Workflows**: Modular, observable agent workflows
- **Slug-Based Caching**: Simple route-level caching (24hr TTL)
- **Hybrid Matching**: Exact + semantic via ChromaDB
- **Category-Based Batching**: Progressive results per category
- **SSE Streaming**: Real-time progress updates

## API Usage

### Phase 1: Analyze Company

```bash
curl -X POST http://localhost:8000/analyze/company \
  -H "Content-Type: application/json" \
  -d '{"company_url": "https://hellofresh.com"}'
# Returns: slug_id (e.g., "company_abc123")
```

### Phase 2: Visibility Analysis

```bash
curl -X POST http://localhost:8000/analyze/visibility \
  -H "Content-Type: application/json" \
  -d '{
    "company_slug_id": "company_abc123",
    "num_queries": 20,
    "models": ["llama", "gemini"]
  }'
# Returns: SSE stream with visibility_score, model_scores, category_breakdown
```

## Performance

| Scenario   | Phase 1 | Phase 2 | Total    |
| ---------- | ------- | ------- | -------- |
| Cold cache | 5-10s   | 30-60s  | 35-70s   |
| Warm cache | 10-50ms | 10-50ms | 20-100ms |

**Cost Optimization**: 70% savings with 4-level caching

## Technology Stack

- **Backend**: FastAPI (Python 3.11+)
- **LLMs**: OpenAI (gpt-4-mini), Gemini, Claude, Llama
- **Vector DB**: ChromaDB (semantic search)
- **Cache**: Redis (multi-level caching)
- **Web Scraping**: Firecrawl (markdown extraction)
- **Embeddings**: OpenAI text-embedding-ada-002

## Supported AI Models

| Model    | Provider   | Cost     | Model Name                |
| -------- | ---------- | -------- | ------------------------- |
| ChatGPT  | OpenAI     | Low      | gpt-3.5-turbo             |
| Gemini   | Google     | Very Low | gemini-2.5-flash-lite     |
| Claude   | Anthropic  | Low      | claude-3-5-haiku-20241022 |
| Llama    | Groq       | **FREE** | llama-3.1-8b-instant      |
| Grok     | OpenRouter | Low      | grok-4.1-fast             |
| DeepSeek | OpenRouter | **FREE** | deepseek-chat-v3          |

## Dynamic Industry Classification

No hardcoded industries - LLM generates specific classifications (e.g., "AI-Powered Meal Kit Delivery" not "food_services")

## Caching Strategy

### Slug-Based Caching

| Phase   | Slug Format                                       | TTL  |
| ------- | ------------------------------------------------- | ---- |
| Phase 1 | `company_{hash(url + region)}`                    | 24hr |
| Phase 2 | `visibility_{hash(url + queries + models + llm)}` | 24hr |

**Cache Behavior:**

- Same params → Instant results (10-50ms)
- Different params → New analysis, new slug_id

## Database Setup

### ChromaDB (Vector Store)

```bash
# Runs on port 8001
docker-compose up chromadb -d

# Test connection
curl http://localhost:8001/api/v1/heartbeat
```

**Collections**:

- `companies`: Company profiles with embeddings
- `competitors`: Competitor data with rich metadata

### Redis (Cache)

```bash
# Runs on port 6379
docker-compose up redis -d

# Test connection
redis-cli ping  # Should return PONG
```

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Test Individual Agents

```bash
pytest tests/agents/test_industry_detector.py -v
pytest tests/agents/test_query_generator.py -v
pytest tests/agents/test_ai_model_tester.py -v
pytest tests/agents/test_scorer_analyzer.py -v
```

### Integration Tests

```bash
pytest tests/integration/ -v
```

## Troubleshooting

### ChromaDB Not Connecting

```bash
docker-compose logs chromadb
curl http://localhost:8001/api/v1/heartbeat
```

### Redis Not Connecting

```bash
docker-compose logs redis
redis-cli ping
```

### Low Visibility Score

- Check generated queries are relevant
- Verify API keys are valid
- Review error logs for API failures
- Ensure company name is correct

### Industry Detected as "other"

- Check Firecrawl API key is configured
- Verify website is accessible
- Provide company_description to skip scraping
- Review scraped content in logs

## Configuration

### Environment Variables

```bash
# LLM Provider
INDUSTRY_ANALYSIS_PROVIDER=claude  # claude, gemini, llama, openai
QUERY_GENERATION_PROVIDER=claude

# API Keys (at least one required)
ANTHROPIC_API_KEY=sk-ant-...       # Claude
GROK_API_KEY=gsk_...               # Llama (FREE)
GEMINI_API_KEY=...                 # Gemini
FIRECRAWL_API_KEY=...              # Required

# Databases
CHROMA_HOST=localhost
CHROMA_PORT=8001
REDIS_HOST=localhost
REDIS_PORT=6379
```

See [LLM_PROVIDER_CONFIGURATION.md](./LLM_PROVIDER_CONFIGURATION.md) for details.

## Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

### Logs

Check logs for cache performance:

```
[INFO] Cache HIT for industry analysis: https://...
[INFO] Cache HIT for queries: https://... (20 queries)
[INFO] Cache MISS for complete flow: https://...
```

### Metrics

Track in production:

- Cache hit rates (should be >70%)
- API latency per agent
- Error rates per model
- Cost per request

## Project Structure

```
.
├── agents/                           # LangGraph agents
│   ├── industry_detection_agent/     # Agent 1
│   ├── query_generator_agent/        # Agent 2
│   ├── ai_model_tester_agent/        # Agent 3
│   ├── scorer_analyzer_agent/        # Agent 4
│   └── visibility_orchestrator/      # Orchestrator
├── src/
│   ├── app.py                        # FastAPI app
│   ├── routes/                       # API routes
│   └── controllers/                  # Business logic
├── config/                           # Configuration
├── storage/                          # RAG store
├── models/                           # Data models
├── tests/                            # Tests
└── docs/                             # Documentation
```

## Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System design
- [API_ENDPOINTS.md](./API_ENDPOINTS.md) - API reference
- [LLM_PROVIDER_CONFIGURATION.md](./LLM_PROVIDER_CONFIGURATION.md) - LLM setup
- [AGENTS.md](../AGENTS.md) - Agent workflows
