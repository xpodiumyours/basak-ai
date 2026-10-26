"""chat/kosu_deposu.py — kalıcı koşu defteri (uzun iş).

Neden bu dosya: Vercel fonksiyonu 300 saniyede kesiliyor ve
`chat/agent_runtime.AgentRunState.pause()` yalnız bellekteki durumu
işaretliyordu; koşunun gerçek kaydı istemcinin taşıdığı imzalı handoff'ta
duruyordu. İstemci kapanınca iş kayboluyordu. Burada koşu ve koşunun her
araç adımı kalıcı bir deftere yazılır: hangi araç, hangi argüman, hangi
sonuç, kaçıncı tur. Kopan koşu aynı kimlikle kaldığı yerden sürdürülür.

Kural (AGENTS.md §0): bu modül KARAR VERMEZ. Hangi aracın koşacağını,
hangi sağlayıcının seçileceğini, cevabın ne olacağını model belirler.
Burada yalnız kayıt, tekrar koruması ve devam paketi üretimi vardır;
kullanıcı metni okunmaz, kelime eşleştirilmesi yapılmaz, sonuç kırpılmaz.

Depolama:
- `DATABASE_URL` / `POSTGRES_URL` / `NEON_DATABASE_URL` varsa Postgres
  (üretim yolu; Neon).
- Yoksa ve üretimde değilsek yerel SQLite (`<state>/kosular.db`) —
  masaüstünde gerçekten kalıcı.
- Üretimde DSN yoksa defter AÇILMAZ (`hazir()` False) ve çağıran taraf
  bunu bilir. Geçici diske yazıp "kalıcı" demek yalan olurdu.

Kimlik: her koşu bir `run_id` taşır; adımlar `(kosu_id, cagri_id)` ile
tektir. Aynı çağrı kimliği ikinci kez geldiğinde satır EZİLMEZ, ilk
sonuç döner — yeniden deneme tıklamayı iki kez çalıştırmaz.
"""

import datetime
import json
import logging
import os
import sqlite3
import tempfile
import threading
import time
import uuid

try:
    from worker.kuyruk import (
        IS_TABLO as ISCI_IS_TABLO,
        KALP_TABLO as ISCI_KALP_TABLO,
    )
except Exception:  # pragma: no cover — worker paketi yoksa adlar sabit
    ISCI_IS_TABLO = "basak_isci_is"
    ISCI_KALP_TABLO = "basak_isci_kalp"

logger = logging.getLogger(__name__)

KOSU_TABLO = "basak_kosu"
ADIM_TABLO = "basak_kosu_adim"

DURUMLAR = ("running", "paused", "completed", "error")

_DEPO = None
_DEPO_KILIT = threading.Lock()
_UYARI_VERILDI = False


def _dsn():
    """Kalıcı defterin DSN'i; yoksa bos metin."""
    if (os.environ.get("VERCEL_ENV") or "").strip().lower() == "preview":
        ozel = (os.environ.get("BASAK_PREVIEW_DATABASE_URL") or "").strip()
        if ozel:
            return ozel
    for ad in ("DATABASE_URL", "POSTGRES_URL", "NEON_DATABASE_URL"):
        deger = (os.environ.get(ad) or "").strip()
        if deger:
            return deger
    return ""


def _uretim_mi():
    return bool(os.environ.get("VERCEL") or os.environ.get("BASAK_URETIM"))


def _dizin():
    """Yerel defterin dizini (BASAK_STATE_DIR ya da gecici dizin)."""
    kok = (os.environ.get("BASAK_STATE_DIR") or "").strip()
    if not kok:
        kok = os.path.join(tempfile.gettempdir(), "basak")
    os.makedirs(kok, exist_ok=True)
    return kok


def _simdi():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _iso_z(an):
    """Epoch saniyeyi okunur UTC damgasına çevirir; bozuksa boş döner."""
    try:
        return datetime.datetime.fromtimestamp(
            float(an), datetime.timezone.utc).isoformat().replace(
                "+00:00", "Z")
    except (TypeError, ValueError, OverflowError, OSError):
        return ""


