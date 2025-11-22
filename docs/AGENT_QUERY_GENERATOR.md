# Agent 2: Query Generator

## Purpose

Generates industry-specific search queries that represent real user intent when searching for products/services in a given industry.

## Overview

The Query Generator creates 20-100 contextual queries organized by category (comparison, product selection, how-to, etc.). It uses LLM to generate realistic queries that incorporate company context and competitor names.

## Process Flow

```
Input: industry, company_name, competitors, num_queries
    ↓
Check Cache (24hr TTL)
    ↓
├─> Cache HIT → Return cached queries (10-50ms)
└─> Cache MISS → Continue
    ↓
Select Industry Categories (weighted)
    ↓
For each category:
  ├─> Calculate query count (weighted distribution)
  ├─> Generate queries with LLM
  └─> Incorporate company + competitor context
    ↓
Deduplicate queries
    ↓
Cache Results (24hr)
    ↓
Output: queries + query_categories
```

## Implementation

**File**: `agents/query_generator.py`

**Function Signature**:

```python
def generate_queries(
    state: WorkflowState,
    num_queries: int = None,
    llm_provider: str = "openai"
) -> WorkflowState
```

**Parameters**:

- `state`: WorkflowState with industry, company_name, competitors
- `num_queries`: Number of queries to generate (20-100, default 20)
- `llm_provider`: LLM to use ("openai", "gemini", "llama", "claude")

**Returns**: Updated WorkflowState with:

- `queries`: List of search query strings
- `query_categories`: Dict mapping category keys to query lists
- All previous fields preserved

## Industry Categories

### Food Services

```python
{
    "comparison": {
        "weight": 0.30,  # 30% of queries
        "description": "Direct brand comparisons",
        "examples": ["HelloFresh vs Blue Apron", "Factor vs Home Chef pricing"]
    },
    "product_selection": {
        "weight": 0.25,
        "description": "Finding meal delivery services",
        "examples": ["best meal kits for families", "top organic meal delivery"]
    },
    "dietary_needs": {
        "weight": 0.20,
        "description": "Dietary requirements",
        "examples": ["keto meal delivery", "vegan meal kits"]
    },
    "best_of": {
        "weight": 0.15,
        "description": "Ranked lists",
        "examples": ["top 10 meal delivery 2025", "best meal kits ranked"]
    },
    "how_to": {
        "weight": 0.10,
        "description": "Educational queries",
        "examples": ["how meal kits work", "how to cancel subscription"]
    }
}
```

### Technology

```python
{
    "comparison": {"weight": 0.35},
    "use_cases": {"weight": 0.25},
    "integration": {"weight": 0.20},
    "best_of": {"weight": 0.12},
    "pricing": {"weight": 0.08}
}
```

### Retail

```python
{
    "comparison": {"weight": 0.28},
    "product_selection": {"weight": 0.30},
    "reviews": {"weight": 0.20},
    "best_of": {"weight": 0.15},
    "deals": {"weight": 0.07}
}
```

### Healthcare

```python
{
    "comparison": {"weight": 0.25},
    "symptoms": {"weight": 0.30},
    "provider_selection": {"weight": 0.20},
    "how_to": {"weight": 0.15},
    "best_of": {"weight": 0.10}
}
```

### Finance

```python
{
    "comparison": {"weight": 0.35},
    "product_selection": {"weight": 0.25},
    "how_to": {"weight": 0.20},
    "rates": {"weight": 0.12},
    "best_of": {"weight": 0.08}
}
```

### Other (Default)

```python
{
    "comparison": {"weight": 0.30},
    "product_selection": {"weight": 0.25},
    "problem_solving": {"weight": 0.20},
    "best_of": {"weight": 0.15},
    "how_to": {"weight": 0.10}
}
```

## Query Generation

### LLM Configuration

**Default Model**: gpt-4-mini
**Temperature**: 0.8 (creative)
**Max Tokens**: 1500 per category
**Timeout**: 30 seconds

### Generation Prompt

```python
prompt = f"""Generate {num_queries} search queries for the "{category_name}" category.

Category Description: {category_description}
Category Examples: {examples}

Company Context:
Industry: {industry}
Company: {company_name}
Description: {company_description}
Main Competitors: {', '.join(competitors[:5])}

Requirements:
1. Generate exactly {num_queries} unique queries
2. Queries should represent real user search intent in 2025
3. Make queries specific to the {industry} industry
4. For comparison queries, include competitor names when relevant
5. Use natural language that real users would type
6. Vary query length and style (questions, phrases, statements)
7. Focus on buyer intent and decision-making queries

Return ONLY a JSON array of query strings:
["query 1", "query 2", ...]
```

### Example Output

For HelloFresh (food_services, 20 queries):

**Comparison (6 queries)**:

- "HelloFresh vs Blue Apron meal quality comparison"
- "Factor vs Home Chef pricing plans 2025"
- "HelloFresh or Sun Basket for families"
- "Compare HelloFresh to EveryPlate cost"
- "HelloFresh vs Home Chef which is better"
- "Meal kit comparison HelloFresh Blue Apron Factor"

**Product Selection (5 queries)**:

- "Best meal kits for families with kids"
- "Top rated meal delivery services 2025"
- "Healthy meal kit options"
- "Affordable meal delivery subscriptions"
- "Organic meal kit services"

**Dietary Needs (4 queries)**:

- "Keto meal delivery services"
- "Vegan meal kit options"
- "Gluten-free meal delivery"
- "Low carb meal kits"

**Best-of Lists (3 queries)**:

- "Top 10 meal delivery services 2025"
- "Best meal kits ranked by quality"
- "Highest rated meal delivery companies"

