"""tools/tarayici_ws.py — eklenti ile cekirdek arasinda yerel WebSocket koprusu.

Neden bu dosya var: `tools/tarayici_kopru.py` istemci kaydini tutar ama
gercek bir tasima yoktu. Eklenti tarayicida yasar; sunucu ondan sayfa
gozlemi ister. Bunun icin canli bir kanal gerekir (istek/cevap ayni
baglanti uzerinden gider). Bu modul o kanali acar.

Sinirlar
--------
- Yalniz 127.0.0.1 dinlenir. Varsayilan olarak yalniz bu bilgisayar.
- Kaynak denetimi: tarayici uzantisi kaynagi (chrome-extension:// ya da
  moz-extension://) disindaki Origin reddedilir.
- Anahtar: `ayarlar.json` -> "eklenti_anahtari" ya da ortam degiskeni
  BASAK_EKLENTI_ANAHTARI doluysa URL'deki ?token= eslesmek zorunda.
- Kalici bir surec ister. DUZELTME (2026-10-21, Vercel KB): Vercel artik
  WebSocket'i yerel olarak destekliyor (public beta, Fluid Compute, tum
  planlar). Ama baglanti fonksiyonun AZAMI suresinde kapanir (Hobby 300 sn),
  baglanti tek bir instance'a CIVILENIR ve sohbet istegi baska bir instance'a
  dusebilir; o zaman cekirdek sokete ulasamaz. Bu yuzden bulut icin ya
  paylasimli bir depo (Redis/Postgres) + yeniden baglanma, ya da Koyeb gibi
  tek kalici surec gerekir. Engel protokol degil, instance dagitimi.

Protokol (eklenti tarafi)
-------------------------
  baglan:  ws://127.0.0.1:8788/?token=<anahtar>
  sunucu -> eklenti:  {"id": "c1", "islem": "sayfa_gozlem", "veri": {...}}
  eklenti -> sunucu:  {"id": "c1", "ok": true, "sonuc": {...}}
                  ya da {"id": "c1", "ok": false, "hata": "..."}
"""

import json
import logging
import os
import threading
import urllib.parse

from chat.kimlik import aktif_kullanici
from tools.tarayici_kopru import KOPRU

logger = logging.getLogger(__name__)

VARSAYILAN_PORT = 8788
VARSAYILAN_ADRES = "127.0.0.1"
IZINLI_KOKENLER = ("chrome-extension://", "moz-extension://")


def _ayarlar():
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        with open(os.path.join(kok, "ayarlar.json"), "r",
                  encoding="utf-8-sig") as f:
            veri = json.load(f)
        return veri if isinstance(veri, dict) else {}
    except (OSError, ValueError):
        return {}


def beklenen_anahtar():
    ortam = os.environ.get("BASAK_EKLENTI_ANAHTARI", "").strip()
    if ortam:
        return ortam
    return str(_ayarlar().get("eklenti_anahtari") or "").strip()


