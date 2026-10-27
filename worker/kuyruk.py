"""Bulut işçisinin kalıcı iş kuyruğu.

Neden bu dosya: tarayıcı işçisi Vercel'de yaşamaz. Beyin onaylı tek bir
eylemi burada bırakır, işçi onu alır, uygular ve sonucu geri yazar. Kuyruk
Postgres'te tutulur; böylece beyin (Vercel), işçi (Oracle) ve yeniden
başlayan süreç aynı defteri görür. Yerel geliştirmede aynı sözleşme SQLite
üzerinde koşar.

Kural (AGENTS.md §0): bu modül KARAR VERMEZ. Hangi eylemin yapılacağını
Başak'ın beyni ve kullanıcı onayı belirler. Burada yalnız şunlar vardır:

- İşi bırakma (aynı koşu + adım ikinci kez satır yaratmaz).
- Atomik alma: iki işçi aynı işi alamaz (`FOR UPDATE SKIP LOCKED`).
- Bitiş/tekrar/şüpheli işaretleme; kapanmış iş EZİLMEZ.
- Kalıcı nonce: süreç yeniden başlasa da aynı onay belgesi ikinci kez
  çalışmaz.
- Kalp atışı: "canlı işçi var mı" sorusunun tek kanıtı.

Zamanlar epoch saniyedir (REAL / DOUBLE PRECISION). Böylece SQLite ve
Postgres aynı karşılaştırmayı yapar; saat dilimi farkı olmaz.
"""

import json
import logging
import os
import sqlite3
import tempfile
import threading
import time
import uuid

from worker.guvenlik import TokenHatasi, kaynak

logger = logging.getLogger(__name__)

IS_TABLO = "basak_isci_is"
KALP_TABLO = "basak_isci_kalp"
NONCE_TABLO = "basak_isci_nonce"

DURUMLAR = ("bekliyor", "calisiyor", "bitti", "hata", "supheli")

_EN_FAZLA_KIMLIK = 96
_EN_FAZLA_TOKEN = 4_096
_EN_FAZLA_EYLEM = 200_000
_VARSAYILAN_ESIK = 90.0


class KuyrukHatasi(RuntimeError):
    """İş kuyruğu güvenli biçimde kullanılamadı."""


def _simdi(deger=None):
    return float(time.time() if deger is None else deger)


def _iso(an):
    if an is None:
        return ""
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(an)))
    except (TypeError, ValueError, OverflowError):
        return ""


def _kimlik(ad, deger):
    metin = str(deger or "").strip()
    if not metin:
        raise KuyrukHatasi("%s kimliği boş" % ad)
    if len(metin) > _EN_FAZLA_KIMLIK:
        raise KuyrukHatasi("%s kimliği çok uzun" % ad)
    return metin


def _json_yaz(deger, sinir=0):
    try:
        metin = json.dumps(deger, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False)
    except (TypeError, ValueError) as hata:
        raise KuyrukHatasi("iş verisi JSON'a çevrilemedi") from hata
    if sinir and len(metin) > sinir:
        raise KuyrukHatasi("iş verisi çok büyük")
    return metin


def _json_oku(metin, varsayilan=None):
    if not metin:
        return varsayilan
    try:
        return json.loads(metin)
    except (TypeError, ValueError):
        logger.warning("iş kuyruğundaki JSON çözülemedi", exc_info=True)
        return varsayilan


def _dsn():
    if (os.environ.get("VERCEL_ENV") or "").strip().lower() == "preview":
        from chat.kosu_deposu import _dsn as preview_dsn
        return preview_dsn()
    for ad in ("BASAK_ISCI_DATABASE_URL", "DATABASE_URL", "POSTGRES_URL",
               "NEON_DATABASE_URL"):
        deger = (os.environ.get(ad) or "").strip()
        if deger:
            return deger
    return ""


def _state_dizini():
    kok = (os.environ.get("BASAK_STATE_DIR") or "").strip()
    if not kok:
        kok = os.path.join(tempfile.gettempdir(), "basak")
    os.makedirs(kok, exist_ok=True)
    return kok


