"""
SEO Router - обслуживает robots.txt, sitemap.xml и другие SEO требования
"""

from fastapi import APIRouter
from fastapi.responses import Response
from datetime import datetime
from xml.etree.ElementTree import Element, tostring

router = APIRouter(tags=["seo"])

# Базовый URL приложения (в production используйте из конфига)
BASE_URL = "https://smartcards.example.com"

# Определение индексируемых маршрутов
PUBLIC_ROUTES = [
    {
        "path": "/",
        "priority": 1.0,
        "changefreq": "daily",
        "lastmod": datetime.now().isoformat(),
    },
    {
        "path": "/login",
        "priority": 0.8,
        "changefreq": "never",
        "lastmod": datetime.now().isoformat(),
    },
    {
        "path": "/register",
        "priority": 0.9,
        "changefreq": "never",
        "lastmod": datetime.now().isoformat(),
    },
]


@router.get("/robots.txt", response_class=Response, include_in_schema=False)
async def robots_txt():
    """
    Возвращает robots.txt для управления индексацией поисковыми системами
    
    Правила:
    - Разрешаем индексацию публичных маршрутов
    - Запрещаем индексацию приватных маршрутов
    - Указываем задержку между запросами
    - Ссылка на sitemap
    """
    content = """# SmartCards robots.txt
# Generated automatically

# Allow all bots to crawl public content
User-agent: *
Allow: /
Allow: /login
Allow: /register
Allow: /api/external/*

# Disallow private routes
Disallow: /users
Disallow: /group/
Disallow: /history
Disallow: /loading
Disallow: /admin

# Disallow sensitive paths
Disallow: /api/auth/
Disallow: /api/users/
Disallow: /*.json$
Disallow: /*.py$

# Crawl delay
Crawl-delay: 1

# Sitemap location
Sitemap: """ + f"{BASE_URL}/sitemap.xml"

    return Response(content=content, media_type="text/plain")


@router.get("/sitemap.xml", response_class=Response, include_in_schema=False)
async def sitemap_xml():
    """
    Возвращает sitemap.xml со всеми публичными маршрутами
    
    Формат: XML согласно стандарту https://www.sitemaps.org/
    Включает:
    - loc: URL страницы
    - lastmod: дата последнего изменения
    - changefreq: рекомендуемая частота обновления
    - priority: приоритет для поисковой системы
    """
    # Создаём корневой элемент
    urlset = Element("urlset")
    urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

    # Добавляем маршруты
    for route in PUBLIC_ROUTES:
        url_elem = Element("url")

        # Location
        loc = Element("loc")
        loc.text = f"{BASE_URL}{route['path']}"
        url_elem.append(loc)

        # Last modified
        lastmod = Element("lastmod")
        lastmod.text = route["lastmod"][:10]  # YYYY-MM-DD формат
        url_elem.append(lastmod)

        # Change frequency
        changefreq = Element("changefreq")
        changefreq.text = route["changefreq"]
        url_elem.append(changefreq)

        # Priority
        priority = Element("priority")
        priority.text = str(route["priority"])
        url_elem.append(priority)

        urlset.append(url_elem)

    # Конвертируем в XML string
    xml_str = tostring(urlset, encoding="unicode")
    xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'

    return Response(
        content=xml_declaration + xml_str,
        media_type="application/xml",
    )


@router.get(
    "/.well-known/security.txt",
    response_class=Response,
    include_in_schema=False,
)
async def security_txt():
    """
    Файл security.txt для раскрытия контактов безопасности
    Следует RFC 9116: https://tools.ietf.org/html/rfc9116
    """
    content = """Contact: security@smartcards.example.com
Expires: 2025-04-05T00:00:00.000Z
Preferred-Languages: ru, en
Canonical: https://smartcards.example.com/.well-known/security.txt
"""
    return Response(content=content, media_type="text/plain")
