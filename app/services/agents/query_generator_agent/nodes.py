"""
Node functions for the query generator LangGraph workflow.
"""

import logging
import json
from typing import Dict, List
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config.settings import settings
from app.services.agents.query_generator_agent.models import QueryGeneratorState
from app.services.agents.query_generator_agent.utils import (
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
        category_name = category_info.get("name", category_key)
        category_description = category_info.get("description", "")
        include_brands = category_info.get("include_brands", False)
        category_examples = category_info.get("examples", [])
        
        # Branch logic based on whether brands are allowed
        if include_brands:
            # Brand-specific category - company name MUST be present, can include competitors
            competitors_context = f"\nCompetitors: {', '.join(competitors[:5])}" if competitors else ""
            
            prompt = f"""Generate {num_queries} brand-specific search queries that ALL mention "{company_name}".

Company: {company_name}{competitors_context}

STRICT REQUIREMENTS:
1. Generate exactly {num_queries} unique queries
2. EVERY query MUST include "{company_name}" as the primary brand
3. Use natural language that real users would type in 2025
4. Include variations like:
   - "{company_name} reviews"
   - "what is {company_name}"
   - "{company_name} alternatives"
   - "is {company_name} worth it"
   - "{company_name} pricing"
   - "how does {company_name} work"
   - "{company_name} vs [competitor]" (company name FIRST)
   - "{company_name} features"
   - "best {company_name} plans"
   - "{company_name} compared to [competitor]" (company name FIRST)

For comparison queries, ALWAYS put {company_name} first, then the competitor.

Return ONLY a JSON array of query strings:
["query 1", "query 2", ...]"""

            messages = [
                SystemMessage(content=f"You are an SEO expert. Generate queries where '{company_name}' is ALWAYS mentioned. For comparison queries, always put {company_name} first. Respond with valid JSON array only."),
                HumanMessage(content=prompt)
            ]
        else:
            # Generic category - NO brand names allowed
            examples_text = "\n".join([f"✅ {ex}" for ex in category_examples[:3]]) if category_examples else ""
            
            prompt = f"""Generate {num_queries} GENERIC search queries for the "{category_name}" category.

Category: {category_description}
Industry: {industry}

STRICT REQUIREMENTS:
1. Generate exactly {num_queries} unique queries
2. Queries should represent real user search intent in 2025
3. Make queries specific to the {industry} industry
4. Use natural language that real users would type
5. Vary query length and style (questions, phrases, statements)
6. Focus on buyer intent and decision-making queries
7. **ABSOLUTELY NO BRAND NAMES** - Keep all queries generic and industry-focused
8. Do NOT mention any company names, website names, or specific brands

{f"Good Examples:{chr(10)}{examples_text}" if examples_text else ""}

Return ONLY a JSON array of query strings:
["query 1", "query 2", ...]"""

            messages = [
                SystemMessage(content=f"You are an SEO expert generating GENERIC search queries for the {industry} industry. NEVER mention any specific brand, company, or website names. Keep everything generic. Respond with valid JSON array only."),
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
        
        cleaned_queries = []
        for q in queries:
            if isinstance(q, str) and q.strip():
                cleaned_queries.append(q.strip())
            else:
                logger.warning(f"Skipping invalid query in {category_key}: {q}")
        
        if len(cleaned_queries) < num_queries:
            logger.warning(f"Generated only {len(cleaned_queries)}/{num_queries} valid queries for {category_key}")
        
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
