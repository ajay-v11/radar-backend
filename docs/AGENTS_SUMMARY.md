# Agents Summary

Quick reference for the 5 LangGraph-based agents in the system.

## Agent 1: Industry Detector

- **Module**: `agents/industry_detection_agent/`
- **Nodes**: 9 (parallel scraping, classify, extract, generate categories)
- **Purpose**: Dynamic industry classification + custom query categories
- **Key Output**: `query_categories_template` (used by query generator)
- **Cache**: 24hr

## Agent 2: Query Generator

- **Module**: `agents/query_generator_agent/`
- **Nodes**: 5 (check cache, distribute, generate, cache, finalize)
- **Purpose**: Generate queries using dynamic categories from Industry Detector
- **Key Feature**: No hardcoded categories, weighted distribution
- **Cache**: 24hr

## Agent 3: AI Model Tester

- **Module**: `agents/ai_model_tester_agent/`
- **Nodes**: 3 (initialize, test batch, finalize)
- **Purpose**: Test queries across multiple AI models
- **Models**: ChatGPT, Gemini, Claude, Llama, Grok, DeepSeek
- **Cache**: 1hr per query+model

## Agent 4: Scorer Analyzer

- **Module**: `agents/scorer_analyzer_agent/`
- **Nodes**: 4 (initialize, analyze, calculate, finalize)
- **Purpose**: Calculate visibility score with hybrid matching
- **Method**: Exact string + semantic (ChromaDB, threshold 0.70)
- **Output**: Score (0-100) + detailed report

## Agent 5: Visibility Orchestrator

- **Module**: `agents/visibility_orchestrator/`
- **Nodes**: 7 (with category looping)
- **Purpose**: Orchestrate agents 2-4 with category-based batching
- **Key Feature**: Progressive results, streams after each category
- **Flow**: For each category → generate → test → analyze → aggregate → loop

## Workflow

```
Phase 1: Company Analysis
  └─> Industry Detector

Phase 2: Visibility Analysis
  └─> Visibility Orchestrator
      ├─> Query Generator (per category)
      ├─> AI Model Tester (per category)
      └─> Scorer Analyzer (per category)
```

## All Agents Use LangGraph

- Modular node-based workflows
- Observable state flow
- Non-blocking error handling
- Progress streaming support
- Singleton graph instances
