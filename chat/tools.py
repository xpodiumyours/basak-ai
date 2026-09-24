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
import re
from urllib.parse import urlsplit, urlunsplit

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
    "hava_durumu": "Hava durumu okunuyor",
}

# Durum satırında gösterilecek argüman — araca göre değişir.
DURUM_ALANI = ("query", "url", "path", "folder", "proje", "text",
               "task_id", "sehir")


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


_KAYNAK_ARACLARI = {"derin_oku", "sayfa_oku"}
_URL_RE = re.compile(r"https?://[^\\s<>'\\\"]+", re.IGNORECASE)


def _durum_detayi(args):
    for alan in DURUM_ALANI:
        if (args or {}).get(alan):
            return str(args[alan])[:120]
    return ""


def _web_olay(js_callback, tur, **veri):
    """Web taşıyıcısı varsa zengin olay gönder; diğer istemcileri etkileme."""
    yay = getattr(js_callback, "olay", None)
    if callable(yay):
        yay(tur, **veri)


def _kaynak_url_temizle(url):
    """Kullanıcıya gösterilecek kaynakta secret/query/fragment taşıma."""
    try:
        ham = str(url or "").strip().rstrip(".,);]}")
        p = urlsplit(ham)
        if p.scheme not in ("http", "https") or not p.hostname:
            return ""
        # user:pass@host gibi kimlik parçalarını da taşıma.
        port = (":" + str(p.port)) if p.port and p.port not in (80, 443) else ""
        netloc = (p.hostname or "") + port
        return urlunsplit((p.scheme, netloc, p.path or "/", "", ""))
    except Exception:
        return ""


def _kaynaklari_cikar(tool_name, args, net):
    if tool_name not in _KAYNAK_ARACLARI:
        return []
    adaylar = []
    if isinstance(args, dict) and args.get("url"):
        adaylar.append(str(args["url"]))
    adaylar.extend(_URL_RE.findall(str(net or "")))

    sonuc = []
    for aday in adaylar:
        temiz = _kaynak_url_temizle(aday)
        if temiz and temiz not in sonuc:
            sonuc.append(temiz)
        if len(sonuc) >= 12:
            break
    return sonuc


def sonucu_donustur(sonuc):
    """Araç dönüşünü modele verilecek düz metne çevirir.

    Cursor kullanan araçlarda Python iç kullanıcıları için result düz metin
    kalır; model ise meta + metni birlikte görür.
    """
    if isinstance(sonuc, dict):
        if sonuc.get("error"):
            return "Hata: %s" % sonuc["error"]
        if isinstance(sonuc.get("meta"), dict):
            return json.dumps({
                "meta": sonuc["meta"],
                "metin": str(sonuc.get("result", "")),
            }, ensure_ascii=False)
        return str(sonuc.get("result", ""))
    return str(sonuc)


