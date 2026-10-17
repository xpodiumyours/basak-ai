"""tests/test_profesyonel_mimari.py — Profesyonel mimari kabul testleri.

FAZ 1 (Events), FAZ 2 (Evidence) ve FAZ 3 (Checkpoints) doğrulama testleri.
"""

import pathlib

import pytest
from chat.events import (
    EventThinking, EventToolCall, EventToolResult, EventFinalChunk,
    EventComplete, parse_tool_call, response_to_events
)
from chat.evidence import EvidenceStore
from chat.agent_runtime import AgentRunState


def test_events_stream_and_parsing():
    raw_call = {
        "id": "call_123",
        "type": "function",
        "function": {
            "name": "web_search",
            "arguments": "{\"query\": \"ankara hava durumu\"}",
        }
    }
    tc = parse_tool_call(raw_call)
    assert isinstance(tc, EventToolCall)
    assert tc.name == "web_search"
    assert tc.args.get("query") == "ankara hava durumu"

    response = {
        "content": "Ankara güneşli.",
        "thinking": "Hava durumunu kontrol ettim.",
        "tool_calls": [raw_call],
        "_finish_reason": "stop"
    }
    events = response_to_events(response, provider="groq")
    types = [e.event_type for e in events]
    assert "thinking" in types
    assert "tool_call" in types
    assert "final_chunk" in types
    assert "complete" in types


def test_evidence_store_truthfulness():
    store = EvidenceStore()
    store.add("url", "https://ornek.com", tool="sayfa_oku", call_id="c1", snippet="bilgi")
    # Ayni URL tekrar eklenmemeli
    store.add("url", "https://ornek.com", tool="sayfa_oku", call_id="c1")
    assert store.count() == 1

    store.add("task", "task_42", tool="add_task", call_id="c2", snippet="gorev acildi")
    assert store.count() == 2

    snap = store.snapshot()
    assert len(snap) == 2
    assert snap[0]["kind"] == "url"
    assert snap[1]["kind"] == "task"


def test_durdurma_sinyali_verilir_diske_yazilmaz(tmp_path, monkeypatch):
    """Mola sinyali gercek; disk checkpoint'i DEGIL.

    2026-10-13 OLCUM: `pause()` diske yaziyordu ama hicbir uretim yolu
    `load_checkpoint` cagirmiyordu — dosya hicbir kosulda geri
    yuklenmiyordu. Ayrica Vercel'de durum dizini /tmp'dir (instance basina
    gecici). Duraklamanin devami imzali handoff ile tasinir. Bu test hem
    sinyalin durdugunu hem de diske YAZILMADIGINI kilitler.
    """
    from chat import kimlik
    monkeypatch.setattr(kimlik, "kullanici_koku", lambda: str(tmp_path))

    state = AgentRunState(run_id="run_prof_01")
    state.record_evidence("file", "docs/PLAN.md", tool="read_file", call_id="c1")
    state.evidence_add("https://site.com", tool="sayfa_oku", call_id="c2")

    assert state.evidence_store.count() == 2
    assert len(state.evidence) == 1

    state.pause(reason="sure")
    assert state.status == "paused"
    assert state.phase == "paused"
    assert state.public_snapshot()["resumable"] is True

    # Geri gelen checkpoint katmani olsaydi tam burada bir dosya olurdu.
    assert list(tmp_path.rglob("*")) == [], sorted(tmp_path.rglob("*"))


def test_okunmayan_checkpoint_katmani_geri_gelmedi():
    """Yazip hic okumayan katman silindi; sessizce geri gelmesin.

    Gerekce kodun kendisinde yazili (chat/agent_runtime.py -> pause) ve
    projenin kendi kuraliyla ayni: knowledge/kabul-plani-web-gate.md
    "Gerçek checkpoint/resume henüz yoktur; varmış gibi raporlanmaz."
    """
    import importlib
    assert not pathlib.Path("chat/checkpoints.py").exists()
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("chat.checkpoints")

def test_basarili_arac_cagrisi_kanit_uretir():
    """Kanit katmani kosunun GERCEK sonuclarini kaydetmeli, sadece URL degil.

    2026-10-13 olcumu: `record_evidence` hicbir uretim yolundan
    cagrilmiyordu; depoya yalniz URL giriyordu. Bu test bagi kilitler:
    arac sonucu tek huniden (tool_done) gecer, kanit orada dogar.
    """
    state = AgentRunState(run_id="r_kanit")
    assert state.evidence_store.count() == 0

    state.tool_done("sayfa_oku", "c1", True,
                    args={"url": "https://ornek.com"},
                    result='{"icerik": "gercek sonuc"}', turn=1)
    assert state.evidence_store.count() == 1
    kayit = state.evidence_store.get_items()[0]
    assert kayit.kind == "tool"
    assert kayit.tool == "sayfa_oku"
    assert kayit.call_id == "c1"
    assert "gercek sonuc" in kayit.snippet


def test_basarisiz_arac_cagrisi_kanit_saymaz():
    """Uretilmis sonuc yoksa kanit da yok."""
    state = AgentRunState(run_id="r_kanit2")
    state.tool_done("read_file", "c9", False, args={"path": "yok.md"},
                    result="Hata: dosya yok", turn=1)
    assert state.evidence_store.count() == 0


def test_kanit_sayisi_tek_kaynaktan_gelir():
    """runState.evidence_count ile depo sayisi ayrisamaz.

    Ayrisirsa arayuz kosunun gercegini degil bir alt kumesini gosterir.
    """
    state = AgentRunState(run_id="r_kanit3")
    state.tool_done("hesapla", "c1", True, result="3973", turn=1)
    state.evidence_add("https://a.example", tool="sayfa_oku", call_id="c2")
    assert state.public_snapshot()["evidence_count"] == \
        state.evidence_store.count() == 2


def test_evidence_modulu_cevabi_degistirdigini_iddia_etmez():
    """Modul belgesi koda uymali: bu katman DENETLEYICI degildir.

    Eski baslik "kanit bagini DOGRULAR" diyordu; kod hicbir seyi
    dogrulamiyordu ve dogrulayan katman bilincli olarak silinmisti
    (SILME-GOREVI.md -> olcu.py). Yanlis iddia geri gelmesin.
    """
    import chat.evidence as ev
    # Turkce "İ".lower() -> "i" + U+0307 (birlesik nokta); karsilastirma
    # icin normalize edilir, aksi halde test kendi kodlamasina takilir.
    belge = (ev.__doc__ or "").casefold().replace("\u0307", "")
    assert "denetleyici değildir" in belge, belge[:200]
    assert "dogrular" not in belge.split("2026-10-13")[0]
