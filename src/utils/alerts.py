# Optional File: src/utils/alerts.py
# Назначение: простые алерты в текстовый лог + stdout при многократных 429/банах/выключении отправки в канале.

import os, time, json
from loguru import logger
from pathlib import Path

ALERTS_LOG = Path("logs/alerts.log")

def alert(event: str, account_index: int, details: dict):
    ALERTS_LOG.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": int(time.time()),
        "event": event,
        "account": account_index,
        "details": details,
    }
    with ALERTS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    logger.warning(f"[ALERT] {event} | acc={account_index} | {details}")

# Пример использования (в местах обработки ошибок 429):
#   if status == 429:
#       alert("discord_429", self.account.index, {"channel": channel_id, "retry_after": retry_after})
#       policy.red_flag(self.account.index, "429")   # и тут же замолкаем на 24 часа (см. POLiCY.RED_FLAGS)
