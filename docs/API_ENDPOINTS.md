# API Endpoints - Simplified Two-Phase Architecture

## Overview

The API has been streamlined into a clean two-phase workflow:

1. **Phase 1: Company Analysis** - Analyze company, detect industry, identify competitors
2. **Phase 2: Complete Flow** - Generate queries, test AI models, calculate visibility score

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

Analyzes company website, detects industry, identifies competitors, and generates summary.

**Why separate?**

- Higher chance of failure (broken URLs, scraping issues)
- Can be enhanced independently (user-provided competitors)
- Results are reusable across multiple visibility analyses
- Can be cached for instant subsequent calls

**Request:**

```json
{
  "company_url": "https://hellofresh.com",
  "company_name": "HelloFresh" // optional
}
```

**Response (Cached):**

```json
{
  "cached": true,
  "data": {
    "industry": "food_services",
    "company_name": "HelloFresh",
    "company_description": "Meal kit delivery service...",
    "company_summary": "Detailed 3-4 sentence summary...",
    "competitors": ["Blue Apron", "Home Chef", "EveryPlate"],
    "competitors_data": [
      {
        "name": "Blue Apron",
        "description": "Meal kit delivery with chef-designed recipes",
        "products": "meal kits, wine subscriptions",
        "positioning": "premium quality ingredients"
      }
    ]
  }
}
```

**Response (Streaming - Cache Miss):**

Server-Sent Events (SSE) stream with progress updates:

```
data: {"step": "scraping", "status": "started", "message": "Scraping website..."}

data: {"step": "scraping", "status": "completed", "data": {"content_length": 5000}}

data: {"step": "analysis", "status": "started", "message": "Analyzing with AI..."}

data: {"step": "analysis", "status": "completed", "data": {...}}

data: {"step": "complete", "status": "success", "data": {...}}
```

---

## Phase 2: Visibility Analysis

### `POST /analyze/visibility`

Orchestrates the visibility analysis workflow with parallel batch processing.

**Prerequisites**: Must run `POST /analyze/company` first to get company data.

**Steps:**

1. Industry detection (reuses Phase 1 cache if available)
2. Query generation (cached, organized by category)
3. Parallel batch testing across selected AI models
4. Scoring with RAG-based competitor matching
5. Final aggregation and reporting

**Request:**

```json
{
  "company_url": "https://hellofresh.com",
  "company_name": "HelloFresh", // optional
  "company_description": "", // optional
  "num_queries": 20,
  "models": ["chatgpt", "gemini"],
  "llm_provider": "gemini",
  "batch_size": 5
}
```

**Parameters:**

- `company_url` (required): Company website URL
- `company_name` (optional): Company name
- `company_description` (optional): Company description
- `num_queries` (default: 20): Number of queries to generate
- `models` (default: ["llama", "gemini"]): AI models to test
  - Available: `chatgpt`, `gemini`, `claude`, `llama`, `mistral`, `qwen`
- `llm_provider` (default: "gemini"): LLM for query generation
  - Available: `gemini`, `chatgpt`, `claude`
- `batch_size` (default: 5): Queries per batch for parallel processing

**Response (Streaming):**

Server-Sent Events (SSE) stream with real-time progress:

```
data: {"step": "step1", "status": "started", "message": "Starting industry detection..."}

data: {"step": "step1", "status": "completed", "data": {"industry": "food_services", "company_name": "HelloFresh", "competitors": [...]}}

data: {"step": "step2", "status": "started", "message": "Generating queries..."}

data: {"step": "step2", "status": "completed", "data": {"total_queries": 20, "categories": 5}}

data: {"step": "step3", "status": "started", "message": "Starting parallel batch testing..."}

data: {"step": "batch", "status": "testing_started", "data": {"batch_num": 1, "batch_size": 5, "progress": 0}}

data: {"step": "batch", "status": "testing_completed", "data": {"batch_num": 1, "responses_count": 10}}

data: {"step": "batch", "status": "analysis_started", "data": {"batch_num": 1}}

data: {"step": "batch", "status": "analysis_completed", "data": {"batch_num": 1, "visibility_score": 75.5, "total_mentions": 8}}

... (repeats for each batch)

data: {"step": "step4", "status": "started", "message": "Aggregating results..."}

data: {"step": "step4", "status": "completed", "data": {"visibility_score": 75.5, "total_mentions": 30, "by_model": {...}}}

data: {"step": "complete", "status": "success", "data": {...}, "message": "Analysis completed successfully!"}
```

