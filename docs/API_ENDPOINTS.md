# API Endpoints

## Overview

Two-phase workflow with slug-based caching:

1. **Phase 1: Company Analysis** - Returns `company_slug_id`
2. **Phase 2: Visibility Analysis** - Uses `company_slug_id`, returns `visibility_slug_id`
3. **Report Endpoints** - Use `visibility_slug_id` for detailed data

---

## Endpoints

### Health Check

#### `GET /`

Root endpoint with API information and workflow description.

**Response:**

```json
{
  "name": "AI Visibility Scoring System",
  "version": "1.0.0",
  "description": "Two-phase analysis workflow for company visibility scoring",
  "endpoints": {
    "health": "/health",
    "phase_1_company_analysis": "/analyze/company",
    "phase_2_complete_flow": "/analyze/visibility"
  }
}
```

#### `GET /health`

Health check status and version.

**Response:**

```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## Phase 1: Company Analysis

### `POST /analyze/company`

Analyzes company website, detects industry dynamically, identifies competitors.

**Why separate?** Reusable across multiple visibility analyses, slug-based caching (24hr).

**Request:**

```json
{
  "company_url": "https://hellofresh.com",
  "company_name": "HelloFresh", // optional
  "target_region": "United States" // optional, default: "United States"
}
```

**Response (Always SSE Stream):**

Server-Sent Events (SSE) stream - instant for cache hits, live for cache misses:

```
data: {"step": "complete", "status": "success", "message": "Analysis completed", "slug_id": "company_abc123def456", "cached": true, "data": {...}}
```

**Final Data Structure:**

```json
{
  "step": "complete",
  "status": "success",
  "slug_id": "company_abc123def456",
  "cached": false,
  "data": {
    "industry": "AI-Powered Meal Kit Delivery",
    "company_name": "HelloFresh",
    "company_description": "Meal kit delivery service...",
    "company_summary": "Detailed 3-4 sentence summary...",
    "competitors": ["Blue Apron", "Home Chef", "EveryPlate"],
    "target_region": "United States",
    "query_categories_template": {...}
  }
}
```

---

## Phase 2: Visibility Analysis

### `POST /analyze/visibility`

Orchestrates the visibility analysis workflow with category-based batching.

**Prerequisites**: Must run `POST /analyze/company` first to get `company_slug_id`.

**Steps:**

1. Uses cached company data from Phase 1
2. Query generation per category (dynamic templates)
3. Model testing per category (parallel across models)
4. Scoring with per-model and per-category breakdowns
5. Progressive streaming with partial results

**Request:**

```json
{
  "company_slug_id": "company_abc123def456",
  "num_queries": 20,
  "models": ["chatgpt", "gemini", "claude"],
  "llm_provider": "claude"
}
```

**Parameters:**

- `company_slug_id` (required): Slug from Phase 1 company analysis
- `num_queries` (default: 20): Total queries to generate (distributed across categories)
- `models` (default: ["llama", "gemini"]): AI models to test
  - Available: `chatgpt`, `gemini`, `claude`, `llama`, `grok`, `deepseek`
- `llm_provider` (default: "llama"): LLM for query generation
  - Available: `claude`, `gemini`, `llama`, `openai`, `grok`, `deepseek`

**Response (Always SSE Stream):**

Server-Sent Events (SSE) stream - instant for cache hits, live for cache misses:

```
data: {"step": "initialization", "status": "completed", "message": "Initialized 6 categories", "data": {...}}

data: {"step": "category_complete", "status": "completed", "message": "Category 'product_selection' complete!", "data": {"category": "product_selection", "category_score": 50.0, "model_breakdown": {"gpt-3.5-turbo": {"visibility": 60.0, "mentions": 3, "queries": 5}}, "partial_visibility_score": 50.0, "partial_model_scores": {"gpt-3.5-turbo": 60.0}, ...}}

... (repeats for each category)

data: {"step": "complete", "status": "success", "message": "Visibility analysis completed!", "cached": false, "data": {...}}
```

**Final Data Structure:**

```json
{
  "step": "complete",
  "status": "success",
  "message": "Visibility analysis completed!",
  "cached": false,
  "data": {
    "visibility_score": 75.5,
    "model_scores": {
      "gpt-3.5-turbo": 80.0,
      "gemini-2.5-flash-lite": 71.0,
      "claude-3-5-haiku-20241022": 75.5
    },
    "total_queries": 20,
    "total_mentions": 30,
    "categories_processed": 6,
    "category_breakdown": [
      {
        "category": "product_selection",
        "score": 50.0,
        "queries": 5,
        "mentions": 3
      }
    ],
    "model_category_matrix": {
      "gpt-3.5-turbo": {
        "product_selection": 60.0,
        "comparison": 80.0,
        "best_of": 90.0
      },
      "gemini-2.5-flash-lite": {
        "product_selection": 40.0,
        "comparison": 70.0,
        "best_of": 80.0
      }
    },
    "slug_id": "visibility_abc123def456"
  }
}
```

---

## Caching Strategy

### Slug-Based Caching

Both phases use **slug-based caching** for simple, predictable cache management:

**Phase 1 (Company Analysis)**

- **Slug**: `company_{hash(url + region)}`
- **TTL**: 24 hours
- **Benefit**: Instant results (~10-50ms vs 10-30s)

**Phase 2 (Visibility Analysis)**

- **Slug**: `visibility_{hash(url + num_queries + models + llm_provider)}`
- **TTL**: 24 hours
- **Benefit**: Instant results, 70% cost reduction

### Report Endpoints

Use the `slug_id` from analysis responses to fetch detailed reports:

- `GET /report/{slug_id}` - Full analysis report
- `POST /report/{slug_id}/query-log` - Paginated query log

---

## Frontend Integration

```typescript
// Phase 1: Company Analysis
const eventSource = new EventSource('/analyze/company');
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.step === 'complete') {
    const companySlugId = data.slug_id;
    eventSource.close();
  }
};

// Phase 2: Visibility Analysis
const eventSource2 = new EventSource('/analyze/visibility');
eventSource2.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.step === 'category_complete') {
    // Update progress: data.data.partial_visibility_score
  } else if (data.step === 'complete') {
    // Final: data.data.visibility_score, data.data.model_scores
    const visibilitySlugId = data.data.slug_id;
    eventSource2.close();
  }
};
```

---

## Error Handling

All endpoints return consistent error formats:

**400 Bad Request:**

```json
{
  "detail": "Invalid request: company_url is required"
}
```

**500 Internal Server Error:**

```json
{
  "detail": "Internal server error: <error message>"
}
```

**SSE Error Event:**

```
data: {"step": "error", "status": "failed", "data": {"error": "..."}, "message": "Error: ..."}
```

---

## Summary

**Two-phase workflow:**

1. `POST /analyze/company` → Returns `company_slug_id`
2. `POST /analyze/visibility` → Uses `company_slug_id`, returns `visibility_slug_id`
3. `GET /report/{slug_id}` → Full report (optional)
4. `POST /report/{slug_id}/query-log` → Query log (optional)
5. `GET /report/{slug_id}/export/csv` → CSV export (optional)

**Key Features:**

- Slug-based caching (24hr TTL)
- SSE streaming with real-time progress
- Per-model and per-category breakdowns
- Category-based batching
