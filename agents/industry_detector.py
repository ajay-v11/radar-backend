"""
Industry Detector Agent (Enhanced)

This agent scrapes company websites using Firecrawl, analyzes the content with OpenAI,
and classifies the company into an industry category. It also extracts company information
and identifies competitors.
"""

from typing import Dict, List, Optional
from openai import OpenAI
from models.schemas import WorkflowState
from config.settings import settings
from utils.competitor_matcher import get_competitor_matcher
from utils.vector_store import get_vector_store

import json
import logging
import hashlib
from functools import wraps
import time

logger = logging.getLogger(__name__)

# Constants for content limits and configuration
MAX_SCRAPED_CONTENT_LENGTH = 5000  # Characters to keep from scraped content
MAX_FALLBACK_CONTENT_LENGTH = 1000  # Characters for fallback keyword detection
MAX_VECTOR_STORE_CONTENT_LENGTH = 2000  # Characters for vector storage
SCRAPE_CACHE_TTL = 86400  # 24 hours in seconds
OPENAI_TIMEOUT = 30.0  # Timeout for OpenAI API calls in seconds
RETRY_MAX_ATTEMPTS = 2  # Number of retry attempts for API calls
RETRY_DELAY = 1.0  # Delay between retries in seconds

# Valid industry categories
VALID_INDUSTRIES = ["technology", "retail", "healthcare", "finance", "food_services", "other"]

# Industry keyword patterns for fallback classification
INDUSTRY_KEYWORDS: Dict[str, List[str]] = {
    "technology": [
        "software", "tech", "technology", "saas", "cloud", "ai", "artificial intelligence",
        "machine learning", "data", "analytics", "platform", "app", "application",
        "digital", "cyber", "security", "it", "information technology", "computing",
        "developer", "programming", "code", "api", "web", "mobile", "hardware",
        "semiconductor", "chip", "electronics", "automation", "robotics", "iot"
    ],
    "retail": [
        "retail", "store", "shop", "shopping", "ecommerce", "e-commerce", "marketplace",
        "fashion", "clothing", "apparel", "accessories", "consumer", "goods",
        "merchandise", "boutique", "outlet", "department store", "supermarket",
        "grocery", "convenience", "wholesale", "distribution", "supply chain"
    ],
    "healthcare": [
        "health", "healthcare", "medical", "medicine", "hospital", "clinic",
        "pharmaceutical", "pharma", "biotech", "biotechnology", "drug", "therapy",
        "treatment", "patient", "doctor", "physician", "nurse", "care", "wellness",
        "fitness", "telemedicine", "telehealth", "diagnostic", "laboratory", "lab"
    ],
    "finance": [
        "finance", "financial", "bank", "banking", "investment", "insurance",
        "fintech", "payment", "credit", "loan", "mortgage", "wealth", "asset",
        "trading", "stock", "securities", "fund", "capital", "accounting",
        "tax", "audit", "cryptocurrency", "crypto", "blockchain", "wallet"
    ],
    "food_services": [
        "food", "restaurant", "dining", "meal", "kitchen", "catering", "delivery",
        "takeout", "fast food", "cafe", "coffee", "bakery", "bar", "pub",
        "hospitality", "culinary", "chef", "recipe", "cooking", "grocery delivery",
        "meal kit", "subscription box", "prepared meals", "food service"
    ]
}


