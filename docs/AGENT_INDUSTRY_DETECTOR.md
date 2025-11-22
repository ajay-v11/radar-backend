# Agent 1: Industry Detector

## Purpose

Analyzes company websites to extract foundational data: industry classification, company information, and competitor identification.

## Overview

The Industry Detector is the first agent in the workflow. It scrapes company websites using Firecrawl, analyzes content with LLM (gpt-4-mini), and stores rich embeddings in ChromaDB for semantic search.

## Process Flow

```
Input: company_url, company_name (optional)
    ↓
Check Cache (24hr TTL)
    ↓
├─> Cache HIT → Return cached data (10-50ms)
└─> Cache MISS → Continue
    ↓
Scrape Website (Firecrawl)
    ↓
Analyze with LLM (gpt-4-mini)
    ↓
Extract:
  • Industry classification
  • Company name, description, summary
  • 3-5 competitors with rich metadata
    ↓
Store in ChromaDB (embeddings)
    ↓
Cache Results (24hr)
    ↓
Output: Complete company profile
```

## Implementation

**File**: `agents/industry_detector.py`

**Function Signature**:

```python
def detect_industry(
    state: WorkflowState,
    llm_provider: str = "openai"
) -> WorkflowState
```

**Parameters**:

- `state`: WorkflowState with `company_url` and optional `company_name`
- `llm_provider`: LLM to use ("openai", "gemini", "llama", "claude")

**Returns**: Updated WorkflowState with:

- `industry`: Classification (technology, retail, healthcare, finance, food_services, other)
- `company_name`: Extracted or confirmed name
- `company_description`: Brief 1-2 sentence description
- `company_summary`: Comprehensive 3-4 sentence summary
- `competitors`: List of competitor names
- `competitors_data`: Rich metadata (description, products, positioning)
- `scraped_content`: Raw markdown content
- `errors`: List of non-blocking errors

## Industry Classifications

### Supported Industries

1. **technology**: Software, SaaS, AI, cloud, apps, IT services, hardware
2. **retail**: E-commerce, stores, fashion, consumer goods, marketplaces
3. **healthcare**: Medical services, pharmaceuticals, biotech, telemedicine
4. **finance**: Banking, fintech, payments, insurance, investment
5. **food_services**: Restaurants, meal delivery, catering, meal kits
6. **other**: Default fallback category

### Classification Method

**Primary**: LLM analysis of scraped content
**Fallback**: Keyword matching if LLM fails

## Web Scraping

### Firecrawl Integration

**Tool**: Firecrawl API
**Output**: Markdown format
**Limit**: 5000 characters (token optimization)
**Strategies**: 3 fallback strategies with increasing timeouts

**Strategy 1**: Standard scrape with main content only

```python
{
    "formats": ["markdown"],
    "only_main_content": True,
    "timeout": 30000
}
```

**Strategy 2**: Full content scrape

```python
{
    "formats": ["markdown"],
    "only_main_content": False,
    "timeout": 30000
}
```

**Strategy 3**: Extended timeout

```python
{
    "formats": ["markdown"],
    "only_main_content": True,
    "timeout": 60000
}
```

**Fallback**: Regional domain fallback (.co.in → .com)

### Caching

**Cache Key**: `scrape:{md5(company_url)}`
**TTL**: 24 hours
**Storage**: Redis
**Benefit**: 90% faster on repeated URLs

## LLM Analysis

### Model Configuration

**Default Model**: gpt-4-mini (configurable via `settings.INDUSTRY_ANALYSIS_MODEL`)
**Temperature**: 0.3 (deterministic)
**Max Tokens**: 1000
**Timeout**: 30 seconds

### Supported LLM Providers

1. **OpenAI** (default): gpt-4-mini
2. **Gemini**: gemini-2.5-flash-lite
3. **Llama**: llama-3.1-8b-instant (via Groq)
4. **Claude**: claude-3-haiku-20240307

### Analysis Prompt

```python
prompt = f"""Analyze the following website content and extract key information.

Website URL: {company_url}
Provided Company Name: {provided_name}

Website Content:
{scraped_content}

Provide JSON response with:
{{
    "company_name": "Official company name",
    "company_description": "Brief 1-2 sentence description",
    "company_summary": "Comprehensive 3-4 sentence summary",
    "industry": "One of: technology, retail, healthcare, finance, food_services, other",
    "competitors": [
        {{
            "name": "Competitor name",
            "description": "What they do",
            "products": "Main products/services",
            "positioning": "Market position (premium, budget, innovative)"
        }}
    ]
}}
"""
```

### Retry Logic

**Attempts**: 2
**Delay**: 1 second between retries
**Fallback**: Keyword matching if all attempts fail

## Competitor Extraction

### Rich Metadata

Each competitor includes:

- **name**: Company name
- **description**: Brief 1-sentence description
- **products**: Main products/services (comma-separated)
- **positioning**: Market position (premium, budget, innovative, etc.)

### Example Output

```json
{
  "competitors": ["Blue Apron", "Home Chef", "Sun Basket"],
  "competitors_data": [
    {
      "name": "Blue Apron",
      "description": "Meal kit delivery with chef-designed recipes",
      "products": "meal kits, wine subscriptions",
      "positioning": "premium quality ingredients"
    },
    {
      "name": "Home Chef",
      "description": "Customizable meal kit service",
      "products": "meal kits, oven-ready meals",
      "positioning": "flexible and convenient"
    }
  ]
}
```

## Vector Storage

### ChromaDB Collections

**Collection 1: companies**

- Stores company profiles
- Embeddings of scraped content
- Metadata: name, URL, industry, description

**Collection 2: competitors**

- Stores competitor data
- Rich embeddings: name + description + products + positioning
- Enables semantic matching in Scorer Analyzer

### Storage Process

```python
# Store company profile
vector_store.store_company(
    company_name=company_name,
    company_url=company_url,
    scraped_content=scraped_content,
    industry=industry,
    description=description,
    metadata={"summary": company_summary}
)

# Store competitors with rich embeddings
competitor_matcher.store_competitors(
    company_name=company_name,
    competitors=competitors,
    industry=industry,
    descriptions={comp: data["description"] for comp, data in competitors_data},
    metadata_extra={comp: {
        "products": data["products"],
        "positioning": data["positioning"]
    } for comp, data in competitors_data}
)
```

## Caching Strategy

### Two-Level Caching

**Level 1: Scrape Cache**

- Key: `scrape:{md5(company_url)}`
- TTL: 24 hours
- Stores: Raw scraped content
- Benefit: Avoids redundant Firecrawl API calls

**Level 2: Industry Analysis Cache**

- Key: `industry_analysis:{md5(company_url)}`
- TTL: 24 hours
- Stores: Complete analysis result
- Benefit: Instant return on repeated requests

### Cache Behavior

**First Request**:

```
Scrape cache MISS → Scrape website (2-5s)
Analysis cache MISS → Analyze with LLM (1-2s)
Total: ~4-8 seconds
```

**Second Request**:

```
Analysis cache HIT → Return instantly (10-50ms)
Total: ~10-50ms (100x faster)
```

## Error Handling

### Non-Blocking Errors

Errors are logged but don't stop the workflow:

```python
errors = []

try:
    content = scrape_website(url)
except Exception as e:
    errors.append(f"Scraping failed: {e}")
    content = ""  # Continue with empty content

# Fallback to keyword matching
if not content:
    industry = fallback_keyword_detection(company_name, description)

state["errors"] = errors
return state
```

### Fallback Strategy

If LLM analysis fails, uses keyword matching:

```python
INDUSTRY_KEYWORDS = {
    "technology": ["software", "saas", "cloud", "ai", ...],
    "retail": ["retail", "store", "ecommerce", ...],
    "healthcare": ["health", "medical", "hospital", ...],
    ...
}

def fallback_keyword_detection(company_name, text):
    combined_text = f"{company_name} {text}".lower()

    # Score each industry by keyword matches
    scores = {}
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined_text)
        scores[industry] = score

    # Return industry with highest score
    return max(scores, key=scores.get) if max(scores.values()) > 0 else "other"
```

## Performance

### Latency

- **Cold cache**: 4-8 seconds (scraping + analysis)
- **Warm scrape cache**: 2-3 seconds (analysis only)
- **Full cache**: 10-50ms (instant)

### API Costs

- **Firecrawl**: ~$0.01 per scrape
- **OpenAI (gpt-4-mini)**: ~$0.001 per analysis
- **Total**: ~$0.011 per cold request
- **With caching**: ~$0.001 per warm request (90% savings)

## Configuration

### Environment Variables

```bash
# Required
FIRECRAWL_API_KEY=...
OPENAI_API_KEY=...

# Optional (for alternative LLM providers)
GEMINI_API_KEY=...
GROK_API_KEY=...
ANTHROPIC_API_KEY=...

# Database
CHROMA_HOST=localhost
CHROMA_PORT=8001
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Settings

```python
# config/settings.py
INDUSTRY_ANALYSIS_MODEL = "gpt-4-mini"
MAX_SCRAPED_CONTENT_LENGTH = 5000
SCRAPE_CACHE_TTL = 86400  # 24 hours
RETRY_MAX_ATTEMPTS = 2
RETRY_DELAY = 1.0
```

## Testing

### Unit Test

```python
def test_industry_detector():
    state = {
        "company_url": "https://hellofresh.com",
        "company_name": "",
        "errors": []
    }

    result = detect_industry(state)

    assert result["industry"] == "food_services"
    assert result["company_name"] == "HelloFresh"
    assert len(result["competitors"]) > 0
    assert "Blue Apron" in result["competitors"]
```

### Cache Test

```python
def test_caching():
    url = "https://test.com"

    # First request (cache miss)
    start = time.time()
    result1 = detect_industry({"company_url": url, "errors": []})
    duration1 = time.time() - start

    # Second request (cache hit)
    start = time.time()
    result2 = detect_industry({"company_url": url, "errors": []})
    duration2 = time.time() - start

    assert duration2 < duration1 * 0.1  # 10x faster
    assert result1["industry"] == result2["industry"]
```

## Common Issues

### Issue: Industry detected as "other"

**Cause**: Website content doesn't match keyword patterns or LLM failed
**Solution**:

- Check Firecrawl API key is configured
- Verify website is accessible
- Review scraped content in logs
- Provide more detailed company_description

### Issue: No competitors found

**Cause**: LLM couldn't identify competitors from website content
**Solution**:

- Future enhancement: Allow user-provided competitor list
- Check if website mentions competitors
- Review LLM analysis in logs

### Issue: Scraping fails

**Cause**: Website blocks scraping, timeout, or invalid URL
**Solution**:

- Verify URL is correct and accessible
- Check Firecrawl API status
- Try fallback domain (.co.in → .com)
- Provide company_description to skip scraping

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [ORCHESTRATION.md](./ORCHESTRATION.md) - Workflow orchestration
- [AGENT_QUERY_GENERATOR.md](./AGENT_QUERY_GENERATOR.md) - Next agent in workflow
