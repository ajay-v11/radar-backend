# Simple Slug-Based Caching

## How It Works

**No complex multi-level caching. Just simple slug matching.**

### Slug Generation

**Company Analysis**: `hash(company_url + target_region + date)` → `company_abc123`

**Visibility Analysis**: `hash(company_url + num_queries + models + llm_provider + date)` → `visibility_xyz789`

### Cache Behavior

- **Same params + same day** = Cache HIT (instant response with slug_id)
- **Different params or different day** = Cache MISS (run analysis, cache with new slug_id)

---

## API Endpoints

### 1. POST /analyze/company

**Request**:

```json
{
  "company_url": "https://hellofresh.com",
  "target_region": "United States"
}
```

**Response (cached)**:

```json
{
  "cached": true,
  "slug_id": "company_abc123def456",
  "data": { ... }
}
```

**Response (not cached)**: SSE stream, final event includes `slug_id`

---

### 2. POST /analyze/visibility

**Request**:

```json
{
  "company_url": "https://hellofresh.com",
  "num_queries": 20,
  "models": ["chatgpt", "claude"],
  "llm_provider": "claude"
}
```

**Response (cached)**:

```json
{
  "cached": true,
  "slug_id": "visibility_xyz789abc123",
  "data": {
    "visibility_score": 45.5,
    "total_queries": 20,
    "category_breakdown": [...]
  }
}
```

**Response (not cached)**: SSE stream, final event includes `slug_id`

---

### 3. GET /report/{slug_id}

**Use the slug_id from visibility analysis to get full report.**

**Example**: `GET /report/visibility_xyz789abc123`

**Response**:

```json
{
  "slug_id": "visibility_xyz789abc123",
  "summary": {
    "visibility_score": 45.5,
    "total_queries": 20,
    "total_mentions": 10
  },
  "category_breakdown": [...],
  "competitor_rankings": [...],
  "by_model": {...},
  "sample_mentions": [...]
}
```

---

### 4. POST /report/{slug_id}/query-log

**Get paginated query log by slug_id.**

**Example**: `POST /report/visibility_xyz789abc123/query-log`

**Request**:

```json
{
  "page": 1,
  "limit": 50,
  "model": "chatgpt",
  "mentioned": true
}
```

**Response**:

```json
{
  "total": 100,
  "page": 1,
  "queries": [...]
}
```

---

## Frontend Flow

1. **Run company analysis** → Get `company_slug_id`
2. **Run visibility analysis** → Get `visibility_slug_id`
3. **Fetch full report** → Use `visibility_slug_id`
4. **Fetch query log** → Use `visibility_slug_id`

**Simple. No guessing parameters. Just use the slug_id.**
