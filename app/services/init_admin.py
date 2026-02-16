from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.security import hash_password
from app.core.utils import generate_uuid
from app.models.user import User, UserRole
from app.core.config import settings


async def create_admin_if_not_exists():
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.role == UserRole.admin))
        existing_admin = result.scalars().first()

        if existing_admin:
            print("ℹ️ Admin already exists")
            return

        admin = User(
            id=generate_uuid(),
            email=settings.ADMIN_EMAIL,
            password=hash_password(settings.ADMIN_PASSWORD),
            full_name=settings.ADMIN_FULL_NAME,
            role=UserRole.admin,
        )

        session.add(admin)
        await session.commit()

        print("✅ Default admin created")
        print(f"   email: {settings.ADMIN_EMAIL}")
