#!/usr/bin/env python3
"""Test all available API keys and AI models"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_openai():
    """Test OpenAI (ChatGPT)"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return False, "API key not found"
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'OK'"}],
            max_tokens=5
        )
        
        result = response.choices[0].message.content
        return True, f"Response: {result}"
        
    except Exception as e:
        return False, str(e)


def test_gemini():
    """Test Google Gemini"""
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        return False, "API key not found"
    
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            google_api_key=api_key,
            max_output_tokens=5
        )
        
        response = llm.invoke("Say 'OK'")
        return True, f"Response: {response.content}"
        
    except Exception as e:
        return False, str(e)


def test_claude():
    """Test Anthropic Claude"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        return False, "API key not found"
    
    try:
        from langchain_anthropic import ChatAnthropic
        
        llm = ChatAnthropic(
            model="claude-3-haiku-20240307",
            anthropic_api_key=api_key,
            max_tokens=5
        )
        
        response = llm.invoke("Say 'OK'")
        return True, f"Response: {response.content}"
        
    except Exception as e:
        return False, str(e)


def test_llama():
    """Test Llama (via Groq)"""
    api_key = os.getenv("GROK_API_KEY")
    
    if not api_key:
        return False, "API key not found"
    
    try:
        from langchain_groq import ChatGroq
        
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            groq_api_key=api_key,
            max_tokens=5
        )
        
        response = llm.invoke("Say 'OK'")
        return True, f"Response: {response.content}"
        
    except Exception as e:
        return False, str(e)


def test_openrouter():
    """Test OpenRouter (Grok/DeepSeek)"""
    api_key = os.getenv("OPEN_ROUTER_API_KEY")
    
    if not api_key:
        return False, "API key not found"
    
    try:
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            model="x-ai/grok-4.1-fast",
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            max_tokens=5
        )
        
        response = llm.invoke("Say 'OK'")
        return True, f"Response: {response.content}"
        
    except Exception as e:
        return False, str(e)


def test_firecrawl():
    """Test Firecrawl (web scraping)"""
    api_key = os.getenv("FIRECRAWL_API_KEY")
    
    if not api_key:
        return False, "API key not found"
    
    try:
        from firecrawl import Firecrawl
        
        firecrawl = Firecrawl(api_key=api_key)
        
        # Test with a simple, fast website
        result = firecrawl.scrape(
            url="https://example.com",
            formats=["markdown"],
            only_main_content=True,
            timeout=10000
        )
        
        if hasattr(result, 'markdown') and result.markdown:
            return True, f"Scraped {len(result.markdown)} characters"
        elif isinstance(result, dict) and "markdown" in result:
            return True, f"Scraped {len(result['markdown'])} characters"
        else:
            return False, "No markdown content returned"
        
    except Exception as e:
        return False, str(e)





def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing All API Keys and Models")
    print("=" * 60)
    print()
    
    tests = [
        ("OpenAI (ChatGPT)", test_openai),
        ("Google Gemini", test_gemini),
        ("Anthropic Claude", test_claude),
        ("Llama (Groq)", test_llama),
        ("OpenRouter (Grok)", test_openrouter),
        ("Firecrawl", test_firecrawl),
    ]
    
    results = []
    
    for name, test_func in tests:
        print(f"Testing {name}...", end=" ")
        
        try:
            success, message = test_func()
            
            if success:
                print(f"✅ PASS")
                print(f"   {message}")
                results.append((name, True, message))
            else:
                print(f"❌ FAIL")
                print(f"   {message}")
                results.append((name, False, message))
                
        except Exception as e:
            print(f"❌ ERROR")
            print(f"   {str(e)}")
            results.append((name, False, str(e)))
        
        print()
    
    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print()
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    print()
    
    if passed < total:
        print("Failed tests:")
        for name, success, message in results:
            if not success:
                print(f"  ❌ {name}: {message}")
    else:
        print("✅ All tests passed!")
    
    print()
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
