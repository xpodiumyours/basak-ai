"""chat/context.py — Bağlam, geçmiş ve hafıza.

2026-09-13 sadeleştirmesi: araç katmanı söküldükten sonra bu modül
`_chat_legacy.py`'ye bağlı kalmasın diye dosya yolları, JSON okuma/yazma
ve hafıza bağlantısı buraya taşındı.

Sorumluluğu:
  - dosya yolları ve ayar okuma (kişiye özel: chat.kimlik)
  - modele giden tam geçmişi koruma
  - kalıcı hafıza motoruna tek giriş noktası (kişi başına ayrı DB)

2026-09-23: HISTORY_FILE None ise dinamiktir (kimlik); testler
monkeypatch ile ezebilir (None olmayan deger kullanilir).
"""

import contextvars
import json
import logging
import os
import threading
import uuid

logger = logging.getLogger(__name__)

# ── Dosya yolları ───────────────────────────────────────────────────

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# None = kimlikten hesapla (uretim). Test monkeypatch ederse o deger kullanilir.
HISTORY_FILE = None
SETTINGS_FILE = os.path.join(BASE, "ayarlar.json")
KNOWLEDGE_DIR = os.path.join(BASE, "knowledge")
OBSIDIAN_DIR = os.path.join(BASE, "Basak")

# Her açılışta bir oturum kimliği — kayıtlara işlenir.
OTURUM_ID = uuid.uuid4().hex[:8]

# Gecmis yazma kilidi (tek surec ici; bkz. kaydet).
_kayit_kilidi = threading.Lock()

# ── Geçmiş ────────────────────────────────────────────────────────
# P2: uygulama geçmişi sessizce kırpmaz; sağlayıcı gerçek bağlam sınırını
# aşarsa hata/incomplete durumu görünür olur.

def gecmis_yolu():
    """Aktif kişinin gecmis.json yolu (test monkeypatch'i önce gelir)."""
    if HISTORY_FILE is not None:
        return HISTORY_FILE
    from chat.kimlik import kullanici_koku
    return os.path.join(kullanici_koku(), "gecmis.json")


def yukle(path, varsayilan):
    """JSON dosyasını okur; hata olursa varsayılanı döndürür (BOM güvenli)."""
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return varsayilan


def kaydet(path, veri):
    """JSON dosyasına yazar (kilitli + atomik).

    2026-09-15 checkup: Api.mesaj her mesaji ayri thread'de kosturur;
    kilitsiz oku-degistir-yaz cift mesajda gecmisi kaybediyordu.
    Once .tmp'e yazip os.replace ile degistirir.
    """
    with _kayit_kilidi:
        gecici = path + ".tmp"
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
        os.replace(gecici, path)


def gecmis_pencere(gecmis):
    """Geçmişi tam döndürür; sessiz kırpma yapmaz."""
    return list(gecmis or [])


def gecmis_model_penceresi(gecmis):
    """Modele tam geçmişi verir; sessiz kırpma yapmaz.

    Sağlayıcı bağlamı kabul etmezse hata görünür olur; uygulama eski
    mesajları gizlice düşürmez.
    """
    liste = list(gecmis or [])
    return liste, {
        "compact": False,
        "toplam_token": None,
        "modele_giden_token": None,
        "atlanan_mesaj": 0,
    }


def temizle_history(gecmis):
    """Geçmiş mesajlarını API biçimine indirger.

    Native alanlar korunur (tool_calls/tool_call_id/name): cok-turlu
    arac gecmisi bozulmaz. Yalniz yerel metadata (oturum) duser.
    """
    from brain.message_utils import mesajlari_temizle
    return mesajlari_temizle(gecmis)


# ── Önem puanı ──────────────────────────────────────────────────────
def onem_puanla(text):
    """Her episodik kayıt eşit önemdedir; kullanıcı metni sınıflandırılmaz."""
    return 1


# ── Hafıza ──────────────────────────────────────────────────────────

# None: kullanici bazli (_hafizalar) kullanilir. Test monkeypatch'i
# False/motor verirse o tek deger kullanilir (eski test davranisi).
_hafiza = None
_hafizalar = {}   # {kullanici_id: motor|False}
_hafiza_lock = threading.Lock()


