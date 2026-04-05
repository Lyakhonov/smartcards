"""
External API Router - Random User API Integration
Обслуживает запросы к Random User API для получения случайных пользователей
"""

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
import logging
from app.services.external_api import get_random_users, check_api_health

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/external", tags=["external-api"])


@router.get("/randomuser")
async def external_random_user(limit: int = Query(4, ge=1, le=10)):
    """
    Получить случайных пользователей с русской локализацией

    Query параметры:
    - limit: количество пользователей (1-10, по умолчанию 4)

    Возвращает:
    - список пользователей с именем, фото, локацией и другой информацией

    Graceful degradation:
    - При ошибке возвращает пустой список и HTTP 200
    """
    try:
        users = await get_random_users(limit)
        return JSONResponse(
            content=users,
            status_code=200,
            headers={
                "Cache-Control": "public, max-age=300",  # 5 minutes cache
            },
        )
    except Exception as e:
        logger.error(f"Error fetching random users: {str(e)}")
        # Graceful degradation - возвращаем пустой список вместо ошибки
        return JSONResponse(content=[], status_code=200)


@router.get("/health")
async def external_api_health():
    """
    Проверить доступность Random User API

    Возвращает:
    - {"status": "healthy"} если API доступен
    - {"status": "unhealthy"} если API недоступен
    """
    try:
        is_healthy = await check_api_health()
        return JSONResponse(
            content={"status": "healthy" if is_healthy else "unhealthy"},
            status_code=200 if is_healthy else 503,
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            content={"status": "unhealthy"},
            status_code=503,
        )

