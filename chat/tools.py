"""chat/tools.py — Araç çağırma döngüsü."""

import json
import logging

logger = logging.getLogger(__name__)
TUR_SINIRI = 4
ARAC_SONUC_TAVAN = 4000

DURUM_METNI = {
    "web_search": "İnternette aranıyor",
    "sayfa_oku": "Sayfa okunuyor",
    "read_file": "Dosya okunuyor",
    "list_files": "Klasör listeleniyor",
    "git_durum": "Proje durumu ölçülüyor",
    "belge_ara": "Belgelerde aranıyor",
    "dosya_bilgi": "Dosya bilgisi ölçülüyor",
    "write_file_tool": "Dosya yazılıyor",
    "get_reminders": "Hatırlatmalar kontrol ediliyor",
    "add_task": "Görev ekleniyor",
    "list_tasks": "Görevler listeleniyor",
    "complete_task": "Görev tamamlanıyor",
    "image_analyze": "Görüntü inceleniyor",
}

DURUM_ALANI = ("query", "url", "path", "folder", "proje", "text", "task_id")


def _j(obj):
    return json.dumps(obj, ensure_ascii=False)


def parse_args(ham):
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
    if isinstance(sonuc, dict):
        if sonuc.get("error"):
            return "Hata: %s" % sonuc["error"]
        return str(sonuc.get("result", ""))
    return str(sonuc)


def _kaynak_satiri(cevap, kaynaklar):
    if not kaynaklar or not cevap:
        return cevap
    return cevap + "\n\nKaynaklar: " + "; ".join(kaynaklar[:5])


def arac_dongusu(tool_calls, mesajlar, brain, model, js_callback,
                 calistir, tools=None, tur_siniri=TUR_SINIRI):
    from chat.gate import temizle
    from tools.definitions import TANINMIS_TOOLLAR

    expanded = list(mesajlar)
    kaynaklar = []
    kosan = 0
    tur_sonuclari = []
    for tur in range(tur_siniri):
        tur_sonuclari = []
        for call in tool_calls:
            func = call.get("function", {})
            ad = func.get("name", "")
            args = parse_args(func.get("arguments", "{}"))
            if ad not in TANINMIS_TOOLLAR:
                logger.info("Bilinmeyen arac atlandi: %s", ad)
                continue
            js_callback("BasakUI.toolStatus(" + _j(_durum(ad, args)) + ")")
            net = sonucu_donustur(calistir(ad, args))
            tur_sonuclari.append((ad, net))
            if not net.startswith("Hata:"):
                kosan += 1
                etiket = next((str(args[a]) for a in DURUM_ALANI if args.get(a)), ad)[:60]
                if etiket not in kaynaklar:
                    kaynaklar.append(etiket)
        if not tur_sonuclari:
            break
        expanded = expanded + [{"role": "assistant", "content": "", "tool_calls": tool_calls}]
        for i, (_ad, sonuc) in enumerate(tur_sonuclari):
            kirpilmis = sonuc if len(sonuc) <= ARAC_SONUC_TAVAN else sonuc[:ARAC_SONUC_TAVAN].rstrip() + "... [devami kirpildi]"
            expanded.append({"role": "tool", "tool_call_id": tool_calls[i].get("id", "call_%d" % i), "content": kirpilmis})
        ozet = "\n".join("%s: %s" % (ad, net[:800]) for ad, net in tur_sonuclari)
        sonraki = tools if tur < tur_siniri - 1 else None
        expanded = expanded + [{"role": "user", "content": "Araç sonuçları:\n" + ozet + "\n\nŞimdi bu sonuçları DOĞAL TÜRKÇE ile özetle. Bulduğun somut bilgiyi yaz; sonuçlarda olmayan şeyi UYDURMA."}]
        try:
            yanit, _kaynak = brain.cevapla(expanded, model, tools=sonraki)
        except Exception as e:
            logger.warning("Arac turu sonrasi cevap alinamadi: %s", e)
            break
        yeni = yanit.get("tool_calls")
        if yeni:
            tool_calls = yeni
            continue
        cevap = temizle(yanit.get("content", ""))
        if cevap:
            return _kaynak_satiri(cevap, kaynaklar), kosan
        break
    ham = "\n".join(net for _ad, net in tur_sonuclari if net)
    return ham, kosan
