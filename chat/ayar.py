# -*- coding: utf-8 -*-
"""chat/ayar.py — kişisel talimat ve hafıza yönetimi.

Neden var: kullanıcı kendi talimatını (hitap, dil, cevap uzunluğu, serbest
metin) ve hafızasını yönetebilsin.

Depo YOK: ayar, projenin kendi düzeninde yani kişinin state klasöründe
(`<state>/<kullanici>/ayarlar.json`) durur — `chat/oturum.py` ve
`chat/gorev_kontrol.py` ile aynı sözleşme: `.tmp` + `os.replace`, kilitli
oku-değiştir-yaz.

Kurallar (AGENTS.md §0):
- Kişisel talimat metni yalnız SİSTEM BAĞLAMINA girer. Kod ondan karar
  çıkarmaz: araç seçmez, niyet sınıflandırmaz, kelime aramaz.
- Bu modül karar vermez: ne yazılacağını çağıran söyler; sınırlar burada
  yalnız uzunluktur.
"""

import json
import logging
import os
import threading

logger = logging.getLogger(__name__)

KISISEL_SINIR = 2000
HITAP_SINIR = 80
DIL_SINIR = 40
UZUNLUK_SINIR = 40
HAFIZA_LISTE = 50

DOSYA_ADI = "ayarlar.json"

_KILIT = threading.Lock()

_ALANLAR = ("kisisel_talimat", "hitap", "dil", "uzunluk")


def _yol(kid):
    from chat.kimlik import kullanici_koku

    return os.path.join(kullanici_koku(kid), DOSYA_ADI)


def _oku(kid):
    """Ayarları okur. Dosya yoksa boş alanlar; bozuksa da boş alanlar.

    Bozuk JSON'u sessizce sıfırlamak yazma sırasında eski ayarı siler;
    bu yüzden okuma hatası loglanır ve boş döner (yazma yine tam dosya
    yazar). Ayar kaybı veri kaybı değildir: kullanıcı yeniden yazar.
    """
    yol = _yol(kid)
    try:
        with open(yol, "r", encoding="utf-8-sig") as f:
            ham = json.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:
        logger.warning("Ayar dosyasi okunamadi (%s): %s", yol, e)
        return {}
    return ham if isinstance(ham, dict) else {}


def _yaz(kid, ayar):
    from chat.oturum import _atomik_yaz

    yol = _yol(kid)
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    _atomik_yaz(yol, json.dumps(ayar, ensure_ascii=False, indent=2))


def ayarlari_al(kid):
    """Kişinin ayarları (boş alanlarla birlikte)."""
    ham = _oku(kid)
    return {alan: (str(ham.get(alan) or "") if ham.get(alan) else "")
            for alan in _ALANLAR}


def ayarlari_yaz(kid, kisisel_talimat=None, hitap=None, dil=None,
                 uzunluk=None):
    """Verilen alanları yazar; None olan alan DOKUNULMAZ.

    Boş dizge bilinçli silmedir (kullanıcı alanı temizledi).
    """
    from chat.kimlik import slugla

    kid = slugla(kid)
    yeni = {alan: (str(deger)[:sinir] if deger is not None else None)
            for alan, deger, sinir in (
                ("kisisel_talimat", kisisel_talimat, KISISEL_SINIR),
                ("hitap", hitap, HITAP_SINIR),
                ("dil", dil, DIL_SINIR),
                ("uzunluk", uzunluk, UZUNLUK_SINIR),
            )}
    with _KILIT:
        ayar = _oku(kid)
        for alan, deger in yeni.items():
            if deger is not None:
                if deger.strip():
                    ayar[alan] = deger
                else:
                    ayar.pop(alan, None)
        _yaz(kid, ayar)
    return ayarlari_al(kid)


def kisisel_blogu(kid):
    """Kullanıcının kendi talimatını sistem bağlamına çevirir.

    Metin OLDUĞU GİBİ taşınır; sınıflandırılmaz, araç seçmez. Boşsa boş
    dizge döner (bağlama gereksiz satır eklenmez).
    """
    ayar = ayarlari_al(kid)
    parcalar = []
    talimat = str(ayar.get("kisisel_talimat") or "").strip()
    if talimat:
        parcalar.append(talimat)
    hitap = str(ayar.get("hitap") or "").strip()
    if hitap:
        parcalar.append("Kullanıcıya \"%s\" diye hitap et." % hitap)
    dil = str(ayar.get("dil") or "").strip()
    if dil:
        parcalar.append("Yanıt dili: %s." % dil)
    uzunluk = str(ayar.get("uzunluk") or "").strip()
    if uzunluk:
        parcalar.append("Yanıt uzunluğu tercihi: %s." % uzunluk)
    return "\n".join(parcalar)


def sistem_blogu(kid, misafir=False):
    """Kişilik bloğu + kullanıcının kendi talimatı.

    Misafirde kişisel ayar OKUNMAZ (iz bırakmayan oturum).
    """
    from chat.prompts import kisilik_blogu

    temel = kisilik_blogu(kid, misafir=misafir)
    if misafir:
        return temel
    ek = kisisel_blogu(kid)
    return (temel + "\n" + ek) if ek else temel


# ── hafıza ─────────────────────────────────────────────────────────────

def _motor(kid):
    """Kişinin hafıza motoru.

    `context.hafiza_al` kişiyi contextvar'dan okur; HTTP uçları kendi
    thread'inde çalıştığı için kimlik burada geçici olarak kurulur ve
    çağrı bitince ESKİ değere döndürülür (başka isteğe sızmaz).
    """
    from chat.context import hafiza_al
    from chat.kimlik import aktif_kullanici, kullanici_kur

    onceki = aktif_kullanici()
    degisti = bool(kid) and kid != onceki
    if degisti:
        kullanici_kur(kid)
    try:
        return hafiza_al()
    finally:
        if degisti:
            kullanici_kur(onceki)


def son_anilar(kid, limit=HAFIZA_LISTE):
    """Son anılar. Motor yoksa boş liste (uydurma yok, açık durum)."""
    motor = _motor(kid)
    if not motor:
        return []
    return motor.son_anilar(limit=limit)


def ani_sil(kid, ani_id):
    motor = _motor(kid)
    if not motor:
        return False
    return motor.ani_sil(ani_id)


def hepsini_unut(kid):
    """Sohbetten öğrenilen tüm anıları unutur; silinen sayıyı döner.

    knowledge/defter/obsidyen indekslerine DOKUNULMAZ (dosyadan türetilir).
    """
    motor = _motor(kid)
    if not motor:
        return 0
    return motor.episodik_temizle()


def disa_aktar(kid, limit=200):
    """Hafızayı dışa aktarır: yalnız gerçek kayıtlar, uydurma alan yok."""
    return {"kullanici": kid, "anilar": son_anilar(kid, limit=limit)}
