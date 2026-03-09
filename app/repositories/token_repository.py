from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


async def create_refresh_token(db: AsyncSession, **attrs) -> RefreshToken:
    rt = RefreshToken(**attrs)
    db.add(rt)
    await db.commit()
    await db.refresh(rt)
    return rt


async def get_refresh_token_by_hash(
    db: AsyncSession, token_hash: str
) -> RefreshToken | None:
    # eagerly load related user to avoid triggering a synchronous lazy load
    # when accessing `rt.user` later (that would cause MissingGreenlet).
    q = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .options(joinedload(RefreshToken.user))
    )
    return q.scalars().first()


async def revoke_refresh_token(
    db: AsyncSession, rt: RefreshToken, revoked_at: datetime | None = None
):
    rt.revoked = True
    await db.commit()
    await db.refresh(rt)
    return rt


async def revoke_all_for_user(db: AsyncSession, user_id: str):
    q = await db.execute(select(RefreshToken).where(RefreshToken.user_id == user_id))
    tokens = q.scalars().all()
    for t in tokens:
        t.revoked = True
    await db.commit()
