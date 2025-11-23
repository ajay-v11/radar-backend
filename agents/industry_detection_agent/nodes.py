"""
Node functions for the industry detection LangGraph workflow.
Dynamic industry classification without hardcoded constraints.
"""

import logging
import json
from urllib.parse import urlparse
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import settings
from agents.industry_detection_agent.models import (
    IndustryDetectorState,
    IndustryClassification,
    ExtractionTemplate,
    QueryCategoriesTemplate,
    CompanyAnalysis
)
from agents.industry_detection_agent.utils import (
    scrape_website,
    get_analysis_llm
)

logger = logging.getLogger(__name__)


def scrape_company_pages(state: IndustryDetectorState) -> IndustryDetectorState:
    """Node: Scrape company homepage and about page in parallel."""
    logger.info("🌐 Scraping company pages...")
    
    company_url = state["company_url"]
    errors = state.get("errors", [])
    
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    parsed = urlparse(company_url)
    base_path = f"{parsed.scheme}://{parsed.netloc}"
    
    scraped_pages = {}
    
    # Scrape company pages in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(scrape_website, company_url, [], full_content=True): ("homepage", company_url),
            executor.submit(scrape_website, f"{base_path}/about", [], full_content=True): ("about", f"{base_path}/about")
        }
        
        for future in as_completed(futures):
            page_name, url = futures[future]
            try:
                content = future.result(timeout=60)
                if content:
                    scraped_pages[page_name] = content
                    logger.info(f"✓ Scraped company {page_name} ({len(content)} chars)")
                else:
                    if page_name == "homepage":
                        logger.error(f"✗ Failed to scrape homepage")
                        errors.append("Failed to scrape homepage")
                    else:
                        logger.info(f"⏭️  {page_name} not available (not critical)")
            except Exception as e:
                error_msg = f"Failed to scrape {page_name}: {e}"
                logger.error(error_msg)
                if page_name == "homepage":
                    errors.append(error_msg)
    
    # Return only the fields this node updates
    return {
        "company_pages": scraped_pages,
        "errors": errors
    }


def scrape_competitor_pages(state: IndustryDetectorState) -> IndustryDetectorState:
    """Node: Scrape competitor homepages in parallel (homepage only)."""
    competitor_urls = state.get("competitor_urls", {})
    
    if not competitor_urls:
        logger.info("⏭️  No competitor URLs provided, skipping competitor scraping")
        state["competitor_pages"] = {}
        return state
    
    logger.info(f"🌐 Scraping {len(competitor_urls)} competitor homepages...")
    
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    competitor_pages = {}
    
    # Scrape all competitor homepages in parallel
    with ThreadPoolExecutor(max_workers=min(len(competitor_urls), 10)) as executor:
        futures = {
            executor.submit(scrape_website, comp_url, [], full_content=True): (comp_name, comp_url)
            for comp_name, comp_url in competitor_urls.items()
        }
        
        for future in as_completed(futures):
            comp_name, comp_url = futures[future]
            try:
                content = future.result(timeout=60)
                if content:
                    competitor_pages[comp_name] = content
                    logger.info(f"✓ Scraped competitor {comp_name} ({len(content)} chars)")
                else:
                    logger.info(f"⏭️  {comp_name} not available (not critical)")
            except Exception as e:
                logger.warning(f"✗ Failed to scrape competitor {comp_name}: {e}")
    
    # Return only the fields this node updates
    return {
        "competitor_pages": competitor_pages
    }


def combine_scraped_content(state: IndustryDetectorState) -> IndustryDetectorState:
    """Node: Combine all scraped content for analysis."""
    logger.info("📝 Combining scraped content...")
    
    company_pages = state.get("company_pages", {})
    
    if not company_pages:
        logger.error("❌ No company pages scraped!")
        errors = state.get("errors", [])
        errors.append("No content was scraped from company website")
        state["errors"] = errors
        state["combined_content"] = ""
        return state
    
    combined = "\n\n".join([
        f"=== {page_type.upper()} ===\n{content}" 
        for page_type, content in company_pages.items()
    ])
    
    logger.info(f"✓ Combined {len(company_pages)} pages, total {len(combined)} chars")
    state["combined_content"] = combined
    return state


def classify_industry(state: IndustryDetectorState) -> IndustryDetectorState:
    """Node: Classify company into a specific industry (no constraints)."""
    logger.info("🏷️  Classifying industry dynamically...")
    
    combined_content = state.get("combined_content", "")
    company_url = state["company_url"]
    provided_name = state.get("company_name", "")
    provided_description = state.get("company_description", "")
    llm_provider = state.get("llm_provider") or settings.INDUSTRY_ANALYSIS_PROVIDER
    errors = state.get("errors", [])
    
    if not combined_content:
        error_msg = "No content available for industry classification"
        errors.append(error_msg)
        state["errors"] = errors
        state["industry"] = "Unknown"
        state["broad_category"] = "Other"
        state["industry_description"] = ""
        return state
    
    llm = get_analysis_llm(llm_provider)
    if not llm:
        error_msg = f"Could not initialize {llm_provider} LLM"
        errors.append(error_msg)
        state["errors"] = errors
        state["industry"] = "Unknown"
        state["broad_category"] = "Other"
        state["industry_description"] = ""
        return state
    
    try:
        prompt = f"""Analyze this company and classify it into a SPECIFIC industry.

Website URL: {company_url}
{f"Company Name: {provided_name}" if provided_name else ""}
{f"Description: {provided_description}" if provided_description else ""}

Website Content (first 2000 chars):
{combined_content[:2000]}

Classify this company into a specific, descriptive industry. DO NOT use generic categories.

Examples of GOOD classifications:
- "AI-Powered Meal Kit Delivery"
- "B2B SaaS Project Management Tools"
- "Sustainable Fashion E-commerce"
- "Telehealth Mental Wellness Platform"
- "Crypto Trading & Investment Platform"

Examples of BAD classifications (too generic):
- "Technology"
- "Food Services"
- "Healthcare"

Provide:
1. A specific industry name (2-5 words)
2. A broad category for grouping (e.g., Technology, Commerce, Healthcare, Finance, Services)
3. A 2-3 sentence description of what defines this industry

Be precise and descriptive."""

        messages = [
            SystemMessage(content="You are an industry classification expert. Provide specific, descriptive industry names."),
            HumanMessage(content=prompt)
        ]
        
        try:
            structured_llm = llm.with_structured_output(IndustryClassification)
            classification = structured_llm.invoke(messages)
            
            state["industry"] = classification.industry
            state["broad_category"] = classification.broad_category
            state["industry_description"] = classification.industry_description
            
            logger.info(f"✓ Industry classified: {classification.industry} ({classification.broad_category})")
            
        except Exception as e:
            logger.warning(f"Structured output failed, falling back to JSON: {e}")
            
            response = llm.invoke(messages)
            result_text = response.content
            
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            classification = json.loads(result_text)
            state["industry"] = classification.get("industry", "Unknown")
            state["broad_category"] = classification.get("broad_category", "Other")
            state["industry_description"] = classification.get("industry_description", "")
            
            logger.info(f"✓ Industry classified: {state['industry']} ({state['broad_category']})")
    
    except Exception as e:
        error_msg = f"Industry classification failed: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
        state["errors"] = errors
        state["industry"] = "Unknown"
        state["broad_category"] = "Other"
        state["industry_description"] = ""
    
    return state


def generate_extraction_template(state: IndustryDetectorState) -> IndustryDetectorState:
    """Node: Generate dynamic extraction template for this industry."""
    logger.info("📋 Generating extraction template...")
    
    industry = state.get("industry", "Unknown")
    industry_description = state.get("industry_description", "")
    broad_category = state.get("broad_category", "Other")
    llm_provider = state.get("llm_provider") or settings.INDUSTRY_ANALYSIS_PROVIDER
    errors = state.get("errors", [])
    
    if industry == "Unknown":
        logger.warning("Industry unknown, using generic template")
        state["extraction_template"] = {
            "extract_fields": ["main_offerings", "business_model", "target_market", "key_features"],
            "competitor_focus": "similar companies in the same space"
        }
        return state
    
    llm = get_analysis_llm(llm_provider)
    if not llm:
        state["extraction_template"] = {
            "extract_fields": ["main_offerings", "business_model", "target_market", "key_features"],
            "competitor_focus": "similar companies in the same space"
        }
        return state
    
    try:
        prompt = f"""Generate an extraction template for analyzing companies in this industry.

Industry: {industry}
Broad Category: {broad_category}
Description: {industry_description}

Create a template that specifies:
1. extract_fields: 5-8 specific data points to extract from company websites in this industry
2. competitor_focus: A description of what types of competitors to identify

Examples:
- For "AI-Powered Meal Kit Delivery":
  extract_fields: ["menu_customization_options", "dietary_filters", "delivery_frequency", "subscription_tiers", "ingredient_sourcing"]
  competitor_focus: "meal kit services, AI-powered food delivery, subscription meal platforms"

- For "B2B SaaS Project Management":
  extract_fields: ["collaboration_features", "integrations", "pricing_tiers", "team_size_limits", "reporting_capabilities"]
  competitor_focus: "project management software, team collaboration tools, workflow automation platforms"

Make the fields specific to this industry, not generic."""

        # Skip structured output - go straight to JSON for speed
        messages = [
            SystemMessage(content="You are an expert at designing data extraction templates for business intelligence. Respond ONLY with valid JSON."),
            HumanMessage(content=prompt + "\n\nRespond with JSON only: {\"extract_fields\": [...], \"competitor_focus\": \"...\"}")
        ]
        
        response = llm.invoke(messages)
        result_text = response.content
        
        # Strip markdown code blocks if present
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        template = json.loads(result_text)
        state["extraction_template"] = template
        
        logger.info(f"✓ Template generated with {len(template.get('extract_fields', []))} fields")
    
    except Exception as e:
        error_msg = f"Template generation failed: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
        state["errors"] = errors
        state["extraction_template"] = {
            "extract_fields": ["main_offerings", "business_model", "target_market", "key_features"],
            "competitor_focus": "similar companies in the same space"
        }
    
    return state


def extract_with_template(state: IndustryDetectorState) -> IndustryDetectorState:
    """Node: Extract company data using the generated template."""
    logger.info("🔍 Extracting company data with template...")
    
    combined_content = state.get("combined_content", "")
    company_url = state["company_url"]
    provided_name = state.get("company_name", "")
    provided_description = state.get("company_description", "")
    industry = state.get("industry", "Unknown")
    extraction_template = state.get("extraction_template", {})
    llm_provider = state.get("llm_provider") or settings.INDUSTRY_ANALYSIS_PROVIDER
    errors = state.get("errors", [])
    
    if not combined_content:
        error_msg = "No content available for extraction"
        errors.append(error_msg)
        state["errors"] = errors
        return state
    
    llm = get_analysis_llm(llm_provider)
    if not llm:
        error_msg = f"Could not initialize {llm_provider} LLM"
        errors.append(error_msg)
        state["errors"] = errors
        return state
    
    try:
        extract_fields = extraction_template.get("extract_fields", [])
        competitor_focus = extraction_template.get("competitor_focus", "similar companies")
        
        industry_specific_json = ", ".join([f'"{field}": "value"' for field in extract_fields])
        
        prompt = f"""Analyze this company and extract comprehensive business intelligence.

Website URL: {company_url}
Industry: {industry}
{f"Company Name: {provided_name}" if provided_name else ""}
{f"Description: {provided_description}" if provided_description else ""}

Website Content:
{combined_content}

Extract the following information in JSON format:
{{
    "company_name": "Official company name",
    "company_description": "Brief 1-2 sentence description",
    "company_summary": "Comprehensive 3-4 sentence summary",
    "product_category": "Specific product/service category",
    "market_keywords": ["keyword1", "keyword2", ...],
    "target_audience": "Primary target customers",
    
    "brand_positioning": {{
        "value_proposition": "Main value proposition",
        "differentiators": ["unique feature 1", "unique feature 2"],
        "price_positioning": "premium, mid, or budget"
    }},
    
    "buyer_intent_signals": {{
        "common_questions": ["question 1", "question 2"],
        "decision_factors": ["factor 1", "factor 2"],
        "pain_points": ["pain point 1", "pain point 2"]
    }},
    
    "industry_specific": {{
        {industry_specific_json}
    }},
    
    "competitors": [
        {{
            "name": "Competitor name",
            "description": "Brief description",
            "products": "Main products/services",
            "positioning": "Key differentiator",
            "price_tier": "premium, mid, or budget"
        }}
    ]
}}

For competitors, identify 3-5 main {competitor_focus}.
RESPOND ONLY WITH VALID JSON."""

        messages = [
            SystemMessage(content="You are an expert business analyst. Extract structured data accurately."),
            HumanMessage(content=prompt)
        ]
        
        try:
            structured_llm = llm.with_structured_output(CompanyAnalysis)
            analysis = structured_llm.invoke(messages)
            
            state["company_name"] = analysis.company_name
            state["company_description"] = analysis.company_description
            state["product_category"] = analysis.product_category
            state["market_keywords"] = analysis.market_keywords
            state["target_audience"] = analysis.target_audience
            state["brand_positioning"] = analysis.brand_positioning.dict()
            state["buyer_intent_signals"] = analysis.buyer_intent_signals.dict()
            state["industry_specific"] = analysis.industry_specific
            
            # Process competitors (exclude the company itself)
            company_name = state.get("company_name", provided_name or "Unknown")
            validated = []
            for comp in analysis.competitors:
                # Skip if this is the company itself
                if comp.name.lower() != company_name.lower():
                    validated.append({
                        "name": comp.name,
                        "description": comp.description,
                        "products": comp.products,
                        "positioning": comp.positioning,
                        "price_tier": comp.price_tier
                    })
            
            state["competitors"] = [c["name"] for c in validated]
            state["competitors_data"] = validated
            
            logger.info(f"✓ Extracted data for {company_name} with {len(validated)} competitors")
            
        except Exception as e:
            logger.warning(f"Structured output failed, falling back to JSON: {e}")
            
            response = llm.invoke(messages)
            result_text = response.content
            
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            analysis = json.loads(result_text)
            
            state["company_name"] = analysis.get("company_name", provided_name or "Unknown")
            state["company_description"] = analysis.get("company_description", provided_description or "")
            state["product_category"] = analysis.get("product_category", "")
            state["market_keywords"] = analysis.get("market_keywords", [])
            state["target_audience"] = analysis.get("target_audience", "")
            state["brand_positioning"] = analysis.get("brand_positioning", {})
            state["buyer_intent_signals"] = analysis.get("buyer_intent_signals", {})
            state["industry_specific"] = analysis.get("industry_specific", {})
            
            # Process competitors (exclude the company itself)
            company_name = state.get("company_name")
            competitors = analysis.get("competitors", [])
            validated = []
            for comp in competitors:
                if comp.get("name"):
                    # Skip if this is the company itself
                    if comp["name"].lower() != company_name.lower():
                        validated.append(comp)
            
            state["competitors"] = [c["name"] for c in validated]
            state["competitors_data"] = validated
            
            logger.info(f"✓ Extracted data")
    
    except Exception as e:
        error_msg = f"Data extraction failed: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
        state["errors"] = errors
    
    return state


def generate_query_categories(state: IndustryDetectorState) -> IndustryDetectorState:
    """Node: Generate dynamic query categories for this specific company."""
    logger.info("🎯 Generating query categories...")
    
    industry = state.get("industry", "Unknown")
    industry_description = state.get("industry_description", "")
    company_name = state.get("company_name", "")
    company_description = state.get("company_description", "")
    competitors = state.get("competitors", [])
    llm_provider = state.get("llm_provider") or settings.INDUSTRY_ANALYSIS_PROVIDER
    errors = state.get("errors", [])
    
    llm = get_analysis_llm(llm_provider)
    if not llm:
        logger.warning("Cannot generate query categories without LLM")
        state["query_categories_template"] = None
        return state
    
    try:
        prompt = f"""Generate search query categories for analyzing this company's AI visibility.

Company: {company_name}
Description: {company_description}
Industry: {industry}
Industry Description: {industry_description}
Competitors: {', '.join(competitors[:5])}

Create 5-7 query categories that represent how real users would search for companies in this space.
Each category needs:
- category_key: unique identifier (lowercase, underscores)
- category_name: human-readable name
- weight: importance (0.0-1.0, must sum to 1.0 across all categories)
- description: what this category represents
- examples: 2-3 example queries

Example for "AI Resume Builder":
{{
    "categories": [
        {{
            "category_key": "ai_comparison",
            "category_name": "AI Tool Comparison",
            "weight": 0.30,
            "description": "Comparing AI resume tools",
            "examples": ["Rezi vs Resume.io", "best AI resume builder"]
        }},
        {{
            "category_key": "ats_optimization",
            "category_name": "ATS Optimization",
            "weight": 0.25,
            "description": "Queries about beating ATS systems",
            "examples": ["ATS-friendly resume", "how to pass ATS scan"]
        }},
        ...
    ]
}}

Make categories specific to {industry}, not generic. Weights must sum to 1.0."""

        # Skip structured output - go straight to JSON for speed
        messages = [
            SystemMessage(content="You are an SEO and search intent expert. Generate realistic query categories. Respond ONLY with valid JSON."),
            HumanMessage(content=prompt + "\n\nRespond with JSON only in this exact format: {\"categories\": [{\"category_key\": \"...\", \"category_name\": \"...\", \"weight\": 0.X, \"description\": \"...\", \"examples\": [...]}, ...]}")
        ]
        
        response = llm.invoke(messages)
        result_text = response.content
        
        # Strip markdown code blocks if present
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(result_text)
        categories_list = result.get("categories", [])
        
        # Normalize weights to sum to 1.0
        total_weight = sum(cat.get("weight", 0) for cat in categories_list)
        if total_weight > 0:
            for cat in categories_list:
                cat["weight"] = cat.get("weight", 0) / total_weight
        
        categories_dict = {}
        for cat in categories_list:
            key = cat.get("category_key", "")
            if key:
                categories_dict[key] = {
                    "name": cat.get("category_name", ""),
                    "weight": cat.get("weight", 0),
                    "description": cat.get("description", ""),
                    "examples": cat.get("examples", [])
                }
        
        state["query_categories_template"] = categories_dict
        
        logger.info(f"✓ Generated {len(categories_dict)} query categories")
    
    except Exception as e:
        error_msg = f"Query category generation failed: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
        state["errors"] = errors
        state["query_categories_template"] = None
    
    return state


def enrich_competitors(state: IndustryDetectorState) -> IndustryDetectorState:
    """Node: Enrich competitor data with scraped content."""
    competitor_pages = state.get("competitor_pages", {})
    competitors_data = state.get("competitors_data", [])
    
    if not competitor_pages or not competitors_data:
        logger.info("⏭️  No competitor data to enrich")
        return state
    
    logger.info(f"💎 Enriching {len(competitor_pages)} competitors...")
    
    llm_provider = state.get("llm_provider") or settings.INDUSTRY_ANALYSIS_PROVIDER
    llm = get_analysis_llm(llm_provider)
    
    if not llm:
        logger.warning("Cannot enrich competitors without LLM")
        return state
    
    enriched = []
    for comp in competitors_data:
        comp_name = comp["name"]
        enriched_comp = comp.copy()
        
        if comp_name in competitor_pages:
            try:
                prompt = f"""Analyze this competitor's website and extract key positioning information.

Competitor: {comp_name}
Content: {competitor_pages[comp_name][:1000]}

Provide a JSON response:
{{
    "value_proposition": "Their main value prop",
    "unique_features": ["feature1", "feature2"],
    "price_tier": "premium|mid|budget"
}}"""
                
                messages = [
                    SystemMessage(content="You are a competitive intelligence analyst. Respond with valid JSON only."),
                    HumanMessage(content=prompt)
                ]
                
                response = llm.invoke(messages)
                result_text = response.content
                
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()
                
                comp_analysis = json.loads(result_text)
                
                enriched_comp["value_proposition"] = comp_analysis.get("value_proposition", "")
                enriched_comp["unique_features"] = comp_analysis.get("unique_features", [])
                enriched_comp["price_tier"] = comp_analysis.get("price_tier", comp["price_tier"])
                
                logger.info(f"✓ Enriched: {comp_name}")
            except Exception as e:
                logger.warning(f"✗ Failed to enrich {comp_name}: {e}")
        
        enriched.append(enriched_comp)
    
    state["competitors_data"] = enriched
    return state


def finalize(state: IndustryDetectorState) -> IndustryDetectorState:
    """Node: Finalize and mark as completed."""
    logger.info("✅ Industry detection workflow complete")
    state["completed"] = True
    return state