def detect_industry(state: WorkflowState) -> WorkflowState:
    """
    Enhanced industry detection using Firecrawl and OpenAI.
    
    This function:
    1. Scrapes the company website using Firecrawl
    2. Uses OpenAI to analyze the content and extract:
       - Company name (if not provided)
       - Company description/summary
       - Industry classification
       - List of competitors
    
    Args:
        state: WorkflowState containing company_url and optionally company_name
        
    Returns:
        Updated WorkflowState with industry, company_name, company_description,
        company_summary, competitors, and scraped_content populated
        
    Requirements:
        - 3.1: Scrape company website and analyze content
        - 3.2: Use AI to classify industry and extract information
        - 3.3: Identify competitors in the same industry
        - 3.4: Return comprehensive company profile to workflow state
    """
    company_url = state.get("company_url", "")
    company_name = state.get("company_name", "")
    company_description = state.get("company_description", "")
    errors = state.get("errors", [])
    
    if not company_url:
        errors.append("No company URL provided")
        state["errors"] = errors
        state["industry"] = "other"
        return state
    
    # Check if complete industry analysis is cached
    cached_analysis = _get_cached_industry_analysis(company_url)
    if cached_analysis:
        logger.info(f"Cache HIT for industry analysis: {company_url}")
        # Merge cached data into state
        state.update(cached_analysis)
        return state
    
    # Step 1: Scrape website content using Firecrawl
    scraped_content = _scrape_website(company_url, errors)
    state["scraped_content"] = scraped_content
    
    # Step 2: Analyze content with OpenAI
    if scraped_content:
        try:
            analysis = _analyze_with_openai(
                scraped_content=scraped_content,
                company_url=company_url,
                provided_name=company_name,
                provided_description=company_description,
                errors=errors
            )
        except Exception as e:
            error_msg = f"OpenAI analysis failed after retries: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            analysis = None
        
        # Update state with analysis results
        if analysis:
            state["company_name"] = analysis.get("company_name", company_name)
            state["company_description"] = analysis.get("company_description", company_description)
            state["company_summary"] = analysis.get("company_summary", "")
            state["industry"] = analysis.get("industry", "other")
            
            # Extract competitor data (handle both old and new format)
            competitors_data = analysis.get("competitors", [])
            if competitors_data and len(competitors_data) > 0 and isinstance(competitors_data[0], dict):
                # New format with rich data
                state["competitors"] = [c["name"] for c in competitors_data]
                state["competitors_data"] = competitors_data
            else:
                # Old format (just names)
                state["competitors"] = competitors_data
                state["competitors_data"] = []
            
            # Store in vector database for future use
            storage_errors = _store_company_data(state, scraped_content)
            if storage_errors:
                errors.extend(storage_errors)
            
            # Cache the complete industry analysis result
            _cache_industry_analysis(company_url, state)
        else:
            # Fallback to basic keyword detection if AI analysis fails
            state["industry"] = _fallback_keyword_detection(
                company_name or "",
                company_description or scraped_content[:MAX_FALLBACK_CONTENT_LENGTH]
            )
            state["competitors"] = []
    else:
        # No scraped content - use fallback method
        state["industry"] = _fallback_keyword_detection(
            company_name or "",
            company_description or ""
        )
        state["competitors"] = []
    
    state["errors"] = errors
    return state


def _get_cache_key(url: str) -> str:
    """Generate cache key for scraped content using SHA256 for better collision resistance."""
    return f"scrape:{hashlib.sha256(url.encode()).hexdigest()}"


def _get_industry_analysis_cache_key(url: str) -> str:
    """Generate cache key for complete industry analysis."""
    return f"industry_analysis:{hashlib.sha256(url.encode()).hexdigest()}"


def _get_cached_industry_analysis(url: str) -> Optional[Dict]:
    """Get cached industry analysis result."""
    try:
        from config.database import get_redis_client
        redis_client = get_redis_client()
        cache_key = _get_industry_analysis_cache_key(url)
        cached = redis_client.get(cache_key)
        if cached:
            logger.info(f"Cache HIT for industry analysis: {url}")
            # Redis returns bytes, decode if needed
            if isinstance(cached, bytes):
                cached = cached.decode('utf-8')
            return json.loads(cached)
        logger.debug(f"Cache MISS for industry analysis: {url}")
        return None
    except Exception as e:
        logger.warning(f"Industry analysis cache retrieval failed: {e}")
        return None


def _cache_industry_analysis(url: str, state: WorkflowState, ttl: int = SCRAPE_CACHE_TTL) -> None:
    """Cache complete industry analysis result (24 hour TTL by default)."""
    try:
        from config.database import get_redis_client
        redis_client = get_redis_client()
        cache_key = _get_industry_analysis_cache_key(url)
        
        # Cache only the analysis results, not the full state
        cache_data = {
            "company_name": state.get("company_name", ""),
            "company_description": state.get("company_description", ""),
            "company_summary": state.get("company_summary", ""),
            "industry": state.get("industry", "other"),
            "competitors": state.get("competitors", []),
            "competitors_data": state.get("competitors_data", []),
            "scraped_content": state.get("scraped_content", ""),
            "errors": state.get("errors", [])
        }
        
        redis_client.setex(cache_key, ttl, json.dumps(cache_data))
        logger.info(f"Cached industry analysis for: {url}")
    except Exception as e:
        logger.warning(f"Industry analysis cache storage failed: {e}")


def _get_cached_scrape(url: str) -> Optional[str]:
    """Get cached scraped content."""
    try:
        from config.database import get_redis_client
        redis_client = get_redis_client()
        cache_key = _get_cache_key(url)
        cached = redis_client.get(cache_key)
        if cached:
            logger.info(f"Cache HIT for scrape: {url}")
            return cached
        logger.debug(f"Cache MISS for scrape: {url}")
        return None
    except Exception as e:
        logger.warning(f"Cache retrieval failed: {e}")
        return None


