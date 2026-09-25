"""P2 provider-neutral ajan runtime sozlesmesi.

- Capability = gercek arac katalogu; model yetenek_ac ile alan acar,
  gizli resolver/kelime filtresi yoktur.
- tool_policy = acik run politikasi: auto | required | none.
- Run state, UI olayindan ayridir ve disaridan denetlenebilir.
- Kesilme model cevabina metin eklenmeden state olarak tasinir.
- Gercek checkpoint/resume henuz uygulanmadi; state bunu acikca bildirir.
"""

from dataclasses import dataclass, field
from typing import Any

RUNTIME_VERSION = "p2-provider-neutral-v3"
TOOL_POLICIES = frozenset(("auto", "required", "none"))

AGENT_CONTRACT = (
    "AJAN CALISMA PROTOKOLU:\n"
    "- Ilk turda yalniz yetenek_ac sunulur; bir veya birkac yetenek "
    "alanini acar. Acilan alanlarin semalari gercek ve cagrilabilir arac "
    "katalogudur ve run boyunca acik kalir.\n"
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

    def evidence_add(self, url, tool="", call_id=""):
        url = str(url or "")
        if not url or any(x.get("url") == url for x in self.evidence):
            return
        item = {
            "url": url, "tool": str(tool or ""),
            "call_id": str(call_id or ""),
        }
        self.evidence.append(item)
        self._record("evidence", **item)

    def truncate(self, reason="limit"):
        self.truncated_reason = str(reason or "limit")
        self.status = "incomplete"
        self.phase = "incomplete"
        self._record("run_truncated", reason=self.truncated_reason)

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
            "evidence_count": len(self.evidence),
            "truncated_reason": self.truncated_reason,
            "resumable": False,
        }

    def trace_snapshot(self):
        return {
            **self.public_snapshot(),
            "tool_calls": list(self.tool_calls),
            "evidence": list(self.evidence),
            "trace": list(self.trace),
        }


def emit_run_state(js_callback, state):
    if state is None:
        return
    yay = getattr(js_callback, "olay", None)
    if callable(yay):
        yay("runState", **state.public_snapshot())
