"""
Authentication module for validating JWT tokens from Next.js Auth.js.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from datetime import datetime

from app.core.config.database import get_async_session
from app.core.config.settings import settings
from app.models.db import User
from app.services import user_service


# Security scheme for Bearer token
security = HTTPBearer()


def get_nextauth_secret() -> str:
    """Get NEXTAUTH_SECRET from settings."""
    secret = settings.NEXTAUTH_SECRET
    if not secret:
        raise ValueError("NEXTAUTH_SECRET environment variable is not set")
    return secret


async def decode_jwt_token(token: str) -> dict:
    """
    Decode and validate JWT token from Next.js Auth.js.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        secret = get_nextauth_secret()
        
        # Decode JWT token
        # Next.js Auth.js uses HS256 algorithm by default
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_exp": True}
        )
        
        return payload
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_session)
) -> User:
    """
    Dependency to get current authenticated user from JWT token.
    
    This function:
    1. Validates the JWT token from Authorization header
    2. Extracts user info (email, google_id, name, picture)
    3. Gets or creates user in database
    4. Returns User object
    
    Args:
        credentials: HTTP Bearer credentials from request header
        db: Database session
    
    Returns:
        User object
    
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    
    # Decode and validate token
    payload = await decode_jwt_token(token)
    
    # Extract user information from token
    # Next.js Auth.js token structure:
    # {
    #   "name": "User Name",
    #   "email": "user@example.com",
    #   "picture": "https://...",
    #   "sub": "google_user_id",
    #   "iat": ...,
    #   "exp": ...,
    #   "jti": "..."
    # }
    
    email = payload.get("email")
    google_id = payload.get("sub")  # 'sub' contains the Google user ID
    name = payload.get("name")
    picture = payload.get("picture")
    
    if not email or not google_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing email or user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get or create user in database
    user = await user_service.get_user_by_google_id(db, google_id)
    
    if not user:
        # Create new user
        user = await user_service.create_user(
            db=db,
            email=email,
            google_id=google_id,
            name=name,
            avatar_url=picture
        )
    else:
        # Update user info if changed
        updated = False
        if user.email != email:
            user.email = email
            updated = True
        if user.name != name:
            user.name = name
            updated = True
        if user.avatar_url != picture:
            user.avatar_url = picture
            updated = True
        
        if updated:
            user.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(user)
    
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_async_session)
) -> Optional[User]:
    """
    Optional authentication dependency.
    Returns User if authenticated, None otherwise.
    Does not raise exception if no token provided.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