class _KuyrukDepo:
    ad = ""

    def __init__(self):
        self._kilit = threading.Lock()
        self._hazirla()

    def _hazirla(self):
        raise NotImplementedError

    def _calistir(self, sql, params=()):
        raise NotImplementedError

    def _sorgu(self, sql, params=()):
        raise NotImplementedError

    def _donen(self, sql, params=()):
        raise NotImplementedError

    # — işler —
    def birak(self, kosu_id, adim_id, eylem, token, url, simdi):
        eylem_json = _json_yaz(eylem, _EN_FAZLA_EYLEM)
        token = str(token or "").strip()
        if not token or len(token) > _EN_FAZLA_TOKEN:
            raise KuyrukHatasi("onay belgesi boş ya da çok uzun")
        try:
            kaynak(url)
        except TokenHatasi as hata:
            raise KuyrukHatasi("kaynak adresi geçersiz") from hata
        kimlik = uuid.uuid4().hex
        self._calistir(
            "INSERT INTO %s (id, kosu_id, adim_id, eylem, token, url, "
            "durum, isci, deneme, sonuc, hata, olustu, guncelleme, bitis) "
            "VALUES (%%s, %%s, %%s, %%s, %%s, %%s, 'bekliyor', NULL, 0, "
            "NULL, '', %%s, %%s, NULL) "
            "ON CONFLICT (kosu_id, adim_id) DO NOTHING" % IS_TABLO,
            (kimlik, kosu_id, adim_id, eylem_json, token, str(url),
             simdi, simdi),
        )
        satir = self.adim_oku(kosu_id, adim_id)
        if satir is None:
            raise KuyrukHatasi("iş yazılamadı")
        if str(satir.get("eylem") or "") != eylem_json:
            raise KuyrukHatasi("aynı koşu/adım farklı eylemle bırakıldı")
        # Token süresi dolduğu için beyin aynı bekleyen işe yeni belge
        # verebilir. Çalışan işin belgesi ASLA değiştirilmez.
        if str(satir.get("durum") or "") == "bekliyor" and (
                str(satir.get("token") or "") != token
                or str(satir.get("url") or "") != str(url)):
            self._calistir(
                "UPDATE %s SET token = %%s, url = %%s, guncelleme = %%s "
                "WHERE id = %%s AND durum = 'bekliyor'" % IS_TABLO,
                (token, str(url), simdi, satir["id"]),
            )
            satir = self.adim_oku(kosu_id, adim_id)
        return satir

    def adim_oku(self, kosu_id, adim_id):
        satirlar = self._sorgu(
            "SELECT * FROM %s WHERE kosu_id = %%s AND adim_id = %%s"
            % IS_TABLO, (kosu_id, adim_id))
        return satirlar[0] if satirlar else None

    def oku(self, is_id):
        satirlar = self._sorgu(
            "SELECT * FROM %s WHERE id = %%s" % IS_TABLO, (is_id,))
        return satirlar[0] if satirlar else None

    def bitir(self, is_id, isci, sonuc, hata, simdi):
        durum = "hata" if str(hata or "").strip() else "bitti"
        satirlar = self._donen(
            "UPDATE %s SET durum = %%s, sonuc = %%s, hata = %%s, "
            "bitis = %%s, guncelleme = %%s "
            "WHERE id = %%s AND durum = 'calisiyor' AND isci = %%s "
            "RETURNING *" % IS_TABLO,
            (durum, _json_yaz(sonuc) if sonuc is not None else None,
             str(hata or ""), simdi, simdi, is_id, isci),
        )
        return satirlar[0] if satirlar else None

    def birak_tekrar(self, is_id, isci, hata, azami, simdi):
        try:
            azami = max(1, int(azami))
        except (TypeError, ValueError):
            azami = 1
        satirlar = self._donen(
            "UPDATE %s SET "
            "durum = CASE WHEN deneme >= %%s THEN 'hata' ELSE 'bekliyor' END, "
            "isci = CASE WHEN deneme >= %%s THEN isci ELSE NULL END, "
            "hata = %%s, "
            "bitis = CASE WHEN deneme >= %%s THEN %%s ELSE NULL END, "
            "guncelleme = %%s "
            "WHERE id = %%s AND durum = 'calisiyor' AND isci = %%s "
            "RETURNING *" % IS_TABLO,
            (azami, azami, str(hata or ""), azami, simdi, simdi,
             is_id, isci),
        )
        return satirlar[0] if satirlar else None

    def supheli_yap(self, is_id, isci, hata, simdi):
        satirlar = self._donen(
            "UPDATE %s SET durum = 'supheli', hata = %%s, bitis = %%s, "
            "guncelleme = %%s "
            "WHERE id = %%s AND durum = 'calisiyor' AND isci = %%s "
            "RETURNING *" % IS_TABLO,
            (str(hata or "")[:2_000], simdi, simdi, is_id, isci),
        )
        return satirlar[0] if satirlar else None

    def temizle(self, esik, simdi):
        sinir = simdi - max(1.0, float(esik))
        etkilenen = self._calistir(
            "UPDATE %s SET durum = 'supheli', "
            "hata = CASE WHEN hata = '' THEN %%s ELSE hata || ' | ' || %%s END, "
            "bitis = %%s, guncelleme = %%s "
            "WHERE durum = 'calisiyor' AND guncelleme < %%s "
            "AND (isci IS NULL OR isci NOT IN ("
            "SELECT isci FROM %s WHERE son >= %%s))"
            % (IS_TABLO, KALP_TABLO),
            ("işçi kayboldu", "işçi kayboldu", simdi, simdi, sinir, sinir),
        )
        self._calistir(
            "DELETE FROM %s WHERE bitis < %%s" % NONCE_TABLO, (simdi,))
        return etkilenen

    def kalp(self, isci, durum, surum, is_id, simdi):
        self._calistir(
            "INSERT INTO %s (isci, basladi, son, durum, surum, is_id) "
            "VALUES (%%s, %%s, %%s, %%s, %%s, %%s) "
            "ON CONFLICT (isci) DO UPDATE SET son = EXCLUDED.son, "
            "durum = EXCLUDED.durum, surum = EXCLUDED.surum, "
            "is_id = EXCLUDED.is_id" % KALP_TABLO,
            (isci, simdi, simdi, str(durum or ""), str(surum or ""),
             str(is_id or "")),
        )

    def canli_isciler(self, esik, simdi):
        sinir = simdi - max(1.0, float(esik))
        return self._sorgu(
            "SELECT isci, basladi, son, durum, surum, is_id FROM %s "
            "WHERE son >= %%s ORDER BY isci" % KALP_TABLO, (sinir,))

    def nonce_al(self, nonce, bitis, simdi):
        etkilenen = self._calistir(
            "INSERT INTO %s (nonce, bitis) VALUES (%%s, %%s) "
            "ON CONFLICT (nonce) DO NOTHING" % NONCE_TABLO,
            (nonce, float(bitis or simdi)),
        )
        return bool(etkilenen)

    def sayilar(self):
        satirlar = self._sorgu(
            "SELECT durum, COUNT(*) AS adet FROM %s GROUP BY durum" % IS_TABLO)
        sayilar = {ad: 0 for ad in DURUMLAR}
        for satir in satirlar:
            ad = str(satir.get("durum") or "")
            if ad in sayilar:
                sayilar[ad] = int(satir.get("adet") or 0)
        return sayilar