def arac_dongusu(tool_calls, mesajlar, brain, model, js_callback,
                 calistir, tools=None, tur_siniri=None, yanit=None,
                 tool_choice=None, tum_tools=None, tercih=None,
                 dinamik_resolver=False):
    """Arac sonuclarini modele geri vererek ajan turunu surdurur.

    P2 aktif yolunda model yalnız resolver'ın sunduğu GERCEK araçları görür.
    Her araç turundan sonra dinamik_resolver=True ise güncel bağlamla yeni
    gerçek araç adayları hazırlanır. Eski yetenek_ac dalları yalnız P1
    uyumluluk testleri için pasif kalır; P2 akışında modele sunulmaz.
    """
    from chat.gate import temizle
    from chat.agent_protocol import (
        SON_CEVAP_ADI, YETENEK_AC_ADI, YETENEK_ALANLARI, alan_araclari,
    )
    from tools.definitions import TANINMIS_TOOLLAR

    expanded = list(mesajlar)
    kosan = 0
    tur_sonuclari = []
    _tekrar = {}

    def _muhakeme_al(obj):
        out = {}
        if isinstance(obj, dict):
            for alan in ("reasoning_content", "reasoning",
                         "reasoning_details", "thinking",
                         "reasoning_text", "tool_plan"):
                if alan in obj:
                    out[alan] = obj[alan]
        return out

    # Bir arac zinciri basladiktan sonra ayni saglayici/model ilk tercih
    # olarak korunur. Teknik ariza/kota olursa Brain'in mevcut fallback
    # zinciri yine devreye girer; basarili fallback sonraki turda yeni
    # tercih olur. Bu, cok turlu muhakeme ve provider-ozel durumun gereksiz
    # yere model degistirmesini engeller.
    _tercih_aktif = list(tercih or [])
    _son_secim = tool_choice
    _resolver_dogrulandi = True

    def _beyin_devam(acik_tools, secim=None):
        nonlocal _tercih_aktif
        import inspect

        _kw = {"tools": acik_tools}
        _p = inspect.signature(brain.cevapla).parameters
        _kwargs_var = any(
            x.kind == inspect.Parameter.VAR_KEYWORD
            for x in _p.values())

        _secim = tool_choice if secim is None else secim
        if _secim is not None and (
                "tool_choice" in _p or _kwargs_var):
            _kw["tool_choice"] = _secim
        if _tercih_aktif and ("tercih" in _p or _kwargs_var):
            _kw["tercih"] = list(_tercih_aktif)

        onceki = (_tercih_aktif or [""])[0] if _tercih_aktif else ""
        sonuc = brain.cevapla(expanded, model, **_kw)
        if (isinstance(sonuc, tuple) and len(sonuc) == 2
                and sonuc[1]):
            yeni = str(sonuc[1])
            if onceki and yeni and yeni != onceki:
                _web_olay(
                    js_callback, "providerSwitch",
                    onceki=onceki, yeni=yeni,
                )
            _tercih_aktif = [yeni]
        return sonuc

    ilk_muhakeme = _muhakeme_al(yanit)
    if not ilk_muhakeme and mesajlar:
        ilk_muhakeme = _muhakeme_al(mesajlar[-1])

    while tool_calls:
        tur_sonuclari = []

        # Plan frontend tahmini değildir: bu turda modelin GERÇEKTEN
        # seçtiği gerçek araç çağrılarından çıkar.
        _plan = []
        for _pc in tool_calls:
            if not isinstance(_pc, dict):
                continue
            _pf = _pc.get("function") or {}
            _pa = _pf.get("name", "")
            if _pa in (YETENEK_AC_ADI, SON_CEVAP_ADI):
                continue
            if _pa not in TANINMIS_TOOLLAR:
                continue
            _parg = parse_args(_pf.get("arguments", "{}"))
            _plan.append({
                "id": _pc.get("id") or ("plan_%d" % len(_plan)),
                "baslik": DURUM_METNI.get(_pa, "Çalışıyor"),
                "detay": _durum_detayi(_parg),
            })
        if _plan:
            _web_olay(js_callback, "plan", adimlar=_plan)

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
                if dinamik_resolver:
                    _mesaj = (
                        "Hata: bu arac bu adimda sunulan gercek araclar "
                        "arasinda degil."
                    )
                else:
                    _mesaj = (
                        "Hata: bu arac su an acik degil; once yetenek_ac ile "
                        "ilgili alani ac."
                    )
                tur_sonuclari.append((ad, _mesaj, cagri_id))
                continue

            js_callback("BasakUI.toolStatus(" + _j(_durum(ad, args)) + ")")
            try:
                _arg_anahtar = json.dumps(
                    args or {}, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":"),
                )
            except Exception:
                _arg_anahtar = str(args or {})
            _tekrar_anahtar = ad + "|" + _arg_anahtar
            _once = _tekrar.get(_tekrar_anahtar)
            if _once and int(_once.get("adet") or 0) >= 2:
                net = (
                    "Hata: ayni arac, ayni arguman ve ayni sonuc tekrar "
                    "dongusune girdi; ayni cagri tekrar calistirilmadi."
                )
                basarili = False
                _web_olay(
                    js_callback, "loopGuard", tool=ad,
                    tekrar=int(_once.get("adet") or 0) + 1,
                )
            else:
                net = sonucu_donustur(calistir(ad, args))
                basarili = not net.startswith("Hata:")
                if _once and _once.get("sonuc") == net:
                    _tekrar[_tekrar_anahtar] = {
                        "sonuc": net,
                        "adet": int(_once.get("adet") or 0) + 1,
                    }
                else:
                    _tekrar[_tekrar_anahtar] = {"sonuc": net, "adet": 1}
            _web_olay(
                js_callback, "toolDone",
                id=cagri_id,
                baslik=DURUM_METNI.get(ad, "Çalışıyor"),
                detay=_durum_detayi(args),
                ok=basarili,
            )
            if basarili:
                for _url in _kaynaklari_cikar(ad, args, net):
                    try:
                        _host = urlsplit(_url).hostname or _url
                    except Exception:
                        _host = _url
                    _web_olay(
                        js_callback, "source",
                        url=_url, baslik=_host, tool_id=cagri_id,
                    )
            tur_sonuclari.append((ad, net, cagri_id))
            if basarili:
                kosan += 1

        if not tur_sonuclari:
            break

        # Standart tool-call sirasini koru: assistant tool_calls -> her
        # cagri icin tool sonucu -> modelin bir sonraki karari.
        _asistan = {"role": "assistant", "content": "",
                    "tool_calls": tool_calls}
        if _tercih_aktif:
            _asistan["_provider"] = str(_tercih_aktif[0] or "")
        _asistan.update(ilk_muhakeme)
        expanded = expanded + [_asistan]
        for ad, sonuc, cagri_id in tur_sonuclari:
            expanded.append({
                "role": "tool",
                "tool_call_id": cagri_id,
                "name": ad,
                "content": sonuc,
            })

        _devam_secimi = tool_choice
        _karar = None
        _resolver_dogrulandi = True
        if dinamik_resolver and tum_tools is not None:
            try:
                from chat.tool_resolver import arac_karari_coz
                _karar = arac_karari_coz(
                    brain, model, expanded, tum_tools,
                    tercih=list(_tercih_aktif or []),
                )
                tools = list(_karar.get("tools") or [])
                _resolver_dogrulandi = bool(_karar.get("verified"))
                _devam_secimi = (
                    "required" if _karar.get("tool_required") else "auto"
                )
            except Exception as e:
                _resolver_dogrulandi = False
                logger.warning("Runtime tool resolver yenilenemedi: %s", e)

        _son_secim = _devam_secimi

        if (dinamik_resolver and _karar is not None
                and _resolver_dogrulandi
                and not _karar.get("tool_required")):
            try:
                if tools:
                    from chat.output_control import akan_ajan_adimi
                    _syanit, _skaynak, _sok = akan_ajan_adimi(
                        brain, model, expanded, js_callback, tools,
                        tercih=list(_tercih_aktif or []),
                    )
                    if _sok and _syanit is not None:
                        _onceki = (
                            (_tercih_aktif or [""])[0]
                            if _tercih_aktif else ""
                        )
                        if _skaynak:
                            if _onceki and _skaynak != _onceki:
                                _web_olay(
                                    js_callback, "providerSwitch",
                                    onceki=_onceki, yeni=_skaynak,
                                )
                            _tercih_aktif = [_skaynak]
                        _yeni = _syanit.get("tool_calls")
                        if _yeni:
                            tool_calls = _yeni
                            ilk_muhakeme = _muhakeme_al(_syanit)
                            continue
                        _cevap = temizle(_syanit.get("content", ""))
                        if _cevap:
                            return _cevap, kosan
                else:
                    from chat.output_control import akan_final
                    _akan, _kaynak, _tamam = akan_final(
                        brain, model, expanded, js_callback,
                        tercih=list(_tercih_aktif or []),
                    )
                    if _akan:
                        return temizle(_akan), kosan
            except Exception as e:
                logger.warning("Arac sonrasi final stream acilamadi: %s", e)

        try:
            yanit, _kaynak = _beyin_devam(
                tools, secim=_devam_secimi
            )
        except Exception as e:
            logger.warning("Arac turu sonrasi cevap alinamadi: %s", e)
            break

        yeni = yanit.get("tool_calls") if isinstance(yanit, dict) else None
        if yeni:
            tool_calls = yeni
            ilk_muhakeme = _muhakeme_al(yanit)
            continue

        if _devam_secimi == "required" or not _resolver_dogrulandi:
            logger.warning(
                "Ajan turu dogrulanmis final yerine duz metin dondurdu")
            break

        cevap = temizle(yanit.get("content", ""))
        if cevap:
            try:
                from chat.output_control import (
                    kesik_cevabi_tamamla, kesik_mi,
                )
                if kesik_mi(yanit):
                    cevap, _kaynak, _tamam = kesik_cevabi_tamamla(
                        brain, model, expanded, yanit,
                        js_callback=js_callback,
                        tercih=list(_tercih_aktif or []),
                    )
            except Exception as e:
                logger.warning("Kesik final kontrolu atlandi: %s", e)
            return cevap, kosan
        break

    if _son_secim == "required" or not _resolver_dogrulandi:
        return "", kosan

    ham = "\n".join(net for _ad, net, _id in tur_sonuclari if net)
    return ham, kosan
