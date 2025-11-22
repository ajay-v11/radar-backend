# AI Visibility Scoring System - Documentation

## Overview

The AI Visibility Scoring System analyzes how frequently companies are mentioned by AI models when users search for industry-related queries. The system uses a two-phase workflow with intelligent multi-level caching to provide fast, accurate visibility scores.

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

### Core Documentation

| Document                               | Description                                                 |
| -------------------------------------- | ----------------------------------------------------------- |
| [ARCHITECTURE.md](./ARCHITECTURE.md)   | High-level system architecture, data flow, technology stack |
| [ORCHESTRATION.md](./ORCHESTRATION.md) | Workflow orchestration, agent coordination, flow diagrams   |
| [API_ENDPOINTS.md](./API_ENDPOINTS.md) | Complete API reference with examples                        |

### Agent Documentation

| Agent   | Document                                                   | Purpose                                                      |
| ------- | ---------------------------------------------------------- | ------------------------------------------------------------ |
| Agent 1 | [AGENT_INDUSTRY_DETECTOR.md](./AGENT_INDUSTRY_DETECTOR.md) | Web scraping, industry classification, competitor extraction |
| Agent 2 | [AGENT_QUERY_GENERATOR.md](./AGENT_QUERY_GENERATOR.md)     | Industry-specific query generation with LLM                  |
| Agent 3 | [AGENT_AI_MODEL_TESTER.md](./AGENT_AI_MODEL_TESTER.md)     | Testing queries across multiple AI models                    |
| Agent 4 | [AGENT_SCORER_ANALYZER.md](./AGENT_SCORER_ANALYZER.md)     | Hybrid mention detection and visibility scoring              |

## System Architecture

### Two-Phase Workflow

```
Phase 1: Company Analysis
    └─> Industry Detector Agent
        └─> Output: Company profile with competitors

Phase 2: Complete Visibility Flow
    ├─> Industry Detector (reuses Phase 1 cache)
    ├─> Query Generator
    ├─> AI Model Tester (parallel batches)
    └─> Scorer Analyzer
        └─> Output: Visibility score + detailed report
```

### Key Features

- **Multi-Level Caching**: 4 cache layers (industry, queries, responses, complete flow)
- **Smart Caching**: Granular cache keys for optimal reuse
- **Hybrid Matching**: Exact + semantic mention detection
- **Parallel Processing**: Batch testing for efficiency
- **Streaming Updates**: Real-time progress via SSE

## API Usage

### Phase 1: Analyze Company

```bash
curl -X POST http://localhost:8000/analyze/company \
  -H "Content-Type: application/json" \
  -d '{
    "company_url": "https://hellofresh.com",
    "company_name": "HelloFresh"
  }'
```

**Response (cached)**:

```json
{
  "cached": true,
  "data": {
    "industry": "food_services",
    "company_name": "HelloFresh",
    "competitors": ["Blue Apron", "Home Chef", "Sun Basket"],
    "company_description": "...",
    "company_summary": "..."
  }
}
```

### Phase 2: Complete Visibility Analysis

```bash
curl -X POST http://localhost:8000/analyze/visibility \
  -H "Content-Type: application/json" \
  -d '{
    "company_url": "https://hellofresh.com",
    "num_queries": 20,
    "models": ["chatgpt", "gemini"],
    "llm_provider": "gemini",
    "batch_size": 5
  }'
```

**Response**: Server-Sent Events stream with real-time progress

## Performance

### Latency

| Scenario      | Phase 1 | Phase 2 | Total    |
| ------------- | ------- | ------- | -------- |
| Cold cache    | 5-10s   | 30-60s  | 35-70s   |
| Warm cache    | 10-50ms | 10-50ms | 20-100ms |
| Partial cache | 2-3s    | 15-40s  | 17-43s   |

### Cost Optimization

- **Without caching**: ~$0.10-0.50 per analysis
- **With caching**: ~$0.03-0.15 per analysis (70% savings)

## Technology Stack

- **Backend**: FastAPI (Python 3.11+)
- **LLMs**: OpenAI (gpt-4-mini), Gemini, Claude, Llama
- **Vector DB**: ChromaDB (semantic search)
- **Cache**: Redis (multi-level caching)
- **Web Scraping**: Firecrawl (markdown extraction)
- **Embeddings**: OpenAI text-embedding-ada-002

