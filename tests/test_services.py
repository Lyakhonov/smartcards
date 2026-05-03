"""
Тесты для сервисного слоя (unit тесты)
"""
import pytest
from datetime import timedelta, datetime, timezone
from app.services.auth_service import (
    create_tokens_for_user,
    refresh_tokens,
)
from app.core.security import hash_password
from app.core.config import settings
from app.models.user import User, UserRole
from app.core.utils import generate_uuid


class TestTokenCreation:
    """Unit тесты создания токенов"""
    
    @pytest.mark.asyncio
    async def test_create_tokens_generates_both(self, test_db, test_user):
        """Создание токенов возвращает оба типа"""
        access, refresh = await create_tokens_for_user(test_db, test_user)
        
        assert access is not None
        assert refresh is not None
        assert len(access) > 0
        assert len(refresh) > 0
    
    @pytest.mark.asyncio
    async def test_create_tokens_different_values(self, test_db, test_user):
        """Каждый раз создаются разные токены"""
        access1, refresh1 = await create_tokens_for_user(test_db, test_user)
        access2, refresh2 = await create_tokens_for_user(test_db, test_user)
        
        # Access токены могут совпадать (быстро созданы)
        # Но refresh должны быть разными
        assert refresh1 != refresh2


class TestTokenRefresh:
    """Unit тесты обновления токенов"""
    
    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, test_db):
        """Обновление с невалидным токеном возвращает None"""
        result = await refresh_tokens(test_db, "invalid_token_string")
        
        assert result == (None, None)


class TestPasswordValidation:
    """Unit тесты валидации пароля"""
    
    def test_password_hash_different_each_time(self):
        """Хеш пароля отличается каждый раз (из-за salt)"""
        password = "test123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2
    
    def test_password_verification_success(self):
        """Проверка корректного пароля"""
        from app.core.security import verify_password
        
        password = "test123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed)
    
    def test_password_verification_failure(self):
        """Проверка неправильного пароля"""
        from app.core.security import verify_password
        
        password = "test123"
        hashed = hash_password(password)
        
        assert not verify_password("wrong_password", hashed)


class TestUserValidation:
    """Unit тесты валидации пользователя"""
    
    def test_user_role_enum(self):
        """Проверка enum ролей"""
        assert UserRole.user.value == "user"
        assert UserRole.manager.value == "manager"
        assert UserRole.admin.value == "admin"
    
    def test_user_creation(self):
        """Создание пользователя с валидными данными"""
        user = User(
            id=generate_uuid(),
            email="test@example.com",
            password=hash_password("password"),
            full_name="Test User",
            role=UserRole.user
        )
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.role == UserRole.user


class TestConfigSettings:
    """Unit тесты конфигурации"""
    
    def test_settings_exist(self):
        """Проверка наличия важных настроек"""
        assert hasattr(settings, "SECRET_KEY")
        assert hasattr(settings, "ALGORITHM")
        assert hasattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES")
        assert hasattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS")
        
        assert len(settings.SECRET_KEY) > 0
        assert settings.ALGORITHM == "HS256"
    
    def test_token_expiry_values_reasonable(self):
        """Проверка разумности времени истечения токенов"""
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES < 1440  # менее суток
        
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS > 0
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS <= 90  # не более 3 месяцев