def _anlam_fn():
    """Anlam vektorleri varsa dondurur, yoksa None (kelime aramasi).

    Casper karari (2026-09-13): Google ucretsiz yolu. Anahtar yoksa
    veya servis cevap vermezse motor eski siralamayla calisir —
    sohbet hicbir kosulda durmaz.
    """
    try:
        from brain.gemini_embed import embed_fn, _anahtar_al
        if _anahtar_al():
            return embed_fn
    except Exception as e:
        logger.warning("Anlam vektorleri kapali: %s", e)
    return None


# Vektor uzayi damgasi: saglayici/boyut degince eski vektorler
# cop olur (iki farkli olcum ayni tabloda karsilastirilamaz).
# Damga tutmazsa vektorler silinip metinler yeniden islenir.
# 2026-09-15: taskType (DOCUMENT/QUERY) + L2 normalizasyonu eklendi —
# eski normsuz vektorlerle karsilastirilamaz, damga yukseltildi.
VEKTOR_UZAYI = "gemini-embedding-001@768-norm-tasktype"
_VEKTOR_DAMGA = "embed_uzay"
_GERI_DOLDURMA_TAVAN = 500


def _motor_yolu():
    from chat.kimlik import kullanici_koku
    return os.path.join(kullanici_koku(), "memory", "basak.db")


def hafiza_al():
    """Motoru kişiye göre tek seferlik oluşturur; açılamazsa None."""
    global _hafiza
    # Test/tek-kullanıcı monkeypatch: _hafiza None DEGILSE o kullanilir.
    if _hafiza is not None:
        return _hafiza or None

    from chat.kimlik import aktif_kullanici
    kid = aktif_kullanici()
    with _hafiza_lock:
        if kid not in _hafizalar:
            try:
                from memory import HafizaMotoru
                _hafizalar[kid] = HafizaMotoru(
                    db_yolu=_motor_yolu(), embed_fn=_anlam_fn())
            except Exception as e:
                logger.warning("Hafiza motoru acilamadi: %s", e)
                _hafizalar[kid] = False
    motor = _hafizalar.get(kid)
    return motor or None


def hafizalari_kapat():
    """Tum acik motorlari kapatir (uygulama kapanisinda)."""
    with _hafiza_lock:
        for motor in list(_hafizalar.values()):
            if motor:
                try:
                    motor.kapat()
                except Exception:
                    pass
        _hafizalar.clear()


def ilgili_anilar(sorgu, limit=20):
    """Soruyla ilgili anıları döndürür; hata durumunda boş liste."""
    motor = hafiza_al()
    if not motor:
        return []
    try:
        return motor.ara(sorgu, limit=limit)
    except Exception as e:
        logger.warning("Ani arama hatasi: %s", e)
        return []


def _gecmisi_aktar(motor):
    """gecmis.json'daki eski sohbeti bir kereye mahsus hafızaya taşır."""
    kayitlar = yukle(gecmis_yolu(), [])
    soru = None
    sayac = 0
    for m in kayitlar:
        rol = m.get("role")
        icerik = (m.get("content") or "").strip()
        if not icerik:
            continue
        if rol == "user":
            soru = icerik
        elif rol == "assistant" and soru:
            if motor.episodik_kaydet(soru, icerik):
                sayac += 1
            soru = None
    logger.info("Eski gecmis hafizaya tasindi: %d cift", sayac)


