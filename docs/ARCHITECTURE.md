# AI Visibility Scoring System - Architecture

## Overview

The AI Visibility Scoring System analyzes how frequently companies are mentioned by AI models when users search for industry-related queries. The system uses a two-phase workflow with intelligent caching to provide fast, accurate visibility scores.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                             │
│  Phase 1: Company Analysis                                       │
│  Phase 2: Visibility Scoring                                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI)                         │
│                                                                   │
│  Endpoints:                                                       │
│    • POST /analyze/company        (Phase 1)                      │
│    • POST /analyze/visibility  (Phase 2)                      │
│    • GET  /health                 (Health check)                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                           │
│                                                                   │
│  Two-Phase Workflow:                                             │
│                                                                   │
│  Phase 1: Company Analysis                                       │
│    └─> Industry Detector Agent                                   │
│                                                                   │
│  Phase 2: Complete Flow                                          │
│    ├─> Industry Detector Agent (reuses Phase 1 cache)           │
│    ├─> Query Generator Agent                                     │
│    ├─> AI Model Tester Agent (parallel batches)                 │
│    └─> Scorer Analyzer Agent                                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT LAYER                                 │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Agent 1: Industry Detector                              │   │
│  │  • Scrapes website (Firecrawl)                           │   │
│  │  • Analyzes with LLM (gpt-4-mini)                        │   │
│  │  • Extracts: industry, competitors, summary              │   │
│  │  • Stores in ChromaDB with embeddings                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         │                                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Agent 2: Query Generator                                │   │
│  │  • Uses industry-specific categories                     │   │
│  │  • Generates contextual queries with LLM                 │   │
│  │  • Incorporates company + competitor context             │   │
│  │  • Organizes by category (comparison, selection, etc.)   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         │                                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Agent 3: AI Model Tester                                │   │
│  │  • Tests queries across multiple AI models               │   │
│  │  • Parallel batch processing                             │   │
│  │  • Supports: ChatGPT, Gemini, Claude, Llama, etc.       │   │
│  │  • Caches responses per query+model                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         │                                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Agent 4: Scorer Analyzer                                │   │
│  │  • Hybrid mention detection (exact + semantic)           │   │
│  │  • RAG-based competitor matching                         │   │
│  │  • Calculates visibility score (0-100)                   │   │
│  │  • Generates detailed analysis report                    │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                                 │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   ChromaDB   │  │    Redis     │  │  RAG Store   │          │
│  │  (Vectors)   │  │   (Cache)    │  │ (In-Memory)  │          │
│  │              │  │              │  │              │          │
│  │ • Companies  │  │ • Scrapes    │  │ • Query      │          │
│  │ • Competitors│  │ • Queries    │  │   Templates  │          │
│  │ • Embeddings │  │ • Responses  │  │ • Industry   │          │
│  │              │  │ • Complete   │  │   Categories │          │
│  │              │  │   Flow       │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## Two-Phase Workflow

### Phase 1: Company Analysis

**Purpose**: Analyze company website and extract foundational data

**Why Separate?**

- Higher chance of failure (broken URLs, scraping issues)
- Can be enhanced independently (user-provided competitors)
- Results are reusable across multiple visibility analyses
- Allows user to verify company data before running expensive tests

**Process**:

1. Check cache (24hr TTL)
2. If cache miss:
   - Scrape website with Firecrawl
   - Analyze with LLM (gpt-4-mini)
   - Extract industry, competitors, summary
   - Store in ChromaDB with embeddings
   - Cache results

**Output**:

- Industry classification
- Company name, description, summary
- Competitor list with rich metadata
- Scraped content

### Phase 2: Complete Visibility Flow

**Purpose**: Generate queries, test AI models, calculate visibility score

**Process**:

1. Check complete flow cache (24hr TTL)
2. If cache miss:
   - **Step 1**: Industry detection (reuses Phase 1 cache)
   - **Step 2**: Query generation (cached per company+industry+num_queries)
   - **Step 3**: Parallel batch testing across AI models
   - **Step 4**: Scoring with hybrid mention detection
   - **Step 5**: Aggregate results and cache

**Output**:

- Visibility score (0-100)
- Detailed analysis report
- Per-model breakdown
- Competitor mention tracking
- Sample mentions with context

