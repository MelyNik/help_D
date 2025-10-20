from .start import Start
from .prepare_data import prepare_data
from src.model.discord.chatter import ai_chatter
from src.model.discord.send_chat_message import message_sender
from src.utils.config import Config
from src.utils.constants import DataForTasks

__all__ = ["Start", "prepare_data"]

async def prepare_data(config: Config, task: str) -> DataForTasks:
    """
    Подготавливает данные для выполнения задачи
    
    Args:
        config: Конфигурация
        task: Название задачи
    
    Returns:
        Объект с подготовленными данными
    """
    # Заглушка - можно расширить при необходимости
    return DataForTasks()


class Start:
    """
    Класс для запуска задач по аккаунту
    """
    def __init__(self, account, config):
        self.account = account
        self.config = config
        self.session = None
    
    async def initialize(self):
        """Инициализация сессии"""
        from src.utils.discord_client import create_client
        self.session = create_client(self.account.proxy)
        return True
    
    async def flow(self):
        """Выполнение основной задачи"""
        from loguru import logger
        
        task = self.config.SETTINGS.TASK
        
        try:
            if task == "AI Chatter":
                return await ai_chatter(self.account, self.config, self.session)
            
            elif task == "Send message to the channel [Token]":
                return await message_sender(self.account, self.config, self.session)
            
            else:
                logger.warning(f"[{self.account.index}] Unknown task: {task}")
                return False
        
        finally:
            # Закрываем сессию
            if self.session:
                await self.session.close()