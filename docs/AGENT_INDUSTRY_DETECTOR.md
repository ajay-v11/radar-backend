# Agent 1: Industry Detector (Dynamic)

## Purpose

Analyzes company websites to extract foundational data with **dynamic industry classification** (no hardcoded constraints), generates custom extraction templates, and creates company-specific query categories for the query generator.

## Overview

The Industry Detector uses a **LangGraph-based modular workflow** with parallel scraping. It classifies companies into specific industries (e.g., "AI-Powered Meal Kit Delivery" instead of generic "food_services"), generates custom extraction templates, and creates query categories tailored to each company.

## Process Flow

```
Input: company_url, company_name (optional)
    ↓
Check Cache (24hr TTL)
    ↓
├─> Cache HIT → Return cached data (10-50ms)
└─> Cache MISS → Continue
    ↓
START (parallel scraping)
  ├─> Scrape Company Pages ────┐
  └─> Scrape Competitor Pages ─┴─> Combine Content
    ↓
Classify Industry (Dynamic, No Constraints)
    ↓
Generate Extraction Template (Industry-Specific)
    ↓
Extract Company Data (Using Template)
    ↓
Generate Query Categories (Company-Specific)
    ↓
Enrich Competitors (Optional)
    ↓
Finalize & Store in ChromaDB
    ↓
Cache Results (24hr)
    ↓
Output: Complete company profile + templates
```

## Implementation

**Module**: `agents/industry_detection_agent/`

**Entry Point**: `agents/industry_detection_agent/__init__.py`

**Function Signature**:

```python
def run_industry_detection_workflow(
    company_url: str,
    company_name: str = "",
    company_description: str = "",
    competitor_urls: Dict[str, str] = None,
    llm_provider: str = "openai",
    progress_callback = None
) -> Dict
```

**Parameters**:

- `company_url`: Company website URL (required)
- `company_name`: Optional company name
- `company_description`: Optional company description
- `competitor_urls`: Optional dict of competitor names to URLs
- `llm_provider`: LLM to use ("openai", "gemini", "llama", "claude")
- `progress_callback`: Optional callback for streaming progress

**Returns**: Dictionary with:

- `industry`: Specific industry name (e.g., "AI-Powered Meal Kit Delivery")
- `broad_category`: Broad grouping (e.g., "Technology", "Commerce")
- `industry_description`: 2-3 sentence description of the industry
- `extraction_template`: Dynamic extraction fields for this industry
- `query_categories_template`: Custom query categories for this company
- `company_name`: Extracted or confirmed name
- `company_description`: Brief 1-2 sentence description
- `company_summary`: Comprehensive 3-4 sentence summary
- `competitors`: List of competitor names
- `competitors_data`: Rich metadata (description, products, positioning)
- `product_category`: Specific product/service category
- `market_keywords`: 5-8 search keywords
- `target_audience`: Primary target customers
- `brand_positioning`: Value proposition, differentiators, price tier
- `buyer_intent_signals`: Common questions, decision factors, pain points
- `industry_specific`: Industry-specific fields extracted using template
- `errors`: List of non-blocking errors

## Dynamic Industry Classification

### No Hardcoded Constraints

The agent uses **pure LLM-based classification** without predefined industry lists. The LLM generates:

1. **Specific Industry Name**: Descriptive, 2-5 words (e.g., "B2B SaaS Project Management Tools")
2. **Broad Category**: High-level grouping (e.g., "Technology", "Commerce", "Healthcare")
3. **Industry Description**: 2-3 sentences defining what characterizes this industry

### Examples of Dynamic Classifications

**Good Classifications** (Specific):

- "AI-Powered Meal Kit Delivery"
- "B2B SaaS Project Management Tools"
- "Sustainable Fashion E-commerce"
- "Telehealth Mental Wellness Platform"
- "Crypto Trading & Investment Platform"

**Bad Classifications** (Too Generic):

- "Technology"
- "Food Services"
- "Healthcare"

### Classification Method

**Pure LLM**: No keyword fallback. The LLM analyzes scraped content and generates a specific industry classification based on the company's actual business model, not generic categories.

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

## LangGraph Workflow Nodes

### Node 1: Scrape Company Pages (Parallel)

Scrapes homepage and /about page simultaneously.

### Node 2: Scrape Competitor Pages (Parallel)

Scrapes competitor homepages if URLs provided.

### Node 3: Combine Content

Merges all scraped content for analysis.

### Node 4: Classify Industry

**Pure LLM classification** - generates specific industry name, broad category, and description.

**Prompt**:

```python
"""Classify this company into a SPECIFIC industry.

Examples of GOOD classifications:
- "AI-Powered Meal Kit Delivery"
- "B2B SaaS Project Management Tools"

Examples of BAD classifications (too generic):
- "Technology"
- "Food Services"

Provide:
1. A specific industry name (2-5 words)
2. A broad category for grouping
3. A 2-3 sentence description of what defines this industry
"""
```

### Node 5: Generate Extraction Template

Creates industry-specific extraction fields dynamically.

**Output Example**:

```json
{
  "extract_fields": [
    "menu_customization_options",
    "dietary_filters",
    "delivery_frequency",
    "subscription_tiers",
    "ingredient_sourcing"
  ],
  "competitor_focus": "meal kit services, AI-powered food delivery, subscription meal platforms"
}
```

### Node 6: Extract Company Data

Uses the generated template to extract comprehensive company data.

### Node 7: Generate Query Categories

Creates company-specific query categories with weights for the query generator.

**Output Example**:

