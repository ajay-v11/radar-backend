"""
Node functions for the query generator LangGraph workflow.
"""

import logging
import json
from typing import Dict, List
from langchain_core.messages import SystemMessage, HumanMessage

from agents.query_generator_agent.models import QueryGeneratorState, CategoryQueries
from agents.query_generator_agent.utils import (
    get_query_generation_llm,
    deduplicate_queries,
    distribute_queries
)

logger = logging.getLogger(__name__)

MAX_COMPETITORS_IN_CONTEXT = 5


def check_cache(state: QueryGeneratorState) -> QueryGeneratorState:
    """Node: Skip cache check - using route-level caching only."""
    # No caching at agent level
    return state


def calculate_distribution(state: QueryGeneratorState) -> QueryGeneratorState:
    """Node: Calculate query distribution across categories."""
    logger.info("📊 Calculating query distribution...")
    
    num_queries = state["num_queries"]
    query_categories_template = state.get("query_categories_template", {})
    errors = state.get("errors", [])
    
    if not query_categories_template:
        error_msg = "No query categories template provided"
        errors.append(error_msg)
        logger.error(error_msg)
        state["errors"] = errors
        state["category_distribution"] = {}
        return state
    
    distribution = distribute_queries(num_queries, query_categories_template)
    
    logger.info(f"✓ Distribution calculated: {distribution}")
    state["category_distribution"] = distribution
    state["errors"] = errors
    
    return state


def generate_category_queries(state: QueryGeneratorState) -> QueryGeneratorState:
    """Node: Generate queries for each category."""
    logger.info("🎯 Generating queries for all categories...")
    
    category_distribution = state.get("category_distribution", {})
    query_categories_template = state.get("query_categories_template", {})
    industry = state["industry"]
    company_name = state["company_name"]
    company_description = state.get("company_description", "")
    company_summary = state.get("company_summary", "")
    competitors = state.get("competitors", [])
    llm_provider = state.get("llm_provider") or settings.QUERY_GENERATION_PROVIDER
    errors = state.get("errors", [])
    
    if not category_distribution:
        error_msg = "No category distribution calculated"
        errors.append(error_msg)
        state["errors"] = errors
        state["queries"] = []
        state["query_categories"] = {}
        return state
    
    llm = get_query_generation_llm(llm_provider)
    if not llm:
        error_msg = f"Could not initialize {llm_provider} LLM"
        errors.append(error_msg)
        state["errors"] = errors
        state["queries"] = []
        state["query_categories"] = {}
        return state
    
    all_queries = []
    query_categories = {}
    
    # Generate queries for each category
    for category_key, num_category_queries in category_distribution.items():
        if num_category_queries == 0:
            continue
        
        category_info = query_categories_template.get(category_key, {})
        category_name = category_info.get("name", category_key)
        
        logger.info(f"Generating {num_category_queries} queries for {category_name}...")
        
        queries = _generate_queries_for_category(
            category_key=category_key,
            category_info=category_info,
            num_queries=num_category_queries,
            industry=industry,
            company_name=company_name,
            company_description=company_description,
            company_summary=company_summary,
            competitors=competitors,
            llm=llm,
            errors=errors
        )
        
        query_categories[category_key] = {
            "name": category_name,
            "queries": queries
        }
        all_queries.extend(queries)
        
        logger.info(f"✓ Generated {len(queries)} queries for {category_name}")
    
    # Deduplicate across all categories
    all_queries = deduplicate_queries(all_queries)
    
    logger.info(f"✓ Total queries generated: {len(all_queries)}")
    
    state["queries"] = all_queries
    state["query_categories"] = query_categories
    state["errors"] = errors
    
    return state


