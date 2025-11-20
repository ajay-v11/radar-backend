"""
Debug cache keys.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.query_generator import _get_query_cache_key

# Test different URL formats
urls = [
    "https://hellofresh.com",
    "https://hellofresh.com/",
    "https://example-test-company.com",
]

for url in urls:
    for num in [20, 30, 50]:
        key = _get_query_cache_key(url, num)
        print(f"{url:40} ({num:2} queries) -> {key}")
