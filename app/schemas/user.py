from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str]
    role: UserRole


class Token(BaseModel):
    access_token: str
    token_type: str


class ChangeUserRole(BaseModel):
    role: UserRole
