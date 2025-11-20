"""
Query Generation Controller

Handles query generation logic with streaming support.
"""

import json
import logging
from typing import Optional, AsyncGenerator

from agents.industry_detector import detect_industry
from agents.query_generator import generate_queries_stream as sync_generate_queries_stream
from models.schemas import WorkflowState

logger = logging.getLogger(__name__)


async def generate_queries_stream(
    company_url: str,
    company_name: Optional[str] = None,
    num_queries: int = 50
) -> AsyncGenerator[str, None]:
    """
    Generate queries with streaming updates.
    
    Args:
        company_url: Company website URL
        company_name: Optional company name
        num_queries: Number of queries to generate (50-100)
        
    Yields:
        JSON strings representing stream events
    """
    try:
        # Initialize state
        state: WorkflowState = {
            "company_url": company_url,
            "company_name": company_name or "",
            "company_description": "",
            "errors": [],
            "num_queries": num_queries
        }
        
        # Step 1: Detect industry
        yield json.dumps({
            "step": "industry_detection",
            "status": "in_progress",
            "message": "Detecting company industry..."
        })
        
        state = detect_industry(state)
        
        if state.get("industry"):
            yield json.dumps({
                "step": "industry_detection",
                "status": "completed",
                "message": f"Industry detected: {state['industry']}",
                "data": {
                    "industry": state["industry"],
                    "company_name": state.get("company_name", ""),
                    "competitors": state.get("competitors", [])
                }
            })
        else:
            yield json.dumps({
                "step": "industry_detection",
                "status": "failed",
                "message": "Failed to detect industry"
            })
            return
        
        # Step 2: Check cache FIRST
        from agents.query_generator import _get_cached_queries, _get_query_cache_key, _cache_queries
        
        cache_key = _get_query_cache_key(company_url, num_queries)
        print(f"\n{'='*60}")
        print(f"[CACHE CHECK] URL: {company_url}")
        print(f"[CACHE CHECK] Queries: {num_queries}")
        print(f"[CACHE CHECK] Key: {cache_key}")
        logger.info(f"[CACHE CHECK] URL: {company_url}, Queries: {num_queries}, Key: {cache_key}")
        
        cached_result = _get_cached_queries(company_url, num_queries)
        
        if cached_result:
            # CACHE HIT - Return instantly (no streaming needed)
            print(f"[CACHE HIT] ⚡ Returning {len(cached_result['queries'])} cached queries instantly")
            print(f"{'='*60}\n")
            logger.info(f"[CACHE HIT] Returning {len(cached_result['queries'])} cached queries instantly")
            
            yield json.dumps({
                "step": "query_generation",
                "status": "cached",
                "message": f"⚡ Using cached queries (instant retrieval)"
            })
            
            # Send all cached categories at once (instant)
            for category_key, category_data in cached_result.get("query_categories", {}).items():
                yield json.dumps({
                    "step": "category",
                    "status": "completed",
                    "message": f"Loaded {len(category_data['queries'])} cached queries for {category_data['name']}",
                    "data": {
                        "category_key": category_key,
                        "category_name": category_data["name"],
                        "queries": category_data["queries"]
                    }
                })
            
            # Update state with cached data
            state["queries"] = cached_result["queries"]
            state["query_categories"] = cached_result["query_categories"]
            
        else:
            # CACHE MISS - Generate with streaming
            print(f"[CACHE MISS] 🔄 Generating new queries with streaming")
            print(f"{'='*60}\n")
            logger.info(f"[CACHE MISS] Generating new queries with streaming")
            
            yield json.dumps({
                "step": "query_generation",
                "status": "in_progress",
                "message": f"Generating new queries..."
            })
            
            # Generate queries and stream them as they're created
            all_queries = []
            query_categories = {}
            
            # Get industry-specific categories
            from agents.query_generator import INDUSTRY_CATEGORIES
            categories = INDUSTRY_CATEGORIES.get(state.get("industry", "other"), INDUSTRY_CATEGORIES["other"])
            
            # Generate each category and stream immediately
            for category_key, category_info in categories.items():
                weight = category_info["weight"]
                category_count = int(num_queries * weight)
                
                if category_count == 0:
                    continue
                
                # Announce we're generating this category
                yield json.dumps({
                    "step": "category",
                    "status": "in_progress",
                    "message": f"Generating {category_info['name']}...",
                    "data": {
                        "category_key": category_key,
                        "category_name": category_info["name"]
                    }
                })
                
                # Generate queries for this category (this will take 2-4 seconds per category)
                from agents.query_generator import _generate_category_queries
                print(f"  [GENERATING] {category_info['name']} - {category_count} queries")
                logger.info(f"[GENERATING] {category_info['name']} - {category_count} queries")
                queries = _generate_category_queries(
                    category_key=category_key,
                    category_info=category_info,
                    num_queries=category_count,
                    industry=state.get("industry", "other"),
                    company_name=state.get("company_name", ""),
                    company_description=state.get("company_description", ""),
                    company_summary=state.get("company_summary", ""),
                    competitors=state.get("competitors", []),
                    errors=state.get("errors", [])
                )
                
                # Stream the completed queries immediately
                yield json.dumps({
                    "step": "category",
                    "status": "completed",
                    "message": f"Generated {len(queries)} queries for {category_info['name']}",
                    "data": {
                        "category_key": category_key,
                        "category_name": category_info["name"],
                        "queries": queries
                    }
                })
                
                # Store for caching
                query_categories[category_key] = {
                    "name": category_info["name"],
                    "queries": queries
                }
                all_queries.extend(queries)
            
            # Update state
            state["queries"] = all_queries
            state["query_categories"] = query_categories
            
            # Cache the results for next time
            _cache_queries(company_url, num_queries, all_queries, query_categories)
            print(f"[CACHE STORED] 💾 Cached {len(all_queries)} queries for future use\n")
            logger.info(f"[CACHE STORED] Cached {len(all_queries)} queries for future use")
        
        # Step 3: Complete
        total_queries = len(state.get("queries", []))
        yield json.dumps({
            "step": "complete",
            "status": "success",
            "message": f"Successfully generated {total_queries} queries",
            "data": {
                "total_queries": total_queries,
                "query_categories": state.get("query_categories", {})
            }
        })
        
    except Exception as e:
        logger.error(f"Error in query generation: {str(e)}")
        yield json.dumps({
            "step": "error",
            "status": "failed",
            "message": f"Error: {str(e)}"
        })
