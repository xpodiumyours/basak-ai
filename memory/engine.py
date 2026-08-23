"""memory/engine.py — Başak hafıza motoru.

Üç katman tek SQLite dosyasında (data/memory/basak.db):
- memories: ana tablo (metin, tür, kaynak, zaman)
- memories_fts: FTS5/BM25 anahtar kelime indeksi
- memories_vec: sqlite-vec anlam araması (nomic-embed-text, 768 boyut)

Bozulma kuralı: Ollama kapalıysa veya sqlite-vec yüklenemezse motor
sadece BM25 ile çalışmaya devam eder — asla çökmez.
"""

import json
import logging
import os
import sqlite3
import threading

import numpy as np
import requests

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_YOLU = os.path.join(BASE, "data", "memory", "basak.db")

OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text:latest"
EMBED_DIM = 768

PARCA_BOYUTU = 700
VEKTOR_KAPALI = "vektor_kapali"


def _vec_yukle(conn):
    """sqlite-vec eklentisini yükler; olmazsa None döner."""
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return True
    except Exception as e:
        logger.warning("sqlite-vec yuklenemedi, sadece BM25 calisacak: %s", e)
        return False


def parcalara_bol(metin, boyut=PARCA_BOYUTU):
    """Metni paragraf sinirlarindan parcalara boler (~boyut karakter)."""
    metin = (metin or "").strip()
    if not metin:
        return []
    paragraflar = [p.strip() for p in metin.split("\n\n") if p.strip()]
    parcalar = []
    ucret = ""

    for p in paragraflar:
        # Tek paragraf bile cok uzussa zorla kes
        while len(p) > boyut:
            kesim = p[:boyut]
            nokta = max(kesim.rfind(". "), kesim.rfind("\n"))
            if nokta > boyut // 2:
                kesim = kesim[:nokta + 1]
            parcalar.append(kesim.strip())
            p = p[len(kesim):].strip()
        if not p:
            continue
        if ucret and len(ucret) + len(p) + 2 <= boyut:
            ucret = ucret + "\n\n" + p
        else:
            if ucret:
                parcalar.append(ucret)
            ucret = p
    if ucret:
        parcalar.append(ucret)

    return [p for p in parcalar if p]


class HafizaMotoru:
    """Hibrit hafiza motoru: vektor + BM25 ayni DB uzerinden."""

    def __init__(self, db_yolu=None, embed_fn=None):
        self.db_yolu = db_yolu or DB_YOLU
        self._embed_fn = embed_fn
        self._lock = threading.Lock()

        os.makedirs(os.path.dirname(self.db_yolu), exist_ok=True)
        self.conn = sqlite3.connect(self.db_yolu, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.vektor_var = _vec_yukle(self.conn)

        cur = self.conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS memories ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " kind TEXT NOT NULL,"
            " text TEXT NOT NULL,"
            " source TEXT NOT NULL DEFAULT '',"
            " created_at REAL NOT NULL,"
            " has_vec INTEGER NOT NULL DEFAULT 0,"
            " speaker TEXT DEFAULT '')"
        )
        # Eski DB'de speaker sütunu yoksa ekle (migrasyon)
        try:
            cur.execute("SELECT speaker FROM memories LIMIT 1")
        except sqlite3.OperationalError:
            cur.execute("ALTER TABLE memories ADD COLUMN speaker TEXT DEFAULT ''")
            logger.info("memories tablosuna speaker sutunu eklendi")
        cur.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts "
            "USING fts5(text)"
        )
        if self.vektor_var:
            try:
                cur.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS memories_vec "
                    "USING vec0(embedding float[%d])" % EMBED_DIM
                )
            except sqlite3.DatabaseError as e:
                logger.warning("vec0 tablosu acilamadi: %s", e)
                self.vektor_var = False
        cur.execute(
            "CREATE TABLE IF NOT EXISTS meta ("
            " anahtar TEXT PRIMARY KEY, deger TEXT NOT NULL)"
        )
        self.conn.commit()

    # ---------- yazma ----------

    def ekle(self, metin, kind="episodic", kaynak="", zaman=None, speaker=""):
        """Bir ani ekler. Vektor alinamazsa BM25-only olarak kaydeder.

        Args:
            metin: Anı metni.
            kind: Anı türü (episodic, semantic, vb.).
            kaynak: Kaynak etiketi.
            zaman: Unix timestamp (None ise simdi).
            speaker: Konuşmacı adı (opsiyonel).
        """
        metin = (metin or "").strip()
        if not metin:
            return False
        vektor = self._embed(metin)
        zaman = zaman if zaman is not None else _simdi()

        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO memories (kind, text, source, created_at, has_vec, speaker)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (kind, metin, kaynak, zaman, 1 if vektor else 0, speaker or ""),
            )
            rowid = cur.lastrowid
            self.conn.execute(
                "INSERT INTO memories_fts (rowid, text) VALUES (?, ?)",
                (rowid, metin),
            )
            if vektor and self.vektor_var:
                try:
                    self.conn.execute(
                        "INSERT INTO memories_vec (rowid, embedding)"
                        " VALUES (?, ?)",
                        (rowid, _serialize(vektor)),
                    )
                except sqlite3.DatabaseError as e:
                    logger.warning("Vektor yazilamadi (BM25-only kaldı): %s", e)
                    self.conn.execute(
                        "UPDATE memories SET has_vec=0 WHERE id=?", (rowid,))
            self.conn.commit()
        return True

    def episodik_kaydet(self, soru, cevap, kaynak="sohbet", speaker=""):
        """Soru-cevap ciftini tarih etiketiyle episodic hafizaya yazar.

        Args:
            soru: Kullanıcı sorusu.
            cevap: Asistan cevabı.
            kaynak: Kaynak etiketi (varsayılan "sohbet").
            speaker: Konuşmacı adı (opsiyonel, ör: "Casper").
        """
        from datetime import datetime
        tarih = datetime.now().strftime("%Y-%m-%d")
        konusmaci = speaker or "Kullanıcı"
        metin = (
            "%s (%s): %s\nBaşak: %s"
            % (konusmaci, tarih, (soru or "").strip()[:1000], (cevap or "").strip()[:1000])
        )
        return self.ekle(metin, kind="episodic", kaynak=kaynak, speaker=speaker)

    def kaynak_sil(self, kaynak):
        """Belirli bir kaynagin tum parcalarini siler (yeniden indeks icin)."""
        with self._lock:
            ids = [r[0] for r in self.conn.execute(
                "SELECT id FROM memories WHERE source=?", (kaynak,))]
            for rowid in ids:
                self.conn.execute(
                    "DELETE FROM memories_fts WHERE rowid=?", (rowid,))
                if self.vektor_var:
                    self.conn.execute(
                        "DELETE FROM memories_vec WHERE rowid=?", (rowid,))
                self.conn.execute("DELETE FROM memories WHERE id=?", (rowid,))
            self.conn.commit()
        return len(ids)

    def kaynak_satir(self, kaynak):
        """Belirli kaynaga ait parca sayisini dondurur."""
        return self.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE source=?", (kaynak,)
        ).fetchone()[0]

    def meta_al(self, anahtar, varsayilan=None):
        row = self.conn.execute(
            "SELECT deger FROM meta WHERE anahtar=?", (anahtar,)).fetchone()
        if row is None:
            return varsayilan
        try:
            return json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            return row[0]

    def meta_koy(self, anahtar, deger):
        with self._lock:
            self.conn.execute(
                "INSERT INTO meta (anahtar, deger) VALUES (?, ?)"
                " ON CONFLICT(anahtar) DO UPDATE SET deger=excluded.deger",
                (anahtar, json.dumps(deger, ensure_ascii=False)),
            )
            self.conn.commit()

    def say(self):
        return self.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

    # ---------- arama ----------

    def ara(self, sorgu, limit=4):
        """Hibrit arama: vektor + BM25 listeleri RRF ile birlestirilir."""
        sorgu = (sorgu or "").strip()
        if not sorgu:
            return []

        bm25 = self._bm25_ara(sorgu, limit * 2)
        vektor = self._vektor_ara(sorgu, limit * 2)

        skorlar = {}
        detaylar = {}
        for sirano, satir in enumerate(bm25):
            rrf = 1.0 / (60 + sirano + 1)
            skorlar[satir["id"]] = skorlar.get(satir["id"], 0) + rrf
            detaylar[satir["id"]] = satir
        for sirano, satir in enumerate(vektor):
            rrf = 1.0 / (60 + sirano + 1)
            skorlar[satir["id"]] = skorlar.get(satir["id"], 0) + rrf
            detaylar[satir["id"]] = satir

        sirali = sorted(skorlar.items(), key=lambda x: -x[1])[:limit]
        sonuclar = []
        for hid, skor in sirali:
            d = dict(detaylar[hid])
            d["score"] = round(skor, 6)
            sonuclar.append(d)
        return sonuclar

    def _bm25_ara(self, sorgu, limit):
        """FTS5 BM25 aramasi; sorgu hatasinda guvenli sekilde bos doner."""
        # Türkçe stop words filtresi: arama kalitesini artirmak için
        stop_words = {"ve", "veya", "ile", "için", "olan", "olması", "olmak",
                      "bu", "bu", "bu", "bu", "bu", "bu", "bu", "bu"}
        words = [w for w in sorgu.lower().split() if w not in stop_words and len(w) > 2]
        
        if not words:
            return []
        
        fts_sorgu = " OR ".join(f'"{w}"' for w in words)
        if not fts_sorgu:
            return []
        try:
            rows = self.conn.execute(
                "SELECT m.id, m.kind, m.text, m.source, m.created_at"
                " FROM memories_fts f JOIN memories m ON m.id = f.rowid"
                " WHERE memories_fts MATCH ? ORDER BY bm25(memories_fts)"
                " LIMIT ?",
                (fts_sorgu, limit),
            ).fetchall()
        except sqlite3.OperationalError as e:
            logger.warning("FTS sorgu hatasi: %s", e)
            return []
        return [dict(zip(("id", "kind", "text", "source", "created_at"), r))
                for r in rows]

    def _vektor_ara(self, sorgu, limit):
        """Anlam aramasi; vektor yoksa bos liste doner."""
        if not self.vektor_var:
            return []
        vektor = self._embed(sorgu)
        if not vektor:
            return []
        try:
            rows = self.conn.execute(
                "SELECT m.id, m.kind, m.text, m.source, m.created_at"
                " FROM memories_vec v JOIN memories m ON m.id = v.rowid"
                " WHERE v.embedding MATCH ? AND k = ?"
                " ORDER BY distance LIMIT ?",
                (_serialize(vektor), limit * 4, limit),
            ).fetchall()
        except sqlite3.DatabaseError as e:
            logger.warning("Vektor arama hatasi: %s", e)
            return []
        return [dict(zip(("id", "kind", "text", "source", "created_at"), r))
                for r in rows]

    def _embed(self, metin):
        """Ollama'dan embedding alir; hata olursa None doner."""
        if self._embed_fn is not None:
            try:
                return self._embed_fn(metin)
            except Exception:
                return None
        try:
            r = requests.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": metin[:2000]},
                timeout=(5, 30),
            )
            r.raise_for_status()
            vektor = r.json().get("embedding")
            if vektor and len(vektor) == EMBED_DIM:
                return vektor
            return None
        except requests.RequestException as e:
            logger.warning("Embedding alinamadi (BM25-only mod): %s", e)
            return None

    def kapat(self):
        try:
            self.conn.close()
        except sqlite3.Error:
            pass


