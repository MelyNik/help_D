from src.utils.reader import read_txt_file
import asyncio
import random
from loguru import logger
from curl_cffi.requests import AsyncSession

from .utils import calculate_nonce, create_x_super_properties
from src.utils.config import Config, get_config
from src.utils.constants import Account
from src.utils.writer import update_account
from src.utils.redact import redact_sensitive

async def message_sender(account: Account, config: Config, session: AsyncSession) -> bool:
    """
    Отправляет сообщения из файла в указанный канал
    """
    try:
        # === OVERRIDE: подхват MESSAGE_FILE_OVERRIDE из конфига ===
        cfg = get_config()
        override = getattr(cfg.MESSAGE_SENDER, 'MESSAGE_FILE_OVERRIDE', '') or ''
        
        if override:
            # Если задан override - загружаем файл напрямую
            from src.utils.reader import read_txt_file
            from pathlib import Path
            file_path = Path(f"data/messages/{override}.txt")
            if not file_path.exists():
                logger.error(f"[{account.index}] Override file not found: {file_path}")
                return False
            messages_list = read_txt_file(override, str(file_path))
            logger.info(f"[{account.index}] Using MESSAGE_FILE_OVERRIDE: {override}")
        else:
            # Иначе берем из MESSAGES_TXT аккаунта
            messages_list = account.messages_to_send
        
        if not messages_list:
            logger.warning(f"[{account.index}] No messages to send")
            return False
        
        # === Выбираем сообщения ===
        num_to_send = config.MESSAGE_SENDER.NUMBER_OF_MESSAGES_TO_SEND
        
        if config.MESSAGE_SENDER.SEND_MESSAGES_RANDOMLY:
            selected = random.sample(messages_list, min(num_to_send, len(messages_list)))
        else:
            selected = messages_list[:num_to_send]
        
        logger.info(f"[{account.index}] Will send {len(selected)} messages to channel {config.MESSAGE_SENDER.CHANNEL_ID}")
        
        # === Отправляем ===
        for i, message_text in enumerate(selected, 1):
            try:
                # Отправка
                url = f"https://discord.com/api/v9/channels/{config.MESSAGE_SENDER.CHANNEL_ID}/messages"
                payload = {"content": message_text}
                
                response = await session.post(
                    url,
                    json=payload,
                    headers={
                        "Authorization": account.token,
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    logger.success(f"[{account.index}] Message {i}/{len(selected)} sent")
                    
                    # Если нужно сразу удалить
                    if config.MESSAGE_SENDER.DELETE_MESSAGE_INSTANTLY:
                        message_id = response.json().get("id")
                        if message_id:
                            await asyncio.sleep(1)
                            delete_url = f"https://discord.com/api/v9/channels/{config.MESSAGE_SENDER.CHANNEL_ID}/messages/{message_id}"
                            await session.delete(delete_url, headers={"Authorization": account.token})
                            logger.info(f"[{account.index}] Message deleted")
                
                elif response.status_code == 429:
                    retry_after = response.json().get("retry_after", 60)
                    logger.warning(f"[{account.index}] Rate limited, retry after {retry_after}s")
                    
                    # Устанавливаем silence через PolicyEngine
                    if hasattr(config, 'POLICY_ENGINE'):
                        config.POLICY_ENGINE.set_silence(account.index)
                    
                    await asyncio.sleep(retry_after)
                    continue
                
                else:
                    logger.error(f"[{account.index}] Failed to send: {response.status_code} {redact_sensitive(response.text)}")
                
                # Пауза между сообщениями
                if i < len(selected):
                    pause = random.randint(*config.MESSAGE_SENDER.PAUSE_BETWEEN_MESSAGES)
                    logger.info(f"[{account.index}] Waiting {pause}s before next message...")
                    await asyncio.sleep(pause)
            
            except Exception as e:
                logger.error(f"[{account.index}] Error sending message: {e}")
                continue
        
        return True
    
    except Exception as e:
        logger.error(f"[{account.index}] message_sender failed: {e}")
        return False
    

async def send_chat_message(account: Account, config: Config, session: AsyncSession, server_id: str, channel_id: str, message: str) -> str:
    for retry in range(config.SETTINGS.ATTEMPTS):
        try:
            headers = {
                'accept': '*/*',
                'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,zh-TW;q=0.6,zh;q=0.5',
                'authorization': account.token,
                'content-type': 'application/json',
                'origin': 'https://discord.com',
                'priority': 'u=1, i',
                'referer': f'https://discord.com/channels/{server_id}/{channel_id}',
                'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
                'x-debug-options': 'bugReporterEnabled',
                'x-discord-locale': 'en-US',
                'x-discord-timezone': 'Etc/GMT-2',
                'x-super-properties': create_x_super_properties(),
            }

            json_data = {
                'mobile_network_type': 'unknown',
                'content': message,
                'nonce': calculate_nonce(),
                'tts': False,
                'flags': 0,
            }

            response = await session.post(
                f'https://discord.com/api/v9/channels/{channel_id}/messages',
                headers=headers,
                json=json_data,
            )

            if response.status_code == 200:
                logger.success(f"{account.index} | Message sent successfully.")
                return response.json()['id']
            else:
                raise Exception(response.text)

        except Exception as e:
            random_sleep = random.randint(config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0], config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1])
            logger.error(f"{account.index} | Error sending chat message: {e}. Retrying in {random_sleep} seconds...")
            await asyncio.sleep(random_sleep)

    return None

async def delete_message(account: Account, config: Config, session: AsyncSession, server_id: str, channel_id: str, message_id: str) -> bool:
    for retry in range(config.SETTINGS.ATTEMPTS):
        try:
            headers = {
                'accept': '*/*',
                'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,zh-TW;q=0.6,zh;q=0.5',
                'authorization': account.token,
                'origin': 'https://discord.com',
                'priority': 'u=1, i',
                'referer': f'https://discord.com/channels/{server_id}/{channel_id}',
                'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
                'x-debug-options': 'bugReporterEnabled',
                'x-discord-locale': 'en-US',
                'x-discord-timezone': 'Etc/GMT-2',
                'x-super-properties': create_x_super_properties(),
                }

            response = await session.delete(
                f'https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}',
                headers=headers,
            )

            if response.status_code == 204:
                logger.success(f"{account.index} | Message deleted successfully.")
                return True
            else:
                raise Exception(response.text)

        except Exception as e:
            logger.error(f"{account.index} | Error deleting message: {e}")

    return False

