"""
Detailed streaming test with timestamps.
"""

import requests
import json
import time

url = "http://localhost:8000/queries/generate"
import random
payload = {
    "company_url": f"https://test-streaming-{random.randint(1000,9999)}.com",  # Random URL to avoid cache
    "company_name": "StreamTest",
    "num_queries": 20
}

print("="*80)
print("DETAILED STREAMING TEST (with timestamps)")
print("="*80)
print()

start_time = time.time()
last_event_time = start_time

try:
    response = requests.post(
        url,
        json=payload,
        headers={"Accept": "text/event-stream"},
        stream=True
    )
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                current_time = time.time()
                elapsed = current_time - start_time
                delta = current_time - last_event_time
                last_event_time = current_time
                
                data = json.loads(line_str[6:])
                
                step = data.get("step")
                status = data.get("status")
                message = data.get("message")
                
                if step == "industry_detection":
                    if status == "in_progress":
                        print(f"[{elapsed:6.2f}s] (+{delta:5.2f}s) 🔍 {message}")
                    elif status == "completed":
                        print(f"[{elapsed:6.2f}s] (+{delta:5.2f}s) ✅ {message}")
                
                elif step == "query_generation":
                    if status == "cached":
                        print(f"[{elapsed:6.2f}s] (+{delta:5.2f}s) ⚡ CACHE HIT")
                    else:
                        print(f"[{elapsed:6.2f}s] (+{delta:5.2f}s) 🚀 {message}")
                
                elif step == "category":
                    if status == "in_progress":
                        category_name = data.get("data", {}).get("category_name")
                        print(f"[{elapsed:6.2f}s] (+{delta:5.2f}s) ⏳ Generating {category_name}...")
                    elif status == "completed":
                        category_name = data.get("data", {}).get("category_name")
                        queries = data.get("data", {}).get("queries", [])
                        print(f"[{elapsed:6.2f}s] (+{delta:5.2f}s) ✅ {category_name}: {len(queries)} queries")
                
                elif step == "complete":
                    total = data.get("data", {}).get("total_queries", 0)
                    print(f"[{elapsed:6.2f}s] (+{delta:5.2f}s) ✨ Complete! {total} queries")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*80)
print("ANALYSIS:")
print("  - Each category should appear 2-4 seconds apart (OpenAI API call time)")
print("  - Total time should be 10-20 seconds for 5 categories")
print("  - Delta times show gaps between events")
print("="*80)
