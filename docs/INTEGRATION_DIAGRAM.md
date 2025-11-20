# Agent Integration Flow Diagram

## Complete Data Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           USER INPUT                                      │
│  • company_url: "https://www.hellofresh.com"                             │
│  • company_name: "" (optional)                                            │
│  • company_description: "" (optional)                                     │
│  • num_queries: 50                                                        │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    AGENT 1: INDUSTRY DETECTOR                             │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ STEP 1: Check Redis Cache                                        │    │
│  │   Key: scrape:{md5(url)}                                         │    │
│  │   TTL: 24 hours                                                  │    │
│  │                                                                   │    │
│  │   ✓ Cache HIT  → Use cached content (0.01s)                     │    │
│  │   ✗ Cache MISS → Continue to scraping                           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                 │                                         │
│                                 ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ STEP 2: Scrape Website (if cache miss)                          │    │
│  │   Tool: Firecrawl API                                            │    │
│  │   Output: Markdown content (5000 chars)                          │    │
│  │   Time: ~2-5 seconds                                             │    │
│  │   Cache: Store in Redis for 24 hours                             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                 │                                         │
│                                 ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ STEP 3: Analyze with OpenAI                                      │    │
│  │   Model: gpt-4o-mini                                             │    │
│  │   Extract:                                                        │    │
│  │     • Company name                                               │    │
│  │     • Description (1-2 sentences)                                │    │
│  │     • Summary (3-4 sentences)                                    │    │
│  │     • Industry classification                                    │    │
│  │     • Competitors (3-5 with rich metadata)                       │    │
│  │   Time: ~1-2 seconds                                             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                 │                                         │
│                                 ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ STEP 4: Store in Vector Database                                 │    │
│  │   ChromaDB Collections:                                           │    │
│  │     • companies: Company profile + embeddings                    │    │
│  │     • competitors: Competitor data + rich embeddings             │    │
│  │   Time: ~0.5 seconds                                             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                           │
│  OUTPUT STATE:                                                            │
│    ✓ industry: "food_services"                                           │
│    ✓ company_name: "HelloFresh"                                          │
│    ✓ company_description: "Meal kit delivery service..."                 │
│    ✓ company_summary: "HelloFresh specializes in..."                     │
│    ✓ competitors: ["Blue Apron", "Home Chef", "Sun Basket", ...]        │
│    ✓ competitors_data: [{name, description, products, positioning}, ...] │
│    ✓ scraped_content: "# HelloFresh\n\n..."                              │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                    DATA FLOWS TO NEXT AGENT
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    AGENT 2: QUERY GENERATOR                               │
│                                                                           │
│  INPUT (from Agent 1):                                                    │
│    • company_url                                                          │
│    • industry: "food_services"                                           │
│    • company_name: "HelloFresh"                                          │
│    • company_description: "Meal kit delivery service..."                 │
│    • company_summary: "HelloFresh specializes in..."                     │
│    • competitors: ["Blue Apron", "Home Chef", ...]                       │
│    • num_queries: 50                                                      │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ STEP 1: Check Redis Cache                                        │    │
│  │   Key: queries:{md5(url:num_queries)}                            │    │
│  │   TTL: 24 hours                                                  │    │
│  │                                                                   │    │
│  │   ✓ Cache HIT  → Return cached queries (0.01s)                  │    │
│  │   ✗ Cache MISS → Continue to generation                         │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                 │                                         │
│                                 ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ STEP 2: Select Industry Categories                               │    │
│  │   Industry: food_services                                        │    │
│  │   Categories (weighted):                                          │    │
│  │     • Comparison (30%) → 15 queries                              │    │
│  │     • Product Selection (25%) → 12 queries                       │    │
│  │     • Dietary & Health (20%) → 10 queries                        │    │
│  │     • Best-of Lists (15%) → 8 queries                            │    │
│  │     • How-to & Educational (10%) → 5 queries                     │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                 │                                         │
│                                 ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ STEP 3: Generate Queries with OpenAI                             │    │
│  │   Model: gpt-4o-mini                                             │    │
│  │   For each category:                                              │    │
│  │     • Use company context (name, description, summary)           │    │
│  │     • Include competitor names                                   │    │
│  │     • Generate realistic search queries                          │    │
│  │   Time: ~5-10 seconds (5 API calls)                              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                 │                                         │
│                                 ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ STEP 4: Cache Results                                            │    │
│  │   Store in Redis:                                                 │    │
│  │     • queries: [list of 50 queries]                              │    │
│  │     • query_categories: {category: {name, queries}}              │    │
│  │   TTL: 24 hours                                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                           │
│  OUTPUT STATE (preserves all previous + adds):                           │
│    ✓ queries: [                                                          │
│        "HelloFresh vs Blue Apron meal quality comparison",               │
│        "Factor vs Home Chef pricing plans 2025",                         │
│        "Best meal kits for families",                                    │
│        ...                                                                │
│      ]                                                                    │
│    ✓ query_categories: {                                                 │
│        "comparison": {name: "Comparison", queries: [...]},               │
│        "product_selection": {name: "Product Selection", queries: [...]}, │
│        ...                                                                │
│      }                                                                    │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         FINAL OUTPUT                                      │
│                                                                           │
│  Complete WorkflowState with:                                            │
│    • All company data (name, description, summary, industry)             │
│    • Competitor information                                              │
│    • 50 contextual, industry-specific queries                            │
│    • Organized by category                                               │
│    • Ready for AI Model Tester (next agent)                              │
└──────────────────────────────────────────────────────────────────────────┘
```

## Cache Hit Scenarios

### Scenario 1: First Request (Cold Cache)

```
Request: https://www.hellofresh.com, 50 queries

