
# src/policy/policy.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import random
import re
import threading
import hashlib
from pathlib import Path
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple
from zoneinfo import ZoneInfo
from loguru import logger

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

_WORD_RE = re.compile(r"[^\s]+", re.UNICODE)
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_CHANNEL_MENTION_RE = re.compile(r"<#\d+>")
_EMOJI_RE = re.compile(r"([\U0001F1E6-\U0001F1FF]|[\U0001F300-\U0001FAFF]|[\U00002700-\U000027BF])")

REACTION_PACK = ("thumbsup", "eyes", "white_check_mark")


@dataclass
class PolicyClock:
    tz: str
    active_start: int
    active_end: int

    def now(self) -> datetime:
        if ZoneInfo:
            return datetime.now(ZoneInfo(self.tz))
        return datetime.utcnow()

    def is_active_hours(self, dt: Optional[datetime] = None) -> bool:
        dt = dt or self.now()
        h = dt.hour
        start, end = self.active_start, self.active_end
        if start <= end:
            return start <= h < end
        return h >= start or h < end


class PolicyEngine:
    def __init__(self, cfg_dict: Dict[str, Any]):
        self.config = cfg_dict.get("POLICY", {})
        self.state_path = Path(cfg_dict.get("STATE", {}).get("PATH", "data/state.json"))
        self.state = self._load_state()
        
        # Параметры политики
        self.timezone = self.config.get("TIMEZONE", "UTC")
        self.active_hours = self.config.get("ACTIVE_HOURS", [9, 23])
        
        # Инициативы
        initiative = self.config.get("INITIATIVE_SLOTS", {})
        self.daily_target = initiative.get("DAILY_TARGET", [4, 6])
        self.min_gap_minutes = initiative.get("MIN_GAP_MINUTES", [45, 120])
        
        # Дедупликация
        dedup = self.config.get("DEDUP", {})
        self.dedup_window_hours = dedup.get("WINDOW_HOURS", 24)
        
        # Красные флаги
        red_flags = self.config.get("RED_FLAGS", {})
        self.silence_hours = red_flags.get("SILENCE_HOURS", 24)
        
        logger.info(f"PolicyEngine initialized | TZ={self.timezone} | Hours={self.active_hours}")
    
    def _load_state(self) -> Dict:
        """Загружает состояние из JSON"""
        if self.state_path.exists():
            try:
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")
        return {"initiatives": [], "messages": [], "red_flags": {}}
    
    def _save_state(self):
        """Сохраняет состояние в JSON"""
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def is_active_now(self) -> bool:
        """Проверяет, находимся ли в активных часах (поддержка через полночь)"""
        try:
            tz = ZoneInfo(self.timezone)
            now = datetime.now(tz)
            h = now.hour
            
            start, end = self.active_hours
            
            if start == end:
                return True  # 24/7
            
            if start < end:
                return start <= h < end
            
            # Окно через полночь (например, 9-1 = 09:00-01:00)
            return (h >= start) or (h < end)
        except Exception as e:
            logger.error(f"Error checking active hours: {e}")
            return True  # На всякий случай разрешаем
    
    def is_silenced(self, account_index: int) -> bool:
        """Проверяет, находится ли аккаунт в режиме молчания (после 429/Verify)"""
        key = str(account_index)
        if key not in self.state.get("red_flags", {}):
            return False
        
        silence_until = self.state["red_flags"][key]
        try:
            until_dt = datetime.fromisoformat(silence_until)
            if datetime.now() < until_dt:
                logger.warning(f"[{account_index}] Still silenced until {silence_until}")
                return True
            else:
                # Время молчания истекло
                del self.state["red_flags"][key]
                self._save_state()
                return False
        except Exception as e:
            logger.error(f"Error parsing silence time: {e}")
            return False
    
    def set_silence(self, account_index: int):
        """Устанавливает режим молчания на SILENCE_HOURS"""
        until = datetime.now() + timedelta(hours=self.silence_hours)
        self.state.setdefault("red_flags", {})[str(account_index)] = until.isoformat()
        self._save_state()
        logger.warning(f"[{account_index}] Silenced until {until}")
    
    def can_initiate_now(self, account_index: int) -> bool:
        """Проверяет, можно ли сейчас отправлять инициативу"""
        if not self.is_active_now():
            logger.debug(f"[{account_index}] Outside active hours")
            return False
        
        if self.is_silenced(account_index):
            return False
        
        # Проверяем дневной лимит инициатив
        today = datetime.now().date().isoformat()
        initiatives = self.state.get("initiatives", [])
        today_count = sum(1 for i in initiatives if i.get("date") == today and i.get("account") == account_index)
        
        max_target = self.daily_target[1] if isinstance(self.daily_target, list) else self.daily_target
        if today_count >= max_target:
            logger.debug(f"[{account_index}] Daily initiative limit reached: {today_count}/{max_target}")
            return False
        
        # Проверяем минимальный промежуток между инициативами
        last_init = next((i for i in reversed(initiatives) if i.get("account") == account_index), None)
        if last_init:
            try:
                last_time = datetime.fromisoformat(last_init["timestamp"])
                min_gap = timedelta(minutes=self.min_gap_minutes[0] if isinstance(self.min_gap_minutes, list) else self.min_gap_minutes)
                if datetime.now() - last_time < min_gap:
                    logger.debug(f"[{account_index}] Too soon since last initiative")
                    return False
            except Exception as e:
                logger.error(f"Error checking last initiative: {e}")
        
        return True
    
    def record_initiative(self, account_index: int):
        """Записывает инициативу в историю"""
        self.state.setdefault("initiatives", []).append({
            "account": account_index,
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().date().isoformat()
        })
        self._save_state()
    
    def is_duplicate(self, text: str) -> bool:
        """Проверяет, было ли похожее сообщение в окне DEDUP_WINDOW_HOURS"""
        text_hash = hashlib.sha256(self._normalize_text(text).encode()).hexdigest()
        
        cutoff = datetime.now() - timedelta(hours=self.dedup_window_hours)
        messages = self.state.get("messages", [])
        
        # Очищаем старые
        messages = [m for m in messages if datetime.fromisoformat(m["timestamp"]) > cutoff]
        self.state["messages"] = messages
        
        # Проверяем дубликат
        if any(m["hash"] == text_hash for m in messages):
            logger.debug(f"Duplicate detected: {text[:50]}...")
            return True
        
        return False
    
    def record_message(self, text: str):
        """Записывает сообщение в историю (для дедупликации)"""
        text_hash = hashlib.sha256(self._normalize_text(text).encode()).hexdigest()
        self.state.setdefault("messages", []).append({
            "hash": text_hash,
            "timestamp": datetime.now().isoformat()
        })
        self._save_state()
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """Нормализует текст для дедупликации"""
        import re
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s]', '', text)
        return text
    
    def get_stats(self, account_index: int) -> Dict:
        """Возвращает статистику по аккаунту"""
        today = datetime.now().date().isoformat()
        initiatives = self.state.get("initiatives", [])
        today_count = sum(1 for i in initiatives if i.get("date") == today and i.get("account") == account_index)
        
        return {
            "initiatives_today": today_count,
            "target": self.daily_target,
            "is_silenced": self.is_silenced(account_index),
            "is_active_hours": self.is_active_now()
        }
