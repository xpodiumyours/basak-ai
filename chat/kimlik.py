"""chat/kimlik.py — Kişi kimliği, kök yol ve tek seferlik taşıma.

Tasarım (2026-09-23): her şeyin kişiye göre çözüldüğü TEK nokta.
- yerel (CLI/basak_app/telegram): her zaman `casper`
- web: giriş yapan kullanıcı (contextvar, istek/thread başına set)
- kök: BASAK_STATE_DIR yoksa data/

Taşıma: eski tek kişilik veriler data/casper/ altına tek sefer taşınır;
bayrak yazıldıktan sonra eski yollar okunmaz (kod artık oraya bakmaz).
"""

import contextvars
import os
import re
import shutil
import threading
from pathlib import Path

VARSAYILAN_KULLANICI = "casper"

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_ctx_kullanici = contextvars.ContextVar(
    "basak_kullanici", default=VARSAYILAN_KULLANICI)

_MIGRASYON_KILIT = threading.Lock()
_MIGRASYON_YAPILDI = False

_TURKCE = str.maketrans({
    "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "İ": "i",
    "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u",
})


def slugla(ad):
    """Adı kısa slug'a indirger; Türkçe karakterler sadeleştirilir."""
    metin = str(ad or "").strip().translate(_TURKCE).lower()
    metin = re.sub(r"[^a-z0-9]+", "-", metin).strip("-")
    return metin[:32] or VARSAYILAN_KULLANICI


def aktif_kullanici():
    """Bu istek/thread'in kişi kimliği (varsayılan: casper)."""
    return _ctx_kullanici.get() or VARSAYILAN_KULLANICI


def kullanici_kur(kid):
    """Aktif kişiyi ayarlar (web girişinde, yerelde sabit casper)."""
    _ctx_kullanici.set(slugla(kid) if kid else VARSAYILAN_KULLANICI)


def state_kok():
    """Kişilerin üst dizini: BASAK_STATE_DIR yoksa data/."""
    kok = os.environ.get("BASAK_STATE_DIR")
    if kok:
        return kok
    return os.path.join(BASE, "data")


def kullanici_koku(kid=None):
    """Kişinin veri kökü: <state>/<kullanici_id>."""
    kid = kid or aktif_kullanici()
    _migrasyonu_calistir()
    return os.path.join(state_kok(), kid)


def gorunur_ad(kid=None):
    """Prompt'ta görünecek kullanıcı adı (yerelde Casper)."""
    kid = kid or aktif_kullanici()
    return "Casper" if kid == VARSAYILAN_KULLANICI else kid


# ── Taşıma (tek seferlik) ────────────────────────────────────────────

def migrasyon_bayrak_yolu():
    return os.path.join(state_kok(), "migration_kisi_v1.done")


def migrasyon_gerekli_mi():
    return not os.path.exists(migrasyon_bayrak_yolu())


def _tasi(kaynak, hedef):
    """Tek öğeyi taşır; hedef varsa kaynak silinmez, iş yapılır sayılır."""
    if not os.path.exists(kaynak):
        return
    if os.path.exists(hedef):
        return
    os.makedirs(os.path.dirname(hedef), exist_ok=True)
    shutil.move(kaynak, hedef)


def migrasyon_yap():
    """Eski tek kişilik verileri data/casper/ altına taşır.

    Yok etme: yalnız taşıma. Bayrak yazıldıktan sonra ikinci çağrı
    hiçbir iş yapmaz. Dönüş: taşınan öğe sayısı.
    """
    global _MIGRASYON_YAPILDI
    with _MIGRASYON_KILIT:
        bayrak = migrasyon_bayrak_yolu()
        if os.path.exists(bayrak):
            _MIGRASYON_YAPILDI = True
            return 0
        kok = state_kok()
        hedef_kok = os.path.join(kok, VARSAYILAN_KULLANICI)
        say = 0

        # sohbetler/ ve aktif_oturum -> data/casper/
        for ad in ("sohbetler", "aktif_oturum"):
            kaynak = os.path.join(kok, ad)
            hedef = os.path.join(hedef_kok, ad)
            if os.path.exists(kaynak) and not os.path.exists(hedef):
                _tasi(kaynak, hedef)
                say += 1

        # memory/basak.db (+ yan dosyalar) -> data/casper/memory/
        for ad in ("basak.db", "basak.db-wal", "basak.db-shm"):
            kaynak = os.path.join(kok, "memory", ad)
            hedef = os.path.join(hedef_kok, "memory", ad)
            if os.path.exists(kaynak) and not os.path.exists(hedef):
                _tasi(kaynak, hedef)
                say += 1

        # gecmis.json: Vercel'de state altında, yerelde proje kökünde.
        for kaynak in (os.path.join(kok, "gecmis.json"),
                       os.path.join(BASE, "gecmis.json")):
            hedef = os.path.join(hedef_kok, "gecmis.json")
            if os.path.exists(kaynak) and not os.path.exists(hedef):
                _tasi(kaynak, hedef)
                say += 1

        os.makedirs(kok, exist_ok=True)
        try:
            with open(bayrak, "w", encoding="utf-8") as f:
                f.write("tamam\n")
        except OSError:
            pass
        _MIGRASYON_YAPILDI = True
        return say


def _migrasyonu_calistir():
    """İlk yol hesabında taşımayı tetikler (tembel, tek seferlik)."""
    global _MIGRASYON_YAPILDI
    if _MIGRASYON_YAPILDI:
        return
    migrasyon_yap()
