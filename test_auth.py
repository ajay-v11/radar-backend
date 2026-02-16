"""
Test script to verify authentication setup.
Run this after starting the FastAPI server to test JWT validation.
"""
import requests
import jwt
from datetime import datetime, timedelta
import os

# Load NEXTAUTH_SECRET from environment
NEXTAUTH_SECRET = os.getenv("NEXTAUTH_SECRET", "ikLzYfsYF4FYEPOgtE3hGV9jddM/QKcQi2d3yjlCMdg=")
API_URL = "http://localhost:8000"

def create_test_token():
    """Create a test JWT token matching Next.js Auth.js format."""
    payload = {
        "name": "Test User",
        "email": "test@example.com",
        "picture": "https://example.com/avatar.jpg",
        "sub": "google_123456789",  # Google user ID
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(days=30)).timestamp()),
        "jti": "test-jwt-id"
    }
    
    token = jwt.encode(payload, NEXTAUTH_SECRET, algorithm="HS256")
    return token

def test_auth_endpoint():
    """Test the /auth/me endpoint with a valid JWT token."""
    print("🔐 Testing Authentication...")
    print(f"API URL: {API_URL}")
    print(f"Secret: {NEXTAUTH_SECRET[:20]}...")
    
    # Create test token
    token = create_test_token()
    print(f"\n✅ Generated JWT token: {token[:50]}...")
    
    # Test /auth/me endpoint
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{API_URL}/auth/me", headers=headers)
        
        if response.status_code == 200:
            print("\n✅ Authentication successful!")
            print(f"Response: {response.json()}")
        else:
            print(f"\n❌ Authentication failed!")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")

def test_quota_endpoint():
    """Test the /auth/quota endpoint."""
    print("\n\n📊 Testing Quota Endpoint...")
    
    token = create_test_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{API_URL}/auth/quota", headers=headers)
        
        if response.status_code == 200:
            print("✅ Quota endpoint successful!")
            print(f"Response: {response.json()}")
        else:
            print(f"❌ Quota endpoint failed!")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("RADAR Authentication Test")
    print("=" * 60)
    
    test_auth_endpoint()
    test_quota_endpoint()
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)