**Final Data Structure:**

```json
{
  "industry": "food_services",
  "company_name": "HelloFresh",
  "competitors": ["Blue Apron", "Home Chef"],
  "total_queries": 20,
  "total_responses": 40,
  "visibility_score": 75.5,
  "analysis_report": {
    "total_mentions": 30,
    "mention_rate": 0.75,
    "by_model": {
      "chatgpt": {
        "mentions": 16,
        "total_responses": 20,
        "mention_rate": 0.80,
        "competitor_mentions": {
          "Blue Apron": 8,
          "Home Chef": 5
        }
      },
      "gemini": {
        "mentions": 14,
        "total_responses": 20,
        "mention_rate": 0.70
      }
    },
    "sample_mentions": [
      "Query: 'What are the best meal kit services?' -> Chatgpt mentioned company (with Blue Apron, Home Chef)"
    ]
  },
  "batch_results": [
    {
      "batch_num": 1,
      "visibility_score": 80.0,
      "total_mentions": 8,
      "by_model": {...}
    }
  ]
}
```

---

## Caching Strategy

### Phase 1 (Company Analysis)

- **Cache Key**: `company_url`
- **TTL**: 24 hours
- **Storage**: Redis
- **Benefit**: Instant results on repeated analysis (~10-50ms vs 10-30s)

### Phase 2 (Complete Flow)

- **Industry Detection**: Uses Phase 1 cache
- **Query Generation**: Cached per `company_url + industry + num_queries`
- **Model Responses**: Cached per `query + model` (1hr TTL)
- **Benefit**: 70% cost reduction on repeated queries

---

## Frontend Integration Example

### React/TypeScript Example

```typescript
// Phase 1: Analyze Company
async function analyzeCompany(companyUrl: string, companyName?: string) {
  const response = await fetch('/analyze/company', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({company_url: companyUrl, company_name: companyName}),
  });

  const data = await response.json();

  if (data.cached) {
    // Instant cached result
    return data.data;
  } else {
    // Handle SSE stream
    const eventSource = new EventSource('/analyze/company');
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log(data.step, data.status, data.message);
    };
  }
}

// Phase 2: Complete Flow
async function runCompleteFlow(params: CompleteFlowParams) {
  const eventSource = new EventSource('/analyze/visibility');

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch (data.step) {
      case 'step1':
        // Update UI: Industry detection progress
        break;
      case 'step2':
        // Update UI: Query generation progress
        break;
      case 'batch':
        // Update UI: Batch testing progress
        break;
      case 'complete':
        // Final results
        console.log('Visibility Score:', data.data.visibility_score);
        eventSource.close();
        break;
    }
  };
}
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

## Removed Endpoints

The following redundant endpoints have been removed:

- ❌ `/industry/analyze` - Replaced by `/analyze/company`
- ❌ `/industry/analyze-smart` - Merged into `/analyze/company`
- ❌ `/queries/generate` - Integrated into `/analyze/visibility`
- ❌ `/queries/generate-smart` - Integrated into `/analyze/visibility`
- ❌ `/visibility/analyze` - Replaced by `/analyze/visibility`
- ❌ `/parallel/test-and-analyze` - Replaced by `/analyze/visibility`

---

## Summary

**Two endpoints, clean workflow:**

1. `POST /analyze/company` - Get company profile (cached)
2. `POST /analyze/visibility` - Run full visibility analysis (streaming)

Simple, predictable, and optimized for frontend integration.
