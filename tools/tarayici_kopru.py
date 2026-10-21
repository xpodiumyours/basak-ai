"""tools/tarayici_kopru.py — eklenti ile cekirdek arasindaki tek tasima.

Basak'in beyni Python cekirdeginde kalir (AGENTS.md S9 tek beyin kurali).
Eklenti yalnizca GOZ ve EL'dir: sayfayi ham olarak okur, istenen eylemi
uygular. Bu modul o istemcileri kaydeder ve istekleri tek yerden gecirir.
Burada sayfa yorumlanmaz; ham gozlem tools/tarayici_goz.py'de modele
cevrilir.

Sozlesme
--------
Istemci kaydi:  KOPRU.bagla(kimlik, gonder)
  gonder(islem, veri, sure) -> dict
  Beklenen cevap: {"ok": True, "sonuc": {...}}
              ya da {"ok": False, "hata": "..."}
  Istemci `sure` saniyesine kendi icinde uyar (soket zaman asimi).

Cekirdek cagrisi: KOPRU.iste(islem, veri, sure)
  Istemci yoksa, cevap vermezse ya da hata donerse ACIK hata sozlugu
  doner; istisna disari sizmaz, sohbet kesilmez.
"""

import queue
import threading
import time

from chat.kimlik import aktif_kullanici
from tools import tarayici_goz

ZAMAN_ASIMI = 15.0


class Kopru:
    """Bagli tarayici istemcilerinin defteri."""

    def __init__(self):
        self._kilit = threading.Lock()
        # kimlik -> {"gonder": callable, "zaman": ts, "kullanici": kid}
        self._istemciler = {}

    def bagla(self, kimlik, gonder, kullanici=None):
        """Istemciyi KAYITLI KISIYE baglar; ayni kimlik tazelenir.

        Kullanici ayrimi sart: cok kullanicili sunucuda "en son baglanan
        istemci" secilirse bir kullanicinin sayfasi baskasina gidebilir.
        """
        kimlik = str(kimlik or "").strip()
        if not kimlik or not callable(gonder):
            raise ValueError("Istemci kimligi ve gonderilebilir cagri gerekli.")
        kullanici = str(kullanici or aktif_kullanici()).strip() or "casper"
        with self._kilit:
            self._istemciler[kimlik] = {
                "gonder": gonder,
                "zaman": time.time(),
                "kullanici": kullanici,
            }
        return kimlik

    def ayir(self, kimlik):
        with self._kilit:
            return self._istemciler.pop(str(kimlik or ""), None) is not None

    def kimlikler(self):
        with self._kilit:
            return tuple(self._istemciler)

    def var_mi(self, kullanici=None):
        """Bu kisi icin bagli istemci var mi? (kullanici bos = herhangi biri)"""
        with self._kilit:
            if kullanici is None:
                return bool(self._istemciler)
            return any(k["kullanici"] == kullanici
                       for k in self._istemciler.values())

    def _sec(self, kullanici):
        """O KISIYE ait en son istemci; baskasinin istemcisi ASLA secilmez.

        Doner: (gonder | None, herhangi_bir_istemci_var_mi)
        """
        with self._kilit:
            adaylar = [k for k in self._istemciler.values()
                       if k["kullanici"] == kullanici]
            if not adaylar:
                return None, bool(self._istemciler)
            return max(adaylar, key=lambda k: k["zaman"])["gonder"], True

    def iste(self, islem, veri=None, sure=ZAMAN_ASIMI, kullanici=None):
        """Istemciden cevap ister; her hata acik sozluk olarak doner."""
        kullanici = str(kullanici or aktif_kullanici()).strip() or "casper"
        gonder, baska_var = self._sec(kullanici)
        if gonder is None:
            if baska_var:
                return {"error": "Bu kullanici icin bagli tarayici yok; "
                                 "Basak eklentisini bu hesapta bagla."}
            return {"error": "Tarayiciya bagli istemci yok; "
                             "once Basak eklentisini ac."}
        try:
            sure = float(sure or ZAMAN_ASIMI)
        except (TypeError, ValueError):
            sure = ZAMAN_ASIMI

        # Istemci kendi zaman asimina uymazsa sohbet kilitlenmesin diye
        # cagri ayri bir daemon is parcaciginda kosar ve burada beklenir.
        kutu = queue.Queue(maxsize=1)

        def kos():
            try:
                kutu.put(("ok", gonder(islem, veri or {}, sure)))
            except BaseException as hata:      # noqa: BLE001 - disari sizmaz
                kutu.put(("hata", hata))

        threading.Thread(target=kos, daemon=True).start()
        try:
            tur, deger = kutu.get(timeout=sure)
        except queue.Empty:
            return {"error": "Tarayici %.0f saniye icinde cevap vermedi." % sure}
        if tur == "hata":
            return {"error": "Tarayici istegi tamamlanamadi: %s" % deger}
        return deger if isinstance(deger, dict) else {
            "error": "Tarayici beklenmeyen bicimde cevap verdi."}


KOPRU = Kopru()


def cevabi_coz(cevap):
    """Istemci cevabini sonuc/hata olarak ayirir."""
    if not isinstance(cevap, dict):
        return {"error": "Tarayici beklenmeyen bicimde cevap verdi."}
    if cevap.get("error"):
        return {"error": str(cevap["error"])}
    if cevap.get("ok") is False:
        return {"error": str(cevap.get("hata")
                               or "Tarayici islemi tamamlayamadi.")}
    sonuc = cevap.get("sonuc")
    if sonuc is None:
        return {"error": "Tarayici gozlem govdesi bos dondu."}
    return sonuc


def sayfa_bakis(baslangic=0, adet=tarayici_goz.VARSAYILAN_ADET, kullanici=None):
    """Kullanicinin acik sekmesindeki sayfayi modele okunur halde doner."""
    ham = KOPRU.iste("sayfa_gozlem", {"baslangic": baslangic, "adet": adet},
                     kullanici=kullanici)
    sonuc = cevabi_coz(ham)
    if "error" in sonuc:
        return sonuc
    return tarayici_goz.modelle(sonuc, baslangic=baslangic, adet=adet)
