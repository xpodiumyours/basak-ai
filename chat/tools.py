"""chat/tools.py — Modelin istediği araç çağrılarını çalıştırır.

Mimari kural: araç seçimine kod karar vermez. Modelin çağırdığı tanınmış
araç çalıştırılır, gerçek araç sonucu role=tool olarak modele geri verilir.
Sabit tur sayısı, araç-sonucu özet promptu ve son turda araç kapatma yoktur.
"""

import json
import logging

logger = logging.getLogger(__name__)

DURUM_METNI = {
    "web_search": "İnternette aranıyor",
    "sayfa_oku": "Sayfa okunuyor",
    "adres_kontrol": "Adres kontrol ediliyor",
    "read_file": "Dosya okunuyor",
    "list_files": "Klasör listeleniyor",
    "write_file_tool": "Dosya kaydediliyor",
    "get_reminders": "Hatırlatmalar okunuyor",
    "add_task": "Görev ekleniyor",
    "list_tasks": "Görevler listeleniyor",
    "complete_task": "Görev tamamlanıyor",
    "ac_uygulama": "Uygulama açılıyor",
    "git_durum": "Proje durumu ölçülüyor",
    "git_gecmis": "Git geçmişi okunuyor",
    "git_degisenler": "Git değişiklikleri ölçülüyor",
    "belge_ara": "Belgelerde aranıyor",
    "icerik_ara": "İçerikte aranıyor",
    "dosya_bilgi": "Dosya bilgisi ölçülüyor",
    "github_durum": "GitHub durumu okunuyor",
    "testleri_kos": "Testler çalıştırılıyor",
    "image_analyze": "Görüntü inceleniyor",
}

DURUM_ALANI = ("query", "url", "path", "folder", "proje", "sorgu",
               "islem", "uygulama", "text", "task_id")


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


def _kaynak_satiri(cevap, kaynaklar):
    if not kaynaklar or not cevap:
        return cevap
    return cevap + "\n\nKaynaklar: " + "; ".join(kaynaklar[:5])


def _cagri_imzasi(tool_calls):
    """Aynı tool-call paketinin sonsuz tekrarını teknik olarak yakalar.

    Bu kontrol araç seçmez ve kullanıcı metnini yorumlamaz; yalnız aynı
    model çıktısının birebir tekrar ederek sonsuz döngüye girmesini önler.
    """
    parcalar = []
    for call in tool_calls or []:
        func = call.get("function", {}) or {}
        parcalar.append((func.get("name", ""), func.get("arguments", "{}")))
    return repr(parcalar)


def arac_dongusu(tool_calls, mesajlar, brain, model, js_callback,
                 calistir, tools=None):
    """Model araç istediği sürece sonuçları geri vererek akışı sürdürür.

    Dönüş: (cevap_metni, calisan_arac_sayisi)
    """
    from chat.gate import temizle
    from tools.definitions import TANINMIS_TOOLLAR

    expanded = list(mesajlar)
    kaynaklar = []
    kosan = 0
    son_sonuclar = []
    gorulen_cagri_paketleri = set()

    while tool_calls:
        imza = _cagri_imzasi(tool_calls)
        if imza in gorulen_cagri_paketleri:
            logger.warning("Ayni arac cagrisi tekrarlandi; sonsuz dongu durduruldu")
            break
        gorulen_cagri_paketleri.add(imza)

        expanded.append({
            "role": "assistant",
            "content": "",
            "tool_calls": tool_calls,
        })

        son_sonuclar = []
        for i, call in enumerate(tool_calls):
            func = call.get("function", {}) or {}
            ad = func.get("name", "")
            args = parse_args(func.get("arguments", "{}"))
            call_id = call.get("id", "call_%d" % i)

            if ad not in TANINMIS_TOOLLAR:
                net = "Hata: '%s' diye bir arac yok." % ad
                logger.info("Bilinmeyen arac reddedildi: %s", ad)
            else:
                js_callback("BasakUI.toolStatus(" + _j(_durum(ad, args)) + ")")
                net = sonucu_donustur(calistir(ad, args))
                if not net.startswith("Hata:"):
                    kosan += 1
                    etiket = next((str(args[a]) for a in DURUM_ALANI
                                   if args.get(a)), ad)[:60]
                    if etiket not in kaynaklar:
                        kaynaklar.append(etiket)

            son_sonuclar.append((ad, net))
            expanded.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": net,
            })

        try:
            yanit, _kaynak = brain.cevapla(expanded, model, tools=tools)
        except Exception as e:
            logger.warning("Arac turu sonrasi cevap alinamadi: %s", e)
            break

        yeni = yanit.get("tool_calls") if isinstance(yanit, dict) else None
        if yeni:
            tool_calls = yeni
            continue

        cevap = temizle(
            yanit.get("content", "") if isinstance(yanit, dict) else yanit)
        if cevap:
            return _kaynak_satiri(cevap, kaynaklar), kosan
        break

    ham = "\n".join(net for _ad, net in son_sonuclar if net)
    return ham, kosan
