"""
External API Service - Random User API Integration
Управляет интеграцией с Random User API
Включает обработку ошибок и повторные попытки
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Конфигурация
REQUEST_TIMEOUT = 5  # секунд
MAX_RETRIES = 2
RETRY_DELAY = 1  # секунда
CACHE_TTL = 300  # 5 минут



class CacheEntry:
    """Простое кэширование с TTL"""

    def __init__(self, data: Any, ttl: int = CACHE_TTL):
        self.data = data
        self.created_at = datetime.now()
        self.ttl = ttl

    def is_expired(self) -> bool:
        return datetime.now() - self.created_at > timedelta(seconds=self.ttl)


class ExternalAPICache:
    """Кэш для результатов внешних API"""

    def __init__(self):
        self._cache = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            entry = self._cache[key]
            if not entry.is_expired():
                return entry.data
            else:
                del self._cache[key]
        return None

    def set(self, key: str, data: Any, ttl: int = CACHE_TTL):
        self._cache[key] = CacheEntry(data, ttl)

    def clear(self):
        self._cache.clear()


cache = ExternalAPICache()


async def fetch_with_retry(
    url: str,
    method: str = "GET",
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    json: Optional[dict] = None,
    retries: int = MAX_RETRIES,
) -> dict:
    """
    Выполняет HTTP запрос с повторными попытками и обработкой ошибок

    Args:
        url: URL для запроса
        method: HTTP метод (GET, POST и т.д.)
        headers: Заголовки запроса
        params: Query параметры
        json: JSON тело запроса
        retries: Количество повторных попыток

    Returns:
        dict: Ответ от API

    Raises:
        Exception: При недоступности API после всех попыток
    """
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)

    for attempt in range(retries + 1):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json,
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status >= 500:
                        # Retry на 5xx ошибках
                        if attempt < retries:
                            await asyncio.sleep(RETRY_DELAY)
                            continue
                    raise Exception(
                        f"API Error: {response.status} "
                        f"{response.reason}"
                    )
        except asyncio.TimeoutError:
            if attempt < retries:
                await asyncio.sleep(RETRY_DELAY)
                continue
            raise Exception("API request timeout")
        except aiohttp.ClientError as e:
            if attempt < retries:
                await asyncio.sleep(RETRY_DELAY)
                continue
            raise Exception(f"API connection error: {str(e)}")

    raise Exception("Max retries exceeded")


async def get_random_users(count: int = 3) -> list:
    """
    Получить случайных пользователей из Random User API

    Особенности:
    - Возвращает пользователей из восточной европы (UA, RS)
    - Кэшируется на 5 минут
    - Graceful degradation при ошибке
    """
    cache_key = f"randomuser_{count}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        users = []
        # Random User API поддерживает только эти страны
        # для близких к русскому языку/культуре
        nationalities = ["ua", "rs"]
        per_country = (count + len(nationalities) - 1) // len(
            nationalities
        )

        for nat in nationalities:
            if len(users) >= count:
                break

            response = await fetch_with_retry(
                "https://randomuser.me/api/",
                params={
                    "results": per_country,
                    "nat": nat,
                    "inc": "name,picture,location,email",
                },
            )

            country_users = response.get("results", [])
            users.extend(country_users)

        # Берём ровно count пользователей
        selected_users = users[:count]

        cache.set(cache_key, selected_users)
        return selected_users
    except Exception as e:
        logger.warning(f"Failed to fetch random users: {str(e)}")
        return []
    except Exception as e:
        logger.warning(f"Failed to fetch random users: {str(e)}")
        return []


async def check_api_health() -> bool:
    """Проверить доступность Random User API"""
    try:
        await get_random_users(1)
        return True
    except Exception:
        return False
