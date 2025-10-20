import httpx
from loguru import logger


async def ask_chatgpt(
    api_key: str,
    model: str,
    user_message: str,
    system_prompt: str,
    proxy: str = None,
    temperature: float = 0.7,
    max_tokens: int = 150
) -> tuple[bool, str]:
    """
    Отправляет запрос к OpenAI API
    
    Args:
        api_key: OpenAI API ключ
        model: Название модели (gpt-4o-mini, gpt-3.5-turbo и т.д.)
        user_message: Сообщение пользователя
        system_prompt: Системный промпт
        proxy: Прокси в формате http://user:pass@ip:port (опционально)
        temperature: Температура генерации (0.0-2.0)
        max_tokens: Максимум токенов в ответе
    
    Returns:
        tuple[bool, str]: (успех, текст ответа)
    """
    try:
        url = "https://api.openai.com/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Настройка прокси
        proxies = None
        if proxy:
            if not proxy.startswith('http://') and not proxy.startswith('https://'):
                proxy = f"http://{proxy}"
            proxies = {
                "http://": proxy,
                "https://": proxy
            }
        
        # Отправка запроса
        async with httpx.AsyncClient(proxies=proxies, timeout=30.0, verify=False) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                logger.debug(f"GPT response: {content[:100]}...")
                return True, content
            
            elif response.status_code == 429:
                logger.error("GPT rate limit exceeded")
                return False, ""
            
            elif response.status_code == 401:
                logger.error("Invalid OpenAI API key")
                return False, ""
            
            else:
                logger.error(f"GPT API error: {response.status_code} - {response.text[:200]}")
                return False, ""
    
    except httpx.TimeoutException:
        logger.error("GPT request timeout")
        return False, ""
    
    except Exception as e:
        logger.error(f"GPT request failed: {e}")
        return False, ""