"""
Глобальная конфигурация для всех тестов
"""
import pytest
import asyncio
import os
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Enable testing mode BEFORE importing app
os.environ["TESTING"] = "true"

from app.main import app
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.core.utils import generate_uuid


# Используем в памяти БД SQLite для тестов
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
async def test_db():
    """Создает тестовую БД и выполняет миграции"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    
    # Создаем таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Создаем сессию
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    # Очищаем БД после теста
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
def event_loop():
    """Создает event loop для asyncio тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client(test_db):
    """Создает TestClient с переопределенной БД"""
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Мокируем создание админа чтобы не подключаться к реальной БД
    with patch(
        'app.main.create_admin_if_not_exists',
        new_callable=lambda: AsyncMock()
    ):
        with TestClient(app) as test_client:
            yield test_client
    
    app.dependency_overrides.clear()


# Создаем функцию для создания пользователя
async def _create_test_user(db, email, password, role=UserRole.user):
    """Вспомогательная функция для создания тестового пользователя"""
    user = User(
        id=generate_uuid(),
        email=email,
        password=hash_password(password),
        full_name=f"Test {role.value}",
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
def test_user(event_loop, test_db):
    """Создает тестового пользователя"""
    # Используем event_loop чтобы запустить асинхронную функцию
    user = event_loop.run_until_complete(
        _create_test_user(test_db, "test@example.com", "password123")
    )
    return user


@pytest.fixture
def test_admin(event_loop, test_db):
    """Создает тестового администратора"""
    admin = event_loop.run_until_complete(
        _create_test_user(
            test_db,
            "admin@example.com",
            "admin123",
            role=UserRole.admin
        )
    )
    return admin


@pytest.fixture
def authenticated_client(client, test_user):
    """Возвращает клиент с авторизованным пользователем"""
    # Логируемся
    response = client.post(
        "/auth/login",
        data={"username": "test@example.com", "password": "password123"}
    )
    
    if response.status_code == 200:
        token = response.json().get("access_token")
        client.headers.update({"Authorization": f"Bearer {token}"})
    
    return client
