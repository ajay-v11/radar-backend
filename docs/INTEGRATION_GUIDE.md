# Agent Integration Guide

## Overview

This guide explains how the Industry Detector and Query Generator agents are integrated to work together efficiently, avoiding redundant API calls and maximizing cache utilization.

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 1: Industry Detector                     │
│                                                                   │
│  Input:                                                           │
│    - company_url (required)                                       │
│    - company_name (optional)                                      │
│    - company_description (optional)                               │
│                                                                   │
│  Process:                                                         │
│    1. Check Redis cache for scraped content (24hr TTL)           │
│    2. If cache miss: Scrape website with Firecrawl               │
│    3. Analyze content with OpenAI (gpt-4o-mini)                  │
│    4. Store in ChromaDB (company + competitors)                  │
│    5. Cache scrape result in Redis                               │
│                                                                   │
│  Output:                                                          │
│    - industry (classification)                                    │
│    - company_name (extracted/confirmed)                           │
│    - company_description (1-2 sentences)                          │
│    - company_summary (3-4 sentences)                              │
│    - competitors (list of names)                                  │
│    - competitors_data (rich metadata)                             │
│    - scraped_content (raw markdown)                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    Data flows to next agent
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 2: Query Generator                        │
│                                                                   │
│  Input (from Industry Detector):                                 │
│    - company_url                                                  │
│    - industry                                                     │
│    - company_name                                                 │
│    - company_description                                          │
│    - company_summary                                              │
│    - competitors                                                  │
│    - num_queries (20-100)                                         │
│                                                                   │
│  Process:                                                         │
│    1. Check Redis cache for queries (24hr TTL)                   │
│    2. If cache miss: Generate queries with OpenAI                │
│       - Uses industry-specific categories                         │
│       - Incorporates company context                              │
│       - Includes competitor names                                 │
│    3. Cache query results in Redis                               │
│                                                                   │
│  Output:                                                          │
│    - queries (list of search queries)                             │
│    - query_categories (organized by category)                     │
│    - All previous fields preserved                                │
└─────────────────────────────────────────────────────────────────┘
```

## Key Integration Points

### 1. Data Reuse

The Query Generator **reuses** all data from the Industry Detector:

- **industry**: Determines which query categories to use
- **company_name**: Personalizes queries (e.g., "HelloFresh vs Blue Apron")
- **company_description**: Provides context for query generation
- **company_summary**: Enriches AI prompts for better queries
- **competitors**: Enables comparison queries with real competitor names

**No redundant scraping or analysis** - all data flows through the workflow state.

### 2. Two-Level Caching

#### Level 1: Industry Detector Cache (Redis)

- **Key**: `scrape:{md5(company_url)}`
- **TTL**: 24 hours
- **Benefit**: 90% faster on repeated URLs
- **Stores**: Raw scraped content

#### Level 2: Query Generator Cache (Redis)

- **Key**: `queries:{md5(company_url:num_queries)}`
- **TTL**: 24 hours
- **Benefit**: Instant query retrieval on repeated requests
- **Stores**: Generated queries + categories

### 3. Vector Storage

Both agents contribute to ChromaDB:

**Industry Detector stores:**

- Company profiles (name, URL, description, industry)
- Competitor data with rich embeddings (name, description, products, positioning)

**Query Generator uses:**

- Industry classification for category selection
- Competitor names for comparison queries

## Usage Example

### Basic Flow

```python
from agents.industry_detector import detect_industry
from agents.query_generator import generate_queries
from models.schemas import WorkflowState

# Step 1: Initialize state
state: WorkflowState = {
    "company_url": "https://www.hellofresh.com",
    "company_name": "",  # Optional - will be extracted
    "company_description": "",  # Optional - will be extracted
    "errors": [],
    "num_queries": 50
}

# Step 2: Run industry detector
state = detect_industry(state)

# At this point, state contains:
# - industry: "food_services"
# - company_name: "HelloFresh"
# - company_description: "Meal kit delivery service..."
# - company_summary: "HelloFresh specializes in..."
# - competitors: ["Blue Apron", "Home Chef", ...]
# - scraped_content: "# HelloFresh\n\n..."

# Step 3: Run query generator (uses data from step 2)
state = generate_queries(state)

# Now state also contains:
# - queries: ["HelloFresh vs Blue Apron", ...]
# - query_categories: {"comparison": {...}, ...}

print(f"Industry: {state['industry']}")
print(f"Generated {len(state['queries'])} queries")
print(f"Sample: {state['queries'][0]}")
```

### With Full Workflow (LangGraph)

```python
from graph_orchestrator import run_analysis

result = run_analysis(
    company_url="https://www.hellofresh.com",
    models=["chatgpt", "gemini"]
)

# Automatically runs:
# 1. Industry Detector
# 2. Query Generator
# 3. AI Model Tester
# 4. Scorer Analyzer

print(f"Visibility Score: {result['visibility_score']}%")
```

## Performance Characteristics

### First Run (Cold Cache)

```
Industry Detector:
  - Firecrawl scrape: ~2-5 seconds
  - OpenAI analysis: ~1-2 seconds
  - Vector storage: ~0.5 seconds
  Total: ~4-8 seconds

