"""P2 ortak ajan runtime sozlesmesi.

Bu modul OpenAI/Anthropic/Gemini/LangGraph ortak desenlerinin Basak'taki
provider-neutral karsiligidir:

- Capability = arac katalogu. Yetkiyi gizli resolver daraltmaz.
- tool_policy acik run politikasidir: auto | required | none.
- Deferred/native tool-search bir OPTIMIZASYON katmanidir; kabiliyet kapisi
  degildir. Desteklenmeyen provider tam katalogu gorur.
- Calisma durumu tek AgentRunState icinde izlenir; UI olayi ile run state
  birbirine karistirilmaz.
"""

from dataclasses import dataclass, field
from typing import Any

TOOL_POLICIES = frozenset(("auto", "required", "none"))

AGENT_CONTRACT = (
    "AJAN CALISMA SOZLESMESI:\n"
    "- Sana sunulan araclar Basak'in GERCEK capability registry'sidir.\n"
    "- Dis dunya, guncel durum, dosya/proje durumu veya gercek bir eylem "
    "gerekiyorsa uygun GERCEK araci cagir; arac adini tarif etmek is "
    "yapilmis sayilmaz.\n"
    "- Arac sonucunu gordukten sonra ayni ajan dongusunde yeniden karar ver; "
    "gerekirse baska gercek arac cagir.\n"
    "- Basarili arac sonucu olmadan bir eylemi yapilmis gibi soyleme.\n"
    "- Arama sonucu adaydir; okunmus/olculmus kaynak kanittir.\n"
    "- Hafizadaki eski Basak cevaplari kanit degildir; guncel arac sonucu "
    "ile celisirse arac sonucu ustundur."
)


def normalize_tool_policy(value):
    """Acik run politikasini dogrula; kullanici metninden tahmin ETME."""
    policy = str(value or "auto").strip().lower()
    if policy not in TOOL_POLICIES:
        raise ValueError(
            "tool_policy auto, required veya none olmali"
        )
    return policy


def capability_surface(tools, policy):
    """Provider'a verilecek capability yuzeyi.

    P2 ortak tabani eager/full-catalog'dur. Native deferred tool-search daha
    sonra provider capability'si olarak eklenebilir ama bu fonksiyon hicbir
    araci semantik olarak gizlemez.
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
    provider: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        self.tool_policy = normalize_tool_policy(self.tool_policy)

    def provider_set(self, provider):
        if provider:
            self.provider = str(provider)

    def tool_done(self, name, call_id, ok, args=None):
        self.tool_calls.append({
            "name": str(name or ""),
            "call_id": str(call_id or ""),
            "ok": bool(ok),
            "args": dict(args or {}),
        })

    def evidence_add(self, url, tool="", call_id=""):
        url = str(url or "")
        if not url or any(x.get("url") == url for x in self.evidence):
            return
        self.evidence.append({
            "url": url,
            "tool": str(tool or ""),
            "call_id": str(call_id or ""),
        })

    def complete(self, provider=""):
        self.provider_set(provider)
        self.status = "completed"

    def fail(self):
        self.status = "error"

    def public_snapshot(self):
        return {
            "run_id": self.run_id,
            "tool_policy": self.tool_policy,
            "status": self.status,
            "provider": self.provider,
            "tool_count": len(self.tool_calls),
            "evidence_count": len(self.evidence),
        }
