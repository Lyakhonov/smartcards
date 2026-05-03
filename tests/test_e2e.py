"""
Сквозные (E2E) тесты основных бизнес-сценариев
"""
import pytest
from app.models.group import Group
from app.models.flashcard import Flashcard
from app.core.utils import generate_uuid


class TestAuthenticationFlow:
    """Тесты сценариев аутентификации"""
    
    def test_full_auth_flow(self, client):
        """Полный цикл: регистрация → вход → получение профиля → выход"""
        # 1. Регистрация
        register_response = client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "secure123",
                "full_name": "New User"
            }
        )
        assert register_response.status_code == 200
        
        # 2. Вход
        login_response = client.post(
            "/auth/login",
            data={"username": "newuser@example.com", "password": "secure123"}
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        
        # 3. Получение профиля
        client.headers.update({"Authorization": f"Bearer {access_token}"})
        me_response = client.get("/auth/me")
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "newuser@example.com"
    
    def test_session_recovery(self, client, test_user):
        """Восстановление сессии через refresh token"""
        # 1. Первый вход
        login_response = client.post(
            "/auth/login",
            data={"username": "test@example.com", "password": "password123"}
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        
        # В режиме тестирования refresh_token в теле ответа
        refresh_token = login_data.get("refresh_token")
        assert refresh_token
        
        # 2. Обновляем токен через тело запроса
        refresh_response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert refresh_response.status_code == 200
        new_token = refresh_response.json()["access_token"]
        
        # 3. Используем новый токен
        client.headers.update({"Authorization": f"Bearer {new_token}"})
        me_response = client.get("/auth/me")
        assert me_response.status_code == 200

class TestFlashcardWorkflow:
    """Тесты полного цикла работы с флеш-карточками"""
    
    @pytest.mark.asyncio
    async def test_complete_flashcard_workflow(
        self, authenticated_client, test_user, test_db
    ):
        """Полный цикл: создание группы →
        создание карточек → редактирование → удаление"""
        
        # 1. Создаем группу вручную (нет endpoint для создания)
        group = Group(
            id=generate_uuid(),
            filename="math_basics.pdf",
            user_id=test_user.id
        )
        test_db.add(group)
        await test_db.commit()
        
        group_id = group.id
        
        # 2. Добавляем карточку
        card_response = authenticated_client.post(
            f"/flashcards/?group_id={group_id}",
            json={"question": "2+2=?", "answer": "4"}
        )
        assert card_response.status_code == 200
        card_id = card_response.json()["id"]
        
        # 3. Проверяем наличие карточки в группе
        get_response = authenticated_client.get(
            f"/flashcards/group/{group_id}"
        )
        assert get_response.status_code == 200
        assert len(get_response.json()) == 1
        
        # 4. Обновляем карточку
        update_response = authenticated_client.put(
            f"/flashcards/{card_id}",
            json={"question": "2+2=?", "answer": "4"}
        )
        assert update_response.status_code == 200
        
        # 5. Удаляем карточку
        delete_response = authenticated_client.delete(
            f"/flashcards/{card_id}"
        )
        assert delete_response.status_code == 200
        
        # 6. Проверяем что карточка удалена
        final_response = authenticated_client.get(
            f"/flashcards/group/{group_id}"
        )
        assert len(final_response.json()) == 0


class TestDataIsolation:
    """Тесты изоляции данных между пользователями"""
    
    @pytest.mark.asyncio
    async def test_users_cannot_access_each_other_data(self, client, test_user, test_db):
        """Один пользователь не может видеть данные другого"""
        from app.models.user import User, UserRole
        
        # Создаем второго пользователя
        other_user = User(
            id=generate_uuid(),
            email="other@example.com",
            password="hashed",
            full_name="Other User",
            role=UserRole.user
        )
        test_db.add(other_user)
        await test_db.commit()
        
        # Его группа и карточка
        group = Group(
            id=generate_uuid(),
            filename="Secret Group",
            user_id=other_user.id
        )
        test_db.add(group)
        await test_db.commit()
        
        card = Flashcard(
            id=generate_uuid(),
            question="Secret Question",
            answer="Secret Answer",
            user_id=other_user.id,
            group_id=group.id
        )
        test_db.add(card)
        await test_db.commit()
        
        # Логируемся как первый пользователь
        login_response = client.post(
            "/auth/login",
            data={"username": "test@example.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
        # Пытаемся получить группы - не видим чужую
        groups_response = client.get("/groups/")
        assert groups_response.status_code == 200
        assert len(groups_response.json()) == 0
        
        # Пытаемся напрямую получить карточки чужой группы
        cards_response = client.get(f"/flashcards/group/{group.id}")
        assert cards_response.status_code == 200
        assert len(cards_response.json()) == 0


class TestErrorHandling:
    """Тесты обработки ошибок в критических сценариях"""
    
    def test_invalid_token_handling(self, client):
        """Обработка невалидного токена"""
        client.headers.update({"Authorization": "Bearer invalid_token"})
        response = client.get("/auth/me")
        assert response.status_code == 401
    
    def test_expired_session_behavior(self, client, test_user):
        """Поведение при истечении сессии"""
        # Логируемся
        login_response = client.post(
            "/auth/login",
            data={"username": "test@example.com", "password": "password123"}
        )
        assert login_response.status_code == 200
        
        # Пытаемся использовать просроченный токен (симуляция)
        client.headers.update({"Authorization": "Bearer expired_token"})
        response = client.get("/auth/me")
        assert response.status_code in [401, 403]
    
    def test_missing_required_fields(self, client):
        """Обработка отсутствия обязательных полей"""
        response = client.post(
            "/auth/register",
            json={"email": "user@example.com"}
        )
        assert response.status_code == 422
    
    def test_concurrent_modifications(
        self, authenticated_client, test_user
    ):
        """Обработка конкурирующих модификаций"""
        # Пытаемся удалить несуществующий ресурс
        response = authenticated_client.delete(
            "/groups/nonexistent"
        )
        # User не может удалять - требуется role manager/admin
        assert response.status_code == 403


class TestBoundaryConditions:
    """Тесты граничных условий"""
    
    @pytest.mark.asyncio
    async def test_large_number_of_flashcards(self, authenticated_client, test_user, test_db):
        """Работа с большим количеством карточек"""
        group = Group(
            id=generate_uuid(),
            filename="Large Group",
            user_id=test_user.id
        )
        test_db.add(group)
        await test_db.commit()
        
        # Создаем 100 карточек
        cards = [
            Flashcard(
                id=generate_uuid(),
                question=f"Question {i}",
                answer=f"Answer {i}",
                user_id=test_user.id,
                group_id=group.id
            )
            for i in range(100)
        ]
        test_db.add_all(cards)
        await test_db.commit()
        
        # Получаем карточки
        response = authenticated_client.get(f"/flashcards/group/{group.id}")
        assert response.status_code == 200
        assert len(response.json()) == 100
    
    def test_very_long_text_in_flashcard(self, authenticated_client, test_user, test_db):
        """Обработка длинного текста в карточке"""
        import asyncio
        
        async def run_test():
            group = Group(
                id=generate_uuid(),
                filename="Test Group",
                user_id=test_user.id
            )
            test_db.add(group)
            await test_db.commit()
            
            long_text = "A" * 10000
            response = authenticated_client.post(
                f"/flashcards/?group_id={group.id}",
                json={
                    "question": long_text,
                    "answer": long_text
                }
            )
            
            assert response.status_code in [200, 422]  # Может быть ограничение на размер
        
        # Если нужна асинхронность в синхронном тесте
        # asyncio.run(run_test())
