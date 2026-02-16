"""
Rate limiting module for quota management.
"""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import User
from app.services import user_service


async def check_user_quota(db: AsyncSession, user: User) -> None:
    """
    Check if user has quota remaining.
    
    Args:
        db: Database session
        user: User object
    
    Raises:
        HTTPException: 429 if quota exceeded
    """
    has_quota = await user_service.check_user_quota(db, user.id)
    
    if not has_quota:
        quota_info = await user_service.get_user_quota_info(db, user.id)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Quota exceeded. You have used all your available analyses.",
                "quota_used": quota_info["quota_used"],
                "quota_limit": quota_info["quota_limit"],
                "quota_remaining": 0
            }
        )


async def increment_quota(db: AsyncSession, user_id: int) -> User:
    """
    Increment user's quota usage.
    
    Args:
        db: Database session
        user_id: User ID
    
    Returns:
        Updated user
    """
    user = await user_service.update_user_quota(db, user_id, increment=1)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


async def decrement_quota(db: AsyncSession, user_id: int) -> User:
    """
    Decrement user's quota usage (refund).
    Used when a job fails or is cancelled.
    
    Args:
        db: Database session
        user_id: User ID
    
    Returns:
        Updated user
    """
    user = await user_service.update_user_quota(db, user_id, increment=-1)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


async def get_quota_info(db: AsyncSession, user_id: int) -> dict:
    """
    Get user's quota information.
    
    Args:
        db: Database session
        user_id: User ID
    
    Returns:
        Dict with quota_used, quota_limit, quota_remaining
    """
    quota_info = await user_service.get_user_quota_info(db, user_id)
    if not quota_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return quota_info
