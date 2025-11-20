"""
Query Generator Agent

This agent generates industry-specific search queries for AI model testing
using OpenAI to create contextual, category-based queries that represent
real buyer intent.
"""

import logging
from typing import List, Dict, Generator, Tuple, Optional
from openai import OpenAI
from models.schemas import WorkflowState
from config.settings import settings
import json
import hashlib

logger = logging.getLogger(__name__)


def _get_query_cache_key(company_url: str, num_queries: int) -> str:
    """Generate cache key for query results."""
    # Normalize URL (remove trailing slash for consistency)
    normalized_url = company_url.rstrip('/')
    key = f"{normalized_url}:{num_queries}"
    cache_key = f"queries:{hashlib.md5(key.encode()).hexdigest()}"
    logger.debug(f"Cache key for {normalized_url} ({num_queries}): {cache_key}")
    return cache_key


def _get_cached_queries(company_url: str, num_queries: int) -> Optional[Dict]:
    """Get cached query results."""
    try:
        from config.database import get_redis_client
        redis_client = get_redis_client()
        cache_key = _get_query_cache_key(company_url, num_queries)
        cached = redis_client.get(cache_key)
        if cached:
            logger.info(f"Cache HIT for queries: {company_url} ({num_queries} queries)")
            # Redis returns bytes, decode if needed
            if isinstance(cached, bytes):
                cached = cached.decode('utf-8')
            return json.loads(cached)
        logger.debug(f"Cache MISS for queries: {company_url} ({num_queries} queries)")
        return None
    except Exception as e:
        logger.warning(f"Cache retrieval failed: {e}")
        return None


def _cache_queries(company_url: str, num_queries: int, queries: List[str], query_categories: Dict, ttl: int = 86400) -> None:
    """Cache query results (24 hour TTL by default)."""
    try:
        from config.database import get_redis_client
        redis_client = get_redis_client()
        cache_key = _get_query_cache_key(company_url, num_queries)
        cache_data = {
            "queries": queries,
            "query_categories": query_categories
        }
        redis_client.setex(cache_key, ttl, json.dumps(cache_data))
        logger.info(f"Cached queries for: {company_url} ({num_queries} queries)")
    except Exception as e:
        logger.warning(f"Cache storage failed: {e}")

