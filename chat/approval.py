"""chat/approval.py — Onay sistemi modülü.

Hassas araçlar (write_file_tool, deftere_kaydet, save_note, complete_task,
ac_uygulama) çalıştırılmadan önce kullanıcıya gösterilir.
onay_bekle() çağrıldığında thread durur, UI onay_ver() ile devam eder.

Bağımlılıklar: threading, json (standart kütüphane)
DI Container: onay_bekle, onay_ver, _onay_kuyrugu, _onay_kararlari, _onay_lock
"""

import json
import logging
import threading

logger = logging.getLogger(__name__)

# ── Onay sistemi durumu ──────────────────────────────────────────────
_onay_kuyrugu = {}      # {call_id: threading.Event}
_onay_kararlari = {}    # {call_id: True/False}
_onay_lock = threading.Lock()


class ApprovalSystem:
    """Onay sistemi — thread-safe onay bekleme ve verme."""

    def __init__(self):
        self._kuyruk = {}      # {call_id: threading.Event}
        self._kararlari = {}   # {call_id: True/False}
        self._lock = threading.Lock()

    def bekle(self, call_id: str, tool_name: str, arguments: dict,
              timeout: float = 120, js_callback=None) -> bool:
        """Hassas araç için kullanıcı onayı bekle.

        Thread'i durdurur; UI onay_ver() ile devam ettirir.
        timeout süresinde yanıt gelmezse reddedilmiş sayılır.
        Dönüş: True (onaylandı) / False (reddedildi/süre doldu)
        """
        event = threading.Event()
        with self._lock:
            self._kuyruk[call_id] = event
            self._kararlari[call_id] = None

        # UI'a onay isteği gönder — iki yol:
        # 1) js_callback parametresi varsa onu kullan (yeni modül)
        # 2) Yoksa basak_app._api._js() ile doğrudan gönder (legacy)
        _gonder = js_callback
        if not _gonder:
            try:
                import basak_app
                if hasattr(basak_app, '_api') and basak_app._api:
                    _gonder = basak_app._api._js
            except Exception:
                pass
        if _gonder:
            try:
                _gonder(
                    "BasakUI.approval(" + json.dumps({
                        "call_id": call_id,
                        "tool": tool_name,
                        "args": arguments,
                    }, ensure_ascii=False) + ")"
                )
            except Exception as e:
                logger.warning("Onay istegi gonderilemedi: %s", e)

        # Onay bekle (timeout ile)
        event.wait(timeout=timeout)

        with self._lock:
            karar = self._kararlari.pop(call_id, None)
            self._kuyruk.pop(call_id, None)

        return bool(karar)

    def ver(self, call_id: str, kabul: bool):
        """UI'dan gelen onay/red yanıtını işler."""
        with self._lock:
            self._kararlari[call_id] = kabul
            event = self._kuyruk.get(call_id)
        if event:
            event.set()


# ── Modül-seviyesi singleton (backward compatibility) ────────────────
_system = ApprovalSystem()


def onay_bekle(call_id: str, tool_name: str, arguments: dict,
               timeout: float = 120) -> bool:
    """Hassas araç için kullanıcı onayı bekle (eski API)."""
    return _system.bekle(call_id, tool_name, arguments, timeout)


def onay_ver(call_id: str, kabul: bool):
    """UI'dan gelen onay/red yanıtını işler (eski API)."""
    _system.ver(call_id, kabul)
