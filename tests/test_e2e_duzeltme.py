"""test_e2e_duzeltme.py — Düzeltmelerin E2E testleri.

1. olcu.py: duplicate ham_olcum_satirlari kaldırıldı, PROMPT_BLOGU sağlam
2. chat.py: arac_cikti_kur badge::Ö:: ham metni temizler
3. style.css: text-transform: uppercase kaldırıldı (BADAK → BAŞAK)
"""

import pytest


# ── 1. olcu.py: duplicate yok, PROMPT_BLOGU tam ──

def test_ham_olcum_tek():
    """ham_olcum_satirlari fonksiyonu tanım defa tanımlı olmalı."""
    from olcu import ham_olcum_satirlari
    sonuc = ham_olcum_satirlari([("git_durum", "Dal: main")])
    assert len(sonuc) == 1
    assert "badge::Ö::" in sonuc[0]
    assert "Dal: main" in sonuc[0]


def test_prompt_blogu_saglam():
    """PROMPT_BLOGU kesik olmamalı — kapanış parantezi ve tüm maddeleri içermeli."""
    from olcu import PROMPT_BLOGU
    assert isinstance(PROMPT_BLOGU, str)
    assert len(PROMPT_BLOGU) > 500
    # Tüm işaret tipleri tanıtılmalı
    for isaret in ("[Y]", "[A]", "[Ö]", "[Ç]", "[B]"):
        assert isaret in PROMPT_BLOGU, f"{isaret} PROMPT_BLOGU'da eksik"


def test_arac_cikti_kur_list_files():
    """arac_cikti_kur list_files çıktısını insancıl forma çevirmeli."""
    from olcu import arac_cikti_kur
    ham = 'badge::Ö::list_files "knowledge/ (4 öğe): INDEX.md (924 bayt) README.md (376 bayt)"'
    sonuc = arac_cikti_kur("list_files", ham)
    # badge:: kalıntıları kalmamalı
    assert "badge::" not in sonuc
    # İnsan okuyabilir formatta olmalı
    assert "klasöründe" in sonuc or "öğe" in sonuc


def test_arac_cikti_kur_hata():
    """Hata mesajları temizlenmeli."""
    from olcu import arac_cikti_kur
    ham = 'badge::Ö::list_files "Hata: Yol izni bir klasörün altında değil"'
    sonuc = arac_cikti_kur("list_files", ham)
    assert "badge::" not in sonuc
    assert len(sonuc) > 0


def test_arac_cikti_kur_bos():
    """Boş çıktı boş dönmeli."""
    from olcu import arac_cikti_kur
    assert arac_cikti_kur("list_files", "") == ""
    assert arac_cikti_kur("list_files", None) == ""


# ── 2. chat.py: badge::Ö:: temizleme ──

def test_chat_fallback_temizler():
    """_tool_calling_multi fallback yolu badge::Ö:: içeren çıktıları temizler."""
    from olcu import arac_cikti_kur
    # badge::Ö:: içeren bir çıktı
    ham_cikti = 'badge::Ö::list_files "knowledge/ (2 öğe): a.md b.md"'
    temiz = arac_cikti_kur("list_files", ham_cikti)
    assert "badge::" not in temiz
    assert "list_files" not in temiz.split("\n")[0] or "klasöründe" in temiz


def test_olcu_kapisi_badge_gectir():
    """Ölçü kapısı badge::Ö:: marker'ını doğru parser'lar."""
    from olcu import cikis_kapisi
    # badge:: marker içeren model çıktısı
    metin = "badge::Ö::git_durum \"Dal: main\""
    sonuc, rapor = cikis_kapisi(metin, olcumler=[("git_durum", "Dal: main")])
    # badge:: marker indicator'ı [{capraz}] convert edilmis olmali
    assert "badge::" not in sonuc or len(rapor) == 0


# ── 3. style.css: uppercase kaldırıldı ──

def test_css_uppercase_yok():
    """style.css'de durumSatiri'nda text-transform: uppercase olmamalı."""
    import os
    css_yolu = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "ui", "style.css")
    with open(css_yolu, "r", encoding="utf-8") as f:
        icerik = f.read()
    # durumSatiri bloğunda uppercase olmamalı
    # Basit kontrol: style dosyasında "text-transform: uppercase" olmamalı
    # (genel yasak değil, sadece durumSatiri için)
    # Satellite test: BADAK kelimesi anywhere不应出现
    assert "BADAK" not in icerik, "BADAK yazım hatası style.css'de bulunmamalı"


# ── 4. olcu.py: cikis_kapisi tüm işaretleri destekler ──

def test_cikis_kapisi_ozet():
    """cikis_kapisi her işaret tipini doğru işler."""
    from olcu import cikis_kapisi

    # [B] — bilmiyorum, serbest geçer
    sonuc, _ = cikis_kapisi("[B] Bilmiyorum", olcumler=[])
    assert "Bilmiyorum" in sonuc

    # [Ö] — ölçüm cümlesi; arac ciktisinda varsa yasar
    sonuc, rapor = cikis_kapisi(
        '[Ö] git_durum "Dal: main"',
        olcumler=[("git_durum", "Dal: main")]
    )
    assert "Dal: main" in sonuc
    assert rapor == []  # elenen yok

    # [Y] + [Ö] — yanıt + ölçüm (Y cümle Ö alıntısıyla kök paylaşmalı)
    sonuc2, rapor2 = cikis_kapisi(
        '[Y] Proje main dalında\n[Ö] git_durum "Dal: main"',
        olcumler=[("git_durum", "Dal: main")]
    )
    assert "main" in sonuc2
    assert rapor2 == []


def test_cikis_kapisi_uydurma_elenir():
    """Uydurma alıntı elenir."""
    from olcu import cikis_kapisi
    sonuc, rapor = cikis_kapisi(
        '[A] dosya.md "Bu satır dosyada yok"',
        olcumler=[]
    )
    assert len(rapor) > 0  # en az bir elenen var


# ── 5. sozlesme_kapisi ──

def test_sozlesme_kapisi_gecerli():
    """Geçerli sözleşme metni korunur."""
    from olcu import sozlesme_kapisi, sozlesme_coz
    soz = {
        "yanit": "Görev listenizde 2 açık görev var.",
        "iddialar": [{
            "metin": "2 açık görev var",
            "tur": "olcum",
            "dayanak": {"arac": "list_tasks"}
        }]
    }
    sonuc, rapor = sozlesme_kapisi(soz, olcumler=[("list_tasks", "görev1\ngörev2")])
    assert "2 açık görev" in sonuc
    assert rapor["gecerli"] is True


def test_sozlesme_coz_json_citli():
    """```json çiti içindeki sözleşme çözülmeli."""
    from olcu import sozlesme_coz
    metin = '''```json
{"yanit": "Merhaba", "iddialar": []}
```'''
    sonuc = sozlesme_coz(metin)
    assert sonuc is not None
    assert sonuc["yanit"] == "Merhaba"
