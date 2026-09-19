"""chat/tools.py — Araç çağırma döngüsü (ozgur-ajan).

2026-09-13 Faz 1: modeli daraltan tavanlar silindi (AGENTS.md S0-2, S0-5).
- TUR_SINIRI yok: model tool_calls dondurdukce dongu surer.
- Son-tur tools=None kapatma yok: her turda tam sema verilir.
- ARAC_SONUC_TAVAN kirpmasi yok: tam sonuc modele gider.
- "Kaynaklar:" ek satiri yok: model kendi cevabini yazar.

Korunan (guvenlik): TANINMIS_TOOLLAR beyaz listesi — modelin
uydurdugu ad CALISMAZ. DURUM_METNI ekran etiketidir.
"""

import json
import logging

logger = logging.getLogger(__name__)

DURUM_METNI = {
    "web_search": "İnternette aranıyor",
    "haber_ara": "Haberlerde aranıyor",
    "zamanli_ara": "Tarihli aranıyor",
    "site_ara": "Sitede aranıyor",
    "gorsel_ara": "Görsel aranıyor",
    "kitap_ara": "Kitaplarda aranıyor",
    "derin_oku": "Derin okunuyor",
    "sayfa_oku": "Sayfa okunuyor",
    "read_file": "Dosya okunuyor",
    "list_files": "Klasör listeleniyor",
    "git_durum": "Proje durumu ölçülüyor",
    "belge_ara": "Belgelerde aranıyor",
    "dosya_bilgi": "Dosya bilgisi ölçülüyor",
    "image_analyze": "Görüntü inceleniyor",
    "write_file_tool": "Dosya yazılıyor",
    "get_reminders": "Hatırlatmalar ölçülüyor",
    "add_task": "Görev ekleniyor",
    "list_tasks": "Görevler listeleniyor",
    "complete_task": "Görev kapatılıyor",
    "ac_uygulama": "Uygulama açılıyor",
    "icerik_ara": "İçerikte aranıyor",
    "github_durum": "GitHub ölçülüyor",
    "git_gecmis": "Commit geçmişi ölçülüyor",
    "git_degisenler": "Değişenler ölçülüyor",
    "adres_kontrol": "Adres kontrol ediliyor",
    "testleri_kos": "Testler koşuyor",
    "matris_ac": "Tablo açılıyor",
    "matris_liste": "Tablolar listeleniyor",
    "satir_ekle": "Satır ekleniyor",
    "kanit_ekle": "Kanıt ekleniyor",
    "satir_kapat": "Satır kapatılıyor",
    "satir_ac": "Satır açılıyor",
    "satir_sil": "Satır arşivleniyor",
    "satir_tasi": "Satır taşınıyor",
    "matris_durum": "Tablo okunuyor",
    "gorsel_uret": "Görsel üretiliyor",
    "saglik_raporu": "Hat sağlığı ölçülüyor",
    "satir_duzenle": "Satır düzeltiliyor",
    "simdi": "Saat okunuyor",
    "hesapla": "Hesaplanıyor",
    "hafiza_ara": "Hafızada aranıyor",
    "fatura_oku": "Fatura okunuyor",
    "katalog_kur": "Ürün kartları kuruluyor",
    "katalog_getir": "Katalog okunuyor",
    "katalog_liste": "Kataloglar listeleniyor",
    "katalog_fiyat_guncelle": "Satış fiyatı yazılıyor",
    "katalog_onayla": "Vixrex dosyaları hazırlanıyor",
    "yetki_belgesi_ekle": "İzin belgesi saklanıyor",
    "urun_eslestir": "Ürün eşleştiriliyor",
    "yayin_paketi": "Yayın paketi denetleniyor",
    "cikti_oku": "Çıktı okunuyor",
    "sirket_ara": "Şirket bilgisi araştırılıyor",
}

# Durum satırında gösterilecek argüman — araca göre değişir.
DURUM_ALANI = ("query", "url", "path", "folder", "proje", "text",
               "task_id")


def _j(obj):
    return json.dumps(obj, ensure_ascii=False)


def parse_args(ham):
    """Model argümanı bozuk JSON gönderebilir — patlamadan çöz."""
    if isinstance(ham, dict):
        return ham
    try:
        cozulmus = json.loads(ham or "{}")
        return cozulmus if isinstance(cozulmus, dict) else {}
    except (ValueError, TypeError):
        return {}


def _durum(tool_name, args):
    etiket = DURUM_METNI.get(tool_name, "Çalışıyor")
    detay = ""
    for alan in DURUM_ALANI:
        if (args or {}).get(alan):
            detay = str(args[alan])[:70]
            break
    return "%s: %s" % (etiket, detay) if detay else etiket + "..."


def sonucu_donustur(sonuc):
    """Araç dönüşünü modele verilecek düz metne çevirir."""
    if isinstance(sonuc, dict):
        if sonuc.get("error"):
            return "Hata: %s" % sonuc["error"]
        return str(sonuc.get("result", ""))
    return str(sonuc)