def _json_yaz(deger):
    try:
        return json.dumps(deger if deger is not None else {},
                          ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return json.dumps({})


def _json_oku(metin, varsayilan=None):
    if not metin:
        return varsayilan
    try:
        return json.loads(metin)
    except (TypeError, ValueError):
        # Bozuk kayit sessizce yutulmaz: cagiran taraf "devam yok" gorur,
        # uydurma bir gecmis kurulmaz.
        logger.warning("kosu defterindeki JSON cozulemedi", exc_info=True)
        return varsayilan


# ── Depo arka uclari ─────────────────────────────────────────────────
#
# SQL tek bicimde yazilir (`%s` yer tutucu); SQLite ucu bunu `?`ye cevirir.
# Zaman damgalari her yerde Python'dan ISO metin olarak gecilir; Postgres
# TIMESTAMPTZ'ye kendisi cevirir, SQLite metin saklar. Boylece iki ucu
# ayri ayri yazmak yerine tek sorgu govdesi kalir.

class _Depo:
    ad = ""

    def __init__(self):
        self._kilit = threading.Lock()
        self._hazirla()

    # — alt siniflar doldurur —
    def _hazirla(self):
        raise NotImplementedError

    def _calistir(self, sql, params=()):
        raise NotImplementedError

    def _sorgu(self, sql, params=()):
        raise NotImplementedError

    # — ortak isler —
    def kosu_ekle(self, satir):
        self._calistir(
            "INSERT INTO %s (id, kullanici, istek, durum, tool_policy, "
            "saglayici, adim, olustu, guncelleme) "
            "VALUES (%%s, %%s, %%s, %%s, %%s, '', 0, %%s, %%s)"
            % KOSU_TABLO,
            (satir["id"], satir["kullanici"], satir["istek"],
             satir["durum"], satir["tool_policy"],
             satir["olustu"], satir["guncelleme"]),
        )
        return self.kosu_oku(satir["id"])

    def kosu_oku(self, kosu_id):
        satirlar = self._sorgu(
            "SELECT * FROM %s WHERE id = %%s" % KOSU_TABLO, (kosu_id,))
        return satirlar[0] if satirlar else None

    def kosu_guncelle(self, kosu_id, alanlar):
        if not alanlar:
            return
        parcalar = ", ".join("%s = %%s" % ad for ad in alanlar)
        degerler = list(alanlar.values()) + [_simdi(), kosu_id]
        self._calistir(
            "UPDATE %s SET %s, guncelleme = %%s WHERE id = %%s"
            % (KOSU_TABLO, parcalar),
            tuple(degerler),
        )

    def adim_oku(self, kosu_id, cagri_id):
        satirlar = self._sorgu(
            "SELECT * FROM %s WHERE kosu_id = %%s AND cagri_id = %%s"
            % ADIM_TABLO, (kosu_id, cagri_id))
        return satirlar[0] if satirlar else None

    def adim_ekle(self, kosu_id, arac, cagri_id, argumanlar, tur):
        """Sırayı SQL içinde üretir: iki eşzamanlı adım aynı sırayı almaz."""
        simdi = _simdi()
        self._calistir(
            "INSERT INTO %s (kosu_id, sira, arac, cagri_id, argumanlar, "
            "ok, tur, olustu, guncelleme) "
            "SELECT %%s, COALESCE(MAX(sira), -1) + 1, %%s, %%s, %%s, "
            "%%s, %%s, %%s, %%s FROM %s WHERE kosu_id = %%s "
            "ON CONFLICT (kosu_id, cagri_id) DO NOTHING"
            % (ADIM_TABLO, ADIM_TABLO),
            (kosu_id, arac, cagri_id, _json_yaz(argumanlar),
             False, int(tur or 0), simdi, simdi, kosu_id),
        )

    def adim_bitir(self, kosu_id, cagri_id, sonuc, ok, hata=""):
        """Adımı bir kez kapatır; kapanmış adım EZİLMEZ.

        Tek koşullu UPDATE: `sonuc IS NULL` değilse satır zaten kapalıdır
        ve ikinci yazım yoktur. Adım sayacı yalnız gerçekten kapanan
        adımda artar.
        """
        etkilenen = self._calistir(
            "UPDATE %s SET sonuc = %%s, ok = %%s, hata = %%s, "
            "guncelleme = %%s WHERE kosu_id = %%s AND cagri_id = %%s "
            "AND sonuc IS NULL" % ADIM_TABLO,
            (str(sonuc if sonuc is not None else ""), bool(ok),
             str(hata or ""), _simdi(), kosu_id, cagri_id),
        )
        if not etkilenen:
            return False
        # Kosunun guncelleme damgasi da ilerler: "saatlerdir sessiz kosu"
        # sorusu tek yerden (kosu satirindan) cevaplanabilsin.
        self._calistir(
            "UPDATE %s SET adim = adim + 1, guncelleme = %%s WHERE id = %%s"
            % KOSU_TABLO,
            (_simdi(), kosu_id),
        )
        return True

    def adimlar(self, kosu_id):
        return self._sorgu(
            "SELECT * FROM %s WHERE kosu_id = %%s ORDER BY sira, id"
            % ADIM_TABLO, (kosu_id,))

    def son_kosular(self, kullanici, adet=10):
        try:
            adet = max(1, min(50, int(adet)))
        except (TypeError, ValueError):
            adet = 10
        return self._sorgu(
            "SELECT * FROM %s WHERE kullanici = %%s "
            "ORDER BY guncelleme DESC LIMIT %d" % (KOSU_TABLO, adet),
            (kullanici,),
        )

    def isci_ozeti(self, an, esik):
        """İşçi kuyruğunun salt-okunur özeti.

        Tablolar işçi ilk kez başladığında oluşur; yoksa çağıran taraf
        hatayı yakalar ve "kuyruk kapalı" der. Burada yazma YOKTUR.
        """
        sayilar = self._sorgu(
            "SELECT durum, COUNT(*) AS adet FROM %s GROUP BY durum"
            % ISCI_IS_TABLO)
        isciler = self._sorgu(
            "SELECT isci, basladi, son, durum, surum, is_id FROM %s "
            "WHERE son >= %%s ORDER BY isci" % ISCI_KALP_TABLO,
            (float(an) - float(esik),))
        return {"sayilar": sayilar, "isciler": isciler}


class _SqliteDepo(_Depo):
    ad = "sqlite"

    def __init__(self, yol):
        self._yol = yol
        super().__init__()

    def _baglan(self):
        conn = sqlite3.connect(self._yol, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _hazirla(self):
        with self._baglan() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS %s ("
                "id TEXT PRIMARY KEY, kullanici TEXT NOT NULL, "
                "istek TEXT NOT NULL DEFAULT '', "
                "durum TEXT NOT NULL DEFAULT 'running', "
                "tool_policy TEXT NOT NULL DEFAULT 'auto', "
                "saglayici TEXT NOT NULL DEFAULT '', "
                "adim INTEGER NOT NULL DEFAULT 0, devam TEXT, "
                "cevap TEXT, hata TEXT, "
                "olustu TEXT NOT NULL, guncelleme TEXT NOT NULL, "
                "bitis TEXT)" % KOSU_TABLO)
            conn.execute(
                "CREATE TABLE IF NOT EXISTS %s ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "kosu_id TEXT NOT NULL, sira INTEGER NOT NULL, "
                "arac TEXT NOT NULL, cagri_id TEXT NOT NULL, "
                "argumanlar TEXT NOT NULL DEFAULT '{}', sonuc TEXT, "
                "ok INTEGER NOT NULL DEFAULT 0, hata TEXT, "
                "tur INTEGER NOT NULL DEFAULT 0, "
                "olustu TEXT NOT NULL, guncelleme TEXT NOT NULL, "
                "UNIQUE (kosu_id, cagri_id))" % ADIM_TABLO)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS basak_kosu_kisi "
                "ON %s (kullanici, guncelleme)" % KOSU_TABLO)

    def _calistir(self, sql, params=()):
        with self._kilit, self._baglan() as conn:
            imlec = conn.execute(sql.replace("%s", "?"), params)
            return imlec.rowcount

    def _sorgu(self, sql, params=()):
        with self._kilit, self._baglan() as conn:
            imlec = conn.execute(sql.replace("%s", "?"), params)
            return [dict(satir) for satir in imlec.fetchall()]


class _PostgresDepo(_Depo):
    ad = "postgres"

    def __init__(self, dsn):
        try:
            import psycopg
        except ImportError as e:
            raise RuntimeError("psycopg kurulu degil") from e
        self._psycopg = psycopg
        self._dsn = dsn
        super().__init__()

    def _baglan(self):
        conn = self._psycopg.connect(
            self._dsn, autocommit=True, connect_timeout=10)
        try:
            conn.prepare_threshold = None
        except Exception:
            logger.debug("kosu defteri prepare_threshold ayarlanamadi",
                         exc_info=True)
        return conn

    def _hazirla(self):
        with self._baglan() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS %s ("
                    "id TEXT PRIMARY KEY, kullanici TEXT NOT NULL, "
                    "istek TEXT NOT NULL DEFAULT '', "
                    "durum TEXT NOT NULL DEFAULT 'running', "
                    "tool_policy TEXT NOT NULL DEFAULT 'auto', "
                    "saglayici TEXT NOT NULL DEFAULT '', "
                    "adim INTEGER NOT NULL DEFAULT 0, devam TEXT, "
                    "cevap TEXT, hata TEXT, "
                    "olustu TIMESTAMPTZ NOT NULL, "
                    "guncelleme TIMESTAMPTZ NOT NULL, bitis TIMESTAMPTZ)"
                    % KOSU_TABLO)
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS %s ("
                    "id BIGSERIAL PRIMARY KEY, "
                    "kosu_id TEXT NOT NULL REFERENCES %s(id) "
                    "ON DELETE CASCADE, "
                    "sira INTEGER NOT NULL, arac TEXT NOT NULL, "
                    "cagri_id TEXT NOT NULL, "
                    "argumanlar TEXT NOT NULL DEFAULT '{}', sonuc TEXT, "
                    "ok BOOLEAN NOT NULL DEFAULT FALSE, hata TEXT, "
                    "tur INTEGER NOT NULL DEFAULT 0, "
                    "olustu TIMESTAMPTZ NOT NULL, "
                    "guncelleme TIMESTAMPTZ NOT NULL, "
                    "UNIQUE (kosu_id, cagri_id))"
                    % (ADIM_TABLO, KOSU_TABLO))
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS basak_kosu_kisi "
                    "ON %s (kullanici, guncelleme DESC)" % KOSU_TABLO)

    def _calistir(self, sql, params=()):
        with self._kilit, self._baglan() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.rowcount

    def _sorgu(self, sql, params=()):
        with self._kilit, self._baglan() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                adlar = [d[0] for d in (cur.description or ())]
                return [dict(zip(adlar, satir)) for satir in cur.fetchall()]


