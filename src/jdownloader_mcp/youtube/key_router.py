"""Enrutador de múltiples API keys de YouTube Data API v3 (round-robin)."""
from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    _PACIFIC_TZ = ZoneInfo("America/Los_Angeles")
except Exception:
    _PACIFIC_TZ = None

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger("jdownloader-mcp.youtube.key_router")

DEFAULT_DAILY_LIMIT = 10_000
PACIFIC_OFFSET_HOURS = -8
STATE_FILE = Path("outputs/.quota_router_state.json")


def _pacific_today_str() -> str:
    if _PACIFIC_TZ is not None:
        return datetime.now(_PACIFIC_TZ).strftime("%Y-%m-%d")
    now_utc = datetime.now(timezone.utc)
    from datetime import timedelta
    now_pacific = now_utc + timedelta(hours=PACIFIC_OFFSET_HOURS)
    return now_pacific.strftime("%Y-%m-%d")


class QuotaExhaustedError(RuntimeError):
    """Se lanza cuando TODAS las API keys configuradas han agotado su cuota."""


@dataclass
class KeySlot:
    key: str
    label: str
    daily_limit: int = DEFAULT_DAILY_LIMIT
    consumed: int = 0
    exhausted: bool = False
    _client: object = field(default=None, repr=False)

    def is_available(self) -> bool:
        return not self.exhausted and self.consumed < self.daily_limit

    def reset(self) -> None:
        self.consumed = 0
        self.exhausted = False
        self._client = None

    def get_client(self):
        if self._client is None:
            self._client = build("youtube", "v3", developerKey=self.key, cache_discovery=False)
        return self._client


class KeyRouter:
    def __init__(
        self,
        keys: list[str | tuple[str, str]],
        daily_limit: int = DEFAULT_DAILY_LIMIT,
        state_file: Path | str | None = STATE_FILE,
    ):
        if not keys:
            raise ValueError("KeyRouter requiere al menos una API key.")

        self.slots: list[KeySlot] = []
        for i, item in enumerate(keys, start=1):
            if isinstance(item, tuple):
                key, label = item
            else:
                key = item
                label = f"key_{i}"
            self.slots.append(KeySlot(key=key.strip(), label=label, daily_limit=daily_limit))

        self._index = 0
        self._lock = threading.Lock()
        self.state_file = Path(state_file) if state_file else None
        self._load_state()

    @classmethod
    def from_env(cls, env_var: str = "YOUTUBE_API_KEY", daily_limit: int = DEFAULT_DAILY_LIMIT) -> "KeyRouter":
        raw = os.getenv(env_var, "").strip()
        if not raw:
            candidates = [k for k in os.environ if k.startswith("YOUTUBE_API_KEY")]
            if candidates:
                keys = []
                for k in sorted(candidates):
                    val = os.environ[k].strip()
                    if val and val != "tu_api_key_aqui":
                        keys.append((val, k))
                if keys:
                    return cls(keys, daily_limit=daily_limit)
            raise ValueError(f"No se encontró la variable '{env_var}' o está vacía.")

        if "," in raw or "\n" in raw:
            parts = [p.strip() for p in raw.replace("\n", ",").split(",") if p.strip()]
            return cls(parts, daily_limit=daily_limit)

        return cls([raw], daily_limit=daily_limit)

    def _load_state(self) -> None:
        if not self.state_file or not self.state_file.is_file():
            return
        today = _pacific_today_str()
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("date") != today:
                return
            saved = data.get("slots", {})
            for slot in self.slots:
                if slot.label in saved:
                    slot.consumed = saved[slot.label].get("consumed", 0)
                    slot.exhausted = saved[slot.label].get("exhausted", False)
        except Exception as e:
            logger.debug(f"No se pudo cargar el estado del router: {e}")

    def _save_state(self) -> None:
        if not self.state_file:
            return
        today = _pacific_today_str()
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "date": today,
                "slots": {
                    s.label: {"consumed": s.consumed, "exhausted": s.exhausted}
                    for s in self.slots
                },
            }
            tmp = self.state_file.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            tmp.replace(self.state_file)
        except Exception as e:
            logger.debug(f"No se pudo guardar el estado del router: {e}")

    def _check_day_rollover_locked(self) -> None:
        today = _pacific_today_str()
        if not self.state_file or not self.state_file.is_file():
            return
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("date") != today:
                for slot in self.slots:
                    slot.reset()
                self._save_state()
        except Exception:
            pass

    def get_slot(self) -> KeySlot:
        with self._lock:
            self._check_day_rollover_locked()
            n = len(self.slots)
            for step in range(n):
                candidate_idx = (self._index + step) % n
                slot = self.slots[candidate_idx]
                if slot.is_available():
                    self._index = (candidate_idx + 1) % n
                    return slot

            raise QuotaExhaustedError(
                f"Todas las API keys ({len(self.slots)}) han agotado su cuota diaria estimada."
            )

    def get_client(self):
        return self.get_slot().get_client()

    def mark_exhausted(self, label: str) -> None:
        with self._lock:
            for s in self.slots:
                if s.label == label:
                    s.exhausted = True
                    break
            self._save_state()

    def report_cost(self, cost: int, label: str | None = None) -> None:
        with self._lock:
            for s in self.slots:
                if label is None or s.label == label:
                    s.consumed += cost
                    if s.consumed >= s.daily_limit:
                        s.exhausted = True
                    break
            self._save_state()
