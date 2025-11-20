"""
Test streaming with cache - shows real-time updates.
"""

import requests
import json
import time

url = "http://localhost:8000/queries/generate"
payload = {
    "company_url": "https://hellofresh.com",
    "company_name": "HelloFresh",
    "num_queries": 20
}

print("="*80)
print("STREAMING + CACHE TEST")
print("="*80)
print()

for run in [1, 2]:
    print(f"\n{'='*80}")
    print(f"RUN #{run} - {'Should be CACHE MISS' if run == 1 else 'Should be CACHE HIT (instant)'}")
    print(f"{'='*80}\n")
    
    start_time = time.time()
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Accept": "text/event-stream"},
            stream=True
        )
        
        category_count = 0
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data = json.loads(line_str[6:])
                    
                    step = data.get("step")
                    status = data.get("status")
                    message = data.get("message")
                    
                    if step == "query_generation":
                        if status == "cached":
                            print(f"⚡ CACHE HIT! {message}")
                        else:
                            print(f"🔄 CACHE MISS - {message}")
                    
                    elif step == "category" and status == "completed":
                        category_count += 1
                        category_name = data.get("data", {}).get("category_name")
                        queries = data.get("data", {}).get("queries", [])
                        elapsed = time.time() - start_time
                        print(f"  [{elapsed:5.2f}s] ✅ {category_name}: {len(queries)} queries")
                    
                    elif step == "complete":
                        elapsed = time.time() - start_time
                        total = data.get("data", {}).get("total_queries", 0)
                        print(f"\n✨ Complete! {total} queries in {elapsed:.2f}s")
        
        if run == 1:
            print("\n⏳ Waiting 1 second before next run...")
            time.sleep(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "="*80)
print("EXPECTED BEHAVIOR:")
print("  Run #1: Should take 10-15 seconds (generating with OpenAI)")
print("  Run #2: Should take <0.1 seconds (instant cache retrieval)")
print("="*80)