# Industry-specific query categories with realistic weights
INDUSTRY_CATEGORIES = {
    "food_services": {
        "comparison": {
            "name": "Comparison",
            "weight": 0.30,
            "description": "Direct brand comparisons and vs queries",
            "examples": ["HelloFresh vs Blue Apron", "Factor vs Home Chef pricing"]
        },
        "product_selection": {
            "name": "Product Selection",
            "weight": 0.25,
            "description": "Finding and choosing meal delivery services",
            "examples": ["best meal kits for families", "top organic meal delivery"]
        },
        "dietary_needs": {
            "name": "Dietary & Health",
            "weight": 0.20,
            "description": "Specific dietary requirements and health goals",
            "examples": ["keto meal delivery", "vegan meal kits", "gluten-free options"]
        },
        "best_of": {
            "name": "Best-of Lists",
            "weight": 0.15,
            "description": "Ranked lists and top recommendations",
            "examples": ["top 10 meal delivery 2025", "best meal kits ranked"]
        },
        "how_to": {
            "name": "How-to & Educational",
            "weight": 0.10,
            "description": "Learning about meal kits and subscriptions",
            "examples": ["how meal kits work", "how to cancel subscription"]
        }
    },
    "technology": {
        "comparison": {
            "name": "Comparison",
            "weight": 0.35,
            "description": "Feature and pricing comparisons between tools",
            "examples": ["Slack vs Teams", "Notion vs Confluence pricing"]
        },
        "use_cases": {
            "name": "Use Cases",
            "weight": 0.25,
            "description": "Specific business problems and solutions",
            "examples": ["best CRM for startups", "project management for remote teams"]
        },
        "integration": {
            "name": "Integration & Setup",
            "weight": 0.20,
            "description": "How to integrate and configure tools",
            "examples": ["how to integrate Salesforce with Slack", "setup guide"]
        },
        "best_of": {
            "name": "Best-of Lists",
            "weight": 0.12,
            "description": "Top software rankings and reviews",
            "examples": ["best SaaS tools 2025", "top 10 CRM platforms"]
        },
        "pricing": {
            "name": "Pricing & Plans",
            "weight": 0.08,
            "description": "Cost and pricing information",
            "examples": ["Salesforce pricing", "cheapest project management tool"]
        }
    },
    "retail": {
        "comparison": {
            "name": "Comparison",
            "weight": 0.28,
            "description": "Brand and product comparisons",
            "examples": ["Nike vs Adidas", "Amazon vs Walmart prices"]
        },
        "product_selection": {
            "name": "Product Selection",
            "weight": 0.30,
            "description": "Finding specific products",
            "examples": ["best running shoes", "top rated backpacks"]
        },
        "reviews": {
            "name": "Reviews & Quality",
            "weight": 0.20,
            "description": "Product reviews and quality questions",
            "examples": ["are Nike shoes worth it", "Zara quality review"]
        },
        "best_of": {
            "name": "Best-of Lists",
            "weight": 0.15,
            "description": "Top product rankings",
            "examples": ["best sneakers 2025", "top 10 clothing brands"]
        },
        "deals": {
            "name": "Deals & Pricing",
            "weight": 0.07,
            "description": "Discounts and price comparisons",
            "examples": ["Nike discount codes", "cheapest place to buy"]
        }
    },
    "healthcare": {
        "comparison": {
            "name": "Comparison",
            "weight": 0.25,
            "description": "Comparing healthcare services and providers",
            "examples": ["telehealth vs in-person", "insurance plan comparison"]
        },
        "symptoms": {
            "name": "Symptoms & Conditions",
            "weight": 0.30,
            "description": "Health symptoms and medical conditions",
            "examples": ["best treatment for", "symptoms of", "how to manage"]
        },
        "provider_selection": {
            "name": "Provider Selection",
            "weight": 0.20,
            "description": "Finding healthcare providers and services",
            "examples": ["best doctors near me", "top rated clinics"]
        },
        "how_to": {
            "name": "How-to & Educational",
            "weight": 0.15,
            "description": "Medical information and procedures",
            "examples": ["how does telemedicine work", "what to expect"]
        },
        "best_of": {
            "name": "Best-of Lists",
            "weight": 0.10,
            "description": "Top healthcare services rankings",
            "examples": ["best health insurance 2025", "top hospitals"]
        }
    },
    "finance": {
        "comparison": {
            "name": "Comparison",
            "weight": 0.35,
            "description": "Financial product comparisons",
            "examples": ["Chase vs Bank of America", "Robinhood vs Fidelity"]
        },
        "product_selection": {
            "name": "Product Selection",
            "weight": 0.25,
            "description": "Choosing financial products",
            "examples": ["best credit cards", "top savings accounts"]
        },
        "how_to": {
            "name": "How-to & Educational",
            "weight": 0.20,
            "description": "Financial education and guidance",
            "examples": ["how to invest", "how to apply for loan"]
        },
        "rates": {
            "name": "Rates & Fees",
            "weight": 0.12,
            "description": "Interest rates and fee information",
            "examples": ["best mortgage rates", "lowest fee credit card"]
        },
        "best_of": {
            "name": "Best-of Lists",
            "weight": 0.08,
            "description": "Top financial services rankings",
            "examples": ["best banks 2025", "top investment apps"]
        }
    },
    "other": {
        "comparison": {
            "name": "Comparison",
            "weight": 0.30,
            "description": "Brand and service comparisons",
            "examples": ["Brand A vs Brand B", "which is better"]
        },
        "product_selection": {
            "name": "Product Selection",
            "weight": 0.25,
            "description": "Finding products or services",
            "examples": ["best services for", "top rated products"]
        },
        "problem_solving": {
            "name": "Problem-solving",
            "weight": 0.20,
            "description": "Addressing specific needs",
            "examples": ["solutions for", "how to solve"]
        },
        "best_of": {
            "name": "Best-of Lists",
            "weight": 0.15,
            "description": "Top recommendations",
            "examples": ["top 10 services", "best options 2025"]
        },
        "how_to": {
            "name": "How-to & Educational",
            "weight": 0.10,
            "description": "Learning and guidance",
            "examples": ["how to use", "what is"]
        }
    }
}


