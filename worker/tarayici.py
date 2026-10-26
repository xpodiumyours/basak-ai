"""Gerçek Chromium üzerinde tek adım yürütücü.

Bu sınıf KARAR VERMEZ. Her adım, Başak'ın ürettiği ve kullanıcının
onayladığı HMAC belgesiyle gelir. Belge eylem türüne, kaynağa ve
argüman özetine bağlıdır; tek kullanımlıktır.

Oturumlar `kosu_id` başına ayrı tarayıcı bağlamıdır: çerezler başka
koşuya sızmaz. Süreç yeniden başlarsa oturum kaybolur; koşu defteri
kaldığı adımdan devam kararını verir.
"""

import asyncio
import base64
import logging
import os
import time

from playwright.async_api import (
    Error as PwHatasi,
    TimeoutError as PwZamanAsimi,
    async_playwright,
)

from worker.guvenlik import (
    TekKullanim,
    TokenHatasi,
    guvenli_url,
    token_dogrula,
)
from worker.hatalar import TarayiciHatasi

logger = logging.getLogger(__name__)

EYLEMLER = ("ac", "oku", "tikla", "yaz", "ekran", "dogrula")

_EN_FAZLA_METIN = 20_000
_VARSAYILAN_METIN = 8_000
_EN_FAZLA_EKRAN = 2_500_000
_EN_FAZLA_YAZI = 10_000


def _kisa(metin, sinir=500):
    metin = str(metin or "")
    return metin if len(metin) <= sinir else metin[:sinir] + "..."


