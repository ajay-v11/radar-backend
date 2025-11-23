"""
Utility functions for industry detection agent.

Contains caching, scraping, LLM initialization, and helper functions.
"""

from typing import Dict, List, Optional
from models.schemas import WorkflowState
from config.settings import settings
from utils.competitor_matcher import get_competitor_matcher
from utils.vector_store import get_vector_store

import json
import logging
import hashlib
import time

logger = logging.getLogger(__name__)

# Constants
MAX_SCRAPED_CONTENT_LENGTH = 5000
MAX_FALLBACK_CONTENT_LENGTH = 1000
SCRAPE_CACHE_TTL = 86400  # 24 hours
OPENAI_TIMEOUT = 30.0

# Removed hardcoded industry constraints - now using dynamic LLM-based classification


# Caching functions
def get_industry_analysis_cache_key(url: str, llm_provider: str, competitor_urls: Dict[str, str]) -> str:
    """Generate cache key for complete industry analysis."""
    competitor_str = json.dumps(sorted(competitor_urls.items())) if competitor_urls else ""
    key = f"{url}:{llm_provider}:{competitor_str}"
    return f"industry_analysis:{hashlib.sha256(key.encode()).hexdigest()}"


def get_cached_industry_analysis(url: str, llm_provider: str, competitor_urls: Dict[str, str]) -> Optional[Dict]:
    """Get cached industry analysis result."""
    try:
        from config.database import get_redis_client
        redis_client = get_redis_client()
        cache_key = get_industry_analysis_cache_key(url, llm_provider, competitor_urls)
        cached = redis_client.get(cache_key)
        if cached:
            logger.info(f"Cache HIT for industry analysis: {url} (provider={llm_provider})")
            if isinstance(cached, bytes):
                cached = cached.decode('utf-8')
            return json.loads(cached)
        logger.debug(f"Cache MISS for industry analysis: {url} (provider={llm_provider})")
        return None
    except Exception as e:
        logger.warning(f"Industry analysis cache retrieval failed: {e}")
        return None


def cache_industry_analysis(url: str, llm_provider: str, competitor_urls: Dict[str, str], state: WorkflowState) -> None:
    """Cache complete industry analysis result."""
    try:
        from config.database import get_redis_client
        redis_client = get_redis_client()
        cache_key = get_industry_analysis_cache_key(url, llm_provider, competitor_urls)
        
        cache_data = {
            "company_name": state.get("company_name", ""),
            "company_description": state.get("company_description", ""),
            "company_summary": state.get("company_summary", state.get("company_description", "")),
            "target_region": state.get("target_region", "United States"),
            "industry": state.get("industry", "other"),
            "broad_category": state.get("broad_category", "Other"),
            "industry_description": state.get("industry_description", ""),
            "extraction_template": state.get("extraction_template", {}),
            "query_categories_template": state.get("query_categories_template", {}),
            "competitors": state.get("competitors", []),
            "competitors_data": state.get("competitors_data", []),
            "product_category": state.get("product_category", ""),
            "market_keywords": state.get("market_keywords", []),
            "target_audience": state.get("target_audience", ""),
            "brand_positioning": state.get("brand_positioning", {}),
            "buyer_intent_signals": state.get("buyer_intent_signals", {}),
            "industry_specific": state.get("industry_specific", {}),
            "errors": state.get("errors", [])
        }
        
        redis_client.setex(cache_key, SCRAPE_CACHE_TTL, json.dumps(cache_data))
        logger.info(f"Cached industry analysis for: {url} (provider={llm_provider})")
    except Exception as e:
        logger.warning(f"Industry analysis cache storage failed: {e}")


def get_scrape_cache_key(url: str) -> str:
    """Generate cache key for scraped content."""
    return f"scrape:{hashlib.sha256(url.encode()).hexdigest()}"


def get_cached_scrape(url: str) -> Optional[str]:
    """Get cached scraped content."""
    try:
        from config.database import get_redis_client
        redis_client = get_redis_client()
        cache_key = get_scrape_cache_key(url)
        cached = redis_client.get(cache_key)
        if cached:
            logger.info(f"Cache HIT for scrape: {url}")
            return cached
        logger.debug(f"Cache MISS for scrape: {url}")
        return None
    except Exception as e:
        logger.warning(f"Cache retrieval failed: {e}")
        return None


def cache_scrape(url: str, content: str) -> None:
    """Cache scraped content."""
    try:
        from config.database import get_redis_client
        redis_client = get_redis_client()
        cache_key = get_scrape_cache_key(url)
        redis_client.setex(cache_key, SCRAPE_CACHE_TTL, content)
        logger.debug(f"Cached scrape for: {url}")
    except Exception as e:
        logger.warning(f"Cache storage failed: {e}")


