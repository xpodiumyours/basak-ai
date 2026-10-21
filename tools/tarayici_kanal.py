"""tools/tarayici_kanal.py — tek WebSocket bağlantısının senkron köprüsü.

Neden bu dosya var: bulutta eklenti ile çekirdek aynı bağlantıdan konuşur.
Sohbet bir iş parçacığında koşar (bloklayan Python döngüsü), bağlantı ise
asyncio döngüsünde dinler. `Kanal`, araç kodunun "sor ve bekle" demesini
sağlar: istek karşı tarafa gider, cevap asyncio tarafında gelir, burada
`Future` çözülür.

Neden global `KOPRU` yetmiyor: bir sunucu instance'ı aynı anda birden çok
bağlantı taşıyabilir ve eşleştirme "kim bağlı" sorusuyla değil "hangi
bağlantı" sorusuyla yapılmalı. Kanal nesnesi tam olarak o bağlantıdır.

Sınırlar
--------
- `istek()` bloklar; eşzamanlı iki istek aynı kanaldan çıkmaz (araç
  döngüsü sıralıdır).
- Bağlantı kopunca bekleyen her istek açık hatayla döner; sessiz askıda
  kalma yok.
"""

import asyncio
import concurrent.futures
import contextvars
import itertools
import threading

VARSAYILAN_SURE = 20.0

_aktif = contextvars.ContextVar("basak_tarayici_kanali", default=None)


def kanal_kur(kanal):
    """Bu iş parçacığı/istek için geçerli kanalı ayarlar."""
    _aktif.set(kanal)


def aktif_kanal():
    return _aktif.get()


def kanal_temizle():
    _aktif.set(None)


class Kanal:
    """Tek WS bağlantısı: istek gönder, cevabı bekle."""

    def __init__(self, loop, gonder_async, kimlik, kullanici=None):
        self._loop = loop
        self._gonder = gonder_async      # async (cid, islem, veri) -> None
        self.kimlik = kimlik
        self.kullanici = kullanici
        self._kilit = threading.Lock()
        self._bekleyen = {}
        self._sayac = itertools.count(1)
        self.kapandi = False

    def istek(self, islem, veri=None, sure=VARSAYILAN_SURE):
        """İsteği karşı tarafa yollar ve cevabı bekler (ham sözlük)."""
        with self._kilit:
            if self.kapandi:
                return {"error": "Tarayıcı bağlantısı kapandı."}
            cid = "k%d" % next(self._sayac)
            kutu = concurrent.futures.Future()
            self._bekleyen[cid] = kutu
        try:
            asyncio.run_coroutine_threadsafe(
                self._gonder(cid, islem, veri or {}), self._loop)
        except RuntimeError:
            with self._kilit:
                self._bekleyen.pop(cid, None)
            return {"error": "Tarayıcı bağlantısı kullanılamıyor."}
        try:
            return kutu.result(timeout=float(sure))
        except concurrent.futures.TimeoutError:
            return {"error": "Tarayıcı %.0f saniye içinde cevap vermedi." % sure}
        finally:
            with self._kilit:
                self._bekleyen.pop(cid, None)

    def cevap_yaz(self, mesaj):
        """Karşı taraftan gelen cevabı bekleyen isteğe teslim eder."""
        if not isinstance(mesaj, dict):
            return
        with self._kilit:
            kutu = self._bekleyen.get(mesaj.get("id"))
        if kutu is not None and not kutu.done():
            kutu.set_result(mesaj)

    def kapat(self):
        """Bağlantı kapanışı: bekleyen istekleri açık hatayla çözer."""
        with self._kilit:
            self.kapandi = True
            bekleyenler = list(self._bekleyen.values())
            self._bekleyen.clear()
        for kutu in bekleyenler:
            if not kutu.done():
                kutu.set_result({"error": "Tarayıcı bağlantısı kapandı."})