## Smart Caching Strategy

### Multi-Level Caching

```
Level 1: Industry Analysis Cache (24hr TTL)
  Key: company_url
  Stores: Complete industry analysis
  Benefit: Instant company data on repeated requests

Level 2: Query Cache (24hr TTL)
  Key: company_url + industry + num_queries
  Stores: Generated queries + categories
  Benefit: Reuses queries when only models change

Level 3: Model Response Cache (1hr TTL)
  Key: query + model
  Stores: Individual AI model responses
  Benefit: 70% cost reduction on repeated queries

Level 4: Complete Flow Cache (24hr TTL)
  Key: company_url + num_queries + models + query_weights
  Stores: Final aggregated results
  Benefit: Instant results when all parameters match
```

### Cache Behavior Examples

**Scenario 1: First Request**

```
Input: company_url=hellofresh.com, num_queries=20, models=[chatgpt, gemini]
Result: All cache misses → Full analysis (~30-60s)
Caches: Industry, queries, responses, complete flow
```

**Scenario 2: Same Request Again**

```
Input: Same parameters
Result: Complete flow cache HIT → Instant return (~10-50ms)
Speed: 1000x faster
```

**Scenario 3: Different Models**

```
Input: company_url=hellofresh.com, num_queries=20, models=[claude, llama]
Result:
  - Industry cache HIT (reuse)
  - Query cache HIT (reuse)
  - Response cache MISS (new models)
  - Complete flow cache MISS (different models)
Speed: ~20-40s (faster than first request)
```

**Scenario 4: Different Query Count**

```
Input: company_url=hellofresh.com, num_queries=50, models=[chatgpt, gemini]
Result:
  - Industry cache HIT (reuse)
  - Query cache MISS (different count)
  - Response cache PARTIAL (some queries cached)
  - Complete flow cache MISS (different params)
Speed: ~25-45s
```

## Data Flow

### WorkflowState Structure

The workflow state is passed between agents and accumulates data:

```python
{
    # User Input
    "company_url": str,              # Required
    "company_name": str,             # Optional
    "company_description": str,      # Optional
    "num_queries": int,              # Default: 20
    "models": List[str],             # Default: ["llama", "gemini"]
    "llm_provider": str,             # Default: "gemini"
    "batch_size": int,               # Default: 5
    "query_weights": dict,           # Optional (future)

    # Industry Detector Output
    "industry": str,                 # Classification
    "company_summary": str,          # 3-4 sentence summary
    "scraped_content": str,          # Raw markdown
    "competitors": List[str],        # Competitor names
    "competitors_data": List[Dict],  # Rich metadata

    # Query Generator Output
    "queries": List[str],            # Generated queries
    "query_categories": Dict,        # Organized by category

    # AI Model Tester Output
    "model_responses": Dict,         # {model: [responses]}

    # Scorer Analyzer Output
    "visibility_score": float,       # 0-100
    "analysis_report": Dict,         # Detailed results

    # Error Tracking
    "errors": List[str]              # Non-blocking errors
}
```

### Data Dependencies

```
Industry Detector
    ↓ (provides)
    ├─> industry ──────────────┐
    ├─> company_name ──────────┤
    ├─> company_description ───┤
    ├─> company_summary ───────┤
    ├─> competitors ───────────┤
    └─> competitors_data ──────┤
                               ↓
                        Query Generator
                               ↓ (provides)
                        ├─> queries
                        └─> query_categories
                               ↓
                        AI Model Tester
                               ↓ (provides)
                        └─> model_responses
                               ↓
                        Scorer Analyzer
                               ↓ (provides)
                        ├─> visibility_score
                        └─> analysis_report
```

## Technology Stack

### Backend

- **Framework**: FastAPI (async, high-performance)
- **Orchestration**: Custom workflow engine (inspired by LangGraph)
- **Language**: Python 3.11+

### AI/ML

- **LLMs**: OpenAI (gpt-4-mini), Google (Gemini), Anthropic (Claude), Groq (Llama)
- **Embeddings**: OpenAI text-embedding-ada-002
- **Vector Store**: ChromaDB (semantic search)
- **Web Scraping**: Firecrawl (markdown extraction)

### Storage

