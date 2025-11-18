"""
Test client for the Industry Detector API.

This script demonstrates how to consume the streaming API endpoint.
"""

import requests
import json
import sys


def test_streaming_analysis(company_url: str, company_name: str = None):
    """
    Test the streaming company analysis endpoint.
    
    Args:
        company_url: Company website URL
        company_name: Optional company name
    """
    api_url = "http://localhost:8000/industry/analyze"
    
    payload = {
        "company_url": company_url
    }
    
    if company_name:
        payload["company_name"] = company_name
    
    print(f"\n{'='*60}")
    print(f"Analyzing: {company_url}")
    if company_name:
        print(f"Company: {company_name}")
    print(f"{'='*60}\n")
    
    try:
        # Make streaming request
        response = requests.post(
            api_url,
            json=payload,
            stream=True,
            headers={"Accept": "text/event-stream"}
        )
        
        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code}")
            print(response.text)
            return
        
        # Process streaming events
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                
                # SSE format: "data: {json}"
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # Remove "data: " prefix
                    
                    try:
                        event = json.loads(data_str)
                        
                        step = event.get('step', 'unknown')
                        status = event.get('status', 'unknown')
                        message = event.get('message', '')
                        data = event.get('data')
                        
                        # Format output based on step
                        if step == "initialize":
                            print(f"🚀 {message}")
                        
                        elif step == "scraping":
                            if status == "in_progress":
                                print(f"🌐 {message}")
                            elif status == "completed":
                                print(f"✅ {message}")
                            elif status == "failed":
                                print(f"❌ {message}")
                        
                        elif step == "analyzing":
                            if status == "in_progress":
                                print(f"🤖 {message}")
                            elif status == "completed":
                                print(f"✅ {message}")
                            elif status == "warning":
                                print(f"⚠️  {message}")
                        
                        elif step == "competitors":
                            if status == "completed":
                                print(f"🏢 {message}")
                        
                        elif step == "complete":
                            if status == "success":
                                print(f"\n{'='*60}")
                                print(f"✨ {message}")
                                print(f"{'='*60}\n")
                                
                                if data:
                                    print("📊 RESULTS:")
                                    print(f"  Company Name: {data.get('company_name')}")
                                    print(f"  Industry: {data.get('industry')}")
                                    print(f"\n  Description:")
                                    print(f"    {data.get('company_description')}")
                                    print(f"\n  Summary:")
                                    print(f"    {data.get('company_summary')}")
                                    
                                    competitors = data.get('competitors', [])
                                    if competitors:
                                        print(f"\n  Competitors ({len(competitors)}):")
                                        for i, comp in enumerate(competitors, 1):
                                            print(f"    {i}. {comp}")
                                    else:
                                        print(f"\n  Competitors: None identified")
                            
                            elif status == "error":
                                print(f"\n❌ {message}")
                        
                        elif step == "error":
                            print(f"\n❌ ERROR: {message}")
                    
                    except json.JSONDecodeError:
                        print(f"Failed to parse event: {data_str}")
        
        print(f"\n{'='*60}\n")
    
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API server.")
        print("   Make sure the server is running: python src/app.py")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")


if __name__ == "__main__":
    # Example usage
    if len(sys.argv) < 2:
        print("Usage: python test_api_client.py <company_url> [company_name]")
        print("\nExamples:")
        print("  python test_api_client.py https://hellofresh.com HelloFresh")
        print("  python test_api_client.py https://stripe.com")
        sys.exit(1)
    
    url = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 else None
    
    test_streaming_analysis(url, name)
