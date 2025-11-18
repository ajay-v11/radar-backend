"""
Utility functions and helpers for the AI Visibility Scoring System.

This module provides common utility functions used across different components
of the application, including unique identifier generation and shared helpers.
"""

import uuid
from typing import Optional


def generate_job_id() -> str:
    """
    Generate a unique job identifier.
    
    Creates a UUID4-based unique identifier for tracking analysis jobs.
    This function is used to create unique IDs for each analysis request
    to enable tracking and logging.
    
    Returns:
        str: Unique job ID as a string in UUID4 format
        
    Example:
        >>> job_id = generate_job_id()
        >>> print(job_id)
        '550e8400-e29b-41d4-a716-446655440000'
        
    Requirements:
        - 8.4: Use type hints throughout the codebase
    """
    return str(uuid.uuid4())


def sanitize_company_name(company_name: Optional[str]) -> str:
    """
    Sanitize and normalize company name for consistent processing.
    
    Removes extra whitespace, converts to title case, and handles None values.
    This ensures consistent company name formatting across the system.
    
    Args:
        company_name: Raw company name string or None
        
    Returns:
        str: Sanitized company name, or empty string if None
        
    Example:
        >>> sanitize_company_name("  hello FRESH  ")
        'Hello Fresh'
        >>> sanitize_company_name(None)
        ''
    """
    if not company_name:
        return ""
    return " ".join(company_name.strip().split())


def extract_domain_from_url(url: str) -> str:
    """
    Extract the domain name from a URL.
    
    Useful for extracting company identifiers from URLs when company name
    is not provided.
    
    Args:
        url: Full URL string
        
    Returns:
        str: Domain name without protocol and path
        
    Example:
        >>> extract_domain_from_url("https://www.hellofresh.com/about")
        'hellofresh.com'
        >>> extract_domain_from_url("http://example.com")
        'example.com'
    """
    # Remove protocol
    domain = url.replace("https://", "").replace("http://", "")
    
    # Remove www. prefix if present
    if domain.startswith("www."):
        domain = domain[4:]
    
    # Remove path and query parameters
    domain = domain.split("/")[0].split("?")[0]
    
    return domain


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length with optional suffix.
    
    Useful for creating preview text or limiting response lengths in logs.
    
    Args:
        text: Text to truncate
        max_length: Maximum length of the output (default: 100)
        suffix: Suffix to append when truncating (default: "...")
        
    Returns:
        str: Truncated text with suffix if needed
        
    Example:
        >>> truncate_text("This is a very long text", max_length=10)
        'This is...'
        >>> truncate_text("Short", max_length=10)
        'Short'
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
