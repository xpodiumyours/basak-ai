"""Postgres/Neon kalici hafiza motoru.

Yerel SQLite motoruna dokunmaz. Uretimde memory.__init__ fabrikasi bu
motoru secer. Dis davranis HafizaMotoru ile aynidir: ekle, ara, say,
episodik_kaydet, episodik_temizle, kaynak_sil, kaynak_satir, meta_al,
meta_koy, vektorleri_temizle, kapat.
"""

import json
import logging
import re

from memory.engine import EMBED_DIM, EPISODIK_LIMIT, _hassas_maskele, _simdi

logger = logging.getLogger(__name__)

_TABLO = "basak_memories"
_META = "basak_memory_meta"
_TEMIZ_BASLANGIC_ANAHTARI = "memory_clean_start_v2"

_STOP_WORDS = {
    "ve", "veya", "ile", "icin", "için", "olan", "olmasi", "olması",
    "olmak", "bu",
}
_KELIME_RE = re.compile(r"[0-9A-Za-zÇĞİÖŞÜçğıöşü_-]+")


def _vektor_metni(vektor):
    if not vektor or len(vektor) != EMBED_DIM:
        return None
    try:
        return "[" + ",".join(format(float(x), ".9g") for x in vektor) + "]"
    except (TypeError, ValueError):
        return None


def _arama_kelimeleri(sorgu):
    kelimeler = []
    for kelime in _KELIME_RE.findall((sorgu or "").lower()):
        if len(kelime) <= 2 or kelime in _STOP_WORDS:
            continue
        kelimeler.append(kelime)
    return kelimeler


class PostgresHafizaMotoru:
    """Kullanici bazli Postgres hafiza motoru (Neon uyumlu)."""

    def __init__(self, dsn, kullanici_id, embed_fn=None):
        if not dsn:
            raise RuntimeError("Postgres baglanti adresi yok")
        if not kullanici_id:
            raise RuntimeError("Hafiza kullanici kimligi yok")
        try:
            import psycopg
        except ImportError as e:
            raise RuntimeError("psycopg kurulu degil") from e
        self._psycopg = psycopg
        self._dsn = str(dsn)
        self.kullanici_id = str(kullanici_id)
        self._embed_fn = embed_fn
        self.vektor_var = True
        self._hazirla()

    def _baglan(self):
        conn = self._psycopg.connect(
            self._dsn, autocommit=False, connect_timeout=10)
        # Pooled/serverless baglantida oturumlar degisebilir. Otomatik
        # server-side prepared statement kullanma.
        try:
            conn.prepare_threshold = None
        except Exception:
            pass
        return conn

    def _hazirla(self):
        with self._baglan() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS basak_memories ("
                    " id BIGSERIAL PRIMARY KEY,"
                    " user_id TEXT NOT NULL,"
                    " kind TEXT NOT NULL,"
                    " text TEXT NOT NULL,"
                    " source TEXT NOT NULL DEFAULT '',"
                    " created_at DOUBLE PRECISION NOT NULL,"
                    " speaker TEXT NOT NULL DEFAULT '',"
                    " onem SMALLINT NOT NULL DEFAULT 1,"
                    " embedding vector(768),"
                    " search_vector tsvector GENERATED ALWAYS AS ("
                    "   to_tsvector('turkish', coalesce(text, ''))"
                    " ) STORED"
                    ")"
                )
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS basak_memory_meta ("
                    " user_id TEXT NOT NULL,"
                    " anahtar TEXT NOT NULL,"
                    " deger TEXT NOT NULL,"
                    " PRIMARY KEY (user_id, anahtar)"
                    ")"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS basak_memories_user_kind_idx "
                    "ON basak_memories (user_id, kind, id DESC)"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS basak_memories_user_source_idx "
                    "ON basak_memories (user_id, source)"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS basak_memories_search_idx "
                    "ON basak_memories USING GIN (search_vector)"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS basak_memories_embedding_idx "
                    "ON basak_memories USING hnsw (embedding vector_cosine_ops)"
                )
            conn.commit()
        self._temiz_baslangic_sagla()

    def _temiz_baslangic_sagla(self):
        """2026-09-23 temiz başlangıcını veritabanında yalnız bir kez uygular.

        Önceki çoklu-oturum denemesindeki tüm kalıcı hafıza kayıtları ve
        61 kayıtlık legacy kaynak silinir. Sonraki soğuk başlangıçlarda
        sistem işareti görülür ve yeni kullanıcı hafızalarına dokunulmaz.
        Advisory lock eşzamanlı Vercel başlangıçlarını tek işleme indirir.
        """
        with self._baglan() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT pg_advisory_xact_lock(hashtext("
                    "'basak_memory_clean_start_v2'))")
                cur.execute(
                    "SELECT deger FROM basak_memory_meta "
                    "WHERE user_id=%s AND anahtar=%s",
                    ("__system__", _TEMIZ_BASLANGIC_ANAHTARI),
                )
                marker = cur.fetchone()
                if marker is not None:
                    try:
                        if json.loads(marker[0]) is True:
                            conn.commit()
                            return
                    except (json.JSONDecodeError, TypeError):
                        pass

                cur.execute("DELETE FROM basak_memories")
                cur.execute("DELETE FROM basak_memory_meta")

                for tablo in ("basak.anilar", "public.memories"):
                    cur.execute("SELECT to_regclass(%s)", (tablo,))
                    if cur.fetchone()[0] is not None:
                        if tablo == "basak.anilar":
                            cur.execute('DELETE FROM "basak"."anilar"')
                        else:
                            cur.execute('DELETE FROM "public"."memories"')

                cur.execute(
                    "INSERT INTO basak_memory_meta (user_id, anahtar, deger) "
                    "VALUES (%s,%s,%s)",
                    ("__system__", _TEMIZ_BASLANGIC_ANAHTARI,
                     json.dumps(True, ensure_ascii=False)),
                )
            conn.commit()
        logger.info("Basak hafizasi temiz baslangic v2 ile sifirlandi")

    def _embed(self, metin, gorev="RETRIEVAL_DOCUMENT"):
        if self._embed_fn is None:
            return None
        try:
            import inspect
            try:
                params = inspect.signature(self._embed_fn).parameters
                if len(params) >= 2:
                    return self._embed_fn(metin, gorev)
            except (TypeError, ValueError):
                pass
            return self._embed_fn(metin)
        except Exception:
            return None

    def _budu_cur(self, cur, kind="episodic", limit=EPISODIK_LIMIT):
        cur.execute(
            "DELETE FROM basak_memories WHERE user_id=%s AND kind=%s "
            "AND id NOT IN ("
            " SELECT id FROM basak_memories WHERE user_id=%s AND kind=%s "
            " ORDER BY onem DESC, id DESC LIMIT %s"
            ") RETURNING id",
            (self.kullanici_id, kind, self.kullanici_id, kind, int(limit)),
        )
        return len(cur.fetchall())

    def ekle(self, metin, kind="episodic", kaynak="", zaman=None, speaker="",
             onem=1):
        metin = (metin or "").strip()
        if not metin:
            return False
        zaman = zaman if zaman is not None else _simdi()
        vektor = _vektor_metni(self._embed(metin, "RETRIEVAL_DOCUMENT"))
        with self._baglan() as conn:
            with conn.cursor() as cur:
                if vektor:
                    cur.execute(
                        "INSERT INTO basak_memories "
                        "(user_id, kind, text, source, created_at, speaker, onem, embedding) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s::vector)",
                        (self.kullanici_id, kind, metin, kaynak or "", float(zaman),
                         speaker or "", max(0, min(3, int(onem or 1))), vektor),
                    )
                else:
                    cur.execute(
                        "INSERT INTO basak_memories "
                        "(user_id, kind, text, source, created_at, speaker, onem) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                        (self.kullanici_id, kind, metin, kaynak or "", float(zaman),
                         speaker or "", max(0, min(3, int(onem or 1)))),
                    )
                if kind == "episodic":
                    self._budu_cur(cur)
            conn.commit()
        return True

    def episodik_kaydet(self, soru, cevap, kaynak="sohbet", speaker="", onem=1):
        from datetime import datetime
        tarih = datetime.now().strftime("%Y-%m-%d")
        konusmaci = speaker or "Kullanıcı"
        metin = "%s (%s): %s\nBaşak: %s" % (
            konusmaci, tarih,
            _hassas_maskele((soru or "").strip()),
            _hassas_maskele((cevap or "").strip()),
        )
        with self._baglan() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM basak_memories "
                    "WHERE user_id=%s AND kind='episodic' AND text=%s LIMIT 1",
                    (self.kullanici_id, metin),
                )
                if cur.fetchone() is not None:
                    return False
        return self.ekle(metin, kind="episodic", kaynak=kaynak,
                         speaker=speaker, onem=onem)

    def episodik_temizle(self):
        with self._baglan() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM basak_memories "
                    "WHERE user_id=%s AND kind='episodic' RETURNING id",
                    (self.kullanici_id,),
                )
                sayi = len(cur.fetchall())
            conn.commit()
        return sayi

    def _budu(self, kind="episodic", limit=EPISODIK_LIMIT):
        with self._baglan() as conn:
            with conn.cursor() as cur:
                sayi = self._budu_cur(cur, kind=kind, limit=limit)
            conn.commit()
        return sayi

    def kaynak_sil(self, kaynak):
        with self._baglan() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM basak_memories WHERE user_id=%s AND source=%s "
                    "RETURNING id",
                    (self.kullanici_id, kaynak),
                )
                sayi = len(cur.fetchall())
            conn.commit()
        return sayi

    def kaynak_satir(self, kaynak):
        with self._baglan() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM basak_memories WHERE user_id=%s AND source=%s",
                    (self.kullanici_id, kaynak),
                )
                return int(cur.fetchone()[0])

    def _meta_koy_cur(self, cur, anahtar, deger):
        cur.execute(
            "INSERT INTO basak_memory_meta (user_id, anahtar, deger) "
            "VALUES (%s,%s,%s) "
            "ON CONFLICT (user_id, anahtar) DO UPDATE SET deger=EXCLUDED.deger",
            (self.kullanici_id, anahtar, json.dumps(deger, ensure_ascii=False)),
        )

    def meta_al(self, anahtar, varsayilan=None):
        with self._baglan() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT deger FROM basak_memory_meta "
                    "WHERE user_id=%s AND anahtar=%s",
                    (self.kullanici_id, anahtar),
                )
                row = cur.fetchone()
        if row is None:
            return varsayilan
        try:
            return json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            return row[0]

    def meta_koy(self, anahtar, deger):
        with self._baglan() as conn:
            with conn.cursor() as cur:
                self._meta_koy_cur(cur, anahtar, deger)
            conn.commit()

    def say(self):
        with self._baglan() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM basak_memories WHERE user_id=%s",
                    (self.kullanici_id,),
                )
                return int(cur.fetchone()[0])

    def _bm25_ara_cur(self, cur, sorgu, limit):
        kelimeler = _arama_kelimeleri(sorgu)
        if not kelimeler:
            return []
        web_sorgu = " OR ".join('"%s"' % k for k in kelimeler)
        cur.execute(
            "SELECT id, kind, text, source, created_at "
            "FROM basak_memories "
            "WHERE user_id=%s AND search_vector @@ "
            "websearch_to_tsquery('turkish', %s) "
            "ORDER BY ts_rank_cd(search_vector, "
            "websearch_to_tsquery('turkish', %s)) DESC, id DESC "
            "LIMIT %s",
            (self.kullanici_id, web_sorgu, web_sorgu, int(limit)),
        )
        adlar = ("id", "kind", "text", "source", "created_at")
        return [dict(zip(adlar, r)) for r in cur.fetchall()]

    def _vektor_ara_cur(self, cur, vektor, limit):
        if not vektor:
            return []
        cur.execute(
            "SELECT id, kind, text, source, created_at "
            "FROM basak_memories "
            "WHERE user_id=%s AND embedding IS NOT NULL "
            "ORDER BY embedding <=> %s::vector LIMIT %s",
            (self.kullanici_id, vektor, int(limit)),
        )
        adlar = ("id", "kind", "text", "source", "created_at")
        return [dict(zip(adlar, r)) for r in cur.fetchall()]

    def ara(self, sorgu, limit=4):
        sorgu = (sorgu or "").strip()
        if not sorgu:
            return []
        # Ag cagrisi DB baglantisini bosuna acik tutmasin: sorgu vektoru
        # once alinir, sonra iki arama tek Postgres baglantisinda kosar.
        vektor = _vektor_metni(self._embed(sorgu, "RETRIEVAL_QUERY"))
        with self._baglan() as conn:
            with conn.cursor() as cur:
                bm25 = self._bm25_ara_cur(cur, sorgu, limit * 2)
                vek = self._vektor_ara_cur(cur, vektor, limit * 2)

        skorlar = {}
        detaylar = {}
        for sirano, satir in enumerate(bm25):
            skorlar[satir["id"]] = skorlar.get(satir["id"], 0) + 1.0 / (61 + sirano)
            detaylar[satir["id"]] = satir
        for sirano, satir in enumerate(vek):
            skorlar[satir["id"]] = skorlar.get(satir["id"], 0) + 1.0 / (61 + sirano)
            detaylar[satir["id"]] = satir
        sirali = sorted(skorlar.items(), key=lambda x: -x[1])[:limit]
        sonuc = []
        for hid, skor in sirali:
            d = dict(detaylar[hid])
            d["score"] = round(skor, 6)
            sonuc.append(d)
        return sonuc

    def _bm25_ara(self, sorgu, limit):
        with self._baglan() as conn:
            with conn.cursor() as cur:
                return self._bm25_ara_cur(cur, sorgu, limit)

    def _vektor_ara(self, sorgu, limit):
        vektor = _vektor_metni(self._embed(sorgu, "RETRIEVAL_QUERY"))
        if not vektor:
            return []
        with self._baglan() as conn:
            with conn.cursor() as cur:
                return self._vektor_ara_cur(cur, vektor, limit)

    def vektorleri_temizle(self):
        with self._baglan() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM basak_memories "
                    "WHERE user_id=%s AND embedding IS NOT NULL",
                    (self.kullanici_id,),
                )
                sayi = int(cur.fetchone()[0])
                cur.execute(
                    "UPDATE basak_memories SET embedding=NULL WHERE user_id=%s",
                    (self.kullanici_id,),
                )
            conn.commit()
        return sayi

    def _vektor_uzayi_sagla(self, damga, limit=500):
        """Context'in DB icine girmeden vektor damgasini yenilemesi."""
        if self._embed_fn is None:
            return (0, 0)
        if self.meta_al("embed_uzay", "") == damga:
            return (0, 0)
        temizlenen = self.vektorleri_temizle()
        with self._baglan() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, text FROM basak_memories "
                    "WHERE user_id=%s AND embedding IS NULL AND text<>'' "
                    "ORDER BY id LIMIT %s",
                    (self.kullanici_id, int(limit)),
                )
                satirlar = cur.fetchall()
                doldurulan = 0
                for rid, metin in satirlar:
                    v = _vektor_metni(self._embed(metin, "RETRIEVAL_DOCUMENT"))
                    if not v:
                        continue
                    cur.execute(
                        "UPDATE basak_memories SET embedding=%s::vector "
                        "WHERE user_id=%s AND id=%s",
                        (v, self.kullanici_id, rid),
                    )
                    doldurulan += 1
                self._meta_koy_cur(cur, "embed_uzay", damga)
            conn.commit()
        return (temizlenen, doldurulan)

    def kapat(self):
        # Baglantilar her islemde context-manager ile acilip kapanir.
        return None