```json
{
  "product_comparison": {
    "name": "Product Comparison",
    "weight": 0.25,
    "description": "Users comparing specific products",
    "examples": ["HelloFresh vs Blue Apron", "best meal kits"]
  },
  "dietary_needs": {
    "name": "Dietary Needs",
    "weight": 0.2,
    "description": "Specific dietary requirements",
    "examples": ["keto meal delivery", "vegan meal kits"]
  }
}
```

### Node 8: Enrich Competitors

Enriches competitor data with scraped content (if available).

### Node 9: Finalize

Marks workflow as complete and returns results.

## LLM Configuration

### Model Settings

**Default Model**: gpt-4-mini (configurable via `settings.INDUSTRY_ANALYSIS_MODEL`)
**Temperature**: 0.3 (deterministic) / 0.8 (query generation)
**Max Tokens**: 2000
**Timeout**: 30 seconds

### Supported LLM Providers

1. **OpenAI** (default): gpt-4-mini
2. **Gemini**: gemini-2.5-flash-lite
3. **Llama**: llama-3.1-8b-instant (via Groq)
4. **Claude**: claude-3-haiku-20240307

### Structured Output

Uses Pydantic models for structured LLM output with automatic fallback to JSON parsing if structured output fails.

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

# No keyword fallback - pure LLM approach
if not content:
    errors.append("No content available for analysis")
    state["industry"] = "Unknown"
    state["broad_category"] = "Other"

state["errors"] = errors
return state
```

### No Fallback Strategy

**Removed**: Keyword matching fallback has been removed. The system uses pure LLM-based classification. If LLM fails, the industry is marked as "Unknown" rather than falling back to hardcoded keyword matching.

## Performance

### Latency

- **Cold cache**: 8-15 seconds (parallel scraping + 4 LLM calls)
- **Warm scrape cache**: 4-6 seconds (4 LLM calls only)
- **Full cache**: 10-50ms (instant)

### Parallel Scraping Benefit

With parallel scraping (company + competitors):

- **Sequential**: 10-15 seconds for 3 sites
- **Parallel**: 5-8 seconds for 3 sites (40% faster)

### API Costs

- **Firecrawl**: ~$0.01 per scrape
- **OpenAI (gpt-4-mini)**: ~$0.004 per analysis (4 LLM calls)
  - Industry classification: ~$0.001
  - Template generation: ~$0.001
  - Data extraction: ~$0.001
  - Query categories: ~$0.001
- **Total**: ~$0.014 per cold request
- **With caching**: ~$0.001 per warm request (93% savings)

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
from agents.industry_detection_agent import run_industry_detection_workflow

def test_dynamic_industry_detector():
    result = run_industry_detection_workflow(
        company_url="https://hellofresh.com",
        llm_provider="openai"
    )

    # Dynamic classification (not hardcoded)
    assert "Meal" in result["industry"] or "Food" in result["industry"]
    assert result["broad_category"] in ["Commerce", "Food Services", "Technology"]
    assert result["company_name"] == "HelloFresh"
    assert len(result["competitors"]) > 0
    assert "Blue Apron" in result["competitors"]

    # New dynamic fields
    assert "extract_fields" in result["extraction_template"]
    assert len(result["query_categories_template"]) > 0
    assert result["industry_description"] != ""
```

### Cache Test

```python
def test_caching():
    url = "https://test.com"

    # First request (cache miss)
    start = time.time()
    result1 = run_industry_detection_workflow(company_url=url)
    duration1 = time.time() - start

    # Second request (cache hit)
    start = time.time()
    result2 = run_industry_detection_workflow(company_url=url)
    duration2 = time.time() - start

    assert duration2 < duration1 * 0.1  # 10x faster
    assert result1["industry"] == result2["industry"]
    assert result1["query_categories_template"] == result2["query_categories_template"]
```

## Common Issues

### Issue: Industry detected as "Unknown"

**Cause**: LLM classification failed or no content available
**Solution**:

- Check Firecrawl API key is configured
- Verify website is accessible
- Review scraped content in logs
- Check LLM API key (OpenAI, Gemini, etc.)
- Provide company_description to help classification

### Issue: No query categories generated

**Cause**: LLM failed to generate query categories
**Solution**:

- Check LLM API key and quota
- Review errors in response
- Verify industry classification succeeded
- Try different llm_provider

### Issue: Structured output warning

**Cause**: Pydantic schema incompatible with OpenAI's structured output
**Solution**:

- Ignore warning - system automatically falls back to JSON parsing
- No action needed - fallback works correctly

### Issue: Scraping fails

**Cause**: Website blocks scraping, timeout, or invalid URL
**Solution**:

- Verify URL is correct and accessible
- Check Firecrawl API status
- Try fallback domain (.co.in → .com)
- Provide company_description to skip scraping

## New Features

### Dynamic Industry Classification

- No hardcoded industry lists
- LLM generates specific industry names
- Broad category for grouping
- Industry description for context

### Dynamic Extraction Templates

- Industry-specific fields generated on-the-fly
- Competitor focus tailored to industry
- No manual template maintenance

### Dynamic Query Categories

- Company-specific query categories
- Weighted distribution based on industry
- Used by query generator agent
- No hardcoded category lists

### Parallel Scraping

- Company and competitor pages scraped simultaneously
- 40% faster when competitor URLs provided
- LangGraph fan-out/fan-in pattern

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [ORCHESTRATION.md](./ORCHESTRATION.md) - Workflow orchestration
- [AGENT_QUERY_GENERATOR.md](./AGENT_QUERY_GENERATOR.md) - Next agent in workflow
