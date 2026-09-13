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
                 calistir, tools=None, tur_siniri=None):
    """Araç sonuçlarını modele geri vererek cevap ürettirir.

    Ozgu-ajan: tur_siniri parametresi uyumluluk icin durur, kullanilmaz.
    Dongu model cevap yazana kadar surer; tam sonuc tasinir.
    Dönüş: (cevap_metni, calisan_arac_sayisi)
    """
    from chat.gate import temizle
    from tools.definitions import TANINMIS_TOOLLAR

    expanded = list(mesajlar)
    kosan = 0
    tur_sonuclari = []

    while tool_calls:
        tur_sonuclari = []
        for call in tool_calls:
            func = call.get("function", {})
            ad = func.get("name", "")
            args = parse_args(func.get("arguments", "{}"))

            # Model olmayan bir arac uydurursa sessizce atlanir.
            if ad not in TANINMIS_TOOLLAR:
                logger.info("Bilinmeyen arac atlandi: %s", ad)
                continue

            js_callback("BasakUI.toolStatus(" + _j(_durum(ad, args)) + ")")
            net = sonucu_donustur(calistir(ad, args))
            # Çağrı kimliği sonuçla BİRLİKTE taşınır. Eskiden sonuçlar
            # sırayla eşleştiriliyordu (tool_calls[i]); model tanımadığı
            # bir araç isteyip o atlanınca dizi kayıyor ve sonuç YANLIŞ
            # çağrıya bağlanıyordu.
            tur_sonuclari.append(
                (ad, net, call.get("id") or "call_%d" % len(tur_sonuclari)))
            if not net.startswith("Hata:"):
                kosan += 1

        if not tur_sonuclari:
            break

        # Standart sıra (Groq/OpenAI belgeleri): kullanıcı → tool_calls
        # taşıyan assistant → her çağrı için bir `tool` mesajı. Model
        # sonucu görüp KENDİ karar verir: ya cevabı yazar ya yeni araç
        # ister. Araya "şimdi şunu özetle" gibi sahte kullanıcı mesajı
        # KONULMAZ — belgeler ek talimat gerekmediğini söylüyor ve o
        # mesaj sonucu ikinci kez göndererek bağlamı da şişiriyordu.
        expanded = expanded + [
            {"role": "assistant", "content": "", "tool_calls": tool_calls}]
        for ad, sonuc, cagri_id in tur_sonuclari:
            expanded.append({
                "role": "tool",
                "tool_call_id": cagri_id,
                "name": ad,          # Groq belgesi: name zorunlu
                "content": sonuc,
            })

        try:
            yanit, _kaynak = brain.cevapla(expanded, model, tools=tools)
        except Exception as e:
            logger.warning("Arac turu sonrasi cevap alinamadi: %s", e)
            break

        yeni = yanit.get("tool_calls")
        if yeni:
            tool_calls = yeni
            continue

        cevap = temizle(yanit.get("content", ""))
        if cevap:
            return cevap, kosan
        break

    # Model özet üretmediyse ham sonuç kullanıcıya gitsin — boş ekran olmasın.
    ham = "\n".join(net for _ad, net, _id in tur_sonuclari if net)
    return ham, kosan