def _vektor_uzay_sagla(motor):
    """Vektor uzay damgasini denetler; tutmazsa temizler + doldurur.

    Yalniz anlam motoru aciksa calisir (fn yoksa eski duzen aynen
    kalir). Metinler asla silinmez; yalniz vektorler yenilenir.
    Donus: (temizlenen, doldurulan) sayilari.
    """
    # Bulut motoru kendi veritabani ayrintisini kendisi yonetir. SQLite
    # motorunda bu ozel yordam yok; alttaki mevcut yol aynen calisir.
    backend_sagla = getattr(motor, "_vektor_uzayi_sagla", None)
    if callable(backend_sagla):
        try:
            return backend_sagla(VEKTOR_UZAYI, _GERI_DOLDURMA_TAVAN)
        except Exception as e:
            logger.warning("Bulut vektor uzayi yenilenemedi: %s", e)
            return (0, 0)

    fn = getattr(motor, "_embed_fn", None)
    if fn is None:
        return (0, 0)
    try:
        if motor.meta_al(_VEKTOR_DAMGA, "") == VEKTOR_UZAYI:
            return (0, 0)
        temizlenen = motor.vektorleri_temizle()
        doldurulan = 0
        try:
            from memory.engine import _serialize
            satirlar = motor.conn.execute(
                "SELECT id, text FROM memories WHERE has_vec=0 "
                "AND text <> '' LIMIT ?",
                (_GERI_DOLDURMA_TAVAN,)).fetchall()
            for rid, metin in satirlar:
                try:
                    v = fn(metin)
                except Exception:
                    v = None
                if not v or len(v) != 768:
                    continue
                try:
                    motor.conn.execute(
                        "INSERT INTO memories_vec (rowid, embedding)"
                        " VALUES (?, ?)", (rid, _serialize(v)))
                    motor.conn.execute(
                        "UPDATE memories SET has_vec=1 WHERE id=?", (rid,))
                    doldurulan += 1
                except Exception:
                    continue
            motor.conn.commit()
        except Exception as e:
            logger.warning("Geri doldurma yarim kaldi: %s", e)
        try:
            motor.meta_koy(_VEKTOR_DAMGA, VEKTOR_UZAYI)
        except Exception as e:
            logger.warning("Damga yazilamadi: %s", e)
        logger.info("Vektor uzayi yenilendi: %d temizlendi, %d dolduruldu",
                    temizlenen, doldurulan)
        return (temizlenen, doldurulan)
    except Exception as e:
        logger.warning("Uzay saglama atlandi: %s", e)
        return (0, 0)


def _hafiza_hazirla():
    """Arka planda: eski geçmişi aktar, notları indeksle.

    2026-09-23: bilgi sızıntısı önlenmesi — global knowledge/ ve
    Obsidian yalnız `casper` oturumunda indekslenir; diğer kullanıcılar
    yalnız kendi kökündeki knowledge/ dosyalarını indeksler (bu fazda
    kimsede yok → 0).
    """
    from chat.kimlik import VARSAYILAN_KULLANICI, aktif_kullanici, kullanici_koku
    kid = aktif_kullanici()
    motor = hafiza_al()
    if not motor:
        return
    _vektor_uzay_sagla(motor)
    try:
        from memory.engine import indeksle_klasor

        if not motor.meta_al("gecmis_aktarildi", False):
            _gecmisi_aktar(motor)
            motor.meta_koy("gecmis_aktarildi", True)

        if kid == VARSAYILAN_KULLANICI:
            n1 = indeksle_klasor(motor, KNOWLEDGE_DIR, "knowledge")
            n2 = indeksle_klasor(motor, OBSIDIAN_DIR, "obsidian")
        else:
            kendi = os.path.join(kullanici_koku(kid), "knowledge")
            n1 = indeksle_klasor(motor, kendi, "knowledge")
            n2 = 0
        logger.info("Hafiza hazir: %d ani, indeksleme +%d",
                    motor.say(), n1 + n2)
    except Exception as e:
        logger.warning("Hafiza hazirlanamadi (sohbet etkilenmez): %s", e)


def init_cache():
    """Açılışta çağrılır: hafızayı arka planda hazırlar."""
    from chat.kimlik import kullanici_koku  # noqa: F401  (migration tetik)
    # 2026-09-23: thread context kopyasi alinmazsa aktif_kullanici()
    # her zaman fabrika degerini (casper) gorur — diger kisi icin
    # bilincli knowledge/ yolu fiilen olu kalirdi.
    ctx = contextvars.copy_context()
    threading.Thread(target=ctx.run, args=(_hafiza_hazirla,),
                     daemon=True).start()