def _depo():
    """Defteri (tek kez) kurar; kurulanıyorsa None."""
    global _DEPO, _UYARI_VERILDI
    with _DEPO_KILIT:
        if _DEPO is not None:
            return _DEPO
        dsn = _dsn()
        try:
            if dsn:
                _DEPO = _PostgresDepo(dsn)
            elif _uretim_mi():
                if not _UYARI_VERILDI:
                    _UYARI_VERILDI = True
                    logger.warning(
                        "Kalici kosu defteri kapali: uretimde DSN yok "
                        "(DATABASE_URL). Kosular yalniz istek omrunde yasar.")
                return None
            else:
                _DEPO = _SqliteDepo(os.path.join(_dizin(), "kosular.db"))
        except Exception:
            if not _UYARI_VERILDI:
                _UYARI_VERILDI = True
                logger.warning("Kosu defteri acilamadi; kosular kalici degil",
                               exc_info=True)
            _DEPO = None
        return _DEPO


def hazir():
    """Kalıcı defter kullanılabilir mi?"""
    return _depo() is not None


def sifirla():
    """Yalnız testler için: defteri ve uyarı bayrağını sıfırlar."""
    global _DEPO, _UYARI_VERILDI
    with _DEPO_KILIT:
        _DEPO = None
        _UYARI_VERILDI = False


