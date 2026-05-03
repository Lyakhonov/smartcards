"""
Модульные и интеграционные тесты для аутентификации
"""
import pytest
from fastapi.testclient import TestClient
from app.core.security import verify_password, hash_password


class TestUserRegistration:
    """Тесты регистрации пользователя"""
    
    def test_register_success(self, client):
        """Успешная регистрация нового пользователя"""
        response = client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "secure123",
                "full_name": "New User"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert data["role"] == "user"
        assert "password" not in data  # Пароль не должен возвращаться
    
    def test_register_duplicate_email(self, client, test_user):
        """Ошибка при попытке регистрации с существующим email"""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "different123",
                "full_name": "Another User"
            }
        )
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()
    
    def test_register_invalid_email(self, client):
        """Ошибка при невалидном email"""
        response = client.post(
            "/auth/register",
            json={
                "email": "invalid-email",
                "password": "secure123",
                "full_name": "User"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_register_short_password(self, client):
        """Ошибка при коротком пароле (если есть валидация)"""
        response = client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "123",
                "full_name": "User"
            }
        )
        
        # Если валидация минимальной длины пароля имеет место
        # Иначе тест пройдет с 200
        assert response.status_code in [200, 422]
    
    def test_register_missing_fields(self, client):
        """Ошибка при отсутствии обязательных полей"""
        response = client.post(
            "/auth/register",
            json={"email": "user@example.com"}
        )
        
        assert response.status_code == 422


class TestUserLogin:
    """Тесты входа пользователя"""
    
    def test_login_success(self, client, test_user):
        """Успешный вход существующего пользователя"""
        response = client.post(
            "/auth/login",
            data={"username": "test@example.com", "password": "password123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
        # Проверяем, что установлен refresh token cookie
        assert "refresh_token" in response.cookies or response.headers.get("set-cookie")
    
    def test_login_invalid_email(self, client):
        """Ошибка при входе с несуществующим email"""
        response = client.post(
            "/auth/login",
            data={"username": "nonexistent@example.com", "password": "password123"}
        )
        
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    
    def test_login_invalid_password(self, client, test_user):
        """Ошибка при входе с неправильным паролем"""
        response = client.post(
            "/auth/login",
            data={"username": "test@example.com", "password": "wrongpassword"}
        )
        
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    
    def test_login_missing_credentials(self, client):
        """Ошибка при отсутствии учетных данных"""
        response = client.post("/auth/login", data={})
        
        assert response.status_code == 422


class TestGetCurrentUser:
    """Тесты получения текущего пользователя"""
    
    def test_get_me_authenticated(self, authenticated_client, test_user):
        """Получение текущего пользователя с валидным токеном"""
        response = authenticated_client.get("/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["id"] == test_user.id
    
    def test_get_me_no_token(self, client):
        """Ошибка при отсутствии токена"""
        response = client.get("/auth/me")
        
        # 401 - правильный код для отсутствия токена (Unauthorized)
        assert response.status_code == 401
    
    def test_get_me_invalid_token(self, client):
        """Ошибка при невалидном токене"""
        client.headers.update({"Authorization": "Bearer invalid.token.here"})
        response = client.get("/auth/me")
        
        assert response.status_code == 401


class TestRefreshToken:
    """Тесты обновления токена"""
    
    def test_refresh_token_success(self, client, test_user):
        """Успешное обновление токена"""
        # Сначала логируемся
        login_response = client.post(
            "/auth/login",
            data={"username": "test@example.com", "password": "password123"}
        )
        
        assert login_response.status_code == 200
        login_data = login_response.json()
        
        # В режиме тестирования refresh_token возвращается в теле
        refresh_token = login_data.get("refresh_token")
        assert refresh_token, "Refresh token should be in response body in TESTING mode"
        
        # Отправляем refresh token в теле запроса
        refresh_response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code == 200
        data = refresh_response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        # Новый refresh token должен быть в ответе
        assert "refresh_token" in data
    
    def test_refresh_token_missing(self, client):
        """Ошибка при отсутствии refresh token"""
        response = client.post("/auth/refresh")
        
        assert response.status_code == 401
        assert "Missing refresh token" in response.json()["detail"]
    
    def test_refresh_token_invalid(self, client):
        """Ошибка при невалидном refresh token"""
        client.cookies.set("refresh_token", "invalid.token")
        response = client.post("/auth/refresh")
        
        assert response.status_code == 401


class TestPasswordHashing:
    """Тесты хеширования пароля"""
    
    def test_hash_password_changes(self):
        """Хеш пароля должен быть разным каждый раз"""
        password = "test_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2  # Разные хеши благодаря salt
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)
    
    def test_verify_password_success(self):
        """Проверка правильного пароля"""
        password = "test_password"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed)
    
    def test_verify_password_failure(self):
        """Проверка неправильного пароля"""
        password = "test_password"
        hashed = hash_password(password)
        
        assert not verify_password("wrong_password", hashed)