def generate_queries(state: WorkflowState, num_queries: int = None) -> WorkflowState:
    """
    Generates 20-100 industry-specific queries using OpenAI with weighted categories.
    Caches results by company URL and num_queries.
    
    This agent expects the industry detector to have already run and populated:
    - industry: Industry classification
    - company_name: Company name
    - company_description: Brief description
    - company_summary: Detailed summary
    - competitors: List of competitor names
    
    These fields are used to generate contextual, relevant queries.
    """
    if num_queries is None:
        num_queries = state.get("num_queries", 50)
    
    # Allow 20-100 queries for testing flexibility
    if num_queries < 20:
        num_queries = 20
    elif num_queries > 100:
        num_queries = 100
    
    company_url = state.get("company_url", "")
    industry = state.get("industry", "other")
    company_name = state.get("company_name", "")
    company_description = state.get("company_description", "")
    company_summary = state.get("company_summary", "")
    competitors = state.get("competitors", [])
    
    if "errors" not in state:
        state["errors"] = []
    
    errors = state["errors"]
    
    # Validate that industry detector has run
    if not industry or industry == "other":
        logger.warning("Industry not detected or set to 'other'. Query quality may be reduced.")
    
    if not company_name:
        logger.warning("Company name not provided. Queries will be generic.")
    
    # Check cache first
    cached_result = _get_cached_queries(company_url, num_queries)
    if cached_result:
        logger.info(f"Cache HIT for queries: {company_url} ({num_queries} queries)")
        state["queries"] = cached_result["queries"]
        state["query_categories"] = cached_result["query_categories"]
        return state
    
    logger.info(f"Cache MISS for queries: {company_url} ({num_queries} queries)")
    logger.info(f"Using industry data: {industry}, company: {company_name}, competitors: {len(competitors)}")
    
    all_queries = []
    query_categories = {}
    
    try:
        # Get industry-specific categories or fallback to "other"
        categories = INDUSTRY_CATEGORIES.get(industry, INDUSTRY_CATEGORIES["other"])
        
        # Calculate weighted distribution
        for category_key, category_info in categories.items():
            weight = category_info["weight"]
            category_count = int(num_queries * weight)
            
            logger.info(f"Generating {category_count} queries for {category_info['name']} (weight: {weight*100}%)")
            
            queries = _generate_category_queries(
                category_key=category_key,
                category_info=category_info,
                num_queries=category_count,
                industry=industry,
                company_name=company_name,
                company_description=company_description,
                company_summary=company_summary,
                competitors=competitors,
                errors=errors
            )
            
            query_categories[category_key] = {
                "name": category_info["name"],
                "queries": queries
            }
            all_queries.extend(queries)
        
        state["queries"] = all_queries
        state["query_categories"] = query_categories
        
        logger.info(f"Generated {len(all_queries)} queries across {len(query_categories)} categories")
        
        # Cache the results (24 hour TTL)
        _cache_queries(company_url, num_queries, all_queries, query_categories)
        
    except Exception as e:
        error_msg = f"Failed to generate queries: {str(e)}"
        errors.append(error_msg)
        logger.error(error_msg)
        state["queries"] = []
        state["query_categories"] = {}
    
    state["errors"] = errors
    return state


