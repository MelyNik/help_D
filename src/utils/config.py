from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import yaml, os
from pathlib import Path
import asyncio

from src.utils.constants import DataForTasks


@dataclass
class SettingsConfig:
    DISCORD_TOKEN_FOR_PARSING: str
    PROXY_FOR_PARSING: str
    THREADS: int
    ATTEMPTS: int
    SHUFFLE_ACCOUNTS: bool
    ACCOUNTS_RANGE: Tuple[int, int]
    EXACT_ACCOUNTS_TO_USE: List[int]
    PAUSE_BETWEEN_ATTEMPTS: Tuple[int, int]
    RANDOM_PAUSE_BETWEEN_ACCOUNTS: Tuple[int, int]
    RANDOM_PAUSE_BETWEEN_ACTIONS: Tuple[int, int]
    RANDOM_INITIALIZATION_PAUSE: Tuple[int, int]
    RANDOM_PROFILE_PICTURES: bool
    TASK: str = ""
    DATA_FOR_TASKS: Optional[DataForTasks] = None

@dataclass
class ChatterConfig:
    GUILD_ID: str
    CHANNEL_ID: str
    ANSWER_PERCENTAGE: int
    REPLY_PERCENTAGE: int
    MESSAGES_TO_SEND_PER_ACCOUNT: Tuple[int, int]
    PAUSE_BETWEEN_MESSAGES: Tuple[int, int]
    PAUSE_BEFORE_MESSAGE: Tuple[int, int]

@dataclass
class MessageSenderConfig:
    GUILD_ID: str
    CHANNEL_ID: str
    DELETE_MESSAGE_INSTANTLY: bool
    SEND_MESSAGES_RANDOMLY: bool
    NUMBER_OF_MESSAGES_TO_SEND: int
    PAUSE_BETWEEN_MESSAGES: Tuple[int, int]
    MESSAGE_FILE_OVERRIDE: str = ""

@dataclass
class ChatGPTConfig:
    API_KEYS: List[str]
    MODEL: str
    PROXY_FOR_CHAT_GPT: str