- **Cache**: Redis (in-memory, fast)
- **Vector DB**: ChromaDB (embeddings, semantic search)
- **In-Memory**: RAG Store (query templates)

### Infrastructure

- **Containerization**: Docker Compose
- **API Docs**: OpenAPI/Swagger (auto-generated)
- **Monitoring**: Structured logging

## Performance Characteristics

### Latency

**Phase 1: Company Analysis**

- Cold cache: 5-10 seconds
- Warm cache: 10-50ms (instant)

**Phase 2: Complete Flow**

- Cold cache: 30-60 seconds (20 queries × 2 models)
- Warm cache: 10-50ms (instant)
- Partial cache: 15-40 seconds (reuses some data)

### Throughput

**Single Instance**

- Concurrent requests: 10-20 (limited by AI API rate limits)
- Queries per second: 2-5 (with caching)

**Horizontal Scaling**

- Stateless design enables easy scaling
- Shared Redis cache across instances
- ChromaDB can be clustered

### Cost Optimization

**Without Caching**

- 20 queries × 2 models = 40 AI API calls
- Cost: ~$0.10-0.50 per analysis

**With Caching**

- First run: 40 API calls
- Subsequent: ~12 API calls (70% cache hit)
- Cost reduction: 70%

## Security Considerations

### API Keys

- Stored in environment variables
- Never logged or exposed
- Separate keys per service

### Data Privacy

- No PII stored
- Company data cached temporarily (24hr)
- Embeddings are anonymized

### Rate Limiting

- 60 calls/min per AI model
- Prevents API throttling
- Configurable per model

## Scalability

### Horizontal Scaling

- Stateless API servers
- Shared Redis cache
- Load balancer ready

### Vertical Scaling

- Async I/O for concurrent requests
- Batch processing for efficiency
- Memory-efficient streaming

### Database Scaling

- ChromaDB: Can be clustered
- Redis: Can use Redis Cluster
- RAG Store: In-memory, replicated per instance

## Monitoring & Observability

### Logging

- Structured JSON logs
- Log levels: DEBUG, INFO, WARNING, ERROR
- Context: request_id, agent, step

### Metrics

- Cache hit rates (industry, queries, responses, complete flow)
- API latency per agent
- Error rates per model
- Cost tracking per request

### Health Checks

- `/health` endpoint
- Database connectivity checks
- API key validation

## Error Handling

### Non-Blocking Errors

- Agents continue on partial failures
- Errors logged to `state["errors"]`
- Graceful degradation

### Retry Logic

- 2 attempts for scraping
- 2 attempts for AI API calls
- Exponential backoff

### Fallback Strategies

- Keyword matching if AI analysis fails
- Empty responses if model unavailable
- Default industry if classification fails

## Future Enhancements

### Planned Features

1. **User-Provided Competitors**: Allow manual competitor input
2. **Query Category Weights**: Customize query distribution
3. **Historical Tracking**: Track visibility changes over time
4. **Sentiment Analysis**: Analyze tone of mentions
5. **Multi-Language Support**: Generate queries in different languages
6. **A/B Testing**: Compare different query strategies
7. **Real-Time Updates**: WebSocket streaming for live progress
8. **Batch Analysis**: Analyze multiple companies in parallel

### Architecture Improvements

1. **Event-Driven**: Use message queue for async processing
2. **Microservices**: Split agents into separate services
3. **GraphQL API**: More flexible data fetching
4. **Distributed Tracing**: Better observability
5. **Auto-Scaling**: Dynamic resource allocation

## Related Documentation

- [AGENTS.md](../AGENTS.md) - Detailed agent documentation
- [API_ENDPOINTS.md](./API_ENDPOINTS.md) - API reference
- [ORCHESTRATION.md](./ORCHESTRATION.md) - Workflow orchestration details
- Individual agent docs:
  - [AGENT_INDUSTRY_DETECTOR.md](./AGENT_INDUSTRY_DETECTOR.md)
  - [AGENT_QUERY_GENERATOR.md](./AGENT_QUERY_GENERATOR.md)
  - [AGENT_AI_MODEL_TESTER.md](./AGENT_AI_MODEL_TESTER.md)
  - [AGENT_SCORER_ANALYZER.md](./AGENT_SCORER_ANALYZER.md)