def _cache_scrape(url: str, content: str, ttl: int = SCRAPE_CACHE_TTL) -> None:
    """Cache scraped content (default TTL from settings)."""
    try:
        from config.database import get_redis_client
        redis_client = get_redis_client()
        cache_key = _get_cache_key(url)
        redis_client.setex(cache_key, ttl, content)
        logger.debug(f"Cached scrape for: {url}")
    except Exception as e:
        logger.warning(f"Cache storage failed: {e}")


def _scrape_website(url: str, errors: List[str]) -> str:
    """
    Scrape website content using Firecrawl with caching.
    
    Args:
        url: Website URL to scrape
        errors: List to append error messages to
        
    Returns:
        Scraped content in markdown format, or empty string on failure
    """
    # Check cache first
    cached_content = _get_cached_scrape(url)
    if cached_content:
        return cached_content
    
    if not settings.FIRECRAWL_API_KEY:
        errors.append("Firecrawl API key not configured")
        return ""
    
    try:
        from firecrawl import Firecrawl
        
        firecrawl = Firecrawl(api_key=settings.FIRECRAWL_API_KEY)
        
        # Scrape the website with markdown format
        result = firecrawl.scrape(
            url=url,
            formats=["markdown"],
            only_main_content=True,
            timeout=30000
        )
        
        # Handle both dict and object responses
        markdown_content = None
        if hasattr(result, 'markdown') and result.markdown:
            markdown_content = result.markdown
        elif isinstance(result, dict) and "markdown" in result:
            markdown_content = result["markdown"]
        
        if markdown_content:
            # Limit content length to reduce token usage
            content = markdown_content[:MAX_SCRAPED_CONTENT_LENGTH]
            
            # Cache the result
            _cache_scrape(url, content)
            
            logger.info(f"Successfully scraped {len(content)} characters from {url}")
            return content
        else:
            errors.append(f"Firecrawl returned no content for {url}")
            logger.error(f"Firecrawl returned no markdown content for {url}")
            return ""
            
    except ImportError:
        errors.append("Firecrawl package not installed. Install with: pip install firecrawl-py")
        logger.error("Firecrawl package not installed")
        return ""
    except Exception as e:
        errors.append(f"Firecrawl scraping error for {url}: {str(e)}")
        logger.error(f"Firecrawl scraping error for {url}: {str(e)}")
        return ""


def _retry_on_failure(max_attempts: int = RETRY_MAX_ATTEMPTS, delay: float = RETRY_DELAY):
    """Decorator to retry function on failure."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        logger.error(f"All {max_attempts} attempts failed. Last error: {e}")
                        raise last_exception
                    logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed: {e}. Retrying...")
                    time.sleep(delay)
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            return None
        return wrapper
    return decorator


@_retry_on_failure()
def _analyze_with_openai(
    scraped_content: str,
    company_url: str,
    provided_name: str,
    provided_description: str,
    errors: List[str]
) -> Optional[Dict]:
    """
    Analyze scraped content using OpenAI to extract company information.
    
    Args:
        scraped_content: Markdown content from Firecrawl
        company_url: Company website URL
        provided_name: User-provided company name (if any)
        provided_description: User-provided description (if any)
        errors: List to append error messages to
        
    Returns:
        Dictionary with company_name, company_description, company_summary,
        industry, and competitors, or None on failure
    """
    if not settings.OPENAI_API_KEY:
        error_msg = "OpenAI API key not configured for industry analysis"
        errors.append(error_msg)
        logger.error(error_msg)
        return None
    
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=OPENAI_TIMEOUT)
        
        # Create analysis prompt
        prompt = f"""Analyze the following website content and extract key information about the company.

Website URL: {company_url}
{f"Provided Company Name: {provided_name}" if provided_name else ""}
{f"Provided Description: {provided_description}" if provided_description else ""}

Website Content:
{scraped_content}

Please analyze this content and provide a JSON response with the following structure:
{{
    "company_name": "The official company name",
    "company_description": "A brief 1-2 sentence description of what the company does",
    "company_summary": "A comprehensive 3-4 sentence summary of the company's business, products/services, and value proposition",
    "industry": "One of: technology, retail, healthcare, finance, food_services, or other",
    "competitors": [
        {{
            "name": "Competitor name",
            "description": "Brief 1-sentence description of what they do",
            "products": "Main products/services (comma-separated)",
            "positioning": "Key differentiator or market position (e.g., premium, budget, innovative)"
        }}
    ]
}}

Industry Classification Guidelines:
- technology: Software, SaaS, AI, cloud, apps, IT services, hardware, semiconductors, automation
- retail: E-commerce, stores, fashion, consumer goods, marketplace platforms
- healthcare: Medical services, pharmaceuticals, biotech, telemedicine, health tech
- finance: Banking, fintech, payments, insurance, investment, cryptocurrency
- food_services: Restaurants, meal delivery, catering, food tech, meal kits
- other: Anything that doesn't clearly fit the above categories