class _SqliteDepo(_KuyrukDepo):
    ad = "sqlite"

    def __init__(self, yol):
        self._yol = yol
        super().__init__()

    def _baglan(self):
        conn = sqlite3.connect(
            self._yol, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    def _hazirla(self):
        with self._baglan() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS %s ("
                "id TEXT PRIMARY KEY, kosu_id TEXT NOT NULL, "
                "adim_id TEXT NOT NULL, eylem TEXT NOT NULL, "
                "token TEXT NOT NULL, url TEXT NOT NULL, "
                "durum TEXT NOT NULL DEFAULT 'bekliyor', isci TEXT, "
                "deneme INTEGER NOT NULL DEFAULT 0, sonuc TEXT, "
                "hata TEXT NOT NULL DEFAULT '', "
                "olustu REAL NOT NULL, guncelleme REAL NOT NULL, "
                "bitis REAL, UNIQUE (kosu_id, adim_id))" % IS_TABLO)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS basak_isci_is_durum "
                "ON %s (durum, olustu)" % IS_TABLO)
            conn.execute(
                "CREATE TABLE IF NOT EXISTS %s ("
                "isci TEXT PRIMARY KEY, basladi REAL NOT NULL, "
                "son REAL NOT NULL, durum TEXT NOT NULL DEFAULT '', "
                "surum TEXT NOT NULL DEFAULT '', "
                "is_id TEXT NOT NULL DEFAULT '')" % KALP_TABLO)
            conn.execute(
                "CREATE TABLE IF NOT EXISTS %s ("
                "nonce TEXT PRIMARY KEY, bitis REAL NOT NULL)" % NONCE_TABLO)

    def _calistir(self, sql, params=()):
        with self._kilit, self._baglan() as conn:
            imlec = conn.execute(sql.replace("%s", "?"), params)
            return imlec.rowcount

    def _sorgu(self, sql, params=()):
        with self._kilit, self._baglan() as conn:
            imlec = conn.execute(sql.replace("%s", "?"), params)
            return [dict(satir) for satir in imlec.fetchall()]

    def _donen(self, sql, params=()):
        with self._kilit, self._baglan() as conn:
            imlec = conn.execute(sql.replace("%s", "?"), params)
            return [dict(satir) for satir in imlec.fetchall()]

    def al(self, isci, simdi):
        # Tek ifade: seçim + güncelleme atomiktir. SQLite yazma kilidi
        # sayesinde iki süreç aynı satırı alamaz.
        satirlar = self._donen(
            "UPDATE %s SET durum = 'calisiyor', isci = %%s, "
            "deneme = deneme + 1, guncelleme = %%s "
            "WHERE id = (SELECT id FROM %s WHERE durum = 'bekliyor' "
            "ORDER BY olustu, id LIMIT 1) AND durum = 'bekliyor' "
            "RETURNING *" % (IS_TABLO, IS_TABLO),
            (isci, simdi),
        )
        return satirlar[0] if satirlar else None


