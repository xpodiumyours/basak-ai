"""Gerçek Başak ortamında Harness v1 için kısa canlı smoke.

Bu bir test sistemi değildir. Gerçek Brain + gerçek ücretsiz provider zinciri +
gerçek salt-okunur araçları dört kısa görevde gözlemler.

Güvenlik:
- master üzerinde çalışmaz,
- gerçek geçmişi/geçici hafızayı yazmaz,
- görev dosyasını değiştirmez,
- yalnız mevcut ayarlar/anahtarları okur,
- ücretli provider yolu sert kapalıdır,
- yazma/sistem aracı çağrılırsa smoke başarısız sayılır.
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
os.chdir(BASE)
sys.path.insert(0, str(BASE))

SAFE_BRANCH = "feature/task-model-harness-v1-20260912"
FORBIDDEN_TOOLS = {
    "add_task", "complete_task", "save_note", "deftere_kaydet",
    "write_file_tool", "ac_uygulama", "is_ac", "is_onayla",
}


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(BASE), *args],
            text=True, encoding="utf-8", errors="replace",
            stderr=subprocess.STDOUT, timeout=10,
        ).strip()
    except Exception:
        return ""


def _first_heading(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            m = re.match(r"^\s*#+\s+(.+?)\s*$", line)
            if m:
                return m.group(1).strip()
    except OSError:
        pass
    return ""


class Collector:
    def __init__(self):
        self.text = ""
        self.source = ""
        self.error = ""

    @staticmethod
    def _json_args(code: str):
        raw = code.split("(", 1)[1].rsplit(")", 1)[0]
        values = []
        decoder = json.JSONDecoder()
        i = 0
        while i < len(raw):
            while i < len(raw) and raw[i] in " \t\r\n,":
                i += 1
            if i >= len(raw):
                break
            value, used = decoder.raw_decode(raw[i:])
            values.append(value)
            i += used
        return values

    def __call__(self, code: str):
        try:
            if code.startswith("BasakUI.reply(") or code.startswith("BasakUI.bitir("):
                vals = self._json_args(code)
                if vals:
                    self.text = str(vals[0] or "")
                if len(vals) > 1:
                    self.source = str(vals[1] or "")
            elif code.startswith("BasakUI.error("):
                vals = self._json_args(code)
                if vals:
                    self.error = str(vals[0] or "")
        except Exception:
            pass


class HarnessLog(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record):
        msg = record.getMessage()
        if "Harness task=" in msg:
            self.lines.append(msg)


def main() -> int:
    branch = _git("branch", "--show-current")
    if branch != SAFE_BRANCH:
        print("DURDU: Bu smoke yalnız güvenli dalda çalışır.")
        print("Beklenen:", SAFE_BRANCH)
        print("Mevcut :", branch or "DOĞRULANAMADI")
        return 2

    plan = BASE / "ANA-PLAN.md"
    heading = _first_heading(plan)
    short_commit = _git("log", "-1", "--format=%h")

    # Önce chat paketini normal public girişinden başlat. _chat_legacy'yi
    # doğrudan ilk import etmek chat.__init__ ile circular import üretir.
    import chat  # noqa: F401
    import _chat_legacy as legacy
    import chat.context as chat_context
    import chat.oturum as oturum
    import tools as tools_pkg
    from basak_app import KISILIK
    from brain import Brain
    from brain.harness import harness_scope
    from chat.flow import mesaj_isle_yeni
    from tools import TOOLS

    brain = Brain()
    # ZERO-COST: ücretli/özel provider smoke sırasında hiçbir koşulda denenmez.
    if hasattr(brain, "_genel"):
        brain._genel = None
    for paid_name in ("deepseek", "kimi"):
        if hasattr(brain, "_providers"):
            brain._providers.pop(paid_name, None)

    try:
        free_chain = [ad for ad, _ in brain._bulut_zinciri()]
    except Exception:
        free_chain = []

    harness_log = HarnessLog()
    logging.getLogger("brain.harness").addHandler(harness_log)
    logging.getLogger("brain.harness").setLevel(logging.INFO)

    original_history = legacy.HISTORY_FILE
    original_tasks = legacy.GOREVLER_FILE
    original_hafiza_al = legacy._hafiza_al
    original_ilgili = legacy._ilgili_anilar
    original_context_hafiza = chat_context.hafiza_al
    original_context_ilgili = chat_context.ilgili_anilar
    original_oturum = oturum.kaydet_cift
    original_calistir = tools_pkg.calistir

    calls: list[str] = []

    def tracked_calistir(name, arguments, *args, **kwargs):
        calls.append(str(name))
        if name in FORBIDDEN_TOOLS:
            return {"error": "SMOKE GÜVENLİK ENGELİ: yazma/sistem aracı çalıştırılmaz"}
        return original_calistir(name, arguments, *args, **kwargs)

    cases = [
        {
            "id": "A",
            "text": "Merhaba, nasılsın?",
            "expected_profile": "chat-lite",
            "expected_tools": set(),
        },
        {
            "id": "B",
            "text": f"{plan} dosyasını oku ve ilk başlığı söyle.",
            "expected_profile": "read-lite",
            "expected_tools": {"read_file"},
        },
        {
            "id": "C",
            "text": "Başak reposunun son commitini göster.",
            "expected_profile": "read-lite",
            "expected_tools": {"git_durum"},
        },
        {
            "id": "D",
            "text": "Vixrex için ne yapabiliriz?",
            "expected_profile": "legacy",
            "expected_tools": None,
        },
    ]

    results = []
    try:
        with tempfile.TemporaryDirectory(prefix="basak-harness-smoke-") as td:
            temp = Path(td)
            history = temp / "gecmis.json"
            tasks = temp / "gorevler.json"
            history.write_text("[]", encoding="utf-8")
            tasks.write_text("[]", encoding="utf-8")

            # Gerçek kullanıcı geçmişi/profili kirlenmesin.
            legacy.HISTORY_FILE = str(history)
            legacy.GOREVLER_FILE = str(tasks)
            legacy._hafiza_al = lambda: None
            legacy._ilgili_anilar = lambda *a, **k: []
            chat_context.hafiza_al = lambda: None
            chat_context.ilgili_anilar = lambda *a, **k: []
            oturum.kaydet_cift = lambda *a, **k: None
            tools_pkg.calistir = tracked_calistir

            for case in cases:
                history.write_text("[]", encoding="utf-8")
                calls.clear()
                harness_log.lines.clear()
                collector = Collector()

                with harness_scope(case["text"]) as profile:
                    try:
                        mesaj_isle_yeni(case["text"], brain, KISILIK, collector, TOOLS)
                    except Exception as exc:
                        collector.error = collector.error or f"Beklenmeyen hata: {exc}"

                actual_tools = list(calls)
                forbidden = sorted(set(actual_tools) & FORBIDDEN_TOOLS)
                checks = []
                checks.append(("profil", profile.name == case["expected_profile"]))
                if case["expected_tools"] is not None:
                    checks.append((
                        "tool",
                        bool(case["expected_tools"] & set(actual_tools))
                        if case["expected_tools"] else not actual_tools,
                    ))
                checks.append(("yasak_tool", not forbidden))
                checks.append(("hata", not collector.error))

                # İçerik doğrulaması yalnız nesnel kanıt olan iki okuma görevinde.
                if case["id"] == "B" and heading:
                    checks.append(("dosya_kanıtı", heading.casefold() in collector.text.casefold()))
                if case["id"] == "C" and short_commit:
                    checks.append(("commit_kanıtı", short_commit.casefold() in collector.text.casefold()))

                passed = all(ok for _, ok in checks)
                results.append({
                    "id": case["id"],
                    "profile": profile.name,
                    "tools": actual_tools,
                    "source": collector.source,
                    "harness": list(harness_log.lines),
                    "answer": collector.text,
                    "error": collector.error,
                    "checks": checks,
                    "passed": passed,
                })
    finally:
        legacy.HISTORY_FILE = original_history
        legacy.GOREVLER_FILE = original_tasks
        legacy._hafiza_al = original_hafiza_al
        legacy._ilgili_anilar = original_ilgili
        chat_context.hafiza_al = original_context_hafiza
        chat_context.ilgili_anilar = original_context_ilgili
        oturum.kaydet_cift = original_oturum
        tools_pkg.calistir = original_calistir
        logging.getLogger("brain.harness").removeHandler(harness_log)

    print("\n=== BAŞAK HARNESS V1 — GERÇEK SMOKE ===")
    print("Dal:", branch)
    print("Repo commit:", short_commit or "DOĞRULANAMADI")
    print("Ücretsiz zincir:", ", ".join(free_chain) if free_chain else "DOĞRULANAMADI")
    for item in results:
        print("\n[%s] %s" % (item["id"], "GEÇTİ" if item["passed"] else "KALDI"))
        print("  profil :", item["profile"])
        print("  tools  :", ", ".join(item["tools"]) if item["tools"] else "yok")
        print("  kaynak :", item["source"] or "DOĞRULANAMADI")
        for line in item["harness"]:
            print("  harness:", line)
        for name, ok in item["checks"]:
            print("  %-14s %s" % (name + ":", "OK" if ok else "HATA"))
        if item["error"]:
            print("  hata   :", item["error"][:240])
        elif item["answer"]:
            one_line = re.sub(r"\s+", " ", item["answer"]).strip()
            print("  cevap  :", one_line[:240])

    total = sum(1 for x in results if x["passed"])
    print("\nSONUÇ: %d/%d geçti" % (total, len(results)))
    if total == len(results):
        print("KARAR: chat-lite/read-lite canlı smoke temiz.")
        return 0
    print("KARAR: web-lite'a geçme; kalan vaka önce incelenmeli.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
