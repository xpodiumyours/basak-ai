"""tools/kutu.py — web sohbeti ile eklenti arasindaki paylasimli kutu (P6b).

Neden: web sohbeti baska bir sunucu instance'inda kosarken eklenti
baska instance'a baglidir; dogrudan soket yoktur. Kutu Postgres'te
durur: web turu isi birakir, eklenti WS uzerinden yoklayip alir,
sonucu yazar, web turu okur. Yeni servis yok — mevcut DATABASE_URL
kullanilir; DSN yoksa acik hata doner, sessiz bellek dususu YOKTUR
(bellek instance'lar arasi paylasilmaz, uydurma hazirlik olurdu).

Onay kapisi cihazda kalir: eklenti isi mevcut islemYap yolundan
kosar, tiklama/yazma yine panele sorulur (fail-closed).

Hiz: yoklama 3 sn; web tarafi once alinmayi (10 sn), sonra sonucu
bekler. Alinmayan is = eklenti bagli degil/panel kapali → acik hata.
"""

import json
import logging
import os
import threading
import time

logger = logging.getLogger(__name__)

_TABLO = "basak_kutu"
_ALINMA_SURESI = 10.0
_SONUC_SURESI = 150.0
_ARALIK = 1.0


def _dsn():
    if (os.environ.get("VERCEL_ENV") or "").strip().lower() == "preview":
        ozel = (os.environ.get("BASAK_PREVIEW_DATABASE_URL") or "").strip()
        if ozel:
            return ozel
    for ad in ("DATABASE_URL", "POSTGRES_URL", "NEON_DATABASE_URL"):
        deger = (os.environ.get(ad) or "").strip()
        if deger:
            return deger
    return ""


class _BellekDeposu:
    """Yalniz testler icin; uretimde kullanilmaz."""

    def __init__(self):
        self._kilit = threading.Lock()
        self._isler = {}
        self._sayac = 0

    def birak(self, kullanici, islem, veri):
        with self._kilit:
            self._sayac += 1
            kimlik = self._sayac
            self._isler[kimlik] = {
                "id": kimlik, "kullanici": kullanici, "islem": islem,
                "veri": veri, "durum": "bekliyor", "sonuc": None,
                "zaman": time.time(),
            }
            return kimlik

    def alinmayi_bekle(self, kimlik, sure):
        bitis = time.time() + sure
        while time.time() < bitis:
            with self._kilit:
                is_ = self._isler.get(kimlik)
                if is_ is None:
                    return None
                if is_["durum"] != "bekliyor":
                    return True
            time.sleep(0.05)
        with self._kilit:
            is_ = self._isler.get(kimlik)
            return None if is_ is None else is_["durum"] != "bekliyor"

    def sonucu_bekle(self, kimlik, sure):
        bitis = time.time() + sure
        while time.time() < bitis:
            with self._kilit:
                is_ = self._isler.get(kimlik)
                if is_ is None:
                    return None
                if is_["durum"] == "yapildi":
                    return is_["sonuc"]
            time.sleep(0.05)
        with self._kilit:
            is_ = self._isler.get(kimlik)
            if is_ and is_["durum"] == "yapildi":
                return is_["sonuc"]
            return False

    def al(self, kullanici):
        with self._kilit:
            for kimlik in sorted(self._isler):
                is_ = self._isler[kimlik]
                if is_["kullanici"] == kullanici and \
                        is_["durum"] == "bekliyor":
                    is_["durum"] = "alindi"
                    return {"id": kimlik, "islem": is_["islem"],
                            "veri": is_["veri"]}
            return None

    def yaz(self, kimlik, cevap):
        with self._kilit:
            is_ = self._isler.get(kimlik)
            if is_ is None:
                return False
            is_["durum"] = "yapildi"
            is_["sonuc"] = cevap
            return True


_DEPO = None


def _depo():
    global _DEPO
    if _DEPO is not None:
        return _DEPO
    dsn = _dsn()
    if not dsn:
        return None
    _DEPO = _PostgresDeposu(dsn)
    return _DEPO