For competitors, provide 3-5 main competitors with:
- Accurate company names
- Brief description of what they do
- Their main products/services
- Market positioning (premium, budget, innovative, etc.)

Be specific and accurate."""

        response = client.chat.completions.create(
            model=settings.INDUSTRY_ANALYSIS_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert business analyst specializing in company classification and competitive analysis. Always respond with valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Lower temperature for more consistent results
            max_tokens=1000,
            timeout=OPENAI_TIMEOUT,
            response_format={"type": "json_object"}  # Ensure JSON response
        )
        
        result_text = response.choices[0].message.content
        if not result_text:
            error_msg = "OpenAI returned empty response for industry analysis"
            errors.append(error_msg)
            logger.error(error_msg)
            return None
        
        # Parse JSON response
        analysis = json.loads(result_text)
        
        # Validate and normalize industry
        if analysis.get("industry") not in VALID_INDUSTRIES:
            analysis["industry"] = "other"
        
        # Ensure all required fields exist
        analysis.setdefault("company_name", provided_name or "Unknown")
        analysis.setdefault("company_description", provided_description or "")
        analysis.setdefault("company_summary", "")
        analysis.setdefault("competitors", [])
        
        # Validate competitor data structure
        competitors = analysis.get("competitors", [])
        if competitors and isinstance(competitors[0], dict):
            validated_competitors = []
            for comp in competitors:
                # Ensure each competitor has required fields
                if comp.get("name"):
                    validated_comp = {
                        "name": comp.get("name", ""),
                        "description": comp.get("description", ""),
                        "products": comp.get("products", ""),
                        "positioning": comp.get("positioning", "")
                    }
                    validated_competitors.append(validated_comp)
            analysis["competitors"] = validated_competitors
            logger.info(f"Validated {len(validated_competitors)} competitors")
        
        return analysis
        
    except json.JSONDecodeError as e:
        errors.append(f"Failed to parse OpenAI response as JSON: {str(e)}")
        logger.error(f"JSON parsing error: {str(e)}")
        return None
    except Exception as e:
        errors.append(f"OpenAI analysis error: {str(e)}")
        logger.error(f"OpenAI analysis error: {str(e)}")
        return None


def _store_company_data(state: WorkflowState, scraped_content: str) -> List[str]:
    """
    Store company data and competitors in vector database.
    
    Args:
        state: WorkflowState with company information
        scraped_content: Scraped website content
        
    Returns:
        List of error messages (empty if successful)
    """
    errors = []
    
    try:
        company_name = state.get("company_name", "")
        if not company_name:
            logger.debug("No company name provided, skipping vector storage")
            return errors
        
        # Store company profile
        vector_store = get_vector_store()
        vector_store.store_company(
            company_name=company_name,
            company_url=state.get("company_url", ""),
            scraped_content=scraped_content,
            industry=state.get("industry", "other"),
            description=state.get("company_description", ""),
            metadata={
                "summary": state.get("company_summary", "")
            }
        )
        
        # Store competitors with rich embeddings
        competitors = state.get("competitors", [])
        competitors_data = state.get("competitors_data", [])
        
        if competitors:
            competitor_matcher = get_competitor_matcher()
            
            # Build rich metadata from competitors_data
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
        # Don't fail the workflow if storage fails
        error_msg = f"Failed to store company data in vector DB: {str(e)}"
        errors.append(error_msg)
        logger.error(error_msg)
    
    return errors


def _fallback_keyword_detection(company_name: str, text_content: str) -> str:
    """
    Fallback keyword-based industry detection when AI analysis fails.
    
    This is the original simple keyword matching approach, used as a backup.
    Uses module-level INDUSTRY_KEYWORDS constant for better performance.
    
    Args:
        company_name: Company name
        text_content: Text to analyze (description or scraped content)
        
    Returns:
        Detected industry category
    """
    # Combine text for analysis (lowercase for case-insensitive matching)
    combined_text = f"{company_name} {text_content}".lower()
    
    # Extract keywords from the combined text
    text_words = set(combined_text.split())
    
    # Score each industry based on keyword matches
    industry_scores: Dict[str, int] = {}
    
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        score = 0
        
        for keyword in keywords:
            if " " in keyword:
                # Multi-word phrase - check in full text
                if keyword in combined_text:
                    score += 2  # Multi-word matches get higher weight
            else:
                # Single word - check in word set
                if keyword in text_words:
                    score += 1
        
        industry_scores[industry] = score
    
    # Determine the best matching industry
    if not industry_scores or max(industry_scores.values()) == 0:
        return "other"
    else:
        # Get industry with highest score
        return max(industry_scores, key=industry_scores.get)
