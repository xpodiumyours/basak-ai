"""chat/evidence.py — Kanıt Kaydı (ADR-2).

Bu modül bir DENETLEYİCİ değildir. Modelin cevabını okumaz, değiştirmez,
silmez ve cevabi engellemez (AGENTS.md §0: modelin çıktısına dokunan kod
yasaktır). Yaptığı tek şey: bir çalıştırma sırasında GERÇEKTEN üretilen
sonuçları kaydetmek.

Neden kayıt yeterli sayılıyor: modele kanıt dayatmak yerine gerçek araç
sonucu zaten konuşmaya geri verilir (chat/tools.py -> role="tool");
nihai cevabı "doğru" diye işaretlemek ya da cümle elemek modele güveni
keser ve ölçülmüş biçimde yasaklanmıştır (bkz. AGENTS.md §0
"GERİ GETİRİLMESİ KESİNLİKLE YASAK", silinen `olcu.py` çıkış kapısı).

Burada tutulanlar:
  * kind="url"  — aracın döndürdüğü gerçek kaynak adresleri
                  (chat/tools.py kaynak çıkarımı)
  * kind="tool" — BAŞARILI her araç çağrısının gerçek sonucu
                  (chat/agent_runtime.py -> tool_done)
  * kind="file"/"task"/"calculation"/"general" — çagiran kod ne bildirirse
                  (agent_runtime.record_evidence)

Sayı tek kaynaktan okunur: `AgentRunState._kanit_sayisi()` ve bu sayı
`runState.evidence_count` olarak arayüze düşer.

2026-10-13 düzeltmesi: bu dosyanın eski başlığı "araç çalıştırma
sonuçları ile üretilen son cevap arasındaki kanıt bağını DOĞRULAR" diyordu.
Kod hiçbir şeyi doğrulamıyordu; doğrulayan bir katman da yoktu
(`olcu.py` 2026-09-25'te bilinçli silindi, bkz. SILME-GOREVI.md). Yanlış
iddia metinden kaldırıldı.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class EvidenceItem:
    kind: str  # 'url', 'file', 'task', 'calculation', 'general'
    reference: str  # URL, dosya yolu, task ID vb.
    tool: str
    call_id: str
    verified: bool = True
    snippet: str = ""


class EvidenceStore:
    """Bir çalıştırma (run) sırasındaki tüm gerçek kanıtları tutar."""

    def __init__(self):
        self._items: list[EvidenceItem] = []

    def add(self, kind: str, reference: str, tool: str, call_id: str,
            verified: bool = True, snippet: str = "") -> None:
        reference = str(reference or "").strip()
        if not reference:
            return
        # Tekrar kontrolü
        for it in self._items:
            if it.kind == kind and it.reference == reference:
                return
        self._items.append(EvidenceItem(
            kind=kind,
            reference=reference,
            tool=str(tool or ""),
            call_id=str(call_id or ""),
            verified=bool(verified),
            snippet=str(snippet or "")[:200],
        ))

    def get_items(self) -> list[EvidenceItem]:
        return list(self._items)

    def count(self) -> int:
        return len(self._items)

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {
                "kind": it.kind,
                "reference": it.reference,
                "tool": it.tool,
                "call_id": it.call_id,
                "verified": it.verified,
                "snippet": it.snippet,
            }
            for it in self._items
        ]