Industry Detector:
  ✗ Scrape cache MISS → Scrape website (2-5s)
  → Analyze with OpenAI (1-2s)
  → Store in ChromaDB (0.5s)
  → Cache scrape result
  Total: ~4-8 seconds

Query Generator:
  ✗ Query cache MISS → Generate queries (5-10s)
  → Cache query results
  Total: ~5-10 seconds

Combined: ~9-18 seconds
```

### Scenario 2: Second Request (Warm Scrape Cache)

```
Request: https://www.hellofresh.com, 50 queries

Industry Detector:
  ✓ Scrape cache HIT → Use cached content (0.01s)
  → Analyze with OpenAI (1-2s)
  → Store in ChromaDB (0.5s)
  Total: ~2-3 seconds

Query Generator:
  ✗ Query cache MISS → Generate queries (5-10s)
  → Cache query results
  Total: ~5-10 seconds

Combined: ~7-13 seconds (30% faster)
```

### Scenario 3: Third Request (Full Cache)

```
Request: https://www.hellofresh.com, 50 queries

Industry Detector:
  ✓ Scrape cache HIT → Use cached content (0.01s)
  → Analyze with OpenAI (1-2s)
  → Store in ChromaDB (0.5s)
  Total: ~2-3 seconds

Query Generator:
  ✓ Query cache HIT → Return cached queries (0.01s)
  Total: ~0.01 seconds

Combined: ~2-3 seconds (85% faster than cold cache)
```

### Scenario 4: Different Query Count (Partial Cache)

```
Request: https://www.hellofresh.com, 20 queries (different from cached 50)

Industry Detector:
  ✓ Scrape cache HIT → Use cached content (0.01s)
  → Analyze with OpenAI (1-2s)
  → Store in ChromaDB (0.5s)
  Total: ~2-3 seconds

Query Generator:
  ✗ Query cache MISS (different num_queries) → Generate 20 queries (2-4s)
  → Cache query results
  Total: ~2-4 seconds

Combined: ~4-7 seconds
```

## Data Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│                    Industry Detector                         │
│                                                              │
│  Produces:                                                   │
│    • industry ──────────────────────┐                       │
│    • company_name ──────────────────┤                       │
│    • company_description ───────────┤                       │
│    • company_summary ───────────────┤                       │
│    • competitors ───────────────────┤                       │
│    • competitors_data ──────────────┤                       │
│    • scraped_content ───────────────┤                       │
└─────────────────────────────────────┼───────────────────────┘
                                      │
                                      │ All data flows through
                                      │ WorkflowState
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Query Generator                           │
│                                                              │
│  Consumes:                                                   │
│    • industry ◄─────────── Selects query categories         │
│    • company_name ◄──────── Personalizes queries            │
│    • company_description ◄─ Provides context                │
│    • company_summary ◄───── Enriches AI prompts             │
│    • competitors ◄────────── Enables comparison queries     │
│                                                              │
│  Produces:                                                   │
│    • queries                                                 │
│    • query_categories                                        │
│    • (preserves all input fields)                           │
└─────────────────────────────────────────────────────────────┘
```

## Key Integration Benefits

### 🚀 Performance

- **90% faster** scraping on cache hits (24hr TTL)
- **Instant** query retrieval on cache hits
- **70-85% overall** speed improvement on repeated requests

### 💰 Cost Efficiency

- **No redundant** Firecrawl API calls
- **Reduced** OpenAI API calls through caching
- **Optimized** token usage (5000 char limit on scrapes)

### 🎯 Quality

- **Rich context** for query generation
- **Real competitor names** in queries
- **Industry-specific** query categories

### 🔧 Maintainability

- **Clear separation** of concerns
- **Stateless** agent design
- **Easy to test** independently

### 📈 Scalability

- **Horizontal scaling** ready
- **Cache-first** architecture
- **Vector storage** for future features
