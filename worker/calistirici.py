"""Kuyruktan iş alıp onaylı tarayıcı eylemini uygulayan döngü.

Kural: bu sınıf KARAR VERMEZ. Hangi eylemin yapılacağına Başak'ın beyni
ve kullanıcı karar verir; burada yalnız sıra, kalp atışı, hata sınıflaması
ve sonucun deftere yazılması vardır.

Sınıflama:
- `TokenHatasi`: belge geçersiz/süresi dolmuş/ikinci kullanım. Eylem
  HİÇ başlamadı → iş `hata`.
- `TarayiciHatasi`: tarayıcı adımı tamamlanamadı → iş `hata` (kanıt
  metniyle). Otomatik tekrar YOK: tıklama yarım kalmış olabilir.
- Beklenmeyen istisna ya da işçi durdurma: eylem kısmen çalışmış
  olabilir → iş `supheli`; kör tekrar yapılmaz.
- Çöken işçinin `calisiyor` işleri heartbeat süresi dolunca `temizle`
  tarafından `supheli` işaretlenir.
"""

import asyncio
import json
import logging
import signal
import time

from worker.guvenlik import TokenHatasi
from worker.hatalar import TarayiciHatasi

logger = logging.getLogger(__name__)


def _kisa(metin, sinir=500):
    metin = str(metin or "")
    return metin if len(metin) <= sinir else metin[:sinir] + "..."


def _iso(an):
    if an is None:
        return ""
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(an)))
    except (TypeError, ValueError, OverflowError):
        return ""


