from datetime import datetime, timedelta, timezone
from typing import Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token_raw,
    hash_refresh_token,
)
from app.repositories.token_repository import (
    create_refresh_token as repo_create_refresh_token,
    get_refresh_token_by_hash,
    revoke_refresh_token,
    revoke_all_for_user,
)
from app.models.user import User


async def create_tokens_for_user(db: AsyncSession, user: User) -> Tuple[str, str]:
    """Create access token and refresh token (raw) and persist refresh token hash."""
    access = create_access_token(
        {"sub": user.email}, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    raw_refresh = generate_refresh_token_raw()
    token_hash = hash_refresh_token(raw_refresh)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    await repo_create_refresh_token(
        db,
        user_id=user.id,
        token_hash=token_hash,
        created_at=now,
        expires_at=expires,
        revoked=False,
    )

    return access, raw_refresh


async def refresh_tokens(db: AsyncSession, raw_refresh_token: str) -> Tuple[str, str]:
    """Validate refresh token and rotate (create new refresh token, revoke old one).
    Returns (access_token, new_raw_refresh_token).
    """
    token_hash = hash_refresh_token(raw_refresh_token)
    rt = await get_refresh_token_by_hash(db, token_hash)
    
    # Ensure expires_at is timezone-aware for comparison
    if rt and rt.expires_at and not rt.expires_at.tzinfo:
        rt.expires_at = rt.expires_at.replace(tzinfo=timezone.utc)
    
    if not rt or rt.revoked or rt.expires_at < datetime.now(timezone.utc):
        return None, None

    # rotation: revoke old and create new
    await revoke_refresh_token(db, rt)

    user = rt.user
    return await create_tokens_for_user(db, user)


async def logout_refresh(db: AsyncSession, raw_refresh_token: str):
    token_hash = hash_refresh_token(raw_refresh_token)
    rt = await get_refresh_token_by_hash(db, token_hash)
    if rt:
        await revoke_refresh_token(db, rt)


async def logout_all(db: AsyncSession, user_id: str):
    await revoke_all_for_user(db, user_id)
