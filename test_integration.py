"""
Test script to verify JWT token generation and validation between frontend and backend.
"""
import jwt
from datetime import datetime, timedelta
from app.core.config.settings import settings

def test_jwt_integration():
    """Test that JWT tokens can be created and validated."""
    
    # Get the secret
    secret = settings.NEXTAUTH_SECRET
    print(f"✓ Secret loaded: {secret[:20]}...")
    
    # Create a test token (simulating what Next.js Auth.js does)
    payload = {
        "name": "Test User",
        "email": "test@example.com",
        "picture": "https://example.com/avatar.jpg",
        "sub": "google_123456789",  # Google user ID
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(days=30)).timestamp()),
        "jti": "test-jwt-id"
    }
    
    # Encode token
    token = jwt.encode(payload, secret, algorithm="HS256")
    print(f"✓ Token created: {token[:50]}...")
    
    # Decode token (simulating what backend does)
    try:
        decoded = jwt.decode(token, secret, algorithms=["HS256"])
        print(f"✓ Token decoded successfully")
        print(f"  - Email: {decoded['email']}")
        print(f"  - Name: {decoded['name']}")
        print(f"  - Google ID: {decoded['sub']}")
        return True
    except Exception as e:
        print(f"✗ Token validation failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing JWT Integration...\n")
    success = test_jwt_integration()
    print(f"\n{'✓ All tests passed!' if success else '✗ Tests failed!'}")
