from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base
from app.core.utils import generate_uuid
import enum


class UserRole(str, enum.Enum):
    user = "user"
    manager = "manager"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    groups = relationship("Group", back_populates="user", cascade="all, delete-orphan")
