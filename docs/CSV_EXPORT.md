# CSV Export Feature

## Overview

Export complete visibility analysis reports as CSV files for offline analysis, sharing, or importing into spreadsheet tools.

## Endpoint

```
GET /report/{slug_id}/export/csv
```

## Usage

### 1. Run Visibility Analysis

First, get the `slug_id` from a visibility analysis:

```bash
# Phase 1: Company Analysis
curl -X POST http://localhost:8000/analyze/company \
  -H "Content-Type: application/json" \
  -d '{"company_url": "https://hellofresh.com"}'

# Returns: {"slug_id": "company_abc123..."}

# Phase 2: Visibility Analysis
curl -X POST http://localhost:8000/analyze/visibility \
  -H "Content-Type: application/json" \
  -d '{
    "company_slug_id": "company_abc123...",
    "num_queries": 20,
    "models": ["chatgpt", "gemini"]
  }'

# Returns: {"slug_id": "visibility_xyz789..."}
```

### 2. Export CSV Report

```bash
curl -X GET http://localhost:8000/report/visibility_xyz789.../export/csv \
  --output report.csv
```

Or open directly in browser:

```
http://localhost:8000/report/visibility_xyz789.../export/csv
```

## CSV Structure

The exported CSV contains 6 sections:

### 1. Summary

- Company name
- Industry
- Overall visibility score
- Total queries tested
- Total mentions
- Total responses

### 2. Model Performance

- Per-model breakdown
- Mentions count
- Total responses
- Visibility percentage

### 3. Category Breakdown

- Performance by query category
- Queries per category
- Mentions per category
- Category visibility score

### 4. Competitor Rankings

- Ranked list of all competitors
- Total mentions
- Visibility percentage

### 5. Detailed Query Log

- Every single query tested
- Results per model
- Mentioned status (Yes/No)
- Rank position
- Competitors mentioned

### 6. Model-Category Matrix

- Cross-tabulation of model performance by category
- Visibility scores for each model-category combination

## Example Output

```csv
AI VISIBILITY ANALYSIS REPORT

Company,HelloFresh
Industry,AI-Powered Meal Kit Delivery
Overall Visibility Score,34.50%
Total Queries Tested,20
Total Mentions,14
Total Responses,40

MODEL PERFORMANCE
Model,Mentions,Total Responses,Visibility %
gpt-3.5-turbo,8,20,40.00%
gemini-2.0-flash-exp,6,20,30.00%

CATEGORY BREAKDOWN
Category,Queries,Mentions,Visibility %
product_selection,8,6,37.50%
comparison,7,5,35.71%
best_of,5,3,30.00%

COMPETITOR RANKINGS
Rank,Competitor,Total Mentions,Visibility %
1,Blue Apron,32,80.00%
2,HelloFresh,14,35.00%
3,Factor,12,30.00%

DETAILED QUERY LOG
Query,Category,Model,Mentioned?,Rank,Competitors Mentioned
best meal kits for weight loss,comparison,gpt-3.5-turbo,Yes,2,"Factor, Trifecta"
organic meal delivery services,product_selection,gemini-2.0-flash-exp,No,N/A,"HelloFresh, Blue Apron"
...
```

## Use Cases

- **Offline Analysis**: Import into Excel/Google Sheets for custom analysis
- **Reporting**: Share with stakeholders
- **Historical Tracking**: Compare reports over time
- **Data Integration**: Import into BI tools or databases
- **Compliance**: Archive analysis results

## Notes

- CSV uses UTF-8 encoding
- Filename format: `{company_name}_visibility_report.csv`
- File size depends on number of queries (typically 50-500 KB)
- All data from the cached analysis is included
