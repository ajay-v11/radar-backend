#!/usr/bin/env python3
"""Test database clients (Redis and ChromaDB)"""

import sys
import os

# Add parent directory to path to import config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_redis():
    """Test Redis connection"""
    try:
        from config.database import get_redis_client
        
        redis_client = get_redis_client()
        
        # Test ping
        redis_client.ping()
        
        # Test set/get
        redis_client.set("test_key", "test_value", ex=10)
        value = redis_client.get("test_key")
        
        if value == b"test_value" or value == "test_value":
            return True, "Connection successful, set/get works"
        else:
            return False, "Set/get test failed"
        
    except Exception as e:
        return False, str(e)


def test_chromadb():
    """Test ChromaDB connection"""
    try:
        from config.database import get_chroma_client
        
        client = get_chroma_client()
        
        # Test heartbeat
        heartbeat = client.heartbeat()
        
        # List collections
        collections = client.list_collections()
        
        return True, f"Connection successful, {len(collections)} collections"
        
    except Exception as e:
        return False, str(e)


def main():
    """Run all client tests"""
    print("=" * 60)
    print("Testing Database Clients")
    print("=" * 60)
    print()
    
    tests = [
        ("Redis", test_redis),
        ("ChromaDB", test_chromadb),
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
        print()
        print("💡 Tip: Make sure Docker services are running:")
        print("   docker-compose up -d")
    else:
        print("✅ All client tests passed!")
    
    print()
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
