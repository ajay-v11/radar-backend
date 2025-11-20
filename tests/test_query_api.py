"""
Test the query generation API endpoint.

This script tests the streaming API endpoint.
"""

import requests
import json


def test_query_api():
    """Test the query generation API with streaming."""
    
    print("=" * 80)
    print("QUERY GENERATION API TEST")
    print("=" * 80)
    print()
    
    url = "http://localhost:8000/queries/generate"
    payload = {
        "company_url": "https://hellofresh.com",
        "company_name": "HelloFresh",
        "num_queries": 20
    }
    
    print(f"Testing: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    print("Streaming results...")
    print("-" * 80)
    print()
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Accept": "text/event-stream"},
            stream=True
        )
        
        if response.status_code != 200:
            print(f"❌ Error: HTTP {response.status_code}")
            print(response.text)
            return
        
        # Process streaming response
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data = json.loads(line_str[6:])
                    
                    step = data.get("step")
                    status = data.get("status")
                    message = data.get("message")
                    
                    if step == "industry_detection":
                        if status == "completed":
                            print(f"✅ {message}")
                            industry = data.get("data", {}).get("industry")
                            competitors = data.get("data", {}).get("competitors", [])
                            print(f"   Industry: {industry}")
                            print(f"   Competitors: {', '.join(competitors[:3])}...")
                        else:
                            print(f"🔍 {message}")
                    
                    elif step == "query_generation":
                        print(f"\n🚀 {message}")
                    
                    elif step == "category":
                        if status == "in_progress":
                            category_name = data.get("data", {}).get("category_name")
                            print(f"\n⏳ Generating {category_name}...", end="", flush=True)
                        elif status == "completed":
                            category_name = data.get("data", {}).get("category_name")
                            queries = data.get("data", {}).get("queries", [])
                            print(f"\r✅ {category_name} ({len(queries)} queries)")
                            # Show first 3 queries as sample
                            for i, query in enumerate(queries[:3], 1):
                                print(f"   {i}. {query}")
                            if len(queries) > 3:
                                print(f"   ... and {len(queries) - 3} more")
                    
                    elif step == "complete":
                        print(f"\n✨ {message}")
                        total = data.get("data", {}).get("total_queries", 0)
                        print(f"   Total queries: {total}")
                    
                    elif step == "error":
                        print(f"❌ {message}")
        
        print()
        print("=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API server")
        print("   Make sure the server is running:")
        print("   python -m uvicorn src.app:app --reload")
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    test_query_api()
