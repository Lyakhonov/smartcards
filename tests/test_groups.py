"""
Тесты для работы с группами карточек
"""
import pytest
from app.models.group import Group
from app.models.flashcard import Flashcard
from app.models.user import User, UserRole
from app.core.security import hash_password
from app.core.utils import generate_uuid


class TestGroupRetrieval:
    """Тесты получения групп"""
    
    @pytest.mark.asyncio
    async def test_get_user_groups(
        self, authenticated_client, test_user, test_db
    ):
        """Получение списка групп пользователя"""
        # Создаем несколько групп
        groups = [
            Group(
                id=generate_uuid(),
                filename=f"group_{i}.pdf",
                user_id=test_user.id
            )
            for i in range(3)
        ]
        test_db.add_all(groups)
        await test_db.commit()
        
        response = authenticated_client.get("/groups/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all(g["filename"] for g in data)
    
    @pytest.mark.asyncio
    async def test_get_user_groups_empty(self, authenticated_client):
        """Получение пустого списка групп"""
        response = authenticated_client.get("/groups/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
    
    @pytest.mark.asyncio
    async def test_get_groups_isolation(
        self, authenticated_client, test_user, test_db
    ):
        """Группы видны только их владельцу"""
        # Создаем второго пользователя
        other_user = User(
            id=generate_uuid(),
            email="other@example.com",
            password=hash_password("password123"),
            role=UserRole.user
        )
        test_db.add(other_user)
        await test_db.commit()
        
        # Их группы
        my_groups = [
            Group(
                id=generate_uuid(),
                filename=f"my_group_{i}.pdf",
                user_id=test_user.id
            )
            for i in range(2)
        ]
        other_groups = [
            Group(
                id=generate_uuid(),
                filename=f"other_group_{i}.pdf",
                user_id=other_user.id
            )
            for i in range(2)
        ]
        
        test_db.add_all(my_groups + other_groups)
        await test_db.commit()
        
        response = authenticated_client.get("/groups/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # Видим только свои группы
        assert all(
            g["filename"].startswith("my_group") for g in data
        )


class TestGroupFiltering:
    """Тесты фильтрации группп"""
    
    @pytest.mark.asyncio
    async def test_get_groups_search(
        self, authenticated_client, test_user, test_db
    ):
        """Поиск групп по имени файла"""
        groups = [
            Group(
                id=generate_uuid(),
                filename="python_basics.pdf",
                user_id=test_user.id
            ),
            Group(
                id=generate_uuid(),
                filename="javascript_advanced.pdf",
                user_id=test_user.id
            ),
        ]
        test_db.add_all(groups)
        await test_db.commit()
        
        response = authenticated_client.get("/groups/?q=python")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "python" in data[0]["filename"]
    
    @pytest.mark.asyncio
    async def test_get_groups_sorting(
        self, authenticated_client, test_user, test_db
    ):
        """Сортировка групп"""
        groups = [
            Group(
                id=generate_uuid(),
                filename=f"group_{i}.pdf",
                user_id=test_user.id
            )
            for i in range(3)
        ]
        test_db.add_all(groups)
        await test_db.commit()
        
        response = authenticated_client.get(
            "/groups/?sort_by=filename&order=asc"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3


class TestGroupDeletionAccess:
    """Тесты удаления групп и прав доступа"""
    
    @pytest.mark.asyncio
    async def test_delete_group_requires_manager(
        self, authenticated_client, test_user, test_db
    ):
        """Обычный user не может удалить группу"""
        group = Group(
            id=generate_uuid(),
            filename="to_delete.pdf",
            user_id=test_user.id
        )
        test_db.add(group)
        await test_db.commit()
        
        response = authenticated_client.delete(f"/groups/{group.id}")
        
        # User не может удалять - требуется role manager/admin
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_delete_group_not_found(self, authenticated_client):
        """Ошибка при удалении несуществующей группы"""
        response = authenticated_client.delete(
            "/groups/nonexistent_id"
        )
        
        # User получит 403 (Forbidden) т.к. ему нужна роль manager
        # вместо 404 (Not Found) потому что проверка прав идёт первой
        assert response.status_code == 403

