"""
User service for CRUD operations on User model.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.models.db import User


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email address."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_google_id(db: AsyncSession, google_id: str) -> Optional[User]:
    """Get user by Google ID."""
    result = await db.execute(select(User).where(User.google_id == google_id))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    google_id: str,
    name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    quota_limit: int = 10
) -> User:
    """Create a new user."""
    user = User(
        email=email,
        google_id=google_id,
        name=name,
        avatar_url=avatar_url,
        quota_limit=quota_limit,
        quota_used=0
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_quota(
    db: AsyncSession,
    user_id: int,
    increment: int = 1
) -> Optional[User]:
    """
    Update user quota usage.
    
    Args:
        db: Database session
        user_id: User ID
        increment: Amount to increment quota_used by (can be negative for refunds)
    
    Returns:
        Updated user or None if not found
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    
    user.quota_used += increment
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


async def check_user_quota(db: AsyncSession, user_id: int) -> bool:
    """
    Check if user has quota remaining.
    
    Returns:
        True if user has quota remaining, False otherwise
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    
    return user.quota_used < user.quota_limit


async def get_user_quota_info(db: AsyncSession, user_id: int) -> Optional[dict]:
    """
    Get user quota information.
    
    Returns:
        Dict with quota_used, quota_limit, quota_remaining
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    
    return {
        "quota_used": user.quota_used,
        "quota_limit": user.quota_limit,
        "quota_remaining": user.quota_limit - user.quota_used
    }