def isci_durumu(esik=90.0, simdi=None):
    """Canlı bulut işçisi var mı? (salt-okunur)

    `checkpoint_resume` için tek kanıt budur: koşu defteri tek başına
    "yarım iş sürdürülebilir" demek yetmez. İşçi heartbeat'i yoksa iş
    kuyrukta bekler, ama kimse çalıştırmaz. Ekran bu ayrımı yazar.

    Kuyruk tabloları işçi hiç çalışmadıysa yoktur; bu durum hata değil,
    "işçi kuyruğu kapalı" bilgisidir.
    """
    an = float(time.time() if simdi is None else simdi)
    try:
        esik = max(1.0, float(esik))
    except (TypeError, ValueError):
        esik = 90.0
    bos = {
        "hazir": False,
        "canli": 0,
        "isciler": [],
        "kuyruk": {
            "bekliyor": 0, "calisiyor": 0, "bitti": 0,
            "hata": 0, "supheli": 0,
        },
        "son_kalp": "",
        "son_kalp_yas_sn": None,
        "esik_sn": esik,
        "neden": "",
    }
    depo = _depo()
    if depo is None:
        bos["neden"] = "koşu defteri kapalı (DSN yok)"
        return bos
    try:
        veri = depo.isci_ozeti(an, esik)
    except Exception:
        logger.debug("işçi kuyruğu okunamadı", exc_info=True)
        bos["neden"] = "işçi kuyruğu tablosu yok"
        return bos

    sayilar = dict(bos["kuyruk"])
    for satir in veri.get("sayilar") or []:
        ad = str(satir.get("durum") or "")
        if ad in sayilar:
            try:
                sayilar[ad] = int(satir.get("adet") or 0)
            except (TypeError, ValueError):
                sayilar[ad] = 0

    isciler = []
    son_kalp = None
    for satir in veri.get("isciler") or []:
        son = satir.get("son")
        isciler.append({
            "isci": str(satir.get("isci") or ""),
            "durum": str(satir.get("durum") or ""),
            "surum": str(satir.get("surum") or ""),
            "is": str(satir.get("is_id") or ""),
            "basladi": _iso_z(satir.get("basladi")),
            "son": _iso_z(son),
            "yas_sn": (None if son is None
                       else max(0, round(an - float(son)))),
        })
        try:
            if son is not None and (son_kalp is None or float(son) > son_kalp):
                son_kalp = float(son)
        except (TypeError, ValueError):
            logger.debug("kalp zamanı çözülemedi: %r", son)

    return {
        "hazir": True,
        "canli": len(isciler),
        "isciler": isciler,
        "kuyruk": sayilar,
        "son_kalp": _iso_z(son_kalp),
        "son_kalp_yas_sn": (None if son_kalp is None
                            else max(0, round(an - son_kalp))),
        "esik_sn": esik,
        "neden": "",
    }


class Kosu:
    """Tek bir koşunun defter tutamacı."""

    def __init__(self, depo, satir):
        self._depo = depo
        self._satir = dict(satir or {})
        self._kilit = threading.Lock()

    # — okuma —
    @property
    def id(self):
        return str(self._satir.get("id") or "")

    @property
    def kullanici(self):
        return str(self._satir.get("kullanici") or "")

    @property
    def durum(self):
        return str(self._satir.get("durum") or "")

    @property
    def istek(self):
        return str(self._satir.get("istek") or "")

    def tazele(self):
        satir = self._depo.kosu_oku(self.id)
        if satir:
            self._satir = dict(satir)
        return self

    def adimlar(self):
        return self._depo.adimlar(self.id)

    def adim_onceki(self, cagri_id):
        """Bu çağrı daha önce kapandıysa sonucunu döner (tekrar koruması)."""
        satir = self._depo.adim_oku(self.id, str(cagri_id or ""))
        if satir is None or satir.get("sonuc") is None:
            return None
        return {
            "arac": str(satir.get("arac") or ""),
            "sonuc": str(satir.get("sonuc") or ""),
            "ok": bool(satir.get("ok")),
        }

    # — yazma —
    def adim_basla(self, arac, cagri_id, args=None, tur=0):
        with self._kilit:
            self._depo.adim_ekle(
                self.id, str(arac or ""), str(cagri_id or ""),
                args or {}, tur)
        return self

    def adim_bitti(self, arac, cagri_id, sonuc, ok, hata=""):
        with self._kilit:
            kapandi = self._depo.adim_bitir(
                self.id, str(cagri_id or ""), sonuc, ok, hata)
        if kapandi:
            self._satir["adim"] = int(self._satir.get("adim") or 0) + 1
        return kapandi

    def saglayici(self, ad):
        ad = str(ad or "").strip()
        if ad and ad != str(self._satir.get("saglayici") or ""):
            self._depo.kosu_guncelle(self.id, {"saglayici": ad})
            self._satir["saglayici"] = ad

    def duraklat(self, devam=None):
        paket = devam if devam is not None else self.devam_paketi()
        self._depo.kosu_guncelle(self.id, {
            "durum": "paused",
            "devam": _json_yaz(paket),
        })
        self._satir["durum"] = "paused"
        self._satir["devam"] = _json_yaz(paket)
        return self

    def devam_et(self):
        self._depo.kosu_guncelle(self.id, {"durum": "running"})
        self._satir["durum"] = "running"
        return self

    def bitir(self, durum="completed", cevap=None, hata=""):
        durum = durum if durum in DURUMLAR else "error"
        alanlar = {"durum": durum, "bitis": _simdi()}
        if cevap is not None:
            alanlar["cevap"] = str(cevap)
        if hata:
            alanlar["hata"] = str(hata)
        self._depo.kosu_guncelle(self.id, alanlar)
        self._satir.update(alanlar)
        return self

    # — devam —
    def devam_paketi(self):
        """Cekirdegin `yonlendirme_baglami` olarak kabul ettigi paket.

        Bicim, istemcinin tasidigi imzali handoff ile AYNIDIR
        (`p2-handoff-v1`): runContext + toolDone olaylari. Boylece devam
        yolu tek: ister istemci imzali paketle gelsin, ister kosu kimligiyle.
        """
        olaylar = [{
            "tur": "runContext",
            "istek": self.id,
            "metin": self.istek,
            "tool_policy": str(self._satir.get("tool_policy") or "auto"),
        }]
        for satir in self.adimlar():
            if satir.get("sonuc") is None:
                continue
            olaylar.append({
                "tur": "toolDone",
                "istek": self.id,
                "id": str(satir.get("cagri_id") or ""),
                "name": str(satir.get("arac") or ""),
                "args": _json_oku(satir.get("argumanlar"), {}) or {},
                "result": str(satir.get("sonuc") or ""),
                "turn": int(satir.get("tur") or 0),
                "ok": bool(satir.get("ok")),
            })
        return {
            "schema": "p2-handoff-v1",
            "onceki_run": self.id,
            "olaylar": olaylar,
        }

    def kayitli_devam(self):
        return _json_oku(self._satir.get("devam"), None)

    def ozet(self):
        satirlar = self.adimlar()
        return {
            "kosu_id": self.id,
            "durum": self.durum,
            "istek": self.istek,
            "saglayici": str(self._satir.get("saglayici") or ""),
            "adim": int(self._satir.get("adim") or 0),
            "araclar": [str(s.get("arac") or "") for s in satirlar],
            "olustu": str(self._satir.get("olustu") or ""),
            "guncelleme": str(self._satir.get("guncelleme") or ""),
            "cevap": str(self._satir.get("cevap") or ""),
            "hata": str(self._satir.get("hata") or ""),
            "devam_var": self.kayitli_devam() is not None,
        }


