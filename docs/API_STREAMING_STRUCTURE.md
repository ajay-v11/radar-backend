# API Streaming Structure

## Overview

The API now follows a **lightweight streaming + detailed reports** pattern for optimal UX:

- **Streaming endpoints**: Send minimal data for real-time UI updates
- **Report endpoints**: Provide complete detailed analysis on demand

---

## Phase 1: Company Analysis

### `POST /analyze/company`

**Purpose**: Scrape and analyze company (industry, competitors, etc.)

**Streaming**: Simple progress steps only

- "Scraping website..."
- "Detecting industry..."
- "Finding competitors..."

**Final Response**:

```json
{
  "cached": false,
  "data": {
    "industry": "AI-Powered Meal Kit Delivery",
    "company_name": "HelloFresh",
    "competitors": ["Blue Apron", "Home Chef", "..."],
    "target_region": "United States"
  }
}
```

---

## Phase 2: Visibility Analysis

### `POST /analyze/visibility`

**Purpose**: Generate queries, test models, calculate visibility score

**Streaming Events** (lightweight):

#### 1. Initialization

```json
{
  "step": "initialization",
  "status": "completed",
  "message": "Initialized 6 categories",
  "data": {
    "total_categories": 6,
    "categories": ["product_selection", "comparison", "..."]
  }
}
```

#### 2. Category Complete (per category)

```json
{
  "step": "category_complete",
  "status": "completed",
  "message": "Category 'product_selection' complete! Partial score: 45.5%",
  "data": {
    "category": "product_selection",
    "category_score": 50.0,
    "completed_categories": 3,
    "total_categories": 6,
    "progress": "3/6",
    "partial_visibility_score": 45.5,
    "total_queries": 15,
    "total_mentions": 7,
    "category_breakdown": [
      {
        "category": "product_selection",
        "score": 50.0,
        "queries": 5,
        "mentions": 3
      }
    ]
  }
}
```

#### 3. Final Complete

```json
{
  "step": "complete",
  "status": "success",
  "message": "Visibility analysis completed!",
  "data": {
    "visibility_score": 45.5,
    "total_queries": 20,
    "total_mentions": 10,
    "categories_processed": 6,
    "category_breakdown": [...],
    "analysis_id": "https://hellofresh.com"
  }
}
```

**What's NOT streamed**:

- query_log (detailed query-by-query results)
- competitor_rankings
- by_model analysis
- sample_mentions

---

## Report Endpoints

### `GET /report/{company_url:path}`

**Purpose**: Get complete analysis report with all detailed data

**Example**: `GET /report/https://hellofresh.com`

**Response**:

```json
{
  "summary": {
    "visibility_score": 45.5,
    "total_queries": 20,
    "total_mentions": 10,
    "total_responses": 40,
    "mention_rate": 0.25
  },
  "category_breakdown": [
    {
      "category": "product_selection",
      "name": "Product Selection Queries",
      "total_queries": 5,
      "total_responses": 10,
      "mentions": 3,
      "visibility": 30.0,
      "mention_rate": 0.3,
      "by_model": {
        "chatgpt": {"mentions": 2, "total": 5},
        "gemini": {"mentions": 1, "total": 5}
      }
    }
  ],
  "competitor_rankings": [
    {
      "competitor": "Blue Apron",
      "total_mentions": 15,
      "visibility_score": 75.0,
      "by_category": {
        "product_selection": 5,
        "comparison": 10
      },
      "by_model": {
        "chatgpt": 8,
        "gemini": 7
      }
    }
  ],
  "by_model": {
    "chatgpt": {
      "mentions": 6,
      "total_responses": 20,
      "mention_rate": 0.3,
      "competitor_mentions": {
        "Blue Apron": 8,
        "Home Chef": 5
      }
    }
  },
  "by_category": {
    "product_selection": {
      "name": "Product Selection Queries",
      "total_queries": 5,
      "mentions": 3,
      "visibility": 30.0
    }
  },
  "sample_mentions": [
    "Query: 'best meal kits for families' -> Chatgpt mentioned company at rank 2 (with Blue Apron, Home Chef)"
  ],
  "company_info": {
    "name": "HelloFresh",
    "industry": "AI-Powered Meal Kit Delivery",
    "competitors": ["Blue Apron", "Home Chef", "..."]
  }
}
```

---

### `POST /report/{company_url:path}/query-log`

**Purpose**: Get paginated query log with filtering

**Request Body**:

```json
{
  "page": 1,
  "limit": 50,
  "category": "product_selection", // optional
  "model": "chatgpt", // optional
  "mentioned": true // optional
}
```

**Response**:

```json
{
  "total": 100,
  "page": 1,
  "limit": 50,
  "total_pages": 2,
  "queries": [
    {
      "query": "best meal kits for families",
      "category": "product_selection",
      "results": {
        "chatgpt": {
          "mentioned": true,
          "rank": 2,
          "competitors_mentioned": ["Blue Apron", "Home Chef"],
          "response_preview": "When looking for family meal kits..."
        },
        "gemini": {
          "mentioned": false,
          "rank": null,
          "competitors_mentioned": ["Blue Apron"],
          "response_preview": "Blue Apron offers great family options..."
        }
      }
    }
  ],
  "filters": {
    "category": "product_selection",
    "model": "chatgpt",
    "mentioned": true
  }
}
```

---

## Frontend Integration Guide

### Real-time Dashboard

1. **Start visibility analysis**: `POST /analyze/visibility`
2. **Listen to SSE stream**:
   - Update progress bar from `category_complete` events
   - Update score card with `partial_visibility_score`
   - Update category table with `category_breakdown`
3. **On completion**: Store `analysis_id` for detailed reports

### Detailed Reports (on-demand)

1. **Full report**: `GET /report/{company_url}`
   - Show competitor rankings
   - Show per-model analysis
   - Show sample mentions
2. **Query log table**: `POST /report/{company_url}/query-log`
   - Paginate through all queries
   - Filter by category/model/mentioned
   - Show detailed results per query

---

## Benefits

✅ **Fast streaming**: Minimal data, instant UI updates  
✅ **Progressive loading**: Show summary → load details on demand  
✅ **Better UX**: Live updates + detailed analysis separately  
✅ **Scalable**: 100 queries won't bloat the stream  
✅ **Flexible**: Filter and paginate detailed data as needed
