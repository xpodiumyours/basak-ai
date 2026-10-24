# -*- coding: utf-8 -*-
"""chat/kullanim.py — kota ve kullanım görünürlüğü (F6).

Neden var: kullanıcı ne kadar ücretsiz hakkı kaldığını görsün. Ekranda
YALNIZ ölçülmüş sayılar durur: sağlayıcı limitleri `brain/registry.py`
kartlarından, harcama `brain/stats.py` kayıtlarından, anonim kota
`kota.py` sayacından okunur.

Kurallar:
- Uydurma yok: ölçüm alınamazsa alan `None` döner ve sebep yazılır;
  tahmini bir "kalan" sayısı hesaplanmaz.
- Bu modül karar vermez; yalnız okur.
"""

import logging
import time

logger = logging.getLogger(__name__)


def _istatistik():
    try:
        from brain.stats import model_stats_al

        return model_stats_al()
    except Exception as e:  # noqa: BLE001 — gösterge yüzünden akış düşmesin
        logger.warning("Kullanim istatistigi okunamadi: %s", e)
        return None


def saglayici_durumu():
    """Zincirdeki her sağlayıcı için ölçülmüş durum."""
    from brain.registry import SAGLAYICILAR, VARSAYILAN_SIRA

    stats = _istatistik()
    satirlar = []
    for ad in VARSAYILAN_SIRA:
        kart = SAGLAYICILAR.get(ad) or {}
        if not kart:
            continue
        satir = {
            "ad": ad,
            "gorunen": kart.get("ad") or ad,
            "ucretsiz": bool(kart.get("ucretsiz")),
            "gunluk_istek": kart.get("gunluk_istek"),
            "gunluk_token": kart.get("gunluk_token"),
            "bugun_token": None,
            "son24_istek": None,
            "son24_basari": None,
        }
        if stats is not None:
            try:
                giris, cikis = stats.token_bugun(ad)
                satir["bugun_token"] = int(giris) + int(cikis)
            except Exception as e:  # noqa: BLE001 — tek sağlayıcı hatası
                logger.debug("token_bugun okunamadi (%s): %s", ad, e)
            try:
                ozet = stats.ozet(model=ad, son_saat=24) or []
                kayit = next((k for k in ozet if k.get("model") == ad), None)
                if kayit:
                    satir["son24_istek"] = int(kayit.get("toplam") or 0)
                    satir["son24_basari"] = kayit.get("basari_orani")
            except Exception as e:  # noqa: BLE001 — tek sağlayıcı hatası
                logger.debug("ozet okunamadi (%s): %s", ad, e)
        satirlar.append(satir)
    return satirlar


def kota_ozeti(kid):
    """Kullanıcıya gösterilecek tam durum. Hata durumunda da döner."""
    import kota as kota_modulu

    try:
        tavan = kota_modulu.tavan()
        kalan = kota_modulu.kalan_bildir(kid)
    except Exception as e:  # noqa: BLE001 — gösterge akışı düşürmesin
        logger.warning("Anonim kota okunamadi: %s", e)
        tavan, kalan = None, None

    satirlar = saglayici_durumu()
    toplam_token = sum(s["bugun_token"] or 0 for s in satirlar)
    return {
        "gun": time.strftime("%Y-%m-%d", time.gmtime()),
        "anonim_kota": {"tavan": tavan, "kalan": kalan},
        "bugun_token": toplam_token,
        "saglayicilar": satirlar,
    }