def ac(kullanici, istek, run_id=None, tool_policy="auto"):
    """Yeni koşu açar (aynı kimlik varsa onu döner).

    Aynı `run_id` ile ikinci kez gelinirse satır YENİDEN YARATILMAZ;
    mevcut koşu döner. Böylece yeniden denenen istek geçmişi ikiye katlamaz.
    """
    depo = _depo()
    if depo is None:
        return None
    kimlik = str(run_id or "").strip() or uuid.uuid4().hex[:12]
    mevcut = depo.kosu_oku(kimlik)
    if mevcut is not None:
        if str(mevcut.get("kullanici") or "") == str(kullanici):
            return Kosu(depo, mevcut)
        # Ayni kimlik baskasinin kosusuna denk geldi: satir KULLANILMAZ.
        logger.warning("Kosu kimligi baska kullaniciya ait; yenisi uretildi")
        kimlik = uuid.uuid4().hex[:12]
    simdi = _simdi()
    satir = depo.kosu_ekle({
        "id": kimlik,
        "kullanici": str(kullanici or "casper").strip() or "casper",
        "istek": str(istek or ""),
        "durum": "running",
        "tool_policy": str(tool_policy or "auto"),
        "olustu": simdi,
        "guncelleme": simdi,
    })
    return Kosu(depo, satir) if satir else None


def yukle(kosu_id, kullanici=None):
    """Koşuyu yükler; başka kullanıcının koşusu DÖNMEZ."""
    depo = _depo()
    kimlik = str(kosu_id or "").strip()
    if depo is None or not kimlik:
        return None
    satir = depo.kosu_oku(kimlik)
    if satir is None:
        return None
    if kullanici is not None and str(satir.get("kullanici") or "") != str(
            kullanici):
        logger.warning("Baska kullanicinin kosusu istendi: %s", kimlik)
        return None
    return Kosu(depo, satir)


def son_kosular(kullanici, adet=10):
    depo = _depo()
    if depo is None:
        return []
    return [Kosu(depo, satir) for satir in depo.son_kosular(kullanici, adet)]


def bekleyen(kullanici):
    """Devam tetigi bekleyen kosu; yoksa None.

    Yalniz `paused` kosu doner. `running` kosuya DOKUNULMAZ: "running"
    iki ayri seyi anlatir — su an gercekten calisan istek ve kullanicinin
    durdurduğu (istegi kesilen) kosu. Ikincisini kendiliginden surdurmek
    kullanicinin "Durdur"una ragmen is yapmak olurdu. Kesilen kosuyu
    kullanici arayuzdeki "Devam et" ile surdurur.

    Tikin kendisi BURADA yapilmaz: hangi isin surdurulecegine model karar
    verir; burada yalniz `kosu_id` tasinir.
    """
    depo = _depo()
    if depo is None:
        return None
    kullanici = str(kullanici or "")
    if not kullanici or kullanici == "misafir":
        return None
    for satir in depo.son_kosular(kullanici, 20):
        if str(satir.get("durum") or "") == "paused":
            return Kosu(depo, satir)
    return None