# Scraping functions
def scrape_website(url: str, errors: List[str], full_content: bool = False) -> str:
    """Scrape website content using Firecrawl with caching.
    
    Args:
        url: Website URL to scrape
        errors: List to append error messages to
        full_content: If True, return full content. If False, limit to MAX_SCRAPED_CONTENT_LENGTH
        
    Returns:
        Scraped content in markdown format
    """
    cached_content = get_cached_scrape(url)
    if cached_content:
        return cached_content
    
    if not settings.FIRECRAWL_API_KEY:
        errors.append("Firecrawl API key not configured")
        return ""
    
    try:
        from firecrawl import Firecrawl
        
        firecrawl = Firecrawl(api_key=settings.FIRECRAWL_API_KEY)
        
        strategies = [
            {"formats": ["markdown"], "only_main_content": True, "timeout": 30000},
            {"formats": ["markdown"], "only_main_content": False, "timeout": 30000},
            {"formats": ["markdown"], "only_main_content": True, "timeout": 60000}
        ]
        
        last_error = None
        for i, strategy in enumerate(strategies, 1):
            try:
                logger.info(f"Attempting scrape strategy {i}/{len(strategies)} for {url}")
                result = firecrawl.scrape(url=url, **strategy)
                
                markdown_content = None
                if hasattr(result, 'markdown') and result.markdown:
                    markdown_content = result.markdown
                elif isinstance(result, dict) and "markdown" in result:
                    markdown_content = result["markdown"]
                
                if markdown_content:
                    # Apply length limit only if full_content is False
                    content = markdown_content if full_content else markdown_content[:MAX_SCRAPED_CONTENT_LENGTH]
                    cache_scrape(url, content)
                    logger.info(f"Successfully scraped {len(content)} characters from {url}")
                    return content
                else:
                    logger.warning(f"Strategy {i} returned no markdown content")
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Strategy {i} failed: {last_error}")
                if i < len(strategies):
                    time.sleep(2)
                continue
        
        error_msg = f"All scraping strategies failed for {url}. Last error: {last_error}"
        errors.append(error_msg)
        logger.error(error_msg)
        return ""
            
    except ImportError:
        errors.append("Firecrawl package not installed")
        logger.error("Firecrawl package not installed")
        return ""
    except Exception as e:
        errors.append(f"Firecrawl scraping error: {str(e)}")
        logger.error(f"Firecrawl scraping error: {str(e)}")
        return ""


# LLM functions
def get_analysis_llm(llm_provider: str = None):
    """
    Get LLM instance for analysis tasks.
    
    Args:
        llm_provider: Provider name (openai, claude, gemini, llama, grok, deepseek)
                     If None, uses INDUSTRY_ANALYSIS_PROVIDER from settings
    
    Returns:
        LangChain LLM instance or None if provider not available
    """
    if llm_provider is None:
        llm_provider = settings.INDUSTRY_ANALYSIS_PROVIDER
    
    llm_provider = llm_provider.lower()
    
    try:
        if llm_provider == "claude":
            if not settings.ANTHROPIC_API_KEY:
                logger.error("Anthropic API key not configured")
                return None
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=settings.CLAUDE_MODEL,
                anthropic_api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.7,
                max_tokens=4000,
                timeout=60.0
            )
        
        elif llm_provider == "openai":
            if not settings.OPENAI_API_KEY:
                logger.error("OpenAI API key not configured")
                return None
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.CHATGPT_MODEL,
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0.7,
                max_tokens=4000,
                timeout=60.0
            )
        
        elif llm_provider == "gemini":
            if not settings.GEMINI_API_KEY:
                logger.error("Gemini API key not configured")
                return None
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.7,
                max_output_tokens=4000
            )
        
        elif llm_provider == "llama":
            if not settings.GROK_API_KEY:
                logger.error("Groq API key not configured")
                return None
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.GROQ_LLAMA_MODEL,
                openai_api_key=settings.GROK_API_KEY,
                openai_api_base="https://api.groq.com/openai/v1",
                temperature=0.7,
                max_tokens=4000,
                timeout=60.0
            )
        
        elif llm_provider == "grok":
            if not settings.OPEN_ROUTER_API_KEY:
                logger.error("OpenRouter API key not configured")
                return None
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.OPENROUTER_GROK_MODEL,
                openai_api_key=settings.OPEN_ROUTER_API_KEY,
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=0.7,
                max_tokens=4000,
                timeout=60.0
            )
        
        elif llm_provider == "deepseek":
            if not settings.OPEN_ROUTER_API_KEY:
                logger.error("OpenRouter API key not configured")
                return None
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.OPENROUTER_DEEPSEEK_MODEL,
                openai_api_key=settings.OPEN_ROUTER_API_KEY,
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=0.7,
                max_tokens=4000,
                timeout=60.0
            )
        
        else:
            logger.error(f"Unknown LLM provider: {llm_provider}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to initialize {llm_provider} LLM: {str(e)}")
        return None


# Removed fallback keyword detection - using pure LLM-based approach


def store_company_data(state: WorkflowState, scraped_content: str) -> List[str]:
    """Store company data and competitors in vector database."""
    errors = []
    
    try:
        company_name = state.get("company_name", "")
        if not company_name:
            logger.debug("No company name provided, skipping vector storage")
            return errors
        
        vector_store = get_vector_store()
        vector_store.store_company(
            company_name=company_name,
            company_url=state.get("company_url", ""),
            scraped_content=scraped_content,
            industry=state.get("industry", "other"),
            description=state.get("company_description", ""),
            metadata={"summary": state.get("company_summary", "")}
        )
        
        competitors = state.get("competitors", [])
        competitors_data = state.get("competitors_data", [])
        
        if competitors:
            competitor_matcher = get_competitor_matcher()
            
            descriptions = {}
            metadata_extra = {}
            
            if competitors_data:
                for comp_data in competitors_data:
                    comp_name = comp_data.get("name", "")
                    if comp_name:
                        descriptions[comp_name] = comp_data.get("description", "")
                        metadata_extra[comp_name] = {
                            "products": comp_data.get("products", ""),
                            "positioning": comp_data.get("positioning", "")
                        }
            
            competitor_matcher.store_competitors(
                company_name=company_name,
                competitors=competitors,
                industry=state.get("industry", "other"),
                descriptions=descriptions,
                metadata_extra=metadata_extra
            )
    
    except Exception as e:
        error_msg = f"Failed to store company data in vector DB: {str(e)}"
        errors.append(error_msg)
        logger.error(error_msg)
    
    return errors
