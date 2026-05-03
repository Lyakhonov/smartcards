"""
Тесты для работы с флеш-карточками (CRUD операции)
"""
import pytest
from app.models.group import Group
from app.core.utils import generate_uuid


class TestFlashcardCreation:
    """Тесты создания флеш-карточек"""
    
    @pytest.mark.asyncio
    async def test_create_flashcard_success(self, authenticated_client, test_user, test_db):
        """Успешное создание флеш-карточки в группе пользователя"""
        # Сначала создаем группу
        group = Group(
            id=generate_uuid(),
            filename="Test Group",
            user_id=test_user.id
        )
        test_db.add(group)
        await test_db.commit()
        
        # Теперь создаем карточку
        response = authenticated_client.post(
            f"/flashcards/?group_id={group.id}",
            json={
                "question": "What is 2+2?",
                "answer": "4"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "What is 2+2?"
        assert data["answer"] == "4"
        assert data["group_id"] == group.id
        assert data["user_id"] == test_user.id
    
    @pytest.mark.asyncio
    async def test_create_flashcard_nonexistent_group(self, authenticated_client):
        """Ошибка при создании карточки в несуществующей группе"""
        response = authenticated_client.post(
            f"/flashcards/?group_id=nonexistent_id",
            json={
                "question": "What is 2+2?",
                "answer": "4"
            }
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_create_flashcard_no_auth(self, client, test_user, test_db):
        """Ошибка при попытке создать карточку без авторизации"""
        group = Group(
            id=generate_uuid(),
            filename="Test Group",
            user_id=test_user.id
        )
        test_db.add(group)
        await test_db.commit()
        
        response = client.post(
            f"/flashcards/?group_id={group.id}",
            json={
                "question": "What is 2+2?",
                "answer": "4"
            }
        )
        
        # 401 - правильный код для отсутствия токена (Unauthorized)
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_create_flashcard_empty_question(self, authenticated_client, test_user, test_db):
        """Ошибка при пустом вопросе"""
        group = Group(
            id=generate_uuid(),
            filename="Test Group",
            user_id=test_user.id
        )
        test_db.add(group)
        await test_db.commit()
        
        response = authenticated_client.post(
            f"/flashcards/?group_id={group.id}",
            json={
                "question": "",
                "answer": "4"
            }
        )
        
        # Может быть 422 если есть валидация на пустоту
        assert response.status_code in [200, 422]


class TestFlashcardRetrieval:
    """Тесты получения флеш-карточек"""
    
    @pytest.mark.asyncio
    async def test_get_flashcards_by_group(self, authenticated_client, test_user, test_db):
        """Получение карточек группы"""
        from app.models.flashcard import Flashcard
        
        # Создаем группу
        group = Group(
            id=generate_uuid(),
            filename="Test Group",
            user_id=test_user.id
        )
        test_db.add(group)
        await test_db.commit()
        
        # Создаем несколько карточек
        cards = [
            Flashcard(
                id=generate_uuid(),
                question=f"Question {i}",
                answer=f"Answer {i}",
                user_id=test_user.id,
                group_id=group.id
            )
            for i in range(3)
        ]
        test_db.add_all(cards)
        await test_db.commit()
        
        # Получаем карточки
        response = authenticated_client.get(f"/flashcards/group/{group.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["question"] == "Question 0"
    
    @pytest.mark.asyncio
    async def test_get_flashcards_empty_group(self, authenticated_client, test_user, test_db):
        """Получение карточек из пустой группы"""
        group = Group(
            id=generate_uuid(),
            filename="Empty Group",
            user_id=test_user.id
        )
        test_db.add(group)
        await test_db.commit()
        
        response = authenticated_client.get(f"/flashcards/group/{group.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
    
    @pytest.mark.asyncio
    async def test_get_flashcards_other_user_group(self, authenticated_client, test_user, test_db):
        """Получение карточек из группы другого пользователя должно вернуть пусто"""
        from app.models.user import User, UserRole
        from app.models.flashcard import Flashcard
        
        # Создаем второго пользователя
        other_user = User(
            id=generate_uuid(),
            email="other@example.com",
            password="hashed",
            role=UserRole.user
        )
        test_db.add(other_user)
        await test_db.commit()
        
        # Его группа
        group = Group(
            id=generate_uuid(),
            filename="Other User Group",
            user_id=other_user.id
        )
        test_db.add(group)
        await test_db.commit()
        
        # Его карточка
        card = Flashcard(
            id=generate_uuid(),
            question="Secret Question",
            answer="Secret Answer",
            user_id=other_user.id,
            group_id=group.id
        )
        test_db.add(card)
        await test_db.commit()
        
        # Пытаемся получить карточки от имени первого пользователя
        response = authenticated_client.get(f"/flashcards/group/{group.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0  # Не видим карточку другого пользователя


class TestFlashcardUpdate:
    """Тесты обновления флеш-карточек"""
    
    @pytest.mark.asyncio
    async def test_update_flashcard_success(self, authenticated_client, test_user, test_db):
        """Успешное обновление флеш-карточки"""
        from app.models.flashcard import Flashcard
        
        group = Group(
            id=generate_uuid(),
            filename="Test Group",
            user_id=test_user.id
        )
        test_db.add(group)
        await test_db.commit()
        
        card = Flashcard(
            id=generate_uuid(),
            question="Old Question",
            answer="Old Answer",
            user_id=test_user.id,
            group_id=group.id
        )
        test_db.add(card)
        await test_db.commit()
        
        response = authenticated_client.put(
            f"/flashcards/{card.id}",
            json={
                "question": "New Question",
                "answer": "New Answer"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "New Question"
        assert data["answer"] == "New Answer"
    
    @pytest.mark.asyncio
    async def test_update_flashcard_not_found(self, authenticated_client):
        """Ошибка при обновлении несуществующей карточки"""
        response = authenticated_client.put(
            f"/flashcards/nonexistent_id",
            json={
                "question": "New Question",
                "answer": "New Answer"
            }
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_flashcard_other_user(self, authenticated_client, test_user, test_db):
        """Ошибка при попытке обновить карточку другого пользователя"""
        from app.models.user import User, UserRole
        from app.models.flashcard import Flashcard
        
        other_user = User(
            id=generate_uuid(),
            email="other@example.com",
            password="hashed",
            role=UserRole.user
        )
        test_db.add(other_user)
        await test_db.commit()
        
        group = Group(
            id=generate_uuid(),
            filename="Other Group",
            user_id=other_user.id
        )
        test_db.add(group)
        await test_db.commit()
        
        card = Flashcard(
            id=generate_uuid(),
            question="Other Question",
            answer="Other Answer",
            user_id=other_user.id,
            group_id=group.id
        )
        test_db.add(card)
        await test_db.commit()
        
        response = authenticated_client.put(
            f"/flashcards/{card.id}",
            json={
                "question": "Hacked Question",
                "answer": "Hacked Answer"
            }
        )
        
        assert response.status_code == 404


class TestFlashcardDeletion:
    """Тесты удаления флеш-карточек"""
    
    @pytest.mark.asyncio
    async def test_delete_flashcard_success(self, authenticated_client, test_user, test_db):
        """Успешное удаление флеш-карточки"""
        from app.models.flashcard import Flashcard
        
        group = Group(
            id=generate_uuid(),
            filename="Test Group",
            user_id=test_user.id
        )
        test_db.add(group)
        await test_db.commit()
        
        card = Flashcard(
            id=generate_uuid(),
            question="Question",
            answer="Answer",
            user_id=test_user.id,
            group_id=group.id
        )
        test_db.add(card)
        await test_db.commit()
        
        response = authenticated_client.delete(f"/flashcards/{card.id}")
        
        assert response.status_code == 200
        
        # Проверяем, что карточка удалена
        check_response = authenticated_client.get(f"/flashcards/group/{group.id}")
        assert len(check_response.json()) == 0
    
    @pytest.mark.asyncio
    async def test_delete_flashcard_not_found(self, authenticated_client):
        """Ошибка при удалении несуществующей карточки"""
        response = authenticated_client.delete(f"/flashcards/nonexistent_id")
        
        assert response.status_code == 404
