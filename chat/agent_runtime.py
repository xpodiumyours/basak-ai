"""P2 provider-neutral ajan runtime sozlesmesi.

- Capability = gercek arac katalogu; model yetenek_ac ile alan acar,
  gizli resolver/kelime filtresi yoktur.
- tool_policy = acik run politikasi: auto | required | none.
- Run state, UI olayindan ayridir ve disaridan denetlenebilir.
- Kesilme model cevabina metin eklenmeden state olarak tasinir.
- Sunucu suresi dolmadan run "paused" durumuna gecer; kullanici devam,
  cevap veya yeni yon secer. Devam, imzali handoff ile yeni istekte surer.
"""

import logging
from dataclasses import dataclass, field
from chat.evidence import EvidenceStore
from typing import Any

logger = logging.getLogger(__name__)

RUNTIME_VERSION = "p2-provider-neutral-v3"
TOOL_POLICIES = frozenset(("auto", "required", "none"))

AGENT_CONTRACT = (
    "AJAN CALISMA PROTOKOLU:\n"
    "- Ilk turda yalniz yetenek_ac sunulur; bir veya birkac yetenek "
    "alanini acar. Acilan alanlarin semalari gercek ve cagrilabilir arac "
    "katalogudur ve run boyunca acik kalir.\n"
    "- Yetenek alanlarinin adlari arac adi degildir (ornegin bir alan "
    "adini tool_call olarak cagiramazsin); alan adi yalniz yetenek_ac "
    "alanlar parametresine yazilir, arac olarak sunulan sey o alanin "
    "semalaridir.\n"
    "- Bu ortamdaki araclara sen sahipsin; araclari tarif etmek yerine "
    "cagirirsin.\n"
    "- Arac gerekmiyorsa dogrudan metinle cevap verilebilir.\n"
    "- Bir tool_call uygulama tarafindan calistirilir ve tool sonucu ayni "
    "run icinde sana geri verilir.\n"
    "- Her tool sonucundan sonra sonraki tool_call veya final kararini "
    "yeniden sen verirsin.\n"
    "- Basarisiz veya tamamlanmamis tool sonucu basarili eylem kaniti "
    "degildir."
)


def normalize_tool_policy(value):
    policy = str(value or "auto").strip().lower()
    if policy not in TOOL_POLICIES:
        raise ValueError("tool_policy auto, required veya none olmali")
    return policy


def capability_surface(tools, policy):
    """Run'in gercek arac katalogu: none disinda tamami, kelime filtresi YOK.

    Katalog modele tek seferde dokulmez; model yetenek_ac ile alan acar
    (chat.agent_protocol). Bu fonksiyon yalniz hangi katalogdan
    acilabilecegini belirler.
    """
    policy = normalize_tool_policy(policy)
    if policy == "none":
        return []
    return list(tools or [])


