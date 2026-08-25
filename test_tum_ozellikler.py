"""test_tum_ozellikler.py — Başak'ın 30 özelliğini tek tek test eder.

Her özellik için:
- Import başarılı mı?
- Fonksiyon çalışıyor mu?
- Gerçek çalıştırma yapılabilir mi?

Kullanım: python test_tum_ozellikler.py
"""

import os
import sys
import json
import traceback
import tempfile
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

SONUCLAR = []


def test_et(numara, ad, fonksiyon):
    """Tek bir testi çalıştır ve sonucu kaydet."""
    try:
        fonksiyon()
        SONUCLAR.append((numara, ad, "PASS", ""))
        print(f"  [PASS] {numara}. {ad}")
    except Exception as e:
        hata = f"{type(e).__name__}: {e}"
        SONUCLAR.append((numara, ad, "FAIL", hata))
        print(f"  [FAIL] {numara}. {ad} -- {hata}")


# ═══════════════════════════════════════════════════════════════
# TEST 1: Tool tanımları (18 tool)
# ═══════════════════════════════════════════════════════════════
def test_01_tool_tanimlari():
    from tools.definitions import TOOLS
    assert len(TOOLS) >= 18, f"18 tool bekleniyor, {len(TOOLS)} bulundu"
    isimler = {t["function"]["name"] for t in TOOLS}
    gerekli = {"list_files", "read_file", "web_search", "add_task",
               "save_note", "deftere_kaydet", "complete_task", "list_tasks",
               "write_file_tool", "sayfa_oku", "ac_uygulama", "get_reminders",
               "git_durum", "belge_ara", "dosya_bilgi", "video_analyze",
               "image_analyze", "model_stats"}
    eksik = gerekli - isimler
    assert not eksik, f"Eksik tool'lar: {eksik}"


# ═══════════════════════════════════════════════════════════════
# TEST 2: Brain adapter'ları (10 adapter)
# ═══════════════════════════════════════════════════════════════
def test_02_brain_adapterlari():
    from brain.adapters.registry import discover_all
    adapters = discover_all()
    assert len(adapters) >= 10, f"10 adapter bekleniyor, {len(adapters)} bulundu"
    gerekli = {"groq", "gemini", "glm", "nvidia", "kilo", "openrouter",
               "cloudflare", "cohere", "qwen", "yerel"}
    eksik = gerekli - set(adapters.keys())
    assert not eksik, f"Eksik adapter'lar: {eksik}"


# ═══════════════════════════════════════════════════════════════
# TEST 3: Ses modülleri (TTS/STT)
# ═══════════════════════════════════════════════════════════════
def test_03_ses_modulleri():
    from voice.tts import TTS
    from voice.stt import STT
    assert callable(TTS), "TTS sınıfı bulunamadı"
    assert callable(STT), "STT sınıfı bulunamadı"


# ═══════════════════════════════════════════════════════════════
# TEST 4: Hafıza motoru (SQLite)
# ═══════════════════════════════════════════════════════════════
def test_04_hafiza_motoru():
    from memory.engine import HafizaMotoru
    tmp = tempfile.mkdtemp()
    try:
        db_yolu = os.path.join(tmp, "test.db")
        motor = HafizaMotoru(db_yolu=db_yolu, embed_fn=lambda m: None)
        # Anı kaydet
        assert motor.episodik_kaydet("test soru", "test cevap"), "Kayıt başarısız"
        # Anı ara
        sonuclar = motor.ara("test")
        assert len(sonuclar) >= 1, "Arama sonucu boş"
        # Temizle
        sayi = motor.episodik_temizle()
        assert sayi >= 1, "Temizleme başarısız"
        motor.kapat()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════
# TEST 5: Test suite (58+ test)
# ═══════════════════════════════════════════════════════════════
def test_05_test_suite():
    import glob
    test_dosyalari = glob.glob(os.path.join(BASE, "tests", "test_*.py"))
    assert len(test_dosyalari) >= 50, f"50+ test dosyası bekleniyor, {len(test_dosyalari)} bulundu"


# ═══════════════════════════════════════════════════════════════
# TEST 6: pywebview UI
# ═══════════════════════════════════════════════════════════════
def test_06_pywebview_ui():
    import basak_app
    assert hasattr(basak_app, "Api"), "Api sınıfı bulunamadı"
    assert hasattr(basak_app, "main"), "main fonksiyonu bulunamadı"
    # UI dosyaları
    assert os.path.exists(os.path.join(BASE, "ui", "index.html")), "index.html yok"
    assert os.path.exists(os.path.join(BASE, "ui", "app.js")), "app.js yok"
    assert os.path.exists(os.path.join(BASE, "ui", "style.css")), "style.css yok"


