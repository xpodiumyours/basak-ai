"""chat/evidence.py — Evidence & Truthfulness Katmanı (ADR-2).

Modelin araç çalıştırma sonuçları ile ürettiği son cevap arasındaki
kanıt bağını doğrular. Modelin 'aracı çalıştırdım' veya 'şunu ekledim'
gibi hayali iddialar üretmesini engellemek için araç sonuçlarını
kanıt deposu (EvidenceStore) olarak tutar.
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
