# -*- coding: utf-8 -*-
"""chat/hatirlatma.py — zamanlanmış hatırlatma (web).

Neden var: masaüstünde arka plan süreci hatırlatır; web'de süreç yok.
Bu modül hatırlatmayı kişinin state klasöründe tutar, zamanı geleni
"gönderildi" diye işaretler ve uygulama içinde gösterir.

Depo YOK: `chat/oturum.py` ve `chat/gorev_kontrol.py` ile aynı sözleşme —
`<state>/<kullanici>/hatirlatmalar.json`, `.tmp` + `os.replace`, kilitli
oku-değiştir-yaz. Sunucu tarafında ayrı bir veritabanı katmanı kurulmaz.

Kurallar:
- Aynı hatırlatma iki kez gösterilmez: işaretleme tek kilit altında
  okuma-işaretleme-yazma olarak yapılır.
- SINIR (ölçülmüş): kilit tek süreci kapsar. Vercel'de state klasörü
  `/tmp` olduğundan (sohbetlerin bugünkü durumuyla aynı) iki örnek aynı
  anda tetiklenirse bildirim iki kez görülebilir; örnek yenilenirse
  hatırlatma kaybolur. Kalıcı çözüm sohbetlerle birlikte gelecek.
- E-posta/push yok: bildirim uygulama içinde.
- Bu modül karar vermez: zamanı çağıran verir.
"""

import json
import logging
import os
import threading
import time
import uuid

logger = logging.getLogger(__name__)

# Türkiye saati: web kullanıcısı "09:00" dediğinde yerel saat kastedilir.
VARSAYILAN_DILIM = "Europe/Istanbul"

DOSYA_ADI = "hatirlatmalar.json"

_BICIMLER = (
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%d.%m.%Y %H:%M",
    "%Y-%m-%d",
    "%d.%m.%Y",
)

_KILIT = threading.Lock()


def _dilim():
    ad = (os.environ.get("BASAK_SAAT_DILIMI") or VARSAYILAN_DILIM).strip()
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(ad)
    except Exception:  # noqa: BLE001 — tz verisi yoksa UTC'ye düşülür
        logger.warning("Saat dilimi bulunamadi (%s); UTC kullanilir", ad)
        return None


def zaman_coz(deger):
    """Epoch, ISO ya da 'YYYY-MM-DD HH:MM' biçimini epoch'a çevirir.

    Yerel saat kabul edilir (Türkiye varsayılan). Anlaşılmayan değer
    `ValueError` verir: çağıran kullanıcıya açar.
    """
    if isinstance(deger, (int, float)) and not isinstance(deger, bool):
        return float(deger)
    metin = str(deger or "").strip()
    if not metin:
        raise ValueError("Hatırlatma zamanı boş olamaz")
    try:
        return float(metin)  # epoch sayısı metin olarak geldiyse
    except ValueError as e:
        logger.debug("Epoch olarak okunamadi (%r); bicim denenecek: %s",
                     metin[:40], e)
    from datetime import datetime

    for bicim in _BICIMLER:
        try:
            yerel = datetime.strptime(metin, bicim)
        except ValueError:
            continue
        dilim = _dilim()
        if dilim is not None:
            yerel = yerel.replace(tzinfo=dilim)
        return yerel.timestamp()
    raise ValueError(
        "Zamanı anlayamadım. '2026-10-25 09:00' gibi yazabilirsin.")


# ── depo (dosya) ───────────────────────────────────────────────────────

def _yol(kid, kok=None):
    if kok is not None:
        return os.path.join(kok, kid, DOSYA_ADI)
    from chat.kimlik import kullanici_koku

    return os.path.join(kullanici_koku(kid), DOSYA_ADI)


def _oku(yol):
    try:
        with open(yol, "r", encoding="utf-8-sig") as f:
            ham = json.load(f)
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as e:
        logger.warning("Hatirlatma dosyasi okunamadi (%s): %s", yol, e)
        return []
    if isinstance(ham, dict):
        ham = ham.get("hatirlatmalar") or []
    return [k for k in ham if isinstance(k, dict)]


def _yaz(yol, kayitlar):
    from chat.oturum import _atomik_yaz

    os.makedirs(os.path.dirname(yol), exist_ok=True)
    _atomik_yaz(yol, json.dumps({"hatirlatmalar": kayitlar},
                                ensure_ascii=False, indent=2))