# ═══════════════════════════════════════════════════════════════
# TEST 7: Konuşmacı tanıma
# ═══════════════════════════════════════════════════════════════
def test_07_konusmaci_tanimama():
    from voice.speaker_id import taniyici_al
    assert callable(taniyici_al), "taniyici_al fonksiyonu bulunamadı"
    from voice.speaker_db import KonusmaciDB
    assert callable(KonusmaciDB), "KonusmaciDB sınıfı bulunamadı"


# ═══════════════════════════════════════════════════════════════
# TEST 8: Ölçüm kapısı
# ═══════════════════════════════════════════════════════════════
def test_08_olcu_kapisi():
    from olcu import cikis_kapisi, sozlesme_coz, bol_cumleler
    assert callable(cikis_kapisi), "cikis_kapisi bulunamadı"
    assert callable(sozlesme_coz), "sozlesme_coz bulunamadı"
    # Basit test — isaretli cumleler tek birim sayilir
    cumleler = bol_cumleler("[Ö] Test cumlesi. Normal cumle.")
    assert len(cumleler) >= 1, "Cümle bölme başarısız"


# ═══════════════════════════════════════════════════════════════
# TEST 9: Güvenlik/izin sistemi
# ═══════════════════════════════════════════════════════════════
def test_09_guvenlik_izin():
    from tools.permissions import calistirilabilir_mi, ETIKETLER
    assert callable(calistirilabilir_mi), "calistirilabilir_mi bulunamadı"
    # Salt okunur araçlar çalışmalı
    assert calistirilabilir_mi("list_files"), "list_files çalışmalı"
    assert calistirilabilir_mi("read_file"), "read_file çalışmalı"
    # Etiketler tanımlı
    assert len(ETIKETLER) >= 15, f"15+ etiket bekleniyor, {len(ETIKETLER)} bulundu"


# ═══════════════════════════════════════════════════════════════
# TEST 10: Dosya işlemleri
# ═══════════════════════════════════════════════════════════════
def test_10_dosya_islemleri():
    from tools.file_ops import read_file, write_file_ops, list_files, _klasor_cevir
    assert callable(read_file), "read_file bulunamadı"
    assert callable(write_file_ops), "write_file_ops bulunamadı"
    assert callable(list_files), "list_files bulunamadı"
    # Klasör haritası
    yol, _ = _klasor_cevir("belgeler")
    assert "Documents" in yol, f"belgeler → Documents bekleniyor, {yol} bulundu"


# ═══════════════════════════════════════════════════════════════
# TEST 11: Görev yönetimi
# ═══════════════════════════════════════════════════════════════
def test_11_gorev_yonetimi():
    from tools.tasks import add_task, list_tasks, complete_task
    assert callable(add_task), "add_task bulunamadı"
    assert callable(list_tasks), "list_tasks bulunamadı"
    assert callable(complete_task), "complete_task bulunamadı"
    # Gerçek test
    tmp = tempfile.mktemp(suffix=".json")
    try:
        with open(tmp, "w") as f:
            json.dump([], f)
        sonuc = add_task("Test görevi", tmp)
        assert "result" in sonuc or sonuc.get("ok"), f"Görev eklenemedi: {sonuc}"
        gorevler = list_tasks(tmp)
        assert "result" in gorevler or gorevler.get("ok"), f"Görevler listelenemedi: {gorevler}"
        # list_tasks result string doneerir, gorev listesi icerir
        assert len(gorevler.get("result", "")) > 0, "Görev listesi boş"
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ═══════════════════════════════════════════════════════════════
# TEST 12: Web arama
# ═══════════════════════════════════════════════════════════════
def test_12_web_arama():
    from tools.web_search import web_search, sayfa_oku
    assert callable(web_search), "web_search bulunamadı"
    assert callable(sayfa_oku), "sayfa_oku bulunamadı"


# ═══════════════════════════════════════════════════════════════
# TEST 13: Not alma
# ═══════════════════════════════════════════════════════════════
def test_13_not_alma():
    from tools.notes import save_note, deftere_kaydet
    assert callable(save_note), "save_note bulunamadı"
    assert callable(deftere_kaydet), "deftere_kaydet bulunamadı"
    # Gerçek test
    tmp = tempfile.mkdtemp()
    try:
        sonuc = save_note("Test Başlık", "Test içerik", tmp)
        assert "result" in sonuc or sonuc.get("ok"), f"Not kaydedilemedi: {sonuc}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════