class BulutTarayici:
    """Tek işçi süreci için Playwright oturum yöneticisi."""

    def __init__(self, anahtar, *, guvenlik=True, zaman_asimi_ms=15_000,
                 azami_oturum=3, oturum_suresi=300, nonce_defteri=None):
        if not str(anahtar or ""):
            raise TokenHatasi("işçi anahtarı yok")
        self._anahtar = str(anahtar)
        self._guvenlik = bool(guvenlik)
        self._zaman = max(1_000, int(zaman_asimi_ms))
        self._azami = max(1, int(azami_oturum))
        self._oturum_suresi = max(30, int(oturum_suresi))
        # İşçi yeniden başlarsa süreç içi defter kaybolur; kalıcı kuyruk
        # adaptörü verilirse aynı belge ikinci kez çalışmaz.
        self._tek = nonce_defteri if nonce_defteri is not None else TekKullanim()
        self._oturumlar = {}
        self._kilit = asyncio.Lock()
        self._basla_kilit = asyncio.Lock()
        self._pw = None
        self._browser = None

    # ── yaşam döngüsü ────────────────────────────────────────────────

    async def basla(self):
        if self._browser is not None:
            return
        async with self._basla_kilit:
            if self._browser is not None:
                return
            self._pw = await async_playwright().start()
            argumanlar = ["--disable-dev-shm-usage"]
            # Konteynerde root ise Chromium sandbox'ı açılmaz. İzolasyon
            # konteyner sınırına dayanır; üretimde non-root kullanılmalı.
            if hasattr(os, "geteuid") and os.geteuid() == 0:
                argumanlar.append("--no-sandbox")
            self._browser = await self._pw.chromium.launch(
                headless=True, args=argumanlar)

    async def kapat(self):
        async with self._kilit:
            oturumlar = list(self._oturumlar.values())
            self._oturumlar.clear()
        for oturum in oturumlar:
            try:
                await oturum["context"].close()
            except PwHatasi:
                logger.debug("tarayıcı bağlamı kapanmadı", exc_info=True)
        if self._browser is not None:
            try:
                await self._browser.close()
            except PwHatasi:
                logger.debug("tarayıcı kapanmadı", exc_info=True)
            self._browser = None
        if self._pw is not None:
            try:
                await self._pw.stop()
            except PwHatasi:
                logger.debug("playwright durmadı", exc_info=True)
            self._pw = None

    async def __aenter__(self):
        await self.basla()
        return self

    async def __aexit__(self, *args):
        await self.kapat()

    # ── oturum ───────────────────────────────────────────────────────

    async def _temizle(self):
        an = time.monotonic()
        kapanacak = []
        async with self._kilit:
            for kosu_id, oturum in list(self._oturumlar.items()):
                if an - oturum["son"] > self._oturum_suresi:
                    self._oturumlar.pop(kosu_id, None)
                    kapanacak.append(oturum["context"])
        # Bağlam kapatma kilidin dışında: kapanış beklerken yeni adım
        # alınmasını engellemeyiz.
        for context in kapanacak:
            try:
                await context.close()
            except PwHatasi:
                logger.debug("eski bağlam kapanmadı", exc_info=True)

    async def _oturum_al(self, kosu_id, olustur=False):
        await self._temizle()
        async with self._kilit:
            oturum = self._oturumlar.get(kosu_id)
            if oturum is not None:
                oturum["son"] = time.monotonic()
                return oturum
            if not olustur:
                return None
            if self._browser is None:
                raise TarayiciHatasi("tarayıcı başlatılmadı")
            while len(self._oturumlar) >= self._azami:
                en_eski = min(
                    self._oturumlar.items(), key=lambda x: x[1]["son"])[0]
                eski = self._oturumlar.pop(en_eski)
                try:
                    await eski["context"].close()
                except PwHatasi:
                    logger.debug("kapasite bağlamı kapanmadı", exc_info=True)
            context = await self._browser.new_context(
                locale="tr-TR",
                viewport={"width": 1280, "height": 720},
                java_script_enabled=True,
            )
            page = await context.new_page()
            oturum = {
                "context": context,
                "page": page,
                "son": time.monotonic(),
                "kilit": asyncio.Lock(),
            }
            self._oturumlar[kosu_id] = oturum
            return oturum

    # ── adım ─────────────────────────────────────────────────────────

    async def adim(self, kosu_id, eylem, token, *, adim_id):
        """Tek onaylı eylemi uygular; sonuç sözlüğü döndürür.

        Belge koşuya, adıma, kaynağa, eyleme ve argüman özetine bağlıdır.
        """
        kosu_id = str(kosu_id or "").strip()
        adim_id = str(adim_id or "").strip()
        if not kosu_id or len(kosu_id) > 96:
            raise TarayiciHatasi("koşu kimliği geçersiz")
        if not adim_id or len(adim_id) > 96:
            raise TarayiciHatasi("adım kimliği geçersiz")
        if not isinstance(eylem, dict):
            raise TarayiciHatasi("eylem sözlük olmalı")
        tur = str(eylem.get("tur") or "").strip().lower()
        if tur not in EYLEMLER:
            raise TarayiciHatasi("bilinmeyen eylem: %s" % _kisa(tur, 40))

        if tur == "ac":
            url = str(eylem.get("url") or "").strip()
            if not url:
                raise TarayiciHatasi("açma eylemi URL ister")
            if self._guvenlik:
                engel = guvenli_url(url)
                if engel:
                    raise TarayiciHatasi("adres engellendi: %s" % engel)
            payload = token_dogrula(
                self._anahtar, token, tur=tur, url=url, argumanlar=eylem,
                kosu_id=kosu_id, adim_id=adim_id)
            if not self._tek.kullan(payload["nonce"], payload["exp"]):
                raise TokenHatasi("onay belgesi daha önce kullanıldı")
            await self.basla()
            oturum = await self._oturum_al(kosu_id, olustur=True)
            async with oturum["kilit"]:
                return await self._ac(oturum, url)

        oturum = await self._oturum_al(kosu_id)
        if oturum is None:
            raise TarayiciHatasi("bu koşu için açık tarayıcı oturumu yok")
        async with oturum["kilit"]:
            url = oturum["page"].url
            payload = token_dogrula(
                self._anahtar, token, tur=tur, url=url, argumanlar=eylem,
                kosu_id=kosu_id, adim_id=adim_id)
            if not self._tek.kullan(payload["nonce"], payload["exp"]):
                raise TokenHatasi("onay belgesi daha önce kullanıldı")
            return await self._calistir(oturum["page"], tur, eylem)

    async def _ac(self, oturum, url):
        page = oturum["page"]
        try:
            yanit = await page.goto(
                url, wait_until="domcontentloaded", timeout=self._zaman)
        except PwZamanAsimi as hata:
            raise TarayiciHatasi("sayfa zaman aşımına uğradı") from hata
        except PwHatasi as hata:
            raise TarayiciHatasi("sayfa açılamadı: %s" % _kisa(hata)) from hata
        if self._guvenlik:
            engel = guvenli_url(page.url)
            if engel:
                await page.goto("about:blank")
                raise TarayiciHatasi(
                    "yönlendirme güvenli değil: %s" % engel)
        return {
            "ok": True,
            "tur": "ac",
            "url": page.url,
            "baslik": await self._baslik(page),
            "durum": getattr(yanit, "status", None),
        }

    async def _calistir(self, page, tur, eylem):
        if tur == "oku":
            return await self._oku(page, eylem)
        if tur == "tikla":
            return await self._tikla(page, eylem)
        if tur == "yaz":
            return await self._yaz(page, eylem)
        if tur == "ekran":
            return await self._ekran(page)
        if tur == "dogrula":
            return await self._dogrula(page, eylem)
        raise TarayiciHatasi("bilinmeyen eylem: %s" % tur)

    async def _baslik(self, page):
        try:
            return _kisa(await page.title(), 300)
        except PwHatasi:
            return ""

    async def _oku(self, page, eylem):
        secici = str(eylem.get("secici") or "body")
        try:
            sinir = int(eylem.get("azami_karakter") or _VARSAYILAN_METIN)
        except (TypeError, ValueError):
            sinir = _VARSAYILAN_METIN
        sinir = max(200, min(sinir, _EN_FAZLA_METIN))
        try:
            metin = await page.inner_text(secici, timeout=self._zaman)
        except PwZamanAsimi as hata:
            raise TarayiciHatasi("okuma zaman aşımı") from hata
        except PwHatasi as hata:
            raise TarayiciHatasi("okuma başarısız: %s" % _kisa(hata)) from hata
        kirpildi = len(metin) > sinir
        return {
            "ok": True,
            "tur": "oku",
            "url": page.url,
            "baslik": await self._baslik(page),
            "metin": metin[:sinir],
            "kirpildi": kirpildi,
            "uzunluk": len(metin),
        }

    async def _tikla(self, page, eylem):
        secici = str(eylem.get("secici") or "").strip()
        if not secici:
            raise TarayiciHatasi("tıklama seçici ister")
        try:
            await page.click(secici, timeout=self._zaman)
            try:
                await page.wait_for_load_state(
                    "domcontentloaded", timeout=3_000)
            except PwZamanAsimi:
                logger.debug(
                    "tıklama sonrası yükleme durumu beklenmedi", exc_info=True)
        except PwZamanAsimi as hata:
            raise TarayiciHatasi("tıklama zaman aşımı") from hata
        except PwHatasi as hata:
            raise TarayiciHatasi("tıklama başarısız: %s" % _kisa(hata)) from hata
        return {
            "ok": True,
            "tur": "tikla",
            "url": page.url,
            "baslik": await self._baslik(page),
        }

    async def _yaz(self, page, eylem):
        secici = str(eylem.get("secici") or "").strip()
        if not secici:
            raise TarayiciHatasi("yazma seçici ister")
        metin = str(eylem.get("metin") or "")
        if len(metin) > _EN_FAZLA_YAZI:
            raise TarayiciHatasi("yazı çok uzun")
        try:
            await page.fill(secici, metin, timeout=self._zaman)
        except PwZamanAsimi as hata:
            raise TarayiciHatasi("yazma zaman aşımı") from hata
        except PwHatasi as hata:
            raise TarayiciHatasi("yazma başarısız: %s" % _kisa(hata)) from hata
        return {
            "ok": True,
            "tur": "yaz",
            "url": page.url,
            "uzunluk": len(metin),
        }

    async def _ekran(self, page):
        try:
            png = await page.screenshot(type="png", full_page=False)
        except PwHatasi as hata:
            raise TarayiciHatasi(
                "ekran görüntüsü alınamadı: %s" % _kisa(hata)) from hata
        if len(png) > _EN_FAZLA_EKRAN:
            raise TarayiciHatasi("ekran görüntüsü çok büyük")
        return {
            "ok": True,
            "tur": "ekran",
            "url": page.url,
            "baslik": await self._baslik(page),
            "png_b64": base64.b64encode(png).decode("ascii"),
            "boyut": len(png),
        }

    async def _dogrula(self, page, eylem):
        secici = str(eylem.get("secici") or "").strip()
        beklenen = str(eylem.get("beklenen") or "")
        if not secici:
            raise TarayiciHatasi("doğrulama seçici ister")
        try:
            gercek = await page.inner_text(secici, timeout=self._zaman)
        except PwZamanAsimi as hata:
            raise TarayiciHatasi("doğrulama zaman aşımı") from hata
        except PwHatasi as hata:
            raise TarayiciHatasi(
                "doğrulama başarısız: %s" % _kisa(hata)) from hata
        tam = bool(eylem.get("tam"))
        ok = (gercek == beklenen) if tam else (beklenen in gercek)
        return {
            "ok": bool(ok),
            "tur": "dogrula",
            "url": page.url,
            "beklenen": _kisa(beklenen, 2_000),
            "gercek": _kisa(gercek, 2_000),
        }
