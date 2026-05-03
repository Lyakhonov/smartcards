from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    get_user_by_email,
    get_current_user,
    hash_password,
    verify_password,
)
from app.services.auth_service import (
    create_tokens_for_user,
    refresh_tokens,
    logout_refresh,
)
from app.core.utils import generate_uuid
from app.models.user import User, UserRole
from app.schemas.user import Token, UserCreate, UserResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(user.email, db)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = User(
        id=generate_uuid(),
        email=user.email,
        password=hash_password(user.password),
        full_name=user.full_name,
        role=UserRole.user,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_email(form_data.username, db)

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token, refresh_token = await create_tokens_for_user(db, user)

    # set refresh token in secure httpOnly cookie and return access token JSON
    response_data = {"access_token": access_token, "token_type": "bearer"}
    
    # In testing mode, include refresh token in response body for TestClient compatibility
    if settings.TESTING:
        response_data["refresh_token"] = refresh_token
    
    response = JSONResponse(response_data)

    # Always set httpOnly cookie (ignored in testing but good practice)
    response.set_cookie(
        settings.REFRESH_TOKEN_COOKIE_NAME,
        refresh_token,
        httponly=True,
        samesite="none",
        secure=True,
        max_age=60 * 60 * 24 * settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )
    return response


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Возвращает текущего авторизованного пользователя.
    """
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh(request: Request, db: AsyncSession = Depends(get_db)):
    # Try to get refresh token from cookie first (production)
    raw = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    
    # In testing mode, also try to get from request body (for TestClient)
    if not raw and settings.TESTING:
        try:
            body = await request.json()
            raw = body.get("refresh_token")
        except Exception:
            pass
    
    if not raw:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    new_access, new_refresh = await refresh_tokens(db, raw)
    if not new_access:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    response_data = {"access_token": new_access, "token_type": "bearer"}
    
    # In testing mode, include refresh token in response body
    if settings.TESTING:
        response_data["refresh_token"] = new_refresh
    
    response = JSONResponse(response_data)

    response.set_cookie(
        settings.REFRESH_TOKEN_COOKIE_NAME,
        new_refresh,
        httponly=True,
        samesite="none",
        secure=True,
        max_age=60 * 60 * 24 * settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )
    return response


@router.post("/logout")
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    raw = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    if raw:
        await logout_refresh(db, raw)
    resp = JSONResponse({"detail": "logged out"})
    resp.delete_cookie(settings.REFRESH_TOKEN_COOKIE_NAME)
    return resp