@dataclass
class AgentRunState:
    run_id: str
    tool_policy: str = "auto"
    status: str = "running"
    phase: str = "model"
    provider: str = ""
    truncated_reason: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    evidence_store: Any = field(default_factory=EvidenceStore)
    trace: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        self.tool_policy = normalize_tool_policy(self.tool_policy)
        self._record("run_started", tool_policy=self.tool_policy)

    def _record(self, event, **data):
        self.trace.append({"event": str(event), **data})

    def phase_set(self, phase):
        phase = str(phase or "")
        if phase and phase != self.phase:
            self.phase = phase
            self._record("phase", phase=phase)

    def provider_set(self, provider):
        provider = str(provider or "")
        if provider and provider != self.provider:
            onceki = self.provider
            self.provider = provider
            self._record("provider", onceki=onceki, yeni=provider)

    def tool_started(self, name, call_id, args=None):
        self.phase_set("tools")
        self._record(
            "tool_started", name=str(name or ""),
            call_id=str(call_id or ""), args=dict(args or {}),
        )

    def capability_opened(self, alanlar, call_id=""):
        self._record(
            "capability_opened", alanlar=list(alanlar or []),
            call_id=str(call_id or ""),
        )

    def tool_done(self, name, call_id, ok, args=None, result=None, turn=None):
        kayit = {
            "name": str(name or ""),
            "call_id": str(call_id or ""),
            "ok": bool(ok),
            "args": dict(args or {}),
            "result": "" if result is None else str(result),
            "turn": int(turn or 0),
        }
        self.tool_calls.append(kayit)
        self._record("tool_done", **kayit)
        # KANIT (ADR-2): BASARILI her araç cagrisi gercek bir sonuc uretir;
        # o sonuc bu turun kanitidir. Kayit, aracin KENDI adini ve cagri
        # kimligini soyler; sonuc metni SINIFLANDIRILMAZ, arac adi TAHMIN
        # EDILMEZ, anahtar kelime aranmaz (AGENTS.md §0). Basarisiz cagri
        # uretilmis bir sonuc olmadigi icin kanit saymaz.
        #
        # 2026-10-13 OLCUM: bu baglanti YOKTU. `record_evidence` tanimliydi
        # ama hicbir uretim yolundan cagrilmiyordu; depoya yalniz URL
        # giriyordu (chat/tools.py) ve `public_snapshot().evidence_count`
        # yalniz URL sayisini gosteriyordu. Yani "kanit" katmani kosunun
        # gercegini degil, bulunan link sayisini raporluyordu.
        if kayit["ok"] and getattr(self, "evidence_store", None) is not None:
            self.evidence_store.add(
                "tool",
                "%s#%s" % (kayit["name"], kayit["call_id"]),
                tool=kayit["name"],
                call_id=kayit["call_id"],
                snippet=kayit["result"],
            )

    def _kanit_sayisi(self):
        """Kanit sayisinin TEK kaynagi: depo varsa depo, yoksa URL listesi."""
        depo = getattr(self, "evidence_store", None)
        if depo is None:
            return len(self.evidence)
        return depo.count()

    def evidence_add(self, url, tool="", call_id=""):
        url = str(url or "")
        if not url or any(x.get("url") == url for x in self.evidence):
            return
        item = {
            "url": url, "tool": str(tool or ""),
            "call_id": str(call_id or ""),
        }
        self.evidence.append(item)
        if hasattr(self, "evidence_store") and self.evidence_store is not None:
            self.evidence_store.add("url", url, tool=tool, call_id=call_id)
        self._record("evidence", **item)

    def record_evidence(self, kind, reference, tool="", call_id="", verified=True, snippet=""):
        """ADR-2 Kanıt Katmanı: URL dışındaki araç kanıtlarını da (dosya, hesap, görev) kaydeder."""
        if hasattr(self, "evidence_store") and self.evidence_store is not None:
            self.evidence_store.add(kind, reference, tool=tool, call_id=call_id, verified=verified, snippet=snippet)
        if str(reference).startswith("http://") or str(reference).startswith("https://"):
            self.evidence_add(reference, tool=tool, call_id=call_id)

    def truncate(self, reason="limit"):
        self.truncated_reason = str(reason or "limit")
        self.status = "incomplete"
        self.phase = "incomplete"
        self._record("run_truncated", reason=self.truncated_reason)

    def pause(self, reason="sure"):
        """Is bitmeden kullaniciya karar birakilir; hicbir sonuc atilmaz.

        Duraklayan kosunun devami ISTEMCIYE IMZALI HANDOFF ILE tasinir
        (app.py -> _handoff_tokeni / _yonlendirme_baglami_dogrula): olay
        dokumu ve runContext sunucu imzasiyla geri doner, kullanici devam
        eder. Sunucu tarafinda KALICI checkpoint/resume YOKTUR ve yokmus
        gibi de yazilmaz (knowledge/kabul-plani-web-gate.md: "Gerçek
        checkpoint/resume henüz yoktur; varmış gibi raporlanmaz").

        2026-10-13 OLCUM: burada diske YAZAN bir blok vardi
        (chat/checkpoints.py). `load_checkpoint`/`delete_checkpoint`
        hicbir uretim yolundan cagrilmiyordu — yani yazilan dosya HICBIR
        kosulda geri yuklenmiyordu. Ustelik Vercel'de durum dizini /tmp'dir
        (app.py:36) ve Vercel resmi dokumana gore orasi instance basina
        gecici "scratch space"tir, kalici degil. Katman kaldirildi
        (AGENTS.md §0: gereksiz katman geri gelmez, saran katman yazilmaz).
        Duraklama sinyali (runState + "checkpoint" web olayi) AYNEN durur.
        """
        self.status = "paused"
        self.phase = "paused"
        self._record("run_paused", reason=str(reason or "sure"))

    def complete(self, provider=""):
        self.provider_set(provider)
        if self.truncated_reason:
            self.status = "incomplete"
            self.phase = "incomplete"
        else:
            self.status = "completed"
            self.phase = "completed"
        self._record("run_finished", status=self.status)

    def fail(self):
        self.status = "error"
        self.phase = "error"
        self._record("run_failed")

    def public_snapshot(self):
        return {
            "runtime_version": RUNTIME_VERSION,
            "run_id": self.run_id,
            "tool_policy": self.tool_policy,
            "status": self.status,
            "phase": self.phase,
            "provider": self.provider,
            "tool_count": len(self.tool_calls),
            # Tek kaynak: kanit deposu. `self.evidence` yalniz URL
            # listesidir; araç kanitlari da ayni depoda durur. Iki sayi
            # ayrisirsa ekran kosunun gercegini degil bir alt kumesini
            # gosterir (2026-10-13 olcumu: yalniz URL sayiliyordu).
            "evidence_count": self._kanit_sayisi(),
            "truncated_reason": self.truncated_reason,
            "resumable": self.status == "paused",
        }

def emit_run_state(js_callback, state):
    if state is None:
        return
    yay = getattr(js_callback, "olay", None)
    if callable(yay):
        yay("runState", **state.public_snapshot())