def _temiz(kayit):
    """Dışarı verilen alanlar: saklanan her şey, uydurma alan yok."""
    return {
        "id": kayit.get("id"),
        "metin": kayit.get("metin") or "",
        "zaman": float(kayit.get("zaman") or 0),
        "gonderildi": bool(kayit.get("gonderildi")),
        "goruldu": bool(kayit.get("goruldu")),
    }


# ── işlemler ───────────────────────────────────────────────────────────

def ekle(kid, metin, zaman):
    """Yeni hatırlatma ekler. metin boşsa hata; zaman çözülemezse hata."""
    from chat.kimlik import slugla

    kid = slugla(kid)
    metin = str(metin or "").strip()
    if not metin:
        raise ValueError("Hatırlatma metni boş olamaz")
    kayit = {
        "id": uuid.uuid4().hex[:12],
        "metin": metin[:500],
        "zaman": zaman_coz(zaman),
        "olusturma": time.time(),
        "gonderildi": False,
        "goruldu": False,
    }
    with _KILIT:
        yol = _yol(kid)
        kayitlar = _oku(yol)
        kayitlar.append(kayit)
        _yaz(yol, kayitlar)
    return _temiz(kayit)


def listele(kid, simdi=None):
    """Bekleyenler ve gösterilmeyi bekleyen (zamanı gelmiş) bildirimler."""
    from chat.kimlik import slugla

    kid = slugla(kid)
    simdi = float(simdi or time.time())
    hepsi = _oku(_yol(kid))
    bekleyen = [k for k in hepsi
                if float(k.get("zaman") or 0) > simdi
                and not k.get("gonderildi")]
    gelen = [k for k in hepsi
             if float(k.get("zaman") or 0) <= simdi
             and not k.get("goruldu")]
    bekleyen.sort(key=lambda k: float(k.get("zaman") or 0))
    gelen.sort(key=lambda k: float(k.get("zaman") or 0))
    return {"simdi": simdi,
            "bekleyen": [_temiz(k) for k in bekleyen],
            "gelen": [_temiz(k) for k in gelen]}


def _degistir(kid, hatirlatma_id, alanlar):
    from chat.kimlik import slugla

    kid = slugla(kid)
    with _KILIT:
        yol = _yol(kid)
        kayitlar = _oku(yol)
        bulundu = False
        for kayit in kayitlar:
            if kayit.get("id") == hatirlatma_id:
                kayit.update(alanlar)
                bulundu = True
                break
        if bulundu:
            _yaz(yol, kayitlar)
    return bulundu


def sil(kid, hatirlatma_id):
    from chat.kimlik import slugla

    kid = slugla(kid)
    with _KILIT:
        yol = _yol(kid)
        kayitlar = _oku(yol)
        kalan = [k for k in kayitlar if k.get("id") != hatirlatma_id]
        if len(kalan) == len(kayitlar):
            return False
        _yaz(yol, kalan)
    return True


def goruldu(kid, hatirlatma_id):
    return _degistir(kid, hatirlatma_id, {"goruldu": True})


def tetikle(simdi=None):
    """Zamanı gelenleri işaretler; kaç tanesinin işaretlendiğini söyler.

    Dönüş cron yanıtıdır: kullanıcı metni İÇERMEZ (log'a sızmaz), yalnız
    kimlik ve zaman. Aynı kayıt ikinci çağrıda `gonderildi` olduğu için
    tekrar dönmez.
    """
    simdi = float(simdi or time.time())
    from chat.kimlik import state_kok

    kok = state_kok()
    isaretlenen = []
    try:
        adaylar = sorted(os.listdir(kok))
    except OSError:
        return isaretlenen
    with _KILIT:
        for kid in adaylar:
            yol = _yol(kid, kok=kok)
            if not os.path.isfile(yol):
                continue
            kayitlar = _oku(yol)
            degisti = False
            for kayit in kayitlar:
                zaman = float(kayit.get("zaman") or 0)
                if zaman and zaman <= simdi and not kayit.get("gonderildi"):
                    kayit["gonderildi"] = True
                    isaretlenen.append({"kid": kid, "id": kayit.get("id"),
                                        "zaman": zaman})
                    degisti = True
            if degisti:
                try:
                    _yaz(yol, kayitlar)
                except OSError as e:
                    logger.warning("Hatirlatma isaretlenemedi (%s): %s", yol, e)
    if isaretlenen:
        logger.info("Hatirlatma tetiklendi: %d", len(isaretlenen))
    return isaretlenen
