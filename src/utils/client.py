from curl_cffi.requests import AsyncSession
from loguru import logger


def create_client(proxy: str = None) -> AsyncSession:
    """
    Создает асинхронный HTTP-клиент с curl_cffi
    
    Args:
        proxy: Прокси в формате user:pass@ip:port или http://user:pass@ip:port
    
    Returns:
        AsyncSession с настроенным прокси
    """
    proxies = None
    
    if proxy:
        # Если прокси уже с протоколом - используем как есть
        if proxy.startswith('http://') or proxy.startswith('https://') or proxy.startswith('socks5://'):
            proxies = {"all://": proxy}
            logger.debug(f"Using proxy with protocol: {proxy.split('@')[0]}@***")
        else:
            # Иначе добавляем http://
            proxies = {"all://": f"http://{proxy}"}
            logger.debug(f"Using proxy (added http://): {proxy.split('@')[0]}@***")
    
    return AsyncSession(
        impersonate="chrome131",
        proxies=proxies,
        timeout=30,
        verify=False
    )