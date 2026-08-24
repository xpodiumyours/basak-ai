"""tools/evrim.py — EVRIM-0: Hipotez havuzu + nüfus arşivi (kilitli hedef).

Döngü (Casper'in tanımı):
    hipotez üret → deney → ölç → başarısızı ele / iyiyi tut
    → mutasyon + yeniden kombinasyon → tekrarla

Nüfus arşivi (Darwin Gödel Machine yaklaşımı): tek ajanı değiştirmek
yerine farklı sürümler ARŞİVLENİR; iyi varyantlar yeni varyantların
temeli olur; her değişiklik deney motoruyla ampirik doğrulanır.

Depo: data/evrim_arsivi.json — atomik yazım. Silme yok: elenenler
"elenmis" işaretle arşivde kalır (kanıt zinciri korunur).

Puanlar DENEY-0 motorundan gelir (deney_yurut) — LLM puanı değil,
ölçüm puanıdır.
"""

import json
import logging
import os
import threading

logger = logging.getLogger(__name__)

_DURUMLAR = ("yeni", "test_edildi", "hayatta", "elenmis")


class Arsiv:
    """Hipotez nüfus arşivi."""

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
        veri.setdefault("hipotezler", [])
        return veri

    def _kaydet(self, veri):
        os.makedirs(os.path.dirname(self.dosya), exist_ok=True)
        tmp = self.dosya + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.dosya)

    # ---------- havuz ----------

    def _yeni_id(self, veri):
        return "H%03d" % (len(veri["hipotezler"]) + 1)

    def hipotez_ekle(self, icerik, nesil=0, ebeveynler=None) -> str:
        with self._kilit:
            veri = self._yukle()
            hid = self._yeni_id(veri)
            veri["hipotezler"].append({
                "id": hid,
                "icerik": (icerik or "").strip(),
                "puan": None,
                "olcum": "",
                "nesil": int(nesil),
                "ebeveynler": list(ebeveynler or []),
                "durum": "yeni",
            })
            self._kaydet(veri)
        logger.info("Hipotez eklendi: %s (nesil %d)", hid, nesil)
        return hid

    def hipotez(self, hid):
        for h in self._yukle()["hipotezler"]:
            if h["id"] == hid:
                return h
        return None

    def puanla(self, hid, puan, olcum=""):
        """Deney motorunun ölçümünü hipoteze yazar; durumu ilerletir."""
        with self._kilit:
            veri = self._yukle()
            for h in veri["hipotezler"]:
                if h["id"] == hid:
                    h["puan"] = float(puan)
                    h["olcum"] = (olcum or "")[:200]
                    if h["durum"] in ("yeni", "test_edildi"):
                        h["durum"] = "test_edildi"
                    break
            else:
                raise ValueError("Hipotez yok: %s" % hid)
            self._kaydet(veri)

    def en_iyiler(self, limit=5):
        """Puanlı ve henüz elenmemiş hipotezler, puana göre sıralı."""
        veri = self._yukle()
        adaylar = [h for h in veri["hipotezler"]
                   if h["puan"] is not None and h["durum"] != "elenmis"]
        adaylar.sort(key=lambda h: -h["puan"])
        secilen = [h["id"] for h in adaylar[:limit]]
        with self._kilit:
            veri = self._yukle()
            for h in veri["hipotezler"]:
                if h["id"] in secilen:
                    h["durum"] = "hayatta"
            self._kaydet(veri)
        return [self.hipotez(hid) for hid in secilen]

    def kombinasyon(self, id_a, id_b, yeni_icerik) -> str:
        """İki hipotezin güçlü yanlarını birleştiren YENİ kayıt açar."""
        a, b = self.hipotez(id_a), self.hipotez(id_b)
        if not a or not b:
            raise ValueError("Ebeveyn bulunamadi")
        nesil = max(a["nesil"], b["nesil"]) + 1
        return self.hipotez_ekle(yeni_icerik, nesil=nesil,
                                 ebeveynler=[id_a, id_b])

    def mutasyon(self, id_kaynak, yeni_icerik) -> str:
        k = self.hipotez(id_kaynak)
        if not k:
            raise ValueError("Kaynak bulunamadi")
        return self.hipotez_ekle(yeni_icerik, nesil=k["nesil"] + 1,
                                 ebeveynler=[id_kaynak])


def evrim_turu(arsiv, uretici, degerlendirici, hayatta_limit=5):
    """Bir evrim turu: üret → değerlendir → ele.

    uretici():        yeni hipotez metinleri listesi
    degerlendirici(hid, icerik) -> (puan, olcum_metni)
                        — DENEY-0 motorunu sarmalayan fonksiyon;
                          puan ölçümden gelir.
    Dönüş: hayatta kalanların özeti [{id, icerik, puan}]
    """
    yeni_idler = []
    for icerik in (uretici() or []):
        yeni_idler.append(arsiv.hipotez_ekle(icerik))

    for hid in yeni_idler:
        hipotez = arsiv.hipotez(hid)
        puan, olcum = degerlendirici(hid, hipotez["icerik"])
        arsiv.puanla(hid, float(puan), str(olcum)[:200])

    kalanlar = arsiv.en_iyiler(limit=hayatta_limit)

    # kalanmayan test_edildi hipotezleri elenmis işaretlenir
    kalan_idler = {h["id"] for h in kalanlar}
    veri = arsiv._yukle()
    for h in veri["hipotezler"]:
        if (h["id"] in set(yeni_idler) and h["id"] not in kalan_idler
                and h["durum"] == "test_edildi"):
            h["durum"] = "elenmis"
    arsiv._kaydet(veri)

    return [{"id": h["id"], "icerik": h["icerik"], "puan": h["puan"],
             "nesil": h["nesil"]} for h in kalanlar]