class _PostgresDeposu:
    def __init__(self, dsn):
        try:
            import psycopg
        except ImportError as e:
            raise RuntimeError("psycopg kurulu degil") from e
        self._psycopg = psycopg
        self._dsn = dsn
        self._hazirla()

    def _baglan(self):
        conn = self._psycopg.connect(
            self._dsn, autocommit=True, connect_timeout=10)
        try:
            conn.prepare_threshold = None
        except Exception:
            logger.debug("kutu prepare_threshold ayarlanamadi",
                         exc_info=True)
        return conn

    def _hazirla(self):
        with self._baglan() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS %s ("
                    "id BIGSERIAL PRIMARY KEY, "
                    "kullanici TEXT NOT NULL, islem TEXT NOT NULL, "
                    "veri TEXT NOT NULL DEFAULT '{}', "
                    "durum TEXT NOT NULL DEFAULT 'bekliyor', "
                    "sonuc TEXT, olustu TIMESTAMPTZ DEFAULT now())"
                    % _TABLO)

    def birak(self, kullanici, islem, veri):
        with self._baglan() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM %s WHERE durum = 'yapildi' "
                    "AND olustu < now() - interval '1 hour'" % _TABLO)
                cur.execute(
                    "DELETE FROM %s WHERE durum = 'bekliyor' "
                    "AND olustu < now() - interval '10 minutes'" % _TABLO)
                cur.execute(
                    "INSERT INTO %s (kullanici, islem, veri) "
                    "VALUES (%%s, %%s, %%s) RETURNING id" % _TABLO,
                    (kullanici, islem, json.dumps(veri or {},
                                                  ensure_ascii=False)))
                return cur.fetchone()[0]

    def alinmayi_bekle(self, kimlik, sure):
        bitis = time.time() + sure
        while time.time() < bitis:
            with self._baglan() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT durum FROM %s WHERE id = %%s" % _TABLO,
                        (kimlik,))
                    satir = cur.fetchone()
            if satir is None:
                return None
            if satir[0] != "bekliyor":
                return True
            time.sleep(_ARALIK)
        return False

    def sonucu_bekle(self, kimlik, sure):
        bitis = time.time() + sure
        while time.time() < bitis:
            with self._baglan() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT durum, sonuc FROM %s WHERE id = %%s"
                        % _TABLO, (kimlik,))
                    satir = cur.fetchone()
            if satir is None:
                return None
            if satir[0] == "yapildi":
                try:
                    return json.loads(satir[1] or "null")
                except (TypeError, ValueError):
                    return {"error": "Kutu sonucu anlasilmadi."}
            time.sleep(_ARALIK)
        return False

    def al(self, kullanici):
        with self._baglan() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE %s SET durum = 'alindi' WHERE id = ("
                    "SELECT id FROM %s WHERE kullanici = %%s "
                    "AND durum = 'bekliyor' ORDER BY id LIMIT 1"
                    ") RETURNING id, islem, veri" % (_TABLO, _TABLO),
                    (kullanici,))
                satir = cur.fetchone()
        if not satir:
            return None
        try:
            veri = json.loads(satir[2] or "{}")
        except (TypeError, ValueError):
            veri = {}
        return {"id": satir[0], "islem": satir[1],
                "veri": veri if isinstance(veri, dict) else {}}

    def yaz(self, kimlik, cevap):
        with self._baglan() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE %s SET durum = 'yapildi', sonuc = %%s "
                    "WHERE id = %%s" % _TABLO,
                    (json.dumps(cevap or {}, ensure_ascii=False), kimlik))
                return cur.rowcount > 0


def birak(kullanici, islem, veri):
    """Isi kutuya birakir; donus is kimligi ya da acik hata."""
    depo = _depo()
    if depo is None:
        return {"error": "Paylasilan kutu kapali (veritabani yok); "
                         "eklenti panelinden surdur."}
    try:
        return {"id": depo.birak(kullanici, islem, veri or {})}
    except Exception as e:
        logger.warning("kutu birakma hatasi: %s", e)
        return {"error": "Is kutuya birakilamadi: %s" % str(e)[:120]}


def sonucu_bekle(kimlik, alinma=_ALINMA_SURESI, sonuc=_SONUC_SURESI):
    """Once alinmayi, sonra sonucu bekler; alinmayan is cevrimdisi demek."""
    depo = _depo()
    if depo is None:
        return {"error": "Paylasilan kutu kapali (veritabani yok)."}
    try:
        alindi = depo.alinmayi_bekle(kimlik, alinma)
    except Exception as e:
        logger.warning("kutu yoklama hatasi: %s", e)
        return {"error": "Kutu yoklanamadi: %s" % str(e)[:120]}
    if alindi is None:
        return {"error": "Is kutuda bulunamadi."}
    if not alindi:
        return {"error": "Eklenti bagli degil ya da panel kapali; "
                         "paneli acip baglan, sonra tekrar dene."}
    try:
        sonuc_veri = depo.sonucu_bekle(kimlik, sonuc)
    except Exception as e:
        logger.warning("kutu sonuc hatasi: %s", e)
        return {"error": "Kutu sonucu okunamadi: %s" % str(e)[:120]}
    if sonuc_veri is None:
        return {"error": "Is kutuda bulunamadi."}
    if sonuc_veri is False:
        return {"error": "Eklenti %.0f saniye icinde sonucu yazmadi." % sonuc}
    return sonuc_veri if isinstance(sonuc_veri, dict) else {
        "error": "Kutu beklenmeyen bicimde cevap verdi."}


def al(kullanici):
    """Kullanicinin en eski bekleyen isini atomik olarak ustlenir."""
    depo = _depo()
    if depo is None:
        return {"error": "Paylasilan kutu kapali (veritabani yok)."}
    try:
        is_ = depo.al(kullanici)
    except Exception as e:
        logger.warning("kutu alma hatasi: %s", e)
        return {"error": "Kutu okunamadi: %s" % str(e)[:120]}
    if not is_:
        return {"bos": True}
    return is_


def yaz(kimlik, cevap):
    """Is sonucunu kutuya yazar."""
    depo = _depo()
    if depo is None:
        return {"error": "Paylasilan kutu kapali (veritabani yok)."}
    try:
        ok = depo.yaz(kimlik, cevap or {})
    except Exception as e:
        logger.warning("kutu yazma hatasi: %s", e)
        return {"error": "Kutuya yazilamadi: %s" % str(e)[:120]}
    if not ok:
        return {"error": "Is kutuda bulunamadi."}
    return {"ok": True}