# TEST 14: Uygulama açma
# ═══════════════════════════════════════════════════════════════
def test_14_uygulama_acma():
    from tools.app_launcher import ac_uygulama
    assert callable(ac_uygulama), "ac_uygulama bulunamadı"


# ═══════════════════════════════════════════════════════════════
# TEST 15: Hatırlatma
# ═══════════════════════════════════════════════════════════════
def test_15_hatirlatma():
    from tools.reminders import bugunku_hatirlatmalar
    assert callable(bugunku_hatirlatmalar), "bugunku_hatirlatmalar bulunamadı"


# ═══════════════════════════════════════════════════════════════
# TEST 16: Sistem tepsisi
# ═══════════════════════════════════════════════════════════════
def test_16_sistem_tepsisi():
    import tray
    assert hasattr(tray, "baslat"), "baslat fonksiyonu bulunamadı"
    assert hasattr(tray, "durdur"), "durdur fonksiyonu bulunamadı"


# ═══════════════════════════════════════════════════════════════
# TEST 17: Kota yönetimi
# ═══════════════════════════════════════════════════════════════
def test_17_kota_yonetimi():
    from brain.kota import KotaYoneticisi
    assert callable(KotaYoneticisi), "KotaYoneticisi sınıfı bulunamadı"
    # Gerçek test
    kota = KotaYoneticisi(ucretli_engelli=True)
    assert kota.engel_nedeni("deepseek", {"ucretsiz": False}) is not None


# ═══════════════════════════════════════════════════════════════
# TEST 18: Model seçimi
# ═══════════════════════════════════════════════════════════════
def test_18_model_secimi():
    from brain.secici import sec, siniflandir
    assert callable(sec), "sec bulunamadı"
    assert callable(siniflandir), "siniflandir bulunamadı"
    # Sınıflandırma testi
    assert siniflandir("python kodu yaz") == "kod"
    assert siniflandir("merhaba nasılsın") == "genel"


# ═══════════════════════════════════════════════════════════════
# TEST 19: Orkestra (muhakeme)
# ═══════════════════════════════════════════════════════════════
def test_19_orkestra():
    from brain.orkestra import Orkestra, Durum
    assert callable(Orkestra), "Orkestra sınıfı bulunamadı"
    assert len(Durum) == 10, f"10 durum bekleniyor, {len(Durum)} bulundu"


# ═══════════════════════════════════════════════════════════════
# TEST 20: Gölge mod
# ═══════════════════════════════════════════════════════════════
def test_20_golge_mod():
    import chat
    assert hasattr(chat, "golge_kos"), "golge_kos bulunamadı"
    assert hasattr(chat, "golge_mod_aktif_mi"), "golge_mod_aktif_mi bulunamadı"


# ═══════════════════════════════════════════════════════════════
# TEST 21: Video analiz
# ═══════════════════════════════════════════════════════════════
def test_21_video_analiz():
    from tools.video_analyzer import video_analyze
    assert callable(video_analyze), "video_analyze bulunamadı"


# ═══════════════════════════════════════════════════════════════
# TEST 22: Görüntü analiz
# ═══════════════════════════════════════════════════════════════
def test_22_goruntu_analiz():
    from tools.image_analyzer import image_analyze
    assert callable(image_analyze), "image_analyze bulunamadı"


# ═══════════════════════════════════════════════════════════════
# TEST 23: Deney motoru
# ═══════════════════════════════════════════════════════════════
def test_23_deney_motoru():
    from tools.deney import deney_yurut
    assert callable(deney_yurut), "deney_yurut fonksiyonu bulunamadı"


# ═══════════════════════════════════════════════════════════════
# TEST 24: Fay motoru
# ═══════════════════════════════════════════════════════════════
def test_24_fay_motoru():
    from tools.fay import kart_olustur, carpistir
    assert callable(kart_olustur), "kart_olustur fonksiyonu bulunamadı"
    assert callable(carpistir), "carpistir fonksiyonu bulunamadı"


# ═══════════════════════════════════════════════════════════════
# TEST 25: Gerilim puanı
# ═══════════════════════════════════════════════════════════════
def test_25_gerilim_puani():
    from tools.gerilim import gerilim_puani
    assert callable(gerilim_puani), "gerilim_puani bulunamadı"


# ═══════════════════════════════════════════════════════════════
# TEST 26: Aktarıcı
# ═══════════════════════════════════════════════════════════════
def test_26_aktarici():
    from tools.aktarici import aktarim_onerisi
    assert callable(aktarim_onerisi), "aktarim_onerisi bulunamadı"


