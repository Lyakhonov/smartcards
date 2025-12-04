import json
import re

import httpx

LLM_URL = "http://ollama:11434/api/generate"
MODEL = "mistral"  # или  phi3


async def generate_flashcards(text: str, retries=2):
    for attempt in range(retries + 1):
        try:
            return await call_llm_once(text)
        except Exception as e:
            print(f"LLM FAILED attempt {attempt+1}: {e}")
            if attempt == retries:
                return []


async def call_llm_once(text: str):
    prompt = f"""
    РАЗДЕЛИ ТЕКСТ на смысловые блоки и к каждому блоку напиши вопрос.
    question - твой вопрос, answer - смысловой блок.
    Ты — сервис, который возвращает ТОЛЬКО JSON массив без каких-либо комментариев,
    форматирования, Markdown, троеточий, блоков ```json или ```.

    Формат ОЧЕНЬ строгий:

    [
    {{"question": "строка", "answer": "строка"}},
    {{"question": "строка", "answer": "строка"}}
    ]

    Ключи ТОЛЬКО: "question" и "answer".
    Всегда заключай ключи в кавычки.
    Не используй другие ключи.
    Не пиши markdown.
    Не пиши комментариев.
    Если не можешь — верни [].

    ОТВЕЧАЙ НА РУССКОМ ЯЗЫКЕ
    ТЕКСТ:
    {text}
    """
    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(
            LLM_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1},
            },
        )

    data = response.json()
    print("RAW DATA FULL:", data)
    raw = data.get("response", "")

    print("LLM RAW:")
    print(raw)

    return safe_parse_json(raw)


def safe_parse_json(text: str):
    text = text.strip()

    # убираем блоки ```
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)

    # убираем ```json отдельные
    text = text.replace("```json", "").replace("```", "")

    # выбрасываем всё вне массива
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        print("⚠️ NONE JSON → fallback []")
        return []

    json_text = match.group()

    # чистка мусора типа static_json:
    json_text = re.sub(r"static_json\s*:", "", json_text)

    try:
        return json.loads(json_text)
    except Exception as e:
        print("❌ JSON PARSE FAIL", e)
        print(json_text)
        return []
