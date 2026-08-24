"""tools/gerilim.py — FAY-2: Gerilim puanı + dırdırmayan kuyruk.

Formül (FAY-MOTORU.md Organ 3):
    gerilim = yayılma × tazelik × maliyet

- yayılma : yanlış tarafa kaç şey yaslanıyor (0..1, atıf sayısından)
- tazelik : üstüne iş yapılıyor mu? (yarı ömür 7 gün; yakın=1, eskidir=0'a)
- maliyet : yanlış taraf ne kadar ileri gitmiş
            yerel .25 < commit .50 < birleşmiş .75 < yayında 1.00
- birikme : eşiğin altında kalan çatlak HER GÜN biraz daha ağırlaşır —
            küçük ama hiç çözülmeyen tutarsızlık günler sonra yüzeye çıkar.

Kuyruk kuralları:
- GÜNDE EN FAZLA 1 KART. Aynı gün tekrar çağrılırsa AYNI kart döner
  (dırdır yok).
- Çatlak asla silinmez; sadece "cozuldu" işaretlenerek kapanır.
- Durum data/fay_kuyruk.json'da atomik yazılır.
"""

import json
import logging
import os
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

_MALIYET_SEVIYE = {
    "yerel": 0.25,
    "commit": 0.50,
    "birlestirilmis": 0.75,
    "yayinda": 1.00,
}

_ESIK = 0.30          # bu puanın altındaki çatlak kart olmaz...
_BIRIKME_KATSAYISI = 0.10   # ...ama her bekleyen gün %10 ağırlaşır
_TAZELIK_YARI_OMUR_GUN = 7.0


def gerilim_puani(yayilma, son_temas_gun_once, maliyet_seviyesi,
                  birikme=0):
    """Şeffaf puan formülü — büyü olmadan, hesaplanabilir."""
    yay = max(0.0, min(1.0, float(yayilma)))
    gun = max(0.0, float(son_temas_gun_once))
    tazelik = 0.5 ** (gun / _TAZELIK_YARI_OMUR_GUN)
    maliyet = _MALIYET_SEVIYE.get(maliyet_seviyesi, 0.25)
    carpici = 1.0 + _BIRIKME_KATSAYISI * max(0, int(birikme))
    return round(min(1.0, yay * tazelik * maliyet * carpici), 3)


class FayKuyrugu:
    """Çatlakların kalıcı kuyruğu + günlük tek-kart kapısı."""

    def __init__(self, dosya):
        self.dosya = dosya
        self._kilit = threading.Lock()

    # ---------- disk ----------

    def _yukle(self):
        try:
            with open(self.dosya, "r", encoding="utf-8-sig") as f:
                veri = json.load(f)
        except (OSError, json.JSONDecodeError):
            veri = {}
        veri.setdefault("catlaklar", [])
        veri.setdefault("kart_gunu", "")
        veri.setdefault("kart_id", None)
        return veri

    def _kaydet(self, veri):
        os.makedirs(os.path.dirname(self.dosya), exist_ok=True)
        tmp = self.dosya + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.dosya)

    # ---------- yazma ----------

    def catlak_ekle(self, konu, cift, gerekce, maliyet_seviyesi="yerel",
                    yayilma=0.0, simdi=None) -> str:
        """Yeni çatlak açar; aynı (konu,cift) açıksa birikmesini artırır."""
        simdi = simdi or datetime.now()
        with self._kilit:
            veri = self._yukle()
            for c in veri["catlaklar"]:
                if (c["konu"] == konu and c["durum"] == "acik"
                        and c["cift"] == list(cift)):
                    c["birikme"] = c.get("birikme", 0) + 1
                    c["son_gorulme"] = simdi.isoformat()
                    self._kaydet(veri)
                    return c["id"]
            cid = "C%03d" % (len(veri["catlaklar"]) + 1)
            veri["catlaklar"].append({
                "id": cid,
                "konu": konu,
                "cift": list(cift),
                "gerekce": gerekce[:200],
                "maliyet": maliyet_seviyesi,
                "yayilma": max(0.0, min(1.0, float(yayilma))),
                "birikme": 0,
                "durum": "acik",
                "ilk_gorulme": simdi.isoformat(),
                "son_gorulme": simdi.isoformat(),
            })
            self._kaydet(veri)
            logger.info("FAY catlagi acildi: %s (%s)", cid, konu)
            return cid

    def cozuldu_isaretle(self, catlak_id):
        """Çatlağı kapatır (çözüldü) — silinmez, arşivde kalır."""
        with self._kilit:
            veri = self._yukle()
            for c in veri["catlaklar"]:
                if c["id"] == catlak_id:
                    c["durum"] = "cozuldu"
                    self._kaydet(veri)
                    return True
        return False

    # ---------- kart ----------

    def gunluk_kart(self, yayilma_fn=None, simdi=None):
        """Günün TEK kartını döndürür; yoksa None.

        - Aynı gün ikinci çağrı AYNI kartı verir (dırdır yok).
        - Eşik altındaki açık çatlakların birikmesi artırılır —
          günler geçtikçe yüzeye çıkmaları kolaylaşır.
        yayilma_fn(catlak) -> 0..1 verilmezse kayıtlı yayılma kullanılır.
        """
        simdi = simdi or datetime.now()
        bugun = simdi.strftime("%Y-%m-%d")
        with self._kilit:
            veri = self._yukle()

            if veri["kart_gunu"] == bugun and veri["kart_id"]:
                for c in veri["catlaklar"]:
                    if c["id"] == veri["kart_id"] and c["durum"] == "acik":
                        return self._kart_paketi(c, veri)

            adaylar = []
            for c in veri["catlaklar"]:
                if c["durum"] != "acik":
                    continue
                gun_once = max(
                    0.0, (simdi - datetime.fromisoformat(
                        c["son_gorulme"])).total_seconds() / 86400)
                yay = c["yayilma"]
                if yayilma_fn:
                    yay = max(0.0, min(1.0, float(yayilma_fn(c))))
                puan = gerilim_puani(yay, gun_once, c["maliyet"],
                                     c.get("birikme", 0))
                adaylar.append((puan, c))

            if not adaylar:
                veri["kart_gunu"], veri["kart_id"] = bugun, None
                self._kaydet(veri)
                return None

            adaylar.sort(key=lambda t: (-t[0], t[1]["ilk_gorulme"]))
            puan, secilen = adaylar[0]

            if puan < _ESIK and secilen.get("birikme", 0) == 0:
                # sessiz çatlak: gösterilmedi ama gerilim birikiyor
                secilen["birikme"] = secilen.get("birikme", 0) + 1
                veri["kart_gunu"], veri["kart_id"] = bugun, None
                self._kaydet(veri)
                logger.info("FAY esik altinda birakti: %s (birikme=%d)",
                            secilen["id"], secilen["birikme"])
                return None

            veri["kart_gunu"], veri["kart_id"] = bugun, secilen["id"]
            self._kaydet(veri)
            return self._kart_paketi(secilen, veri, puan)

    @staticmethod
    def _kart_paketi(c, veri, puan=None):
        paket = {
            "id": c["id"],
            "konu": c["konu"],
            "cift": tuple(c["cift"]),
            "gerekce": c["gerekce"],
            "maliyet": c["maliyet"],
            "birikme": c.get("birikme", 0),
        }
        if puan is not None:
            paket["puan"] = puan
        return paket