class Oturum:
    """Tek eklenti baglantisinin istek/cevap muhasebesi."""

    def __init__(self, baglanti, kimlik, kullanici="casper"):
        self._b = baglanti
        self.kimlik = kimlik
        self.kullanici = kullanici
        self._kilit = threading.Lock()
        self._bekleyen = {}     # cagri kimligi -> [threading.Event, cevap]
        self._sayac = 0
        self._sohbet_kilidi = threading.Lock()
        self.kapandi = threading.Event()

    def cevap_gonder(self, mesaj):
        """Eklentiye tek mesaj yazar; baglanti kopmussa iz birakir."""
        try:
            self._b.send(json.dumps(mesaj, ensure_ascii=False))
            return True
        except Exception as hata:               # noqa: BLE001 - kopuk soket
            logger.debug("eklentiye yazilamadi: %s", hata)
            return False

    def istek_baslat(self, mesaj, sohbet_isle):
        """Eklentiden GELEN istegi ayri is parcaciginda kosar.

        Ayri is parcacigi sart: sohbet cekirdegi calisirken ayni baglanti
        uzerinden `sayfa_gozlem` cevabı gelir. Cagriyi alan dongu mesgul
        olursa cevap okunamaz ve arac zaman asimina duser (kilitlenme).
        """
        islem = str(mesaj.get("islem") or "")
        cagri = str(mesaj.get("id") or "")
        if islem != "sohbet":
            self.cevap_gonder({"id": cagri, "ok": False,
                               "hata": "bilinmeyen islem: %s" % islem})
            return
        if sohbet_isle is None:
            self.cevap_gonder({"id": cagri, "ok": False,
                               "hata": "sohbet bu kopruda kapali"})
            return
        veri = mesaj.get("veri") or {}
        metin = str(veri.get("metin") or "").strip()
        if not metin:
            self.cevap_gonder({"id": cagri, "ok": False, "hata": "mesaj bos"})
            return
        if not self._sohbet_kilidi.acquire(blocking=False):
            self.cevap_gonder({"id": cagri, "ok": False,
                               "hata": "onceki mesaj hala suruyor"})
            return

        kullanici = self.kullanici

        def kos():
            try:
                sonuc = sohbet_isle(metin, kullanici)
                if not isinstance(sonuc, dict):
                    sonuc = {"cevap": str(sonuc or "")}
                self.cevap_gonder({"id": cagri, "ok": True, "sonuc": sonuc})
            except Exception as hata:          # noqa: BLE001 - sohbet kesilmesin
                logger.warning("eklenti sohbeti basarisiz: %s", hata)
                self.cevap_gonder({"id": cagri, "ok": False,
                                   "hata": "Bir sorun oldu: %s" % hata})
            finally:
                self._sohbet_kilidi.release()

        threading.Thread(target=kos, daemon=True).start()

    def gonder(self, islem, veri, sure):
        """Cekirdek is parcacigindan cagrilir; eklenti cevabini bekler."""
        if self.kapandi.is_set():
            raise RuntimeError("eklenti baglantisi kapandi")
        with self._kilit:
            self._sayac += 1
            cagri = "c%d" % self._sayac
            olay = threading.Event()
            self._bekleyen[cagri] = [olay, None]
        try:
            self._b.send(json.dumps(
                {"id": cagri, "islem": islem, "veri": veri or {}},
                ensure_ascii=False))
        except Exception as hata:
            with self._kilit:
                self._bekleyen.pop(cagri, None)
            raise RuntimeError("eklentiye yazilamadi: %s" % hata) from hata

        if not olay.wait(sure):
            with self._kilit:
                self._bekleyen.pop(cagri, None)
            raise TimeoutError("eklenti %.1f sn icinde cevap vermedi" % sure)
        with self._kilit:
            kayit = self._bekleyen.pop(cagri, None)
        cevap = kayit[1] if kayit else None
        if not isinstance(cevap, dict):
            raise RuntimeError("eklenti cevabi okunamadi")
        return cevap

    def cevap_yaz(self, mesaj):
        cagri = str(mesaj.get("id") or "")
        with self._kilit:
            kayit = self._bekleyen.get(cagri)
            if kayit is not None:
                kayit[1] = mesaj
        if kayit is not None:
            kayit[0].set()

    def kapat(self):
        self.kapandi.set()
        with self._kilit:
            bekleyen = list(self._bekleyen.values())
            self._bekleyen.clear()
        for olay, _ in bekleyen:
            olay.set()


def _sorgu_tokenu(yol):
    try:
        sorgu = urllib.parse.urlparse(yol or "").query
        return urllib.parse.parse_qs(sorgu).get("token", [""])[0]
    except ValueError:
        return ""


def _kaynak_uygun(baglanti):
    """Yalniz tarayici uzantisi kaynaklarina izin verir."""
    try:
        basliklar = baglanti.request.headers
        kok = basliklar.get("Origin") or ""
    except AttributeError:
        return True
    if not kok:
        return True          # tarayici disi istemci (test/CLI)
    return kok.startswith(IZINLI_KOKENLER)


def islem_yap(baglanti, token=None, kullanici=None, sohbet_isle=None):
    """Tek baglantiyi yasar; cekirdek isteklerini eklentiye tasir."""
    if not _kaynak_uygun(baglanti):
        baglanti.close(1008, "izin verilmeyen kaynak")
        return
    if token and _sorgu_tokenu(getattr(baglanti.request, "path", "")) != token:
        baglanti.close(1008, "gecersiz anahtar")
        return

    # Baglanti KISIYE baglanir: cok kullanicili sunucuda bir kullanicinin
    # sekmesi baskasinin istegine cevap veremez.
    kullanici = str(kullanici or aktif_kullanici())
    kimlik = "eklenti-%s-%d" % (kullanici, id(baglanti))
    oturum = Oturum(baglanti, kimlik, kullanici=kullanici)
    KOPRU.bagla(kimlik, oturum.gonder, kullanici=kullanici)
    logger.info("eklenti baglandi: %s", kimlik)
    try:
        for ham in baglanti:
            try:
                mesaj = json.loads(ham)
            except (TypeError, ValueError):
                continue
            if not isinstance(mesaj, dict):
                continue
            if mesaj.get("islem"):
                # Eklentiden GELEN istek (panel sohbeti).
                oturum.istek_baslat(mesaj, sohbet_isle)
            else:
                # Cekirdegin gonderdigi istege eklentinin cevabi.
                oturum.cevap_yaz(mesaj)
    except Exception as hata:                 # noqa: BLE001 - baglanti sonu
        logger.info("eklenti baglantisi bitti (%s): %s", kimlik, hata)
    finally:
        oturum.kapat()
        KOPRU.ayir(kimlik)
        logger.info("eklenti ayrildi: %s", kimlik)


class KopruSunucusu:
    """Sunucuyu kendi is parcaciginda kosar; testte durdurulabilir."""

    def __init__(self, port=VARSAYILAN_PORT, adres=VARSAYILAN_ADRES, token=None,
                 kullanici=None, sohbet_isle=None):
        self.port = int(port)
        self.adres = adres
        self._token = token
        self._kullanici = kullanici
        self._sohbet_isle = sohbet_isle
        self._sunucu = None
        self._is_parcacigi = None
        self._kilit = threading.Lock()
        self._baglantilar = set()

    def _baglanti_isle(self, baglanti):
        """Acik baglantiyi deftere alir; kapanista istemciyi ayirir.

        Kapanista ayirma islemi burada yapilir: aksi halde `durdur()`
        sunucuyu kapatir ama bagli istemci KOPRU defterinde kalir ve
        kopruyu "bagli" sanan cekirdek cevapsiz istek atar.
        """
        with self._kilit:
            self._baglantilar.add(baglanti)
        try:
            islem_yap(baglanti, self._token, self._kullanici,
                      self._sohbet_isle)
        finally:
            with self._kilit:
                self._baglantilar.discard(baglanti)

    def basla(self):
        from websockets.sync.server import serve

        self._sunucu = serve(self._baglanti_isle, self.adres, self.port)
        self.port = self._sunucu.socket.getsockname()[1]
        self._is_parcacigi = threading.Thread(
            target=self._sunucu.serve_forever, daemon=True)
        self._is_parcacigi.start()
        return self

    def durdur(self):
        """Sunucuyu ve acik baglantilari kapatir; defter temiz kalir."""
        with self._kilit:
            baglantilar = list(self._baglantilar)
        for baglanti in baglantilar:
            try:
                baglanti.close(1001, "sunucu kapaniyor")
            except Exception as hata:          # noqa: BLE001 - kapanis yolu
                logger.debug("baglanti kapatilamadi: %s", hata)
        if self._sunucu is not None:
            self._sunucu.shutdown()
            self._sunucu = None


def baslat(port=None, sohbet_isle=None):
    """Ayarlardan port/anahtar okuyup kopruyu arka planda acar.

    sohbet_isle(metin, kullanici) -> {"cevap": ...}: panel sohbetinin
    cekirdek girisi. Verilmezse panel sohbeti acik hata doner.
    """
    ayar = _ayarlar()
    try:
        port = int(port or ayar.get("eklenti_port") or VARSAYILAN_PORT)
    except (TypeError, ValueError):
        port = VARSAYILAN_PORT
    return KopruSunucusu(port=port, token=beklenen_anahtar(),
                         sohbet_isle=sohbet_isle).basla()
