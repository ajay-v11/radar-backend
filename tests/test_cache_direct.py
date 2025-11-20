"""
Test cache directly with Redis.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.database import get_redis_client
from agents.query_generator import _get_query_cache_key
import json

# Test cache
redis_client = get_redis_client()

url = "https://hellofresh.com"
num_queries = 20

cache_key = _get_query_cache_key(url, num_queries)
print(f"Cache key: {cache_key}")

# Check if key exists
cached = redis_client.get(cache_key)
if cached:
    print(f"\n✅ Cache HIT!")
    print(f"Cached data size: {len(cached)} bytes")
    
    # Decode and parse
    if isinstance(cached, bytes):
        cached = cached.decode('utf-8')
    data = json.loads(cached)
    
    print(f"Total queries: {len(data['queries'])}")
    print(f"Categories: {len(data['query_categories'])}")
    print(f"\nFirst 3 queries:")
    for i, q in enumerate(data['queries'][:3], 1):
        print(f"  {i}. {q}")
else:
    print("\n❌ Cache MISS - No data found")

# List all query cache keys
print("\n" + "="*80)
print("All query cache keys in Redis:")
print("="*80)
for key in redis_client.scan_iter("queries:*"):
    if isinstance(key, bytes):
        key = key.decode('utf-8')
    ttl = redis_client.ttl(key)
    print(f"  {key} (TTL: {ttl}s)")