class _PostgresDepo(_KuyrukDepo):
    ad = "postgres"

    def __init__(self, dsn):
        try:
            import psycopg
        except ImportError as hata:
            raise KuyrukHatasi("psycopg kurulu değil") from hata
        self._psycopg = psycopg
        self._dsn = dsn
        super().__init__()

    def _baglan(self):
        conn = self._psycopg.connect(
            self._dsn, autocommit=True, connect_timeout=10)
        try:
            conn.prepare_threshold = None
        except Exception:
            logger.debug("kuyruk prepare_threshold ayarlanamadı",
                         exc_info=True)
        return conn

    def _hazirla(self):
        with self._baglan() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS %s ("
                    "id TEXT PRIMARY KEY, kosu_id TEXT NOT NULL, "
                    "adim_id TEXT NOT NULL, eylem TEXT NOT NULL, "
                    "token TEXT NOT NULL, url TEXT NOT NULL, "
                    "durum TEXT NOT NULL DEFAULT 'bekliyor', isci TEXT, "
                    "deneme INTEGER NOT NULL DEFAULT 0, sonuc TEXT, "
                    "hata TEXT NOT NULL DEFAULT '', "
                    "olustu DOUBLE PRECISION NOT NULL, "
                    "guncelleme DOUBLE PRECISION NOT NULL, "
                    "bitis DOUBLE PRECISION, "
                    "UNIQUE (kosu_id, adim_id))" % IS_TABLO)
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS basak_isci_is_durum "
                    "ON %s (durum, olustu)" % IS_TABLO)
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS %s ("
                    "isci TEXT PRIMARY KEY, "
                    "basladi DOUBLE PRECISION NOT NULL, "
                    "son DOUBLE PRECISION NOT NULL, "
                    "durum TEXT NOT NULL DEFAULT '', "
                    "surum TEXT NOT NULL DEFAULT '', "
                    "is_id TEXT NOT NULL DEFAULT '')" % KALP_TABLO)
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS %s ("
                    "nonce TEXT PRIMARY KEY, "
                    "bitis DOUBLE PRECISION NOT NULL)" % NONCE_TABLO)

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

    def _donen(self, sql, params=()):
        return self._sorgu(sql, params)

    def al(self, isci, simdi):
        # `SKIP LOCKED`: iki işçi aynı anda gelirse ikincisi kilitli satırı
        # beklemeden sıradakini alır; aynı iş iki kez çalışmaz.
        satirlar = self._donen(
            "WITH aday AS ("
            "SELECT id FROM %s WHERE durum = 'bekliyor' "
            "ORDER BY olustu, id FOR UPDATE SKIP LOCKED LIMIT 1"
            ") UPDATE %s AS is_tablosu SET durum = 'calisiyor', isci = %%s, "
            "deneme = deneme + 1, guncelleme = %%s "
            "FROM aday WHERE is_tablosu.id = aday.id "
            "RETURNING is_tablosu.*" % (IS_TABLO, IS_TABLO),
            (isci, simdi),
        )
        return satirlar[0] if satirlar else None