def _generate_queries_for_category(
    category_key: str,
    category_info: Dict,
    num_queries: int,
    industry: str,
    company_name: str,
    company_description: str,
    company_summary: str,
    competitors: List[str],
    llm,
    errors: List[str]
) -> List[str]:
    """Generate queries for a specific category using LLM."""
    
    if num_queries == 0:
        return []
    
    try:
        # Build context WITHOUT brand names
        context = f"""Industry: {industry}
Description: {company_description or company_summary or "Not provided"}"""
        
        category_name = category_info.get("name", category_key)
        category_description = category_info.get("description", "")
        category_examples = category_info.get("examples", [])
        
        # Request extra queries to account for filtering
        num_queries_to_generate = int(num_queries * 1.5)  # Generate 50% more to account for filtering
        
        prompt = f"""Generate {num_queries_to_generate} search queries for the "{category_name}" category.

Category Description: {category_description}
Category Examples: {', '.join(category_examples)}

Industry Context:
{context}

🚨 CRITICAL REQUIREMENTS - READ CAREFULLY:
1. Generate exactly {num_queries_to_generate} unique queries
2. Queries should represent real user search intent in 2025
3. Make queries specific to the {industry} industry
4. **ABSOLUTELY NO BRAND NAMES ALLOWED** - Zero tolerance policy
5. Do NOT mention ANY company names, brand names, or specific business names
6. All queries must be 100% GENERIC and open-ended
7. Use natural language that real users would type
8. Vary query length and style (questions, phrases, statements)
9. Focus on buyer intent and decision-making queries
10. For comparison queries, use ONLY generic phrases like:
   - "best sites for..."
   - "top platforms to..."
   - "compare online stores for..."
   - "which website is better for..."
   - "list of best services for..."
   - "where to find..."

GOOD EXAMPLES (100% generic, no brand names):
✅ "best online marketplace for electronics"
✅ "where to buy affordable smartphones online"
✅ "top e-commerce sites in India"
✅ "compare online shopping platforms for fashion"
✅ "which website has best deals on laptops"
✅ "list of best sites to buy home appliances"
✅ "customer reviews for online shopping platforms"
✅ "most reliable e-commerce sites for electronics"
✅ "affordable meal kit delivery services"
✅ "best grocery delivery apps"

BAD EXAMPLES (contain brand names - NEVER DO THIS):
❌ "Flipkart customer reviews"
❌ "Amazon smartphone deals"
❌ "Amazon vs Snapdeal comparison"
❌ "Myntra vs Ajio fashion"
❌ "HelloFresh meal kits"
❌ "Blue Apron reviews"

Return ONLY a JSON array of query strings:
["query 1", "query 2", ...]"""

        messages = [
            SystemMessage(content=f"You are an expert SEO and search intent analyst. Generate realistic search queries that users would type when searching for products/services in the {industry} industry. CRITICAL RULE: Do NOT mention ANY brand names, company names, or specific business names whatsoever. All queries must be 100% generic. Always respond with valid JSON array."),
            HumanMessage(content=prompt)
        ]
        
        response = llm.invoke(messages)
        result_text = response.content
        
        if not result_text:
            error_msg = f"LLM returned empty response for {category_key}"
            errors.append(error_msg)
            logger.error(error_msg)
            return []
        
        # Strip markdown code blocks if present
        if result_text.startswith("```"):
            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            elif result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
        
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON for {category_key}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"{error_msg}. Response: {result_text[:200]}")
            return []
        
        # Handle different response formats
        queries = []
        if isinstance(result, dict):
            queries = result.get("queries") or result.get("items") or result.get("results") or []
            
            if not queries and result:
                if all(k.isdigit() for k in result.keys()):
                    queries = [result[k] for k in sorted(result.keys(), key=int)]
                else:
                    for value in result.values():
                        if isinstance(value, list):
                            queries = value
                            break
        elif isinstance(result, list):
            queries = result
        else:
            error_msg = f"Unexpected response format for {category_key}: {type(result)}"
            errors.append(error_msg)
            logger.error(error_msg)
            return []
        
        # Validate and clean queries
        if not isinstance(queries, list):
            error_msg = f"Queries is not a list for {category_key}: {type(queries)}"
            errors.append(error_msg)
            logger.error(error_msg)
            return []
        
        # Build list of brand names to filter out (case-insensitive)
        brand_names_to_filter = [company_name.lower()]
        for competitor in competitors:
            brand_names_to_filter.append(competitor.lower())
        
        cleaned_queries = []
        filtered_count = 0
        
        for q in queries:
            if not isinstance(q, str) or not q.strip():
                logger.warning(f"Skipping invalid query in {category_key}: {q}")
                continue
            
            query_lower = q.strip().lower()
            
            # Check if query contains any brand names
            contains_brand = False
            for brand in brand_names_to_filter:
                if brand in query_lower:
                    contains_brand = True
                    filtered_count += 1
                    logger.warning(f"🚫 Filtered query containing brand '{brand}': {q.strip()}")
                    break
            
            if not contains_brand:
                cleaned_queries.append(q.strip())
        
        if filtered_count > 0:
            logger.warning(f"⚠️ Filtered out {filtered_count} queries containing brand names in {category_key}")
        
        if len(cleaned_queries) < num_queries:
            logger.warning(f"Generated only {len(cleaned_queries)}/{num_queries} valid queries for {category_key} (after filtering)")
        
        return cleaned_queries[:num_queries]
        
    except Exception as e:
        error_msg = f"Error generating {category_key}: {str(e)}"
        errors.append(error_msg)
        logger.error(error_msg)
        return []


def cache_results(state: QueryGeneratorState) -> QueryGeneratorState:
    """Node: Skip caching - using route-level caching only."""
    # No caching at agent level
    return state


def finalize(state: QueryGeneratorState) -> QueryGeneratorState:
    """Node: Finalize and mark as completed."""
    logger.info("✅ Query generation workflow complete")
    state["completed"] = True
    return state
