"""hafiza_olcum.py - Hafiza arama dogruluk olcumu (kod degistirmez).

    python hafiza_olcum.py            # BM25-only; cevrimdisi, kota yok
    python hafiza_olcum.py --canli    # + Gemini anlam vektoru (KOTA HARCAR)
    python hafiza_olcum.py --k 4      # ilk k sonuca bakar (varsayilan 4)

Neden var: hafiza SESSIZCE bozulabilir (parcalama, RRF birlestirme, FTS
indeksi, budama). Sabit kayit/soru seti + sabit esik, bir degisiklikten
sonra "hala dogru hatirliyor mu?" sorusunu sayiyla cevaplar. Bu, hiz_olcum.py
kulturunun hafiza tarafidir.

Iki set ayri raporlanir:
  KELIME - soru, kayitla ortak kelime tasir. BM25 bunlari BULMAK ZORUNDA;
           cevrimdisi taban esigi 1.00'dir (altina duserse regresyon).
  ANLAM  - soru, kayitla ortak kelime TASIMAZ; yalniz anlam vektoru bulur.
           Vektor yoksa "olculmedi" yazilir, TAHMIN DOLDURULMAZ.
"""

import os
import sys
import tempfile

BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from memory.engine import HafizaMotoru  # noqa: E402

KAYNAK = "hafiza-olcum"
VARSAYILAN_K = 4
KELIME_ESIGI = 1.00

# (kayit metni, soru, cevapta gorunmesi gereken parca)
KELIME_SETI = (
    ("Casper'in favori cay markasi Caykur.", "favori cay markasi", "Caykur"),
    ("Final sinavi 25 Agustos tarihinde.", "final sinavi tarihi", "25 Agustos"),
    ("Anne dogum gunu 3 Ekim.", "anne dogum gunu", "3 Ekim"),
    ("Basak projesi Python ile yazildi.", "Basak projesi hangi dilde", "Python"),
    ("Vixrex hazir vitrin kiralamadir.", "Vixrex vitrin modeli", "kirala"),
    ("NumeraMatch numeroloji temelli uygulamadir.", "NumeraMatch nedir", "numeroloji"),
    ("Ses modeli piper TTS ile calisir.", "ses modeli hangisi", "piper"),
    ("Hafiza motoru SQLite uzerinde durur.", "hafiza motoru nerede", "SQLite"),
    ("Zincirde groq en hizli saglayicidir.", "en hizli saglayici", "groq"),
    ("Mistral telefon dogrulamasi ister.", "Mistral dogrulama ister mi", "telefon"),
    ("Fatura fotografi katalog uretir.", "fatura ne uretir", "katalog"),
    ("Kabul matrisi 364 hucreden olusur.", "kabul matrisi kac hucre", "364"),
)

# Soru ile kayit arasinda ortak anlamli kelime YOK - yalniz vektor bulur.
ANLAM_SETI = (
    ("Kullanici kendini cok yorgun ve bitkin hissediyor.",
     "uykusuzluk ve halsizlik sikayeti", "yorgun"),
    ("Tatilde deniz kenarinda kitap okudu.", "plajda edebiyat", "kitap"),
    ("Bilgisayar islemcisi cok isiniyor.", "makine sicaklik sorunu", "isiniyor"),
    ("Kedisi her sabah mama istiyor.", "ev hayvani kahvalti bekliyor", "mama"),
    ("Sinemada korku filmi izledi.", "gala gecesi perde", "film"),
)


def _ekle(motor, seti):
    for metin, _, _ in seti:
        motor.ekle(metin, kind="semantic", kaynak=KAYNAK)


def _sorgula(motor, seti, k):
    """Her soruyu kosar; (soru, beklenen, isabet) listesi doner."""
    satirlar = []
    for _, sorgu, beklenen in seti:
        sonuclar = motor.ara(sorgu, limit=k)
        metinler = [(s.get("text") or "").lower() for s in sonuclar]
        isabet = any(beklenen.lower() in m for m in metinler)
        satirlar.append((sorgu, beklenen, isabet))
    return satirlar


