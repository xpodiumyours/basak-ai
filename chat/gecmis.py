"""chat/gecmis.py — sohbet gecmisi icin kalici (Postgres) depo.

Neden bu dosya: gecmis `<state>/<kullanici>/gecmis.json` dosyasindaydi.
Vercel'de state dizini `/tmp`'dir; ornek yenilenince gecmis kayboluyordu.
Ayrica iki eszamanli istek ayni dosyayi oku-degistir-yaz ettigi icin
mesaj kaybi riski vardi (`chat.context._kayit_kilidi` yalniz tek surec
icinde gecerli).

Kural (AGENTS.md §0): karar vermez, metne bakmaz. Yalniz kayit tutar.
Postgres yoksa (masaustu) cagiran katman dosya yolunu kullanmaya devam
eder; bu modul `aktif()` False doner.
"""

import json
import logging

logger = logging.getLogger(__name__)

TABLO = "basak_sohbet_mesaj"
SATIR_TAVANI = 2000


def aktif():
    """Kalici gecmis kullanilabilir mi? Semayi da hazirlar (idempotent)."""
    from chat import veritabani
    if not veritabani.hazir():
        return False
    return veritabani.hazirla()


def _json(mesaj):
    try:
        return json.dumps(mesaj, ensure_ascii=False)
    except (TypeError, ValueError):
        return None


def ekle(kid, mesajlar):
    """Mesajlari sirayla ekler. Donus: yazilan satir sayisi (0 = hata).

    Ekleme tek islemde yapilir; oku-degistir-yaz YOK. Iki ornek ayni anda
    yazsa bile hicbir mesaj digerini ezmez.
    """
    kid = str(kid or "").strip()
    kayitlar = [m for m in (mesajlar or [])
                if isinstance(m, dict) and _json(m)]
    if not kid or not kayitlar:
        return 0
    if not aktif():
        return 0
    from chat import veritabani
    try:
        with veritabani.baglanti() as conn:
            with conn.cursor() as cur:
                for mesaj in kayitlar:
                    cur.execute(
                        "INSERT INTO %s (kullanici, rol, icerik, oturum) "
                        "VALUES (%%s, %%s, %%s, %%s)" % TABLO,
                        (kid, str(mesaj.get("role") or ""),
                         _json(mesaj), str(mesaj.get("oturum") or "")))
                _kirp(cur, kid)
        return len(kayitlar)
    except Exception:
        logger.warning("Gecmis yazilamadi (kullanici=%s)", kid, exc_info=True)
        return 0


def _kirp(cur, kid):
    cur.execute("SELECT COUNT(*) FROM %s WHERE kullanici=%%s" % TABLO,
                (kid,))
    satir = cur.fetchone()
    adet = int(satir[0] if satir else 0)
    if adet <= SATIR_TAVANI:
        return
    cur.execute(
        "DELETE FROM %s WHERE kullanici=%%s AND seq IN ("
        "SELECT seq FROM %s WHERE kullanici=%%s "
        "ORDER BY seq ASC LIMIT %%s)" % (TABLO, TABLO),
        (kid, kid, adet - SATIR_TAVANI))


def oku(kid, limit=400):
    """Son `limit` mesaji kronolojik sirada dondurur (bozuksa [])."""
    kid = str(kid or "").strip()
    if not kid or not aktif():
        return []
    from chat import veritabani
    try:
        with veritabani.baglanti() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT icerik FROM %s WHERE kullanici=%%s "
                    "ORDER BY seq DESC LIMIT %%s" % TABLO,
                    (kid, int(limit)))
                satirlar = cur.fetchall()
        mesajlar = []
        for (ham,) in reversed(satirlar):
            try:
                mesaj = json.loads(ham)
            except (TypeError, ValueError):
                continue
            if isinstance(mesaj, dict):
                mesajsiz = {k: v for k, v in mesaj.items() if k != "seq"}
                mesajlar.append(mesajsiz)
        return mesajlar
    except Exception:
        logger.warning("Gecmis okunamadi (kullanici=%s)", kid, exc_info=True)
        return []


def temizle(kid):
    """Kullanicinin gecmisini siler (yeni sohbet). Donus: True/False."""
    kid = str(kid or "").strip()
    if not kid or not aktif():
        return False
    from chat import veritabani
    try:
        with veritabani.baglanti() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM %s WHERE kullanici=%%s" % TABLO,
                            (kid,))
        return True
    except Exception:
        logger.warning("Gecmis silinemedi (kullanici=%s)", kid, exc_info=True)
        return False
