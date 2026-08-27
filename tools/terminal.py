"""tools/terminal.py — Gerçek terminal aracı.

Başak'ın workspace'i içinde komut çalıştırır.
Güvenlik: workspace dışına kaçış engeli + yıkıcı işlem onayı + timeout.

Korunan: workspace dışı engeli, secret maskeleme (tool_logger), audit (brain).
Kaldırılan: opt-in/canary dinamik süzgeç yok — tüm providerlara aynı set verilir.
"""

import logging
import os
import shlex
import subprocess
import threading

logger = logging.getLogger(__name__)

# Yıkıcı desenler — onay olmadan engellenir (fail-closed).
# Liste kapalı tutulmaz; en tehlikeli çekirdek kapsanır.
_YIKICI_DESENLER = (
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    ":(){:|:&};:",
    "shutdown",
    "reboot",
    "format c:",
    "del /f /s /q c:\\*",
)

_TIMEOUT_VARSAYILAN = 30  # saniye
_CIKTI_LIMIT = 8000  # karakter — model bağlamını şişirmemek için


def _yikici_mi(komut: str) -> str | None:
    t = (komut or "").lower()
    for d in _YIKICI_DESENLER:
        if d.lower() in t:
            return d
    # Disk kökü silme varyantları
    if "rm" in t and "-rf" in t and " / " in t:
        return "rm -rf / varyantı"
    return None


def _guvenli_cwd(cwd: str | None, base_dir: str) -> tuple[str | None, str | None]:
    """cwd'yi workspace altında doğrula. Hata varsa (None, hata_mesaji)."""
    base = os.path.realpath(base_dir) if base_dir else os.getcwd()
    hedef = os.path.realpath(os.path.join(base, cwd)) if cwd else base
    # commonpath ile dış kaçış engeli (file_ops ile aynı ilke)
    try:
        b = os.path.normcase(os.path.realpath(base))
        h = os.path.normcase(os.path.realpath(hedef))
        if h == b or os.path.commonpath([h, b]) == b:
            return hedef, None
        return None, f"Güvenlik engeli: çalışma dizini workspace dışında ({cwd})"
    except ValueError:
        return None, "Güvenlik engeli: çalışma dizini doğrulanamadı"


def terminal_exec(command: str, cwd: str | None = None, timeout: int | None = None, base_dir: str | None = None) -> dict:
    """Komut çalıştırır.

    Args:
        command: Çalıştırılacak komut (shell string).
        cwd: Base'e göre göreli dizin (boş = base).
        timeout: Saniye (varsayılan 30, max 120).
        base_dir: Workspace kökü (chat.py BASE verir).

    Returns:
        {"result": str} veya {"error": str}
    """
    if not command or not command.strip():
        return {"error": "Komut boş olamaz"}

    y = _yikici_mi(command)
    if y:
        return {"error": f"Yıkıcı işlem engellendi ({y}) — onay gerekiyor. Komut: {command[:120]}"}

    base = base_dir or os.getcwd()
    workdir, hata = _guvenli_cwd(cwd, base)
    if hata:
        return {"error": hata}

    try:
        t = int(timeout) if timeout else _TIMEOUT_VARSAYILAN
        t = max(1, min(120, t))
    except (TypeError, ValueError):
        t = _TIMEOUT_VARSAYILAN

    # Windows'ta shell=True gerekli (cmd builtins). Güvenli cwd ile sınırlı.
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=t,
            encoding="utf-8",
            errors="replace",
        )
        out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
        out = out.strip()
        if not out:
            out = f"(çıkış kodu {proc.returncode}, çıktı yok)"
        else:
            if len(out) > _CIKTI_LIMIT:
                out = out[:_CIKTI_LIMIT] + f"\n... ({len(out) - _CIKTI_LIMIT} karakter kesildi)"
            out = f"[kod {proc.returncode}] {out}"
        # Başarı da hata da result — model görmeli
        if proc.returncode != 0 and not out.strip():
            return {"error": out}
        return {"result": out}
    except subprocess.TimeoutExpired:
        return {"error": f"Zaman aşımı ({t}s) — komut durduruldu: {command[:120]}"}
    except Exception as e:
        logger.warning("terminal_exec hatası: %s", e)
        return {"error": f"Komut çalışmadı: {e}"}
