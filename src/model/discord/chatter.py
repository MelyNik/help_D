"""
Исправленный chatter.py с интеграцией PolicyEngine и "10% реакция"
ЗАМЕНИТЕ ВЕСЬ ФАЙЛ src/model/discord/chatter.py на этот код
"""
import asyncio
import random
import re
from loguru import logger
from curl_cffi.requests import AsyncSession

from src.utils.config import Config
from src.utils.constants import Account
from src.model.gpt import ask_chatgpt


# Регулярка для определения вопросов
QUESTION_RE = re.compile(r"\?|\b(почему|зачем|как|когда|где|что|кто|why|how|when|where|what|who)\b", re.I)

# Белый список реакций
REACTION_EMOJI = ["👍", "🔥", "🙏", "💪", "✨", "❤️", "😊"]

# Запрещенные фразы (голое gm)
GM_WHITELIST = ["gm everyone", "gm all", "gm fam", "gm folks", "gm team", "gm builders", "gm frens"]


def should_reply_with_reaction(incoming_text: str, reaction_chance: float = 0.10) -> bool:
    """Если нет вопроса, в 10% случаев отвечаем реакцией вместо текста"""
    txt = (incoming_text or "").strip()
    has_question = bool(QUESTION_RE.search(txt))
    return (not has_question) and (random.random() < reaction_chance)


def filter_gm(text: str) -> str:
    """Заменяет голое 'gm' на один из разрешенных вариантов"""
    t = text.strip().lower()
    if t == "gm":
        return random.choice(GM_WHITELIST)
    return text


async def ai_chatter(account: Account, config: Config, session: AsyncSession) -> bool:
    """
    AI-чаттер с интеграцией политики
    """
    try:
        policy = getattr(config, 'POLICY_ENGINE', None)
        
        # Проверяем, можем ли работать
        if policy:
            if policy.is_silenced(account.index):
                logger.warning(f"[{account.index}] Account is silenced (red flag)")
                return False
            
            if not policy.is_active_now():
                logger.info(f"[{account.index}] Outside active hours")
                return False
        
        # Получаем историю сообщений канала
        channel_id = config.AI_CHATTER.CHANNEL_ID
        messages = await fetch_channel_messages(session, account.token, channel_id, limit=50)
        
        if not messages:
            logger.warning(f"[{account.index}] No messages in channel")
            return False
        
        # Определяем количество сообщений для отправки
        num_messages = random.randint(*config.AI_CHATTER.MESSAGES_TO_SEND_PER_ACCOUNT)
        sent_count = 0
        
        for _ in range(num_messages):
            # === Проверка политики перед каждой инициативой ===
            if policy and not policy.can_initiate_now(account.index):
                logger.info(f"[{account.index}] Cannot initiate now (policy)")
                break
            
            # Ищем сообщение для ответа
            target_message = find_reply_target(messages, account, config)
            
            if not target_message:
                logger.debug(f"[{account.index}] No suitable message to reply")
                continue
            
            # === 10% реакция вместо текста ===
            if should_reply_with_reaction(target_message.get("content", "")):
                emoji = random.choice(REACTION_EMOJI)
                success = await add_reaction(session, account.token, channel_id, target_message["id"], emoji)
                if success:
                    logger.success(f"[{account.index}] Sent reaction: {emoji}")
                    sent_count += 1
            else:
                # === Генерация текста через GPT ===
                api_key = random.choice(config.CHAT_GPT.API_KEYS)
                system_prompt = get_system_prompt(config)
                user_message = build_context(messages, target_message)
                
                ok, response_text = await ask_chatgpt(
                    api_key,
                    config.CHAT_GPT.MODEL,
                    user_message,
                    system_prompt,
                    proxy=config.CHAT_GPT.PROXY_FOR_CHAT_GPT
                )
                
                if not ok:
                    logger.error(f"[{account.index}] GPT failed")
                    continue
                
                # Фильтруем "голое gm"
                response_text = filter_gm(response_text)
                
                # Проверяем дедупликацию
                if policy and policy.is_duplicate(response_text):
                    logger.warning(f"[{account.index}] Duplicate message, skipping")
                    continue
                
                # Пауза "подумал"
                think_delay = random.randint(*config.AI_CHATTER.PAUSE_BEFORE_MESSAGE)
                logger.info(f"[{account.index}] Thinking for {think_delay}s...")
                await asyncio.sleep(think_delay)
                
                # Отправка
                success = await send_reply(
                    session,
                    account.token,
                    channel_id,
                    response_text,
                    target_message["id"]
                )
                
                if success:
                    logger.success(f"[{account.index}] Sent reply: {response_text[:50]}...")
                    sent_count += 1
                    
                    # Записываем в политику
                    if policy:
                        policy.record_initiative(account.index)
                        policy.record_message(response_text)
                elif "429" in str(success):
                    # Rate limit - молчим
                    if policy:
                        policy.set_silence(account.index)
                    break
            
            # Пауза между сообщениями
            if sent_count < num_messages:
                pause = random.randint(*config.AI_CHATTER.PAUSE_BETWEEN_MESSAGES)
                logger.info(f"[{account.index}] Waiting {pause}s...")
                await asyncio.sleep(pause)
        
        logger.info(f"[{account.index}] AI Chatter finished: {sent_count} messages sent")
        return sent_count > 0
    
    except Exception as e:
        logger.error(f"[{account.index}] ai_chatter failed: {e}")
        return False


async def fetch_channel_messages(session: AsyncSession, token: str, channel_id: str, limit: int = 50):
    """Получает последние сообщения из канала"""
    try:
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit={limit}"
        response = await session.get(url, headers={"Authorization": token})
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to fetch messages: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return []


def find_reply_target(messages: list, account: Account, config: Config):
    """Находит подходящее сообщение для ответа"""
    # Простая логика: берем случайное из последних 20
    recent = messages[:20]
    
    # Исключаем свои сообщения (если есть метка)
    # В реальности нужно проверять author.id, но у нас нет этой инфы в текущей структуре
    
    if not recent:
        return None
    
    # Проверяем ANSWER_PERCENTAGE и REPLY_PERCENTAGE
    target = random.choice(recent)
    
    # Упрощенная логика: 100% отвечаем на вопросы, REPLY_PERCENTAGE% на остальное
    content = target.get("content", "")
    has_question = bool(QUESTION_RE.search(content))
    
    if has_question:
        return target
    elif random.randint(1, 100) <= config.AI_CHATTER.REPLY_PERCENTAGE:
        return target
    
    return None


def build_context(messages: list, target_message: dict) -> str:
    """Формирует контекст для GPT"""
    # Берем последние 5 сообщений + целевое
    recent = messages[:5]
    context_parts = []
    
    for msg in reversed(recent):
        author = msg.get("author", {}).get("username", "User")
        content = msg.get("content", "")
        context_parts.append(f"{author}: {content}")
    
    return "\n".join(context_parts)


def get_system_prompt(config: Config) -> str:
    """Возвращает системный промпт"""
    content_cfg = config.__dict__.get("POLICY", {}).get("CONTENT", {})
    min_words = content_cfg.get("MIN_WORDS", 3)
    max_words = content_cfg.get("MAX_WORDS", 11)
    
    return f"""You are a helpful Discord user chatting naturally in a community.
- Reply in {min_words}-{max_words} words
- Be casual and friendly
- No links, no channel mentions
- Match the conversation tone
- Don't say you're an AI"""


async def send_reply(session: AsyncSession, token: str, channel_id: str, content: str, message_id: str = None) -> bool:
    """Отправляет сообщение (с опциональным reply)"""
    try:
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
        payload = {"content": content}
        
        if message_id:
            payload["message_reference"] = {"message_id": message_id}
        
        response = await session.post(
            url,
            json=payload,
            headers={
                "Authorization": token,
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            return True
        elif response.status_code == 429:
            logger.warning(f"Rate limited: {response.json()}")
            return "429"
        else:
            logger.error(f"Send failed: {response.status_code} {response.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Error sending reply: {e}")
        return False


async def add_reaction(session: AsyncSession, token: str, channel_id: str, message_id: str, emoji: str) -> bool:
    """Добавляет реакцию на сообщение"""
    try:
        # URL-encode emoji
        import urllib.parse
        emoji_encoded = urllib.parse.quote(emoji)
        
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}/reactions/{emoji_encoded}/@me"
        response = await session.put(url, headers={"Authorization": token})
        
        return response.status_code == 204
    except Exception as e:
        logger.error(f"Error adding reaction: {e}")
        return False