# 🧠 AI Visibility Score – Full Problem Specification

**Goal:** Build a system that measures how visible a brand is across AI model responses for industry-relevant user queries.

---

## 🎯 Problem Overview

Brands have **no idea** how often they are mentioned by AI models when users ask buying-intent or category-relevant questions.  
Traditional SEO doesn't measure AI visibility, so we need an **AI Visibility Score** system.

The system will:

- Detect the brand’s industry
- Generate realistic buyer-intent queries (50–100)
- Test these queries across AI models
- Track whether the brand is mentioned, and who is ranked
- Generate a complete transparent report

---

## 🧩 Inputs & Outputs

### **Input**

- **Brand Name**
- **Website URL**

### **Output**

A **Comprehensive AI Visibility Report** with:

- Overall visibility score (0–100%)
- Breakdown by query type
- Competitor ranking by mentions
- Full query log (every single query tested)
- Exportable CSV/Excel

---

## 🚀 Required Functionality

### **1. Industry Detection**

- Scrape/analyze the brand’s website.
- Extract:
  - Industry
  - Product category
  - Target audience
  - Market keywords
- Derive **search contexts** (e.g., "meal kits", "healthy meal plans", etc.)

---

### **2. Query Generation Engine**

Generate **50–100 industry-specific buyer intent queries**.

Categories:

- **Comparison queries**  
  _“best meal kits for weight loss 2025”_
- **Best-of queries**  
  _“top organic meal delivery services”_
- **How-to queries**  
  _“how to choose a meal delivery service”_
- **Product selection queries**  
  _“meal kits with vegetarian options”_

Requirements:

- Not generic
- Must reflect **real consumer search behavior**

---

### **3. AI Model Testing**

For each query:

- Test it against **at least 2 AI models**
  - ChatGPT
  - Claude
  - Gemini
  - Perplexity
- Store:
  - Did brand appear? (Yes/No)
  - Rank/position in the answer
  - Competitors mentioned
  - Model used
  - Full text of the response (optional but useful)

---

### **4. Analysis & Scoring**

#### **Overall Visibility Score**

Visibility % = (# queries where brand is mentioned / total queries) × 100

#### **Breakdown by Query Type**

Example:
| Query Type | Total | Mentioned | Visibility |
|------------|--------|------------|------------|
| Product Selection | 20 | 9 | 45% |
| Comparison | 15 | 3 | 20% |

#### **Competitor Rankings**

Rank competitors based on:

- Frequency of appearance
- Rank positions
- Which query types they dominate

#### **Complete Query Log**

For each query, show:

- Query text
- Brand mentioned? (Yes/No)
- Rank
- Competitors in result
- Model tested

Must show **all queries**, not summaries.

---

## 📊 Sample Final Report (Example Format)

### 🟩 **AI Visibility Report: FreshBox Meal Kits**

**Overall Visibility:** 34% (17/50 queries)

---

### 📂 **Breakdown by Query Type**

#### **Product Selection (20 queries)**

- Visibility: **45%** (9/20)
- **Top Competitors:**
  1. HelloFresh (18/20 – 90%)
  2. Blue Apron (16/20 – 80%)
  3. FreshBox (9/20 – 45%)

#### **Comparison Queries (15 queries)**

- Visibility: **20%** (3/15)
- Example NOT mentioned:
  - _“best meal kits for weight loss 2025”_  
    → Competitors: Factor, Trifecta, HelloFresh

---

### 🧾 **Queries Tested (Sample)**

| Query                             | Mentioned? | Rank   | Competitors                      | Model   |
| --------------------------------- | ---------- | ------ | -------------------------------- | ------- |
| organic meal delivery services    | ✓ Yes      | Rank 3 | HelloFresh, Blue Apron           | ChatGPT |
| budget-friendly meal kits         | ✗ No       | —      | Dinnerly, EveryPlate, HelloFresh | Claude  |
| meal kits with vegetarian options | ✓ Yes      | Rank 2 | HelloFresh, Purple Carrot        | Gemini  |

---

## 🧠 Recommendations Engine (Optional)

- Improve comparison-query visibility
- Strengthen budget-focused visibility
- Target competitor-dominated clusters

---

## 📤 Required Deliverables

Your system must output:

- [x] Overall AI visibility score
- [x] Breakdown by category
- [x] Competitor rankings
- [x] **A complete query log (all 50–100 queries)**
- [x] Multi-model comparison
- [x] Exportable CSV/Excel
- [x] Clear, structured report

---

## 🛠️ Additional Optional Enhancements

- Sentiment analysis of mentions
- Historical tracking
- Intent classification
- Query clustering
- Model-to-model visibility comparisons

---

# ✅ End of Specification

This markdown file defines the full scope required to build an AI Visibility Score system.