def arac_dongusu(tool_calls, mesajlar, brain, model, js_callback,
                 calistir, tools=None, tur_siniri=None, yanit=None,
                 tool_choice=None, tum_tools=None):
    """Arac sonuclarini modele geri vererek ajan turunu surdurur.

    Gercek arac secimini MODEL yapar. `yetenek_ac` yalniz modelin sectigi
    alandaki semalari acan katalog kapisidir; kullanici metnine bakmaz.
    """
    from chat.gate import temizle
    from chat.agent_protocol import (
        SON_CEVAP_ADI, YETENEK_AC_ADI, YETENEK_ALANLARI, alan_araclari,
    )
    from tools.definitions import TANINMIS_TOOLLAR

    expanded = list(mesajlar)
    kosan = 0
    tur_sonuclari = []

    def _muhakeme_al(obj):
        out = {}
        if isinstance(obj, dict):
            for alan in ("reasoning_content", "reasoning",
                         "reasoning_details", "thinking",
                         "reasoning_text", "tool_plan"):
                if alan in obj:
                    out[alan] = obj[alan]
        return out

    def _beyin_devam(acik_tools):
        _kw = {"tools": acik_tools}
        if tool_choice is not None:
            import inspect
            _p = inspect.signature(brain.cevapla).parameters
            _kwargs_var = any(
                x.kind == inspect.Parameter.VAR_KEYWORD
                for x in _p.values())
            if "tool_choice" in _p or _kwargs_var:
                _kw["tool_choice"] = tool_choice
        return brain.cevapla(expanded, model, **_kw)

    ilk_muhakeme = _muhakeme_al(yanit)
    if not ilk_muhakeme and mesajlar:
        ilk_muhakeme = _muhakeme_al(mesajlar[-1])

    while tool_calls:
        tur_sonuclari = []

        _adlar = [
            ((c.get("function") or {}).get("name", ""))
            for c in tool_calls if isinstance(c, dict)
        ]

        # Nihai cevap yalniz basina geldiyse ajan turu bitmistir.
        if _adlar and all(ad == SON_CEVAP_ADI for ad in _adlar):
            for call in tool_calls:
                args = parse_args(
                    (call.get("function") or {}).get("arguments", "{}"))
                metin = args.get("metin")
                if isinstance(metin, str) and metin.strip():
                    return temizle(metin), kosan
            return "", kosan

        # Bu turda modele GERCEKTEN sunulmus araclar. Model eski bir arac
        # adini hafizadan uydurursa, alani acmadan calistirilmaz.
        sunulan_adlar = {
            (t.get("function") or {}).get("name")
            for t in (tools or []) if isinstance(t, dict)
        }

        for call in tool_calls:
            func = call.get("function", {})
            ad = func.get("name", "")
            args = parse_args(func.get("arguments", "{}"))
            cagri_id = call.get("id") or "call_%d" % len(tur_sonuclari)

            if ad == YETENEK_AC_ADI:
                alan = args.get("alan")
                if ad not in sunulan_adlar:
                    net = "Hata: yetenek_ac bu turda sunulmadi."
                elif alan not in YETENEK_ALANLARI:
                    net = "Hata: bilinmeyen yetenek alani."
                elif tum_tools is None:
                    net = "Hata: gercek arac katalogu bu akista yok."
                else:
                    tools = alan_araclari(tum_tools, alan)
                    gercek_adlar = [
                        (t.get("function") or {}).get("name")
                        for t in tools
                        if (t.get("function") or {}).get("name")
                        not in (YETENEK_AC_ADI, SON_CEVAP_ADI)
                    ]
                    net = json.dumps({
                        "acilan_alan": alan,
                        "kullanilabilir_araclar": gercek_adlar,
                    }, ensure_ascii=False)
                    js_callback("BasakUI.toolStatus(" + _j(
                        "Yetenek acildi: " + str(alan)) + ")")
                tur_sonuclari.append((ad, net, cagri_id))
                continue

            if ad == SON_CEVAP_ADI:
                tur_sonuclari.append((
                    ad,
                    "Hata: son_cevap gercek araclarla ayni turda "
                    "kullanilamaz; once arac sonuclarini degerlendir.",
                    cagri_id,
                ))
                continue

            if ad not in TANINMIS_TOOLLAR:
                tur_sonuclari.append((
                    ad, "Hata: bilinmeyen arac.", cagri_id))
                continue

            if ad not in sunulan_adlar:
                tur_sonuclari.append((
                    ad,
                    "Hata: bu arac su an acik degil; once yetenek_ac ile "
                    "ilgili alani ac.",
                    cagri_id,
                ))
                continue

            js_callback("BasakUI.toolStatus(" + _j(_durum(ad, args)) + ")")
            net = sonucu_donustur(calistir(ad, args))
            tur_sonuclari.append((ad, net, cagri_id))
            if not net.startswith("Hata:"):
                kosan += 1

        if not tur_sonuclari:
            break

        # Standart tool-call sirasini koru: assistant tool_calls -> her
        # cagri icin tool sonucu -> modelin bir sonraki karari.
        _asistan = {"role": "assistant", "content": "",
                    "tool_calls": tool_calls}
        _asistan.update(ilk_muhakeme)
        expanded = expanded + [_asistan]
        for ad, sonuc, cagri_id in tur_sonuclari:
            expanded.append({
                "role": "tool",
                "tool_call_id": cagri_id,
                "name": ad,
                "content": sonuc,
            })

        try:
            yanit, _kaynak = _beyin_devam(tools)
        except Exception as e:
            logger.warning("Arac turu sonrasi cevap alinamadi: %s", e)
            break

        yeni = yanit.get("tool_calls") if isinstance(yanit, dict) else None
        if yeni:
            tool_calls = yeni
            ilk_muhakeme = _muhakeme_al(yanit)
            continue

        if tool_choice == "required":
            logger.warning(
                "Zorunlu ajan turu tool call olmadan duz metin dondurdu")
            break

        cevap = temizle(yanit.get("content", ""))
        if cevap:
            return cevap, kosan
        break

    if tool_choice == "required":
        return "", kosan

    ham = "\n".join(net for _ad, net, _id in tur_sonuclari if net)
    return ham, kosan