def _serialize(vektor):
    """float32 little-endian bayt dizisi — sqlite-vec formati."""
    return np.asarray(vektor, dtype="<f4").tobytes()


def _simdi():
    import time
    return time.time()


# ---------- dosya indeksleme ----------

def indeksle_dosya(motor, dosya_yolu, kaynak_adi):
    """Tek bir .md dosyasini parcalara bolup indeksler.

    Dosya degismemisse (mtime ayni) atlar. Silinen/degisen dosyanin
    eski parcalari once temizlenir.
    """
    try:
        mtime = os.path.getmtime(dosya_yolu)
        with open(dosya_yolu, "r", encoding="utf-8", errors="replace") as f:
            icerik = f.read()
    except OSError as e:
        logger.warning("Dosya okunamadi %s: %s", dosya_yolu, e)
        return 0

    mtime_key = "mtime:" + kaynak_adi
    kayitli_mtime = float(motor.meta_al(mtime_key, 0) or 0)
    # Isaret var ama satirlar yoksa (yarida kalmis indeksleme) → yeniden yap
    if kayitli_mtime == mtime and motor.kaynak_satir(kaynak_adi) > 0:
        return 0  # degisiklik yok

    motor.kaynak_sil(kaynak_adi)
    parca_no = 0
    toplam = len(parcalara_bol(icerik))
    for i, parca in enumerate(parcalara_bol(icerik)):
        baslik = os.path.splitext(os.path.basename(dosya_yolu))[0]
        metin = "%s (%d/%d):\n%s" % (baslik, i + 1, toplam, parca)
        if motor.ekle(metin, kind="semantic", kaynak=kaynak_adi, zaman=mtime):
            parca_no += 1
    motor.meta_koy(mtime_key, mtime)
    return parca_no


def indeksle_klasor(motor, klasor, on_ek, uzantilar=(".md",)):
    """Klasoru gezip tum uygun dosyalari indeksler.

    on_ek: kaynak adlari 'obsidian:not.md' seklinde on eklenir.
    Silinmis dosyalarin kalintilari da temizlenir.
    """
    if not os.path.isdir(klasor):
        return 0
    sayac = 0
    gorulen = set()
    for kok, dizinler, dosyalar in os.walk(klasor):
        dizinler[:] = [d for d in dizinler if not d.startswith(".")]
        for ad in dosyalar:
            if not ad.lower().endswith(uzantilar):
                continue
            if ad.upper() == "README.MD":
                continue
            yol = os.path.join(kok, ad)
            rel = os.path.relpath(yol, klasor).replace("\\", "/")
            kaynak = "%s:%s" % (on_ek, rel)
            gorulen.add(kaynak)
            sayac += indeksle_dosya(motor, yol, kaynak)

    # Diskten silinen dosyalarin kalintilarini temizle
    for kaynak in list(motor.meta_al("kaynaklar:%s" % on_ek, []) or []):
        if kaynak not in gorulen:
            motor.kaynak_sil(kaynak)
    motor.meta_koy("kaynaklar:%s" % on_ek, sorted(gorulen))
    return sayac