class Kuyruk:
    """Tek süreç için kuyruk tutamacı; DB bağlantısı işlem başına açılır."""

    def __init__(self, dsn=None, sqlite_yolu=None):
        if sqlite_yolu is None and not dsn:
            dsn = _dsn()
        if dsn and not sqlite_yolu:
            self._depo = _PostgresDepo(str(dsn).strip())
        else:
            yol = sqlite_yolu or os.path.join(_state_dizini(), "isci.db")
            self._depo = _SqliteDepo(yol)

    @property
    def ad(self):
        return self._depo.ad

    # — beyin tarafı —
    def birak(self, kosu_id, adim_id, eylem, token, url, simdi=None):
        kosu_id = _kimlik("koşu", kosu_id)
        adim_id = _kimlik("adım", adim_id)
        if not isinstance(eylem, dict) or not eylem:
            raise KuyrukHatasi("eylem boş sözlük olamaz")
        return self._depo.birak(
            kosu_id, adim_id, eylem, token, url, _simdi(simdi))

    # — işçi tarafı —
    def al(self, isci, simdi=None):
        isci = _kimlik("işçi", isci)
        return self._depo.al(isci, _simdi(simdi))

    def oku(self, is_id):
        return self._depo.oku(str(is_id or ""))

    def adim_oku(self, kosu_id, adim_id):
        return self._depo.adim_oku(
            _kimlik("koşu", kosu_id), _kimlik("adım", adim_id))

    def bitir(self, is_id, isci, sonuc=None, hata="", simdi=None):
        isci = _kimlik("işçi", isci)
        return self._depo.bitir(
            str(is_id or ""), isci, sonuc, hata, _simdi(simdi))

    def birak_tekrar(self, is_id, isci, hata, azami=2, simdi=None):
        isci = _kimlik("işçi", isci)
        return self._depo.birak_tekrar(
            str(is_id or ""), isci, hata, azami, _simdi(simdi))

    def supheli_yap(self, is_id, isci, hata, simdi=None):
        isci = _kimlik("işçi", isci)
        return self._depo.supheli_yap(
            str(is_id or ""), isci, hata, _simdi(simdi))

    def temizle(self, esik=_VARSAYILAN_ESIK, simdi=None):
        return self._depo.temizle(max(1.0, float(esik)), _simdi(simdi))

    # — kalp / nonce / özet —
    def kalp(self, isci, durum="hazir", surum="", is_id="", simdi=None):
        isci = _kimlik("işçi", isci)
        self._depo.kalp(
            isci, str(durum or ""), str(surum or ""), str(is_id or ""),
            _simdi(simdi))

    def canli_isciler(self, esik=_VARSAYILAN_ESIK, simdi=None):
        an = _simdi(simdi)
        satirlar = self._depo.canli_isciler(max(1.0, float(esik)), an)
        return [{
            "isci": str(s.get("isci") or ""),
            "durum": str(s.get("durum") or ""),
            "surum": str(s.get("surum") or ""),
            "is": str(s.get("is_id") or ""),
            "basladi": _iso(s.get("basladi")),
            "son": _iso(s.get("son")),
            "yas_sn": (None if s.get("son") is None
                       else max(0, round(an - float(s.get("son"))))),
        } for s in satirlar]

    def nonce_al(self, nonce, bitis, simdi=None):
        nonce = str(nonce or "").strip()
        if not nonce:
            return False
        return self._depo.nonce_al(
            nonce, float(bitis or 0), _simdi(simdi))

    def ozet(self, esik=_VARSAYILAN_ESIK, simdi=None):
        an = _simdi(simdi)
        sayilar = self._depo.sayilar()
        isciler = self.canli_isciler(esik, an)
        return {
            "bekliyor": sayilar.get("bekliyor", 0),
            "calisiyor": sayilar.get("calisiyor", 0),
            "bitti": sayilar.get("bitti", 0),
            "hata": sayilar.get("hata", 0),
            "supheli": sayilar.get("supheli", 0),
            "canli": len(isciler),
            "isciler": isciler,
            "esik_sn": max(1.0, float(esik)),
        }


class KuyrukNonce:
    """`BulutTarayici` için kalıcı nonce defteri.

    Tarayıcı sınıfı süreç içi `TekKullanim` kullanır; işçi yeniden
    başlarsa aynı belge ikinci kez çalışabilirdi. Bu adaptör aynı
    `kullan` sözleşmesini Postgres satırına bağlar.
    """

    def __init__(self, kuyruk):
        self._kuyruk = kuyruk

    def kullan(self, nonce, exp, simdi=None):
        return self._kuyruk.nonce_al(nonce, exp, simdi=simdi)