class Calistirici:
    """Tek işçi süreci: kuyruk + gerçek/dublör tarayıcı."""

    def __init__(self, kuyruk, tarayici, *, isci="basak-worker-1",
                 surum="dev", aralik=1.0, kalp_aralik=20.0, esik=90.0):
        self._kuyruk = kuyruk
        self._tarayici = tarayici
        self._isci = str(isci or "").strip()
        if not self._isci:
            raise ValueError("işçi adı boş")
        self._surum = str(surum or "dev")
        self._aralik = max(0.1, float(aralik))
        self._kalp_aralik = max(1.0, float(kalp_aralik))
        self._esik = max(10.0, float(esik))
        self._dur = asyncio.Event()
        self._is = ""
        self._son_tur = None
        self._son_hata = ""
        self._yazilamayan = {}

    # ── dış yüz ─────────────────────────────────────────────────────

    @property
    def isci(self):
        return self._isci

    def durdur(self):
        self._dur.set()

    def saglik(self):
        try:
            kuyruk = self._kuyruk.ozet(self._esik)
            ok = True
        except Exception as hata:
            logger.warning("sağlık özeti okunamadı", exc_info=True)
            kuyruk = {"hata": _kisa(hata)}
            ok = False
        return {
            "ok": bool(ok),
            "isci": self._isci,
            "surum": self._surum,
            "calisiyor": self._is,
            "son_tur": _iso(self._son_tur),
            "son_hata": self._son_hata,
            "yazilamayan": len(self._yazilamayan),
            "kuyruk": kuyruk,
        }

    # ── tek tur ─────────────────────────────────────────────────────

    async def tek_tur(self):
        """Bir iş alır ve uygular; iş yoksa None döner."""
        self._bekleyenleri_yaz()
        satir = self._kuyruk.al(self._isci)
        if satir is None:
            # Boşta da kalp atar: "canlı işçi" yalnız iş alırken değil,
            # kuyruğu yoklarken de görünmeli.
            self._kalp_guvenli("hazir")
            return None

        is_id = str(satir.get("id") or "")
        self._is = is_id
        try:
            self._kalp_guvenli("mesgul", is_id)
            return await self._uygula(satir)
        finally:
            self._is = ""
            self._son_tur = time.time()
            self._kalp_guvenli("hazir")

    async def _uygula(self, satir):
        is_id = str(satir.get("id") or "")
        try:
            eylem = json.loads(str(satir.get("eylem") or ""))
        except (TypeError, ValueError):
            eylem = None
        if not isinstance(eylem, dict) or not eylem:
            return self._bitir(satir, {"ok": False, "hata": "eylem çözülemedi"},
                               "eylem çözülemedi")

        try:
            sonuc = await self._tarayici.adim(
                str(satir.get("kosu_id") or ""),
                eylem,
                str(satir.get("token") or ""),
                adim_id=str(satir.get("adim_id") or ""),
            )
        except asyncio.CancelledError:
            self._supheli(satir, "işçi durduruldu")
            raise
        except TokenHatasi as hata:
            return self._bitir(satir, {"ok": False, "hata": str(hata)},
                               str(hata))
        except TarayiciHatasi as hata:
            return self._bitir(satir, {"ok": False, "hata": str(hata)},
                               str(hata))
        except Exception as hata:  # noqa: BLE001 — sınıflama burada
            logger.exception("işçi adımında beklenmeyen hata: %s", is_id)
            return self._supheli(
                satir, "beklenmeyen hata: %s" % _kisa(hata))

        self._yaz(is_id, sonuc, "")
        return self._oku_guvenli(is_id)

    # ── defter yazımı ───────────────────────────────────────────────

    def _bitir(self, satir, sonuc, hata=""):
        is_id = str(satir.get("id") or "")
        self._yaz(is_id, sonuc, hata)
        return self._oku_guvenli(is_id)

    def _supheli(self, satir, neden):
        is_id = str(satir.get("id") or "")
        try:
            self._kuyruk.supheli_yap(is_id, self._isci, neden)
        except Exception:
            logger.exception("şüpheli iş yazılamadı: %s", is_id)
            self._son_hata = _kisa(neden)
        return self._oku_guvenli(is_id)

    def _yaz(self, is_id, sonuc, hata):
        try:
            self._kuyruk.bitir(
                is_id, self._isci, sonuc, hata=hata)
            self._yazilamayan.pop(is_id, None)
        except Exception as hata_db:
            # Eylem çalıştı ama sonuç yazılamadı. Sonucu bellekte tutup
            # sonraki turda tekrar deneriz; süreç çökerse kalp durur ve
            # `temizle` işi `supheli` işaretler.
            logger.exception("iş sonucu yazılamadı: %s", is_id)
            self._son_hata = _kisa(hata_db)
            self._yazilamayan[is_id] = (sonuc, hata)

    def _bekleyenleri_yaz(self):
        for is_id, (sonuc, hata) in list(self._yazilamayan.items()):
            try:
                self._kuyruk.bitir(
                    is_id, self._isci, sonuc, hata=hata)
            except Exception:
                logger.warning("bekleyen sonuç hâlâ yazılamadı: %s", is_id)
                break
            self._yazilamayan.pop(is_id, None)

    def _oku_guvenli(self, is_id):
        try:
            return self._kuyruk.oku(is_id)
        except Exception:
            logger.warning("iş satırı okunamadı: %s", is_id, exc_info=True)
            return None

    # ── kalp ────────────────────────────────────────────────────────

    def _kalp_guvenli(self, durum, is_id=""):
        try:
            self._kuyruk.kalp(
                self._isci, durum=durum, surum=self._surum, is_id=is_id)
        except Exception:
            logger.warning("kalp atışı yazılamadı", exc_info=True)
            self._son_hata = "kalp atışı yazılamadı"

    # ── ana döngü ───────────────────────────────────────────────────

    async def kos(self):
        """Sinyale kadar iş alır; boşta beklerken kalp atışını sürdürür."""
        try:
            temizlenen = self._kuyruk.temizle(self._esik)
            if temizlenen:
                logger.warning(
                    "%d yarım iş şüpheli işaretlendi", temizlenen)
        except Exception:
            logger.warning("başlangıç temizliği yapılamadı", exc_info=True)

        self._sinyalleri_bagla()
        self._kalp_guvenli("hazir")
        son_kalp = time.monotonic()
        logger.info("işçi hazır: %s (%s)", self._isci, self._surum)

        try:
            while not self._dur.is_set():
                try:
                    await self.tek_tur()
                except asyncio.CancelledError:
                    raise
                except Exception as hata:  # noqa: BLE001
                    logger.exception("kuyruk turu başarısız")
                    self._son_hata = _kisa(hata)

                if self._dur.is_set():
                    break
                try:
                    await asyncio.wait_for(
                        self._dur.wait(), timeout=self._aralik)
                except asyncio.TimeoutError:
                    logger.debug("bekleme doldu, kuyruk yeniden yoklanıyor")

                if time.monotonic() - son_kalp >= self._kalp_aralik:
                    self._kalp_guvenli("hazir")
                    son_kalp = time.monotonic()
        finally:
            self._kalp_guvenli("duruyor")
            logger.info("işçi durdu: %s", self._isci)

    def _sinyalleri_bagla(self):
        try:
            dongu = asyncio.get_running_loop()
        except RuntimeError:
            return
        for sinyal in (getattr(signal, "SIGINT", None),
                       getattr(signal, "SIGTERM", None)):
            if sinyal is None:
                continue
            try:
                dongu.add_signal_handler(sinyal, self.durdur)
            except (NotImplementedError, RuntimeError, ValueError):
                # Windows'ta add_signal_handler yok; ana iş parçacığında
                # klasik handler kullanılır.
                try:
                    signal.signal(
                        sinyal,
                        lambda *_args: dongu.call_soon_threadsafe(self.durdur))
                except (ValueError, OSError, RuntimeError):
                    logger.debug("sinyal bağlanamadı: %s", sinyal)
