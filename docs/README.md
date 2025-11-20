# AI Visibility Scoring System - Documentation

## Quick Start

1. **Start services**: `docker-compose up -d`

   - ChromaDB on port 8001
   - Redis on port 6379

2. **Run server**: `python run_server.py` or `uvicorn main:app --reload`

   - Databases initialize automatically on startup
   - Check logs for connection status:
     - ✅ ChromaDB: Connected
     - ✅ Redis: Connected
     - ✅ RAGStore initialized with 6 industry templates

3. **API docs**: http://localhost:8000/docs

**Optional**: Test database connections manually with `python scripts/init_databases.py`

### Startup Process

The server automatically:

1. Initializes RAG Store with query templates
2. Tests ChromaDB connection and creates collections
3. Tests Redis connection
4. Logs status of all services
5. Continues even if databases are unavailable (with warnings)

## System Architecture

Four agents work sequentially to analyze company visibility:

```
Input → Industry Detector → Query Generator → AI Model Tester → Scorer Analyzer → Output
```

### Workflow State

The workflow state is passed between agents and accumulates data:

```python
{
    # Input (provided by user)
    "company_url": str,
    "company_name": str,          # Optional
    "company_description": str,   # Optional
    "models": List[str],          # Optional, defaults to ["chatgpt", "gemini"]

    # Added by Industry Detector
    "industry": str,              # Detected category
    "company_summary": str,       # AI-generated summary
    "scraped_content": str,       # Raw website content
    "competitors": List[str],     # Competitor names
    "competitors_data": List[Dict],  # Rich competitor metadata

    # Added by Query Generator
    "queries": List[str],         # 20 generated queries

    # Added by AI Model Tester
    "model_responses": Dict[str, List[str]],  # {model: [responses]}

    # Added by Scorer Analyzer
    "visibility_score": float,    # 0-100 score
    "analysis_report": Dict,      # Detailed results with competitor mentions

    # Error tracking (all agents)
    "errors": List[str]           # Non-blocking errors
}
```

## Agents

### 1. Industry Detector (`agents/industry_detector.py`)

**Purpose**: Classifies companies into industries using Firecrawl scraping + OpenAI GPT-4o-mini analysis

**Industries**: technology, retail, healthcare, finance, food_services, other

**Process**:

1. Scrapes company website with Firecrawl (markdown format)
2. Analyzes content with OpenAI to extract:
   - Company name, description, and summary
   - Industry classification
   - 3-5 main competitors with rich metadata (description, products, positioning)
3. Stores in ChromaDB with embeddings for semantic search

**Features**:

- Redis caching (24hr TTL) - 90% faster on repeated URLs
- Retry logic (2 attempts for scraping and AI analysis)
- Stores company + competitors in ChromaDB with rich embeddings
- Token-optimized (5k chars vs 10k)
- Fallback to keyword matching if AI analysis fails

### 2. Query Generator (`agents/query_generator.py`)

**Purpose**: Generates 20 industry-specific queries from RAG templates

**Process**:

1. Fetch templates from RAG Store by industry
2. Randomly sample 20 unique templates
3. 30% chance to customize with company name for comparison queries

### 3. AI Model Tester (`agents/ai_model_tester.py`)

**Purpose**: Executes queries against AI models

**Supported Models** (cost-optimized):

- ChatGPT (gpt-3.5-turbo)
- Claude (claude-3-haiku)
- Gemini (gemini-2.5-flash-lite)
- Llama (llama-3.1-8b-instant via Groq - FREE)
- Mistral (mistral-7b-instruct via OpenRouter)
- Qwen (qwen-2-7b-instruct via OpenRouter)

**Features**:

- Redis caching for responses (1hr TTL)
- Retry logic (2 attempts per query)
- Rate limiting (60 calls/min per model)
- Graceful error handling
- 70% cost reduction with caching

### 4. Scorer Analyzer (`agents/scorer_analyzer.py`)

**Purpose**: Calculates visibility score and generates report

**Scoring**: `(total_mentions / (queries × models)) × 100`

**Mention Detection** (Hybrid Approach):

1. **Exact String Matching**: Fast, high-precision company name search
2. **Semantic Matching**: RAG-based competitor detection using ChromaDB
   - Catches variations: "meal kit service" → HelloFresh
   - Similarity threshold: 0.70
   - Rich embeddings: name + description + products + positioning

**Features**:

- Hybrid exact + semantic matching for best accuracy
- Competitor mention tracking per model
- Per-model breakdown with competitor context
- Sample mentions with query and competitor info
- Graceful fallback if semantic search unavailable

## Databases

### ChromaDB (Vector Store)