def _vektor_sayisi(motor):
    try:
        return motor.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE has_vec=1").fetchone()[0]
    except Exception:
        return 0


def kos(db_yolu, k=VARSAYILAN_K, embed_fn=None,
        kelime_seti=KELIME_SETI, anlam_seti=ANLAM_SETI):
    """Setleri temiz bir DB'ye yazip sorar; sayilarla rapor doner."""
    motor = HafizaMotoru(db_yolu=db_yolu, embed_fn=embed_fn)
    try:
        _ekle(motor, kelime_seti)
        _ekle(motor, anlam_seti)
        vektor_olculdu = _vektor_sayisi(motor) > 0
        kelime = _sorgula(motor, kelime_seti, k)
        anlam = _sorgula(motor, anlam_seti, k) if vektor_olculdu else []
    finally:
        motor.kapat()

    def _oran(satirlar):
        if not satirlar:
            return None
        return sum(1 for _, _, i in satirlar if i) / len(satirlar)

    return {
        "k": k,
        "kelime": kelime,
        "anlam": anlam,
        "kelime_orani": _oran(kelime),
        "anlam_orani": _oran(anlam),
        "vektor_olculdu": vektor_olculdu,
    }


def _k_al(argv, varsayilan):
    if "--k" in argv:
        i = argv.index("--k")
        if i + 1 < len(argv) and argv[i + 1].isdigit():
            return max(1, int(argv[i + 1]))
    return varsayilan


def _yaz(metin):
    try:
        print(metin, flush=True)
    except UnicodeEncodeError:
        print(metin.encode("ascii", "replace").decode("ascii"), flush=True)


def _canli_embed_fn():
    try:
        from brain.gemini_embed import embed_fn
        return embed_fn
    except Exception as e:  # noqa: BLE001
        _yaz("canli vektor fonksiyonu alinamadi: %s" % e)
        return None


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    canli = "--canli" in argv
    k = _k_al(argv, VARSAYILAN_K)
    embed_fn = _canli_embed_fn() if canli else None

    with tempfile.TemporaryDirectory() as tmp:
        rapor = kos(os.path.join(tmp, "hafiza-olcum.db"), k=k,
                    embed_fn=embed_fn)

    mod = "BM25 + anlam vektoru" if rapor["vektor_olculdu"] else "BM25-only"
    _yaz("Hafiza dogruluk olcumu (k=%d, mod=%s)" % (k, mod))
    _yaz("")
    _yaz("KELIME seti - BM25 bulmak ZORUNDA")
    for sorgu, beklenen, isabet in rapor["kelime"]:
        _yaz("  %s %-34s -> %s" % ("[OK]" if isabet else "[--]",
                                   sorgu, beklenen))
    oran = rapor["kelime_orani"]
    _yaz("  isabet: %d/%d = %.2f (esik %.2f)"
         % (sum(1 for _, _, i in rapor["kelime"] if i), len(rapor["kelime"]),
            oran, KELIME_ESIGI))
    _yaz("")
    _yaz("ANLAM seti - yalniz vektor bulur")
    if not rapor["vektor_olculdu"]:
        _yaz("  olculmedi (vektor yok) - icin: python hafiza_olcum.py --canli")
    else:
        for sorgu, beklenen, isabet in rapor["anlam"]:
            _yaz("  %s %-34s -> %s" % ("[OK]" if isabet else "[--]",
                                       sorgu, beklenen))
        _yaz("  isabet: %d/%d = %.2f (olcum; esik yok)"
             % (sum(1 for _, _, i in rapor["anlam"] if i),
                len(rapor["anlam"]), rapor["anlam_orani"]))

    return 1 if oran < KELIME_ESIGI else 0


if __name__ == "__main__":
    sys.exit(main())