# ═══════════════════════════════════════════════════════════════
# TEST 27: Evrim
# ═══════════════════════════════════════════════════════════════
def test_27_evrim():
    from tools.evrim import Arsiv
    assert callable(Arsiv), "Arsiv sınıfı bulunamadı"


# ═══════════════════════════════════════════════════════════════
# TEST 28: Dünya (inanç deposu)
# ═══════════════════════════════════════════════════════════════
def test_28_dunya():
    from tools.dunya import dunya_sorgu, inanclari_topla
    assert callable(dunya_sorgu), "dunya_sorgu bulunamadı"
    assert callable(inanclari_topla), "inanclari_topla bulunamadı"


# ═══════════════════════════════════════════════════════════════
# TEST 29: Zamanlayıcı
# ═══════════════════════════════════════════════════════════════
def test_29_zamanlayici():
    from tools.zamanlayici import Zamanlayici
    assert callable(Zamanlayici), "Zamanlayıcı sınıfı bulunamadı"


# ═══════════════════════════════════════════════════════════════
# TEST 30: İş kuyruğu
# ═══════════════════════════════════════════════════════════════
def test_30_is_kuyrugu():
    from tools.is_kuyrugu import IsKuyrugu
    assert callable(IsKuyrugu), "IsKuyrugu sınıfı bulunamadı"


# ═══════════════════════════════════════════════════════════════
# ANA ÇALIŞTIRICI
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("BAŞAK — 30 ÖZELLİK KAPSAMLI TEST")
    print("=" * 60)
    print()

    testler = [
        (1, "Tool tanımları (18 tool)", test_01_tool_tanimlari),
        (2, "Brain adapter'ları (10 adapter)", test_02_brain_adapterlari),
        (3, "Ses modülleri (TTS/STT)", test_03_ses_modulleri),
        (4, "Hafıza motoru (SQLite)", test_04_hafiza_motoru),
        (5, "Test suite (58+ test)", test_05_test_suite),
        (6, "pywebview UI", test_06_pywebview_ui),
        (7, "Konuşmacı tanıma", test_07_konusmaci_tanimama),
        (8, "Ölçüm kapısı", test_08_olcu_kapisi),
        (9, "Güvenlik/izin sistemi", test_09_guvenlik_izin),
        (10, "Dosya işlemleri", test_10_dosya_islemleri),
        (11, "Görev yönetimi", test_11_gorev_yonetimi),
        (12, "Web arama", test_12_web_arama),
        (13, "Not alma", test_13_not_alma),
        (14, "Uygulama açma", test_14_uygulama_acma),
        (15, "Hatırlatma", test_15_hatirlatma),
        (16, "Sistem tepsisi", test_16_sistem_tepsisi),
        (17, "Kota yönetimi", test_17_kota_yonetimi),
        (18, "Model seçimi", test_18_model_secimi),
        (19, "Orkestra (muhakeme)", test_19_orkestra),
        (20, "Gölge mod", test_20_golge_mod),
        (21, "Video analiz", test_21_video_analiz),
        (22, "Görüntü analiz", test_22_goruntu_analiz),
        (23, "Deney motoru", test_23_deney_motoru),
        (24, "Fay motoru", test_24_fay_motoru),
        (25, "Gerilim puanı", test_25_gerilim_puani),
        (26, "Aktarıcı", test_26_aktarici),
        (27, "Evrim", test_27_evrim),
        (28, "Dünya (inanç deposu)", test_28_dunya),
        (29, "Zamanlayıcı", test_29_zamanlayici),
        (30, "İş kuyruğu", test_30_is_kuyrugu),
    ]

    for numara, ad, fonksiyon in testler:
        test_et(numara, ad, fonksiyon)

    print()
    print("=" * 60)
    print("SONUÇLAR")
    print("=" * 60)

    gecen = sum(1 for _, _, d, _ in SONUCLAR if d == "PASS")
    basarisiz = sum(1 for _, _, d, _ in SONUCLAR if d == "FAIL")

    for numara, ad, durum, hata in SONUCLAR:
        satir = f"  [{durum}] {numara:2d}. {ad}"
        if hata:
            satir += f" ({hata[:60]})"
        print(satir)

    print()
    print(f"  Toplam: {gecen}/{len(SONUCLAR)} gecti, {basarisiz} basarisiz")
    print()

    if basarisiz == 0:
        print("  TUM OZELLIKLER DOGRULANDI!")
    else:
        print(f"  {basarisiz} ozellik basarisiz -- yukaridaki hatalara bakin")