- **Port**: 8001
- **Collections**: companies, competitors
- **Usage**: Semantic competitor matching, company embeddings

### Redis (Cache)

- **Port**: 6379
- **Usage**: Scrape cache (24hr), model responses (1hr), rate limiting

## Configuration

### Environment Variables (`.env`)

```bash
# AI Models (at least OPENAI_API_KEY required)
OPENAI_API_KEY=sk-...           # Required for industry analysis
ANTHROPIC_API_KEY=sk-ant-...    # Optional
GEMINI_API_KEY=...              # Optional
GROK_API_KEY=gsk_...            # Optional (Groq - FREE)
OPEN_ROUTER_API_KEY=sk-or-...   # Optional

# Firecrawl (required for web scraping)
FIRECRAWL_API_KEY=...

# Databases (auto-initialized on startup)
CHROMA_HOST=localhost
CHROMA_PORT=8001
REDIS_HOST=localhost
REDIS_PORT=6379
```

## API Usage

### Analyze Company

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "company_url": "https://hellofresh.com",
    "company_name": "HelloFresh",
    "company_description": "Meal kit delivery service",
    "models": ["chatgpt", "gemini"]
  }'
```

### Response Format

```json
{
  "job_id": "uuid",
  "status": "completed",
  "industry": "food_services",
  "visibility_score": 75.5,
  "total_queries": 20,
  "total_mentions": 30,
  "model_results": {
    "chatgpt": {
      "mentions": 16,
      "mention_rate": 0.8,
      "sample_mentions": ["Query: '...' → mentioned"]
    }
  }
}
```

## Performance

### Without Caching

- 20 queries × 2 models = 40 API calls
- ~30-60 seconds per analysis

### With Caching

- First run: 40 API calls
- Subsequent: ~12 API calls (70% cache hit)
- ~10-20 seconds per analysis
- 70% cost reduction

## Competitor Matching

Uses semantic embeddings (ChromaDB + OpenAI) with similarity threshold: 0.70 to catch variations:

- "German sportswear brand" → Adidas
- "premium meal kits" → Blue Apron
- "budget delivery" → EveryPlate
- "meal kit service" → HelloFresh

**Rich embeddings** include: name, description, products, positioning

**How it works**:

1. Industry Detector extracts competitors from website analysis
2. Competitors stored in ChromaDB with rich metadata embeddings
3. Scorer Analyzer uses semantic search to detect mentions in AI responses
4. Tracks which competitors appear alongside company in responses

## Testing

```bash
# Unit tests
python -m pytest tests/

# Integration test
python test_complete_integration.py

# RAG competitor matching
python test_rag_competitor_matching.py
```

## Troubleshooting

**ChromaDB not connecting?**

```bash
docker-compose logs chromadb
curl http://localhost:8001/api/v1/heartbeat
```

**Redis not connecting?**

```bash
redis-cli ping  # Should return PONG
```

**Low visibility score?**

- Check generated queries are relevant
- Verify API keys are valid
- Review error logs for API failures

**Industry detected as "other"?**

- Check Firecrawl API key is configured
- Verify website is accessible and has content
- Check logs for scraping errors
- System falls back to keyword matching if scraping fails

---

## System Features Summary

### Performance Optimizations

- **Redis Caching**: 70% cost reduction on model responses (1hr TTL)
- **Scrape Caching**: 90% faster on repeated URLs (24hr TTL)
- **Rate Limiting**: 60 calls/min per model to avoid throttling
- **Token Optimization**: 5k char limit on scraped content

### Accuracy Improvements

- **Hybrid Mention Detection**: Exact + semantic matching
- **Rich Embeddings**: Competitors stored with description, products, positioning
- **Semantic Search**: Catches variations like "meal kit service" → HelloFresh
- **Competitor Tracking**: Monitors which competitors appear in responses

### Reliability Features

- **Automatic Retry**: 2 attempts for scraping and API calls
- **Graceful Degradation**: Falls back to keyword matching if AI fails
- **Non-Blocking Errors**: Workflow continues even with partial failures
- **Auto-Initialization**: Databases initialize on server startup

### Cost Efficiency

- **Optimized Models**: gpt-3.5-turbo, claude-haiku, gemini-flash-lite
- **Free Options**: Llama via Groq (free tier)
- **Caching Strategy**: Reduces API calls by 70%
- **Token Limits**: 500 tokens per response

### Extensibility

- **Modular Agents**: Easy to add new agents or modify existing ones
- **Pluggable Models**: Simple to add new AI models
- **Industry Templates**: 25+ queries per industry, easy to extend
- **Vector Store**: Ready for advanced semantic features
