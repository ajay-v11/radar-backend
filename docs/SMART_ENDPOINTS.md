# Smart Endpoints - Optimized Caching

## Overview

The smart endpoints automatically detect cache status and choose the optimal response method:

- **Cache HIT**: Returns JSON instantly (~10-50ms)
- **Cache MISS**: Streams SSE with real-time progress

This eliminates unnecessary streaming overhead when data is already cached.

## Endpoints

### Industry Detection

#### `/industry/analyze-smart` (Recommended)

Smart endpoint that checks cache first.

**Request:**

```json
POST /industry/analyze-smart
{
  "company_url": "https://www.hellofresh.com",
  "company_name": "HelloFresh"  // optional
}
```

**Response (Cache HIT):**

```json
{
  "cached": true,
  "data": {
    "company_name": "HelloFresh",
    "company_description": "...",
    "company_summary": "...",
    "industry": "food_services",
    "competitors": ["Blue Apron", "Home Chef", ...]
  }
}
```

**Response (Cache MISS):**

```
Content-Type: text/event-stream

data: {"step": "initialize", "status": "started", ...}
data: {"step": "scraping", "status": "in_progress", ...}
data: {"step": "analyzing", "status": "in_progress", ...}
data: {"step": "complete", "status": "success", "data": {...}}
```

#### `/industry/analyze` (Legacy)

Always streams, even on cache hits. Use for debugging or when you want to see all steps.

### Query Generation

#### `/queries/generate-smart` (Recommended)

Smart endpoint that checks cache first.

**Request:**

```json
POST /queries/generate-smart
{
  "company_url": "https://www.hellofresh.com",
  "company_name": "HelloFresh",  // optional
  "num_queries": 50
}
```

**Response (Cache HIT):**

```json
{
  "cached": true,
  "data": {
    "total_queries": 50,
    "query_categories": {
      "comparison": {
        "name": "Comparison",
        "queries": ["...", "..."]
      },
      ...
    }
  }
}
```

**Response (Cache MISS):**

```
Content-Type: text/event-stream

data: {"step": "industry_detection", "status": "in_progress", ...}
data: {"step": "category", "status": "in_progress", ...}
data: {"step": "complete", "status": "success", "data": {...}}
```

#### `/queries/generate` (Legacy)

Always streams, even on cache hits.

## Performance Comparison

### First Request (Cold Cache)

```
Industry Detection: ~5-8 seconds (scraping + AI analysis)
Query Generation:   ~8-12 seconds (AI generation for 5 categories)
Total:              ~13-20 seconds
```

### Second Request (Warm Cache - Old Streaming Approach)

```
Industry Detection: ~2-3 seconds (cached scrape, but still runs AI)
Query Generation:   ~500ms (streaming overhead even with cache)
Total:              ~2.5-3.5 seconds
```

### Second Request (Smart Endpoints - NEW)

```
Industry Detection: ~10-50ms (instant JSON return)
Query Generation:   ~10-50ms (instant JSON return)
Total:              ~20-100ms (100x faster!)
```

## Client Implementation

### JavaScript Example

```javascript
async function analyzeCompany(url) {
  const response = await fetch('http://localhost:8000/industry/analyze-smart', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({company_url: url}),
  });

  const contentType = response.headers.get('content-type');

  if (contentType.includes('application/json')) {
    // Cache HIT - instant response
    const result = await response.json();
    console.log('⚡ Cached:', result.data);
    return result.data;
  } else {
    // Cache MISS - stream the response
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const {done, value} = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, {stream: true});
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const event = JSON.parse(line.slice(6));
          console.log('Event:', event);

          if (event.step === 'complete') {
            return event.data;
          }
        }
      }
    }
  }
}
```

### Python Example

```python
import requests

def analyze_company(url: str):
    response = requests.post(
        'http://localhost:8000/industry/analyze-smart',
        json={'company_url': url},
        stream=True
    )

    content_type = response.headers.get('content-type', '')

    if 'application/json' in content_type:
        # Cache HIT - instant response
        result = response.json()
        print(f"⚡ Cached: {result['data']}")
        return result['data']
    else:
        # Cache MISS - stream the response
        for line in response.iter_lines():
            if line.startswith(b'data: '):
                event = json.loads(line[6:])
                print(f"Event: {event}")

                if event['step'] == 'complete':
                    return event['data']
```

## Cache Keys

### Industry Detection

- **Key**: `analysis:{md5(company_url)}`
- **TTL**: 24 hours
- **Stores**: Complete analysis result (company info, industry, competitors)

### Query Generation

- **Key**: `queries:{md5(company_url:num_queries)}`
- **TTL**: 24 hours
- **Stores**: Generated queries + categories

## Benefits

1. **100x Faster on Cache Hits**: ~20-100ms vs ~2-3 seconds
2. **Reduced Server Load**: No unnecessary streaming overhead
3. **Lower Bandwidth**: Single JSON response vs multiple SSE events
4. **Better UX**: Instant results feel more responsive
5. **Cost Savings**: Fewer API calls, less compute time

## Migration Guide

### From Old Endpoints

**Before:**

```javascript
// Always streams
fetch('/industry/analyze', {...})
```

**After:**

```javascript
// Smart - instant on cache hit
fetch('/industry/analyze-smart', {...})
```

### Handling Both Response Types

```javascript
async function smartFetch(url, body) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  });

  const contentType = response.headers.get('content-type');

  if (contentType.includes('application/json')) {
    // Instant cached response
    return (await response.json()).data;
  } else {
    // Stream and parse SSE
    return await parseSSEStream(response);
  }
}
```

## Monitoring

Check your server logs for cache performance:

```
[FULL CACHE HIT] ⚡⚡⚡ Returning complete analysis instantly!
[CACHE HIT] ⚡ Returning 50 cached queries instantly
```

vs

```
[CACHE MISS] 🔄 Scraping https://...
[CACHE MISS] 🔄 Generating new queries with streaming
```

## Best Practices

1. **Use smart endpoints by default** - They're optimized for both scenarios
2. **Monitor cache hit rates** - Should be >70% in production
3. **Set appropriate TTLs** - 24 hours balances freshness vs performance
4. **Handle both response types** - Your client should support JSON and SSE
5. **Show cache status to users** - Display "⚡ Instant" vs "🔄 Analyzing"

## Troubleshooting

**Issue**: Always getting cache misses

**Solution**: Check Redis connection and ensure URLs are normalized (lowercase, no trailing slash)

**Issue**: Cached data is stale

**Solution**: Clear cache manually or reduce TTL:

```bash
redis-cli DEL "analysis:*"
redis-cli DEL "queries:*"
```

**Issue**: Client can't handle both response types

**Solution**: Use the legacy streaming endpoints (`/analyze`, `/generate`) until client is updated