def _generate_category_queries(
    category_key: str,
    category_info: Dict,
    num_queries: int,
    industry: str,
    company_name: str,
    company_description: str,
    company_summary: str,
    competitors: List[str],
    errors: List[str]
) -> List[str]:
    """Generate queries for a specific category using OpenAI."""
    
    if not settings.OPENAI_API_KEY:
        errors.append("OpenAI API key not configured")
        return []
    
    if num_queries == 0:
        return []
    
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        context = f"""Industry: {industry}
Company: {company_name}
Description: {company_description or company_summary or "Not provided"}"""
        
        if competitors:
            context += f"\nMain Competitors: {', '.join(competitors[:5])}"
        
        prompt = f"""Generate {num_queries} search queries for the "{category_info['name']}" category.

Category Description: {category_info['description']}
Category Examples: {', '.join(category_info['examples'])}

Company Context:
{context}

Requirements:
1. Generate exactly {num_queries} unique queries
2. Queries should represent real user search intent in 2025
3. Make queries specific to the {industry} industry
4. For comparison queries, include competitor names when relevant
5. Use natural language that real users would type
6. Vary query length and style (questions, phrases, statements)
7. Focus on buyer intent and decision-making queries

Return ONLY a JSON array of query strings:
["query 1", "query 2", ...]"""

        response = client.chat.completions.create(
            model=settings.INDUSTRY_ANALYSIS_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert SEO and search intent analyst. Generate realistic search queries that users would type. Always respond with valid JSON array."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.8,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        if not result_text:
            errors.append(f"OpenAI returned empty response for {category_key}")
            return []
        
        result = json.loads(result_text)
        
        # Handle different response formats
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
            queries = []
        
        queries = [q.strip() for q in queries if isinstance(q, str) and q.strip()]
        
        if len(queries) < num_queries:
            logger.warning(f"Generated only {len(queries)}/{num_queries} for {category_key}")
        
        return queries[:num_queries]
        
    except json.JSONDecodeError as e:
        error_msg = f"JSON parse error for {category_key}: {str(e)}"
        errors.append(error_msg)
        logger.error(error_msg)
        return []
    except Exception as e:
        error_msg = f"Error generating {category_key}: {str(e)}"
        errors.append(error_msg)
        logger.error(error_msg)
        return []


def generate_queries_stream(state: WorkflowState, num_queries: int = None) -> Generator[Tuple[str, str, List[str]], None, WorkflowState]:
    """Generator version that yields queries as they're generated for streaming."""
    
    if num_queries is None:
        num_queries = state.get("num_queries", 50)
    
    # Allow 20-100 queries for testing flexibility
    if num_queries < 20:
        num_queries = 20
    elif num_queries > 100:
        num_queries = 100
    
    industry = state.get("industry", "other")
    company_name = state.get("company_name", "")
    company_description = state.get("company_description", "")
    company_summary = state.get("company_summary", "")
    competitors = state.get("competitors", [])
    
    if "errors" not in state:
        state["errors"] = []
    
    errors = state["errors"]
    all_queries = []
    query_categories = {}
    
    try:
        categories = INDUSTRY_CATEGORIES.get(industry, INDUSTRY_CATEGORIES["other"])
        
        for category_key, category_info in categories.items():
            weight = category_info["weight"]
            category_count = int(num_queries * weight)
            
            logger.info(f"Generating {category_count} queries for {category_info['name']}")
            
            queries = _generate_category_queries(
                category_key=category_key,
                category_info=category_info,
                num_queries=category_count,
                industry=industry,
                company_name=company_name,
                company_description=company_description,
                company_summary=company_summary,
                competitors=competitors,
                errors=errors
            )
            
            query_categories[category_key] = {
                "name": category_info["name"],
                "queries": queries
            }
            all_queries.extend(queries)
            
            # Yield category and queries for streaming
            yield (category_key, category_info["name"], queries)
        
        state["queries"] = all_queries
        state["query_categories"] = query_categories
        
        logger.info(f"Generated {len(all_queries)} queries across {len(query_categories)} categories")
        
    except Exception as e:
        error_msg = f"Failed to generate queries: {str(e)}"
        errors.append(error_msg)
        logger.error(error_msg)
        state["queries"] = []
        state["query_categories"] = {}
    
    state["errors"] = errors
    return state
