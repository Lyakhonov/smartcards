from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base
from app.core.utils import generate_uuid


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False)
    replaced_by = Column(String, nullable=True)  # пока не используется

    user = relationship("User", backref="refresh_tokens")
