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

VALID_INDUSTRIES = ["technology", "retail", "healthcare", "finance", "food_services", "other"]

INDUSTRY_EXTRACTION_TEMPLATES = {
    "food_services": {
        "extract_fields": ["menu_types", "dietary_options", "delivery_areas", "subscription_model"],
        "competitor_focus": "meal delivery services, restaurants, food tech companies"
    },
    "technology": {
        "extract_fields": ["tech_stack", "use_cases", "integrations", "pricing_model"],
        "competitor_focus": "SaaS platforms, software companies, tech startups"
    },
    "retail": {
        "extract_fields": ["product_categories", "shipping_options", "return_policy", "price_range"],
        "competitor_focus": "e-commerce platforms, retail stores, online marketplaces"
    },
    "healthcare": {
        "extract_fields": ["services_offered", "specializations", "insurance_accepted", "telehealth_options"],
        "competitor_focus": "healthcare providers, medical services, health tech companies"
    },
    "finance": {
        "extract_fields": ["financial_products", "fees_structure", "regulatory_compliance", "security_features"],
        "competitor_focus": "fintech companies, banks, financial services"
    },
    "other": {
        "extract_fields": ["main_offerings", "business_model", "target_market", "key_features"],
        "competitor_focus": "similar companies in the same space"
    }
}

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
            "company_summary": state.get("company_summary", ""),
            "industry": state.get("industry", "other"),
            "competitors": state.get("competitors", []),
            "competitors_data": state.get("competitors_data", []),
            "product_category": state.get("product_category", ""),
            "market_keywords": state.get("market_keywords", []),
            "target_audience": state.get("target_audience", ""),
            "brand_positioning": state.get("brand_positioning", {}),
            "buyer_intent_signals": state.get("buyer_intent_signals", {}),
            "industry_specific": state.get("industry_specific", {}),
            "scraped_content": state.get("scraped_content", ""),
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
def scrape_website(url: str, errors: List[str]) -> str:
    """Scrape website content using Firecrawl with caching."""
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
                    content = markdown_content[:MAX_SCRAPED_CONTENT_LENGTH]
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
def get_analysis_llm(llm_provider: str = "openai"):
    """Get LLM instance based on provider."""
    try:
        if llm_provider.lower() == "gemini":
            if not settings.GEMINI_API_KEY:
                logger.warning("Gemini API key not configured")
                return None
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model="gemini-2.5-flash-lite",
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.3,
                max_tokens=2000
            )
        elif llm_provider.lower() == "llama":
            if not settings.GROK_API_KEY:
                logger.warning("Groq API key not configured")
                return None
            from langchain_groq import ChatGroq
            return ChatGroq(
                model="llama-3.1-8b-instant",
                groq_api_key=settings.GROK_API_KEY,
                temperature=0.3,
                max_tokens=2000
            )
        elif llm_provider.lower() == "claude":
            if not settings.ANTHROPIC_API_KEY:
                logger.warning("Anthropic API key not configured")
                return None
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model="claude-3-haiku-20240307",
                api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.3,
                max_tokens=2000
            )
        else:
            if not settings.OPENAI_API_KEY:
                logger.error("OpenAI API key not configured")
                return None
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.INDUSTRY_ANALYSIS_MODEL,
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0.3,
                max_tokens=2000,
                timeout=OPENAI_TIMEOUT
            )
    except Exception as e:
        logger.error(f"Failed to initialize {llm_provider} LLM: {str(e)}")
        return None


# Helper functions
def quick_industry_detection(content: str) -> str:
    """Quick industry detection using keyword matching."""
    return fallback_keyword_detection("", content[:500])


def fallback_keyword_detection(company_name: str, text_content: str) -> str:
    """Fallback keyword-based industry detection."""
    combined_text = f"{company_name} {text_content}".lower()
    text_words = set(combined_text.split())
    
    industry_scores: Dict[str, int] = {}
    
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if " " in keyword:
                if keyword in combined_text:
                    score += 2
            else:
                if keyword in text_words:
                    score += 1
        industry_scores[industry] = score
    
    if not industry_scores or max(industry_scores.values()) == 0:
        return "other"
    return max(industry_scores, key=industry_scores.get)


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
