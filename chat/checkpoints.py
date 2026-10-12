"""chat/checkpoints.py — Durable Run State & Task Lifecycle (ADR-3).

Sunucu kapansa veya Vercel serverless örneği düşse bile görev ve çalışma
durumunu (checkpoint) kalıcı olarak saklayan ve geri yükleyen motor.
"""

import json
import logging
import os
import threading
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

_CHECKPOINT_LOCK = threading.RLock()


def _checkpoints_dir() -> str:
    from chat.kimlik import kullanici_koku
    d = os.path.join(kullanici_koku(), "checkpoints")
    os.makedirs(d, exist_ok=True)
    return d


def _checkpoint_path(run_id: str) -> str:
    safe_id = "".join(c for c in str(run_id or "") if c.isalnum() or c in ("-", "_"))
    return os.path.join(_checkpoints_dir(), f"{safe_id}.json")


def save_checkpoint(run_id: str, state_data: dict[str, Any]) -> bool:
    """Run state'i atomik olarak diske kaydeder."""
    if not run_id or not isinstance(state_data, dict):
        return False
    path = _checkpoint_path(run_id)
    tmp_path = f"{path}.tmp"
    with _CHECKPOINT_LOCK:
        try:
            data = dict(state_data)
            data["_updated_at"] = time.time()
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
            return True
        except Exception as e:
            logger.warning("Checkpoint kaydedilemedi: %s", e)
            return False


def load_checkpoint(run_id: str) -> Optional[dict[str, Any]]:
    """Kayıtlı run state'i diskten okur."""
    if not run_id:
        return None
    path = _checkpoint_path(run_id)
    with _CHECKPOINT_LOCK:
        try:
            if not os.path.exists(path):
                return None
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Checkpoint okunamadi: %s", e)
            return None


def delete_checkpoint(run_id: str) -> bool:
    """Tamamlanan checkpoint'i temizler."""
    if not run_id:
        return False
    path = _checkpoint_path(run_id)
    with _CHECKPOINT_LOCK:
        try:
            if os.path.exists(path):
                os.remove(path)
            return True
        except Exception as e:
            logger.warning("Checkpoint silinemedi: %s", e)
            return False