@dataclass
class Config:
    SETTINGS: SettingsConfig
    AI_CHATTER: ChatterConfig
    CHAT_GPT: ChatGPTConfig
    MESSAGE_SENDER: MessageSenderConfig
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @classmethod
    def load(cls, path: str = "config.yaml") -> "Config":
        """Load configuration from yaml file + ENV overlay"""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with p.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        # ===== ENV overlay (non-destructive) =====
        # OPENAI keys: comma-separated
        env_keys = os.getenv("OPENAI_API_KEYS", "").strip()
        if env_keys:
            keys_list = [k.strip() for k in env_keys.split(",") if k.strip()]
            if keys_list:
                data.setdefault("CHAT_GPT", {})["API_KEYS"] = keys_list

        # Proxies via ENV (optional global fallback)
        env_proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
        if env_proxy:
            data.setdefault("CHAT_GPT", {}).setdefault("PROXY_FOR_CHAT_GPT", data.get("CHAT_GPT", {}).get("PROXY_FOR_CHAT_GPT", ""))
            if not data["CHAT_GPT"]["PROXY_FOR_CHAT_GPT"]:
                data["CHAT_GPT"]["PROXY_FOR_CHAT_GPT"] = env_proxy.replace("http://", "").replace("https://", "")
            data.setdefault("SETTINGS", {}).setdefault("PROXY_FOR_PARSING", data.get("SETTINGS", {}).get("PROXY_FOR_PARSING", ""))
            if not data["SETTINGS"]["PROXY_FOR_PARSING"]:
                data["SETTINGS"]["PROXY_FOR_PARSING"] = env_proxy.replace("http://", "").replace("https://", "")

        # Policy timezone via ENV
        env_tz = os.getenv("POLICY_TIMEZONE", "").strip()
        if env_tz:
            data.setdefault("POLICY", {})["TIMEZONE"] = env_tz

        # --- NEW: ENV override for service parsing token ---
        env_parse = os.getenv("DISCORD_TOKEN_FOR_PARSING", "").strip()
        if env_parse:
            data.setdefault("SETTINGS", {})["DISCORD_TOKEN_FOR_PARSING"] = env_parse

        # --- ENV overrides for task targets ---
        ai_gid = os.getenv("AI_GUILD_ID", "").strip()
        ai_cid = os.getenv("AI_CHANNEL_ID", "").strip()
        if ai_gid:
            data.setdefault("AI_CHATTER", {})["GUILD_ID"] = ai_gid
        if ai_cid:
            data.setdefault("AI_CHATTER", {})["CHANNEL_ID"] = ai_cid

        sender_gid = os.getenv("SENDER_GUILD_ID", "").strip()
        sender_cid = os.getenv("SENDER_CHANNEL_ID", "").strip()
        if sender_gid:
            data.setdefault("MESSAGE_SENDER", {})["GUILD_ID"] = sender_gid
        if sender_cid:
            data.setdefault("MESSAGE_SENDER", {})["CHANNEL_ID"] = sender_cid

        msg_override = os.getenv("MESSAGE_FILE_OVERRIDE", "").strip()
        if msg_override:
            data.setdefault("MESSAGE_SENDER", {})["MESSAGE_FILE_OVERRIDE"] = msg_override
        # --- /ENV overrides ---

        return cls(
            SETTINGS=SettingsConfig(
                DISCORD_TOKEN_FOR_PARSING=data["SETTINGS"]["DISCORD_TOKEN_FOR_PARSING"],
                PROXY_FOR_PARSING=data["SETTINGS"]["PROXY_FOR_PARSING"],
                THREADS=data["SETTINGS"]["THREADS"],
                ATTEMPTS=data["SETTINGS"]["ATTEMPTS"],
                SHUFFLE_ACCOUNTS=data["SETTINGS"]["SHUFFLE_ACCOUNTS"],
                ACCOUNTS_RANGE=tuple(data["SETTINGS"]["ACCOUNTS_RANGE"]),
                EXACT_ACCOUNTS_TO_USE=data["SETTINGS"]["EXACT_ACCOUNTS_TO_USE"],
                PAUSE_BETWEEN_ATTEMPTS=tuple(data["SETTINGS"]["PAUSE_BETWEEN_ATTEMPTS"]),
                RANDOM_PAUSE_BETWEEN_ACCOUNTS=tuple(data["SETTINGS"]["RANDOM_PAUSE_BETWEEN_ACCOUNTS"]),
                RANDOM_PAUSE_BETWEEN_ACTIONS=tuple(data["SETTINGS"]["RANDOM_PAUSE_BETWEEN_ACTIONS"]),
                RANDOM_INITIALIZATION_PAUSE=tuple(data["SETTINGS"]["RANDOM_INITIALIZATION_PAUSE"]),
                RANDOM_PROFILE_PICTURES=data["SETTINGS"]["RANDOM_PROFILE_PICTURES"],
                TASK="",
                DATA_FOR_TASKS=None,
            ),
            AI_CHATTER=ChatterConfig(
                GUILD_ID=data["AI_CHATTER"]["GUILD_ID"],
                CHANNEL_ID=data["AI_CHATTER"]["CHANNEL_ID"],
                ANSWER_PERCENTAGE=data["AI_CHATTER"]["ANSWER_PERCENTAGE"],
                REPLY_PERCENTAGE=data["AI_CHATTER"]["REPLY_PERCENTAGE"],
                MESSAGES_TO_SEND_PER_ACCOUNT=tuple(data["AI_CHATTER"]["MESSAGES_TO_SEND_PER_ACCOUNT"]),
                PAUSE_BETWEEN_MESSAGES=tuple(data["AI_CHATTER"]["PAUSE_BETWEEN_MESSAGES"]),
                PAUSE_BEFORE_MESSAGE=tuple(data["AI_CHATTER"]["PAUSE_BEFORE_MESSAGE"]),
            ),
            MESSAGE_SENDER=MessageSenderConfig(
                GUILD_ID=data["MESSAGE_SENDER"]["GUILD_ID"],
                CHANNEL_ID=data["MESSAGE_SENDER"]["CHANNEL_ID"],
                DELETE_MESSAGE_INSTANTLY=data["MESSAGE_SENDER"]["DELETE_MESSAGE_INSTANTLY"],
                SEND_MESSAGES_RANDOMLY=data["MESSAGE_SENDER"]["SEND_MESSAGES_RANDOMLY"],
                NUMBER_OF_MESSAGES_TO_SEND=data["MESSAGE_SENDER"].get("NUMBER_OF_MESSAGES_TO_SEND", 1),
                PAUSE_BETWEEN_MESSAGES=tuple(data["MESSAGE_SENDER"]["PAUSE_BETWEEN_MESSAGES"]),
                MESSAGE_FILE_OVERRIDE=data["MESSAGE_SENDER"].get("MESSAGE_FILE_OVERRIDE", ""),
            ),
            CHAT_GPT=ChatGPTConfig(
                API_KEYS=data["CHAT_GPT"]["API_KEYS"],
                MODEL=data["CHAT_GPT"]["MODEL"],
                PROXY_FOR_CHAT_GPT=data["CHAT_GPT"]["PROXY_FOR_CHAT_GPT"],
            ),
        )


# Singleton
def get_config() -> 'Config':
    if not hasattr(get_config, "_config"):
        get_config._config = Config.load()
    return get_config._config
