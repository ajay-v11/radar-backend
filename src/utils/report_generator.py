"""
CSV Report Generator for AI Visibility Analysis

Generates comprehensive CSV reports from visibility analysis data.
"""
import csv
import io
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def generate_csv_report(cached_result: Dict[str, Any]) -> str:
    """
    Generate a comprehensive CSV report from visibility analysis data.
    
    Args:
        cached_result: Complete visibility analysis result from cache
        
    Returns:
        CSV content as string
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Extract data
    analysis_report = cached_result.get("analysis_report", {})
    company_name = cached_result.get("company_name", "Unknown")
    industry = cached_result.get("industry", "Unknown")
    visibility_score = cached_result.get("visibility_score", 0)
    total_queries = cached_result.get("total_queries", 0)
    total_mentions = analysis_report.get("total_mentions", 0)
    total_responses = analysis_report.get("total_responses", 0)
    
    # Section 1: Summary
    writer.writerow(["AI VISIBILITY ANALYSIS REPORT"])
    writer.writerow([])
    writer.writerow(["Company", company_name])
    writer.writerow(["Industry", industry])
    writer.writerow(["Overall Visibility Score", f"{visibility_score:.2f}%"])
    writer.writerow(["Total Queries Tested", total_queries])
    writer.writerow(["Total Mentions", total_mentions])
    writer.writerow(["Total Responses", total_responses])
    writer.writerow([])
    
    # Section 2: Model Performance
    writer.writerow(["MODEL PERFORMANCE"])
    writer.writerow(["Model", "Mentions", "Total Responses", "Visibility %"])
    
    by_model = analysis_report.get("by_model", {})
    from agents.visibility_orchestrator.nodes import get_exact_model_name
    
    for model_key, model_data in by_model.items():
        exact_name = get_exact_model_name(model_key)
        mentions = model_data.get("mentions", 0)
        total = model_data.get("total_responses", 0)
        score = (mentions / total * 100) if total > 0 else 0.0
        writer.writerow([exact_name, mentions, total, f"{score:.2f}%"])
    
    writer.writerow([])
    
    # Section 3: Category Breakdown
    writer.writerow(["CATEGORY BREAKDOWN"])
    writer.writerow(["Category", "Queries", "Mentions", "Visibility %"])
    
    category_breakdown = analysis_report.get("category_breakdown", [])
    for cat_data in category_breakdown:
        category = cat_data.get("category", "Unknown")
        queries = cat_data.get("queries", 0)
        mentions = cat_data.get("mentions", 0)
        score = cat_data.get("score", 0)
        writer.writerow([category, queries, mentions, f"{score:.2f}%"])
    
    writer.writerow([])
    
    # Section 4: Competitor Rankings
    writer.writerow(["COMPETITOR RANKINGS"])
    writer.writerow(["Rank", "Competitor", "Total Mentions", "Visibility %"])
    
    competitor_rankings = analysis_report.get("competitor_rankings", {})
    overall_rankings = competitor_rankings.get("overall", [])
    
    for idx, comp_data in enumerate(overall_rankings, 1):
        comp_name = comp_data.get("name", "Unknown")
        total_mentions_comp = comp_data.get("total_mentions", 0)
        percentage = comp_data.get("percentage", 0)
        writer.writerow([idx, comp_name, total_mentions_comp, f"{percentage:.2f}%"])
    
    writer.writerow([])
    
    # Section 5: Detailed Query Log
    writer.writerow(["DETAILED QUERY LOG"])
    writer.writerow(["Query", "Category", "Model", "Mentioned?", "Rank", "Competitors Mentioned"])
    
    # Aggregate query log from all categories
    for cat_data in category_breakdown:
        category = cat_data.get("category", "Unknown")
        cat_analysis = cat_data.get("analysis", {})
        query_log = cat_analysis.get("query_log", [])
        
        for entry in query_log:
            query_text = entry.get("query", "")
            results = entry.get("results", {})
            
            # Write one row per model
            for model_key, result in results.items():
                exact_name = get_exact_model_name(model_key)
                mentioned = "Yes" if result.get("mentioned") else "No"
                rank = result.get("rank", "N/A")
                competitors = ", ".join(result.get("competitors_mentioned", []))
                
                writer.writerow([
                    query_text,
                    category,
                    exact_name,
                    mentioned,
                    rank,
                    competitors
                ])
    
    writer.writerow([])
    
    # Section 6: Model-Category Matrix
    writer.writerow(["MODEL-CATEGORY PERFORMANCE MATRIX"])
    
    # Build header: ["Category", "Model1", "Model2", ...]
    model_names = [get_exact_model_name(m) for m in by_model.keys()]
    writer.writerow(["Category"] + model_names)
    
    # Build rows: one per category
    for cat_data in category_breakdown:
        category = cat_data.get("category", "Unknown")
        cat_analysis = cat_data.get("analysis", {})
        by_model_cat = cat_analysis.get("by_model", {})
        
        row = [category]
        for model_key in by_model.keys():
            model_cat_data = by_model_cat.get(model_key, {})
            mentions = model_cat_data.get("mentions", 0)
            total = model_cat_data.get("total_responses", 0)
            score = (mentions / total * 100) if total > 0 else 0.0
            row.append(f"{score:.2f}%")
        
        writer.writerow(row)
    
    csv_content = output.getvalue()
    output.close()
    
    return csv_content
