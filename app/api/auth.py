"""
Authentication endpoints for testing and user info.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config.database import get_async_session
from app.core.rate_limit import get_quota_info
from app.models.db import User


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get current authenticated user information.
    
    Returns:
        User info including quota information
    """
    quota_info = await get_quota_info(db, current_user.id)
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "avatar_url": current_user.avatar_url,
        "quota": quota_info,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at
    }


@router.get("/quota")
async def get_user_quota(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get current user's quota information.
    
    Returns:
        Quota information (used, limit, remaining)
    """
    return await get_quota_info(db, current_user.id)