Query Generator:
  - OpenAI generation (5 categories): ~5-10 seconds
  - Cache storage: ~0.1 seconds
  Total: ~5-10 seconds

Combined: ~9-18 seconds
```

### Second Run (Warm Cache)

```
Industry Detector:
  - Redis cache hit: ~0.01 seconds
  - OpenAI analysis: ~1-2 seconds (still needed for fresh analysis)
  - Vector storage: ~0.5 seconds
  Total: ~2-3 seconds

Query Generator:
  - Redis cache hit: ~0.01 seconds
  Total: ~0.01 seconds

Combined: ~2-3 seconds (70-85% faster)
```

### Third Run (Full Cache)

```
If same URL + same num_queries:
  - Industry Detector: ~2-3 seconds (scrape cached)
  - Query Generator: ~0.01 seconds (queries cached)
  Total: ~2-3 seconds
```

## Cache Invalidation

### When to Clear Cache

1. **Company website updated**: Clear scrape cache

   ```python
   from config.database import get_redis_client
   import hashlib

   redis = get_redis_client()
   cache_key = f"scrape:{hashlib.md5(url.encode()).hexdigest()}"
   redis.delete(cache_key)
   ```

2. **Query strategy changed**: Clear query cache

   ```python
   cache_key = f"queries:{hashlib.md5(f'{url}:{num_queries}'.encode()).hexdigest()}"
   redis.delete(cache_key)
   ```

3. **Full reset**: Clear all caches
   ```python
   redis.flushdb()  # Warning: Clears entire Redis database
   ```

### Automatic Expiration

Both caches automatically expire after 24 hours (TTL=86400 seconds).

## Testing

Run the integration test suite:

```bash
# Run all integration tests
python tests/clients/test_integrated_flow.py

# Or with pytest
pytest tests/clients/test_integrated_flow.py -v
```

### Test Coverage

The test suite validates:

1. **Full Flow**: Complete pipeline from URL to queries
2. **Cache Efficiency**: Second run uses cached data
3. **Different Industries**: Works across all industry types
4. **Error Handling**: Graceful degradation on failures
5. **Data Preservation**: All fields flow correctly between agents

## Common Issues

### Issue 1: Queries are generic

**Cause**: Industry detector didn't extract company data properly

**Solution**: Check that `company_name`, `company_description`, and `competitors` are populated after industry detection

```python
state = detect_industry(state)
assert state.get("company_name"), "Company name not extracted"
assert state.get("industry") != "other", "Industry not classified"
```

### Issue 2: Cache not working

**Cause**: Redis connection issues or different URLs

**Solution**: Verify Redis is running and URLs are normalized

```python
from config.database import get_redis_client

redis = get_redis_client()
redis.ping()  # Should return True
```

### Issue 3: Slow performance

**Cause**: Cache misses or cold start

**Solution**: Check cache hit rates in logs

```bash
# Look for these log messages:
# "Cache HIT for scrape: ..." (good)
# "Cache MISS for scrape: ..." (expected on first run)
```

## Best Practices

1. **Always run Industry Detector first**: Query Generator depends on its output

2. **Use consistent URLs**: Normalize URLs to maximize cache hits

   ```python
   url = url.rstrip('/')  # Remove trailing slash
   url = url.lower()  # Normalize case
   ```

3. **Monitor cache hit rates**: Track performance in production

   ```python
   # Add metrics to your monitoring system
   cache_hit_rate = cache_hits / (cache_hits + cache_misses)
   ```

4. **Set appropriate num_queries**: Balance quality vs. speed

   - 20 queries: Fast, good for testing
   - 50 queries: Balanced, recommended for production
   - 100 queries: Comprehensive, slower

5. **Handle errors gracefully**: Both agents continue on partial failures
   ```python
   if state.get("errors"):
       logger.warning(f"Errors: {state['errors']}")
   # Workflow continues with available data
   ```

## Architecture Benefits

### ✅ Efficiency

- No redundant API calls
- Two-level caching (scrape + queries)
- 70-85% faster on repeated requests

### ✅ Data Quality

- Rich company context for query generation
- Real competitor names in queries
- Industry-specific query categories

### ✅ Maintainability

- Clear separation of concerns
- Each agent has single responsibility
- Easy to test independently

### ✅ Scalability

- Caching reduces API costs
- Vector storage enables future features
- Stateless design for horizontal scaling

## Future Enhancements

1. **Smarter Cache Invalidation**: Detect website changes automatically
2. **Query Personalization**: Use historical data to improve queries
3. **Competitor Analysis**: Leverage stored competitor data for insights
4. **Multi-language Support**: Generate queries in different languages
5. **A/B Testing**: Compare different query generation strategies

## Related Documentation

- [AGENTS.md](../AGENTS.md) - Detailed agent documentation
- [README.md](../README.md) - Project overview
- [API Documentation](./README.md) - API endpoints and usage