**How-to (2 queries)**:

- "How do meal kit subscriptions work"
- "How to cancel HelloFresh subscription"

## Weighted Distribution

### Algorithm

Distributes queries across categories without rounding errors:

```python
def _distribute_queries(num_queries: int, categories: Dict) -> Dict[str, int]:
    distribution = {}
    remaining = num_queries

    # Sort by weight descending
    sorted_categories = sorted(categories.items(), key=lambda x: x[1]["weight"], reverse=True)

    for i, (category_key, category_info) in enumerate(sorted_categories):
        if i == len(sorted_categories) - 1:
            # Last category gets all remaining (avoids rounding errors)
            distribution[category_key] = remaining
        else:
            count = int(num_queries * category_info["weight"])
            distribution[category_key] = count
            remaining -= count

    return distribution
```

### Example Distribution

For 50 queries in food_services:

- comparison: 15 queries (30%)
- product_selection: 12 queries (25%)
- dietary_needs: 10 queries (20%)
- best_of: 8 queries (15%)
- how_to: 5 queries (10%)
- **Total**: 50 queries (no rounding errors)

## Deduplication

Removes duplicate queries while preserving order:

```python
def _deduplicate_queries(queries: List[str]) -> List[str]:
    seen = set()
    unique = []
    for q in queries:
        q_lower = q.lower().strip()
        if q_lower and q_lower not in seen:
            seen.add(q_lower)
            unique.append(q.strip())
    return unique
```

## Caching

### Cache Key

```python
def _get_query_cache_key(company_url: str, industry: str, num_queries: int) -> str:
    normalized_url = company_url.rstrip('/')
    key = f"{normalized_url}:{industry}:{num_queries}"
    return f"queries:{hashlib.sha256(key.encode()).hexdigest()}"
```

### Cache Behavior

**First Request**:

```
Cache MISS → Generate queries with LLM (5-10s)
Cache results for 24 hours
```

**Second Request (same params)**:

```
Cache HIT → Return instantly (10-50ms)
```

**Third Request (different num_queries)**:

```
Cache MISS → Generate new queries (different cache key)
```

## Performance

### Latency

- **Cold cache**: 5-10 seconds (5 LLM calls, one per category)
- **Warm cache**: 10-50ms (instant)

### API Costs

- **OpenAI (gpt-4-mini)**: ~$0.005 per category
- **Total (5 categories)**: ~$0.025 per cold request
- **With caching**: $0 per warm request

## Configuration

### Settings

```python
# config/settings.py
MIN_QUERIES = 20
MAX_QUERIES = 100
DEFAULT_NUM_QUERIES = 20
QUERY_CACHE_TTL = 86400  # 24 hours
OPENAI_TEMPERATURE = 0.8
MAX_TOKENS_PER_CATEGORY = 1500
MAX_COMPETITORS_IN_CONTEXT = 5
```

## Error Handling

### JSON Parsing

Handles various LLM response formats:

````python
# Strip markdown code blocks
if result_text.startswith("```"):
    result_text = result_text.strip()
    if result_text.startswith("```json"):
        result_text = result_text[7:]
    elif result_text.startswith("```"):
        result_text = result_text[3:]
    if result_text.endswith("```"):
        result_text = result_text[:-3]
    result_text = result_text.strip()

# Parse JSON
result = json.loads(result_text)

# Handle dict or list responses
if isinstance(result, dict):
    queries = result.get("queries") or result.get("items") or []
elif isinstance(result, list):
    queries = result
````

### Validation

Filters invalid queries:

```python
cleaned_queries = []
for q in queries:
    if isinstance(q, str) and q.strip():
        cleaned_queries.append(q.strip())
    else:
        logger.warning(f"Skipping invalid query: {q}")
```

## Testing

### Unit Test

```python
def test_query_generator():
    state = {
        "company_url": "https://hellofresh.com",
        "industry": "food_services",
        "company_name": "HelloFresh",
        "competitors": ["Blue Apron", "Home Chef"],
        "num_queries": 20,
        "errors": []
    }

    result = generate_queries(state)

    assert len(result["queries"]) == 20
    assert "query_categories" in result
    assert len(result["query_categories"]) == 5  # 5 categories
```

### Cache Test

```python
def test_query_caching():
    state = {
        "company_url": "https://test.com",
        "industry": "technology",
        "company_name": "Test",
        "num_queries": 20,
        "errors": []
    }

    # First request (cache miss)
    start = time.time()
    result1 = generate_queries(state)
    duration1 = time.time() - start

    # Second request (cache hit)
    start = time.time()
    result2 = generate_queries(state)
    duration2 = time.time() - start

    assert duration2 < duration1 * 0.1  # 10x faster
    assert result1["queries"] == result2["queries"]
```

## Common Issues

### Issue: Queries are too generic

**Cause**: Industry detector didn't extract company data properly
**Solution**: Ensure `company_name`, `company_description`, and `competitors` are populated

### Issue: Fewer queries than requested

**Cause**: LLM generated duplicates or invalid queries
**Solution**: Deduplication removes duplicates; this is expected behavior

### Issue: Queries don't include competitor names

**Cause**: LLM didn't follow instructions or competitors list is empty
**Solution**: Verify competitors were extracted by Industry Detector

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [ORCHESTRATION.md](./ORCHESTRATION.md) - Workflow orchestration
- [AGENT_INDUSTRY_DETECTOR.md](./AGENT_INDUSTRY_DETECTOR.md) - Previous agent
- [AGENT_AI_MODEL_TESTER.md](./AGENT_AI_MODEL_TESTER.md) - Next agent
