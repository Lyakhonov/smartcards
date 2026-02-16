from fastapi import Depends, HTTPException
from app.core.security import get_current_user
from app.models.user import UserRole, User


def require_role(*allowed_roles: UserRole):
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="Forbidden",
            )
        return current_user

    return role_checker