## Supported AI Models

| Model    | Provider   | Cost     | Notes                 |
| -------- | ---------- | -------- | --------------------- |
| ChatGPT  | OpenAI     | Low      | gpt-3.5-turbo         |
| Gemini   | Google     | Very Low | gemini-2.5-flash-lite |
| Claude   | Anthropic  | Low      | claude-3-haiku        |
| Llama    | Groq       | Free     | llama-3.1-8b-instant  |
| Grok     | OpenRouter | Low      | grok-4.1-fast         |
| DeepSeek | OpenRouter | Free     | deepseek-chat-v3      |

## Supported Industries

1. **technology**: Software, SaaS, AI, cloud, apps, IT services
2. **retail**: E-commerce, stores, fashion, consumer goods
3. **healthcare**: Medical services, pharmaceuticals, biotech
4. **finance**: Banking, fintech, payments, insurance
5. **food_services**: Restaurants, meal delivery, catering
6. **other**: Default fallback category

## Caching Strategy

### Cache Layers

| Layer             | Key                          | TTL  | Purpose                  |
| ----------------- | ---------------------------- | ---- | ------------------------ |
| Industry Analysis | `company_url`                | 24hr | Complete company profile |
| Queries           | `url+industry+count`         | 24hr | Generated queries        |
| Model Responses   | `query+model`                | 1hr  | Individual AI responses  |
| Complete Flow     | `url+queries+models+weights` | 24hr | Final aggregated results |

### Cache Behavior

**Same everything** → Instant cached results (~10-50ms)
**Only models changed** → Reuses queries, re-runs tests
**Only num_queries changed** → Reuses industry, regenerates queries
**Query weights changed** → Re-runs everything (future feature)

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
# AI Models
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...
GROK_API_KEY=...
OPEN_ROUTER_API_KEY=...

# Web Scraping
FIRECRAWL_API_KEY=...

# Databases
CHROMA_HOST=localhost
CHROMA_PORT=8001
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Settings

Edit `config/settings.py` to customize:

```python
# Model selection
INDUSTRY_ANALYSIS_MODEL = "gpt-4-mini"
CHATGPT_MODEL = "gpt-3.5-turbo"
GEMINI_MODEL = "gemini-2.5-flash-lite"

# Query generation
MIN_QUERIES = 20
MAX_QUERIES = 100
DEFAULT_NUM_QUERIES = 20

# Caching
QUERY_CACHE_TTL = 86400  # 24 hours
SCRAPE_CACHE_TTL = 86400  # 24 hours
```

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

## Development

### Project Structure

```
.
├── agents/                    # Agent implementations
│   ├── industry_detector.py
│   ├── query_generator.py
│   ├── ai_model_tester.py
│   └── scorer_analyzer.py
├── src/
│   ├── app.py                # FastAPI application
│   └── routes/
│       ├── health_routes.py
│       └── analysis_routes.py
├── config/
│   ├── settings.py           # Configuration
│   └── database.py           # Database connections
├── utils/                    # Utilities
│   ├── competitor_matcher.py
│   └── vector_store.py
├── storage/
│   └── rag_store.py          # Query templates
├── models/
│   └── schemas.py            # Data models
├── tests/                    # Test suite
└── docs/                     # Documentation
```

### Adding a New AI Model

1. Add API key to `.env`
2. Add model config to `config/settings.py`
3. Implement query function in `agents/ai_model_tester.py`
4. Update model list in documentation

### Adding a New Industry

1. Add industry to `VALID_INDUSTRIES` in `agents/industry_detector.py`
2. Add keywords to `INDUSTRY_KEYWORDS`
3. Add categories to `INDUSTRY_CATEGORIES` in `agents/query_generator.py`
4. Update documentation

## Support

### Common Issues

- [Troubleshooting Guide](./ARCHITECTURE.md#error-handling)
- [Agent-Specific Issues](./AGENT_INDUSTRY_DETECTOR.md#common-issues)
- [API Errors](./API_ENDPOINTS.md#error-handling)

### Documentation

- [Architecture Overview](./ARCHITECTURE.md)
- [Workflow Orchestration](./ORCHESTRATION.md)
- [API Reference](./API_ENDPOINTS.md)
- [Agent Details](./AGENT_INDUSTRY_DETECTOR.md)

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]
