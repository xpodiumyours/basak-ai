"""tests/live/arac_disiplini.py — Arac cagirma disiplini probu (GERCEK KOTA).

Neden: README §9'daki acik sorun "model araci CAGIRMAK yerine TARIF ediyor".
Bu prob o soruyu her seferinde ayni sorularla, sayiyla olcer; degisiklikten
sonra "duzeldi mi, bozuldu mu?" karsilastirmasi yapilabilir.

    python tests/live/arac_disiplini.py                 # hepsi
    python tests/live/arac_disiplini.py --senaryo 2      # tek senaryo

DIKKAT: gercek bulut cagrisi yapar, KOTA HARCAR. Casper'in onayi olmadan
kosulmaz. Uygulama davranisini DEGISTIRMEZ; yalniz olcer.

Hicbir senaryo YAZMA yapan arac istemez; kosan araclar salt-okunur
(list_files, simdi, hesapla, git_gecmis, read_file, icerik_ara). Boylece
probu kosmak Casper'in gorev/hafiza verisini degistirmez.
"""

import json
import os
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, BASE)

# (etiket, mesaj, beklenen araclardan en az biri)
SENARYOLAR = (
    # 2026-09-22 ilk kosu: "bilgisayarimda hangi klasorler var" TARIF cikti —
    # ama model hakli olarak "hangi klasor?" diye sordu. Senaryo belirsizdi,
    # ariza degildi. Yol acikca verilir ki olcum arac cagirmayi olcsun.
    ("klasor listele",
     "C:\\Users\\Casper klasorunde neler var, listeler misin",
     ("list_files",)),
    ("saat", "su an saat kac", ("simdi",)),
    ("hesap", "128 carpi 47 kac eder", ("hesapla",)),
    ("git gecmis", "basak deposunda son commit mesajlari ne",
     ("git_gecmis", "git_durum")),
    ("dosya oku", "README dosyasinda ne yaziyor, oku", ("read_file",)),
    ("icerik ara", "basak projesinde ARAC gecen yerleri bul",
     ("icerik_ara", "belge_ara")),
    # Arac GEREKMEYEN kontrol senaryosu: model gereksiz arac cagirmamali.
    ("duz sohbet", "merhaba, bugun nasilsin", ()),
)


def _olaylari_ayikla(olaylar):
    """BasakUI olaylarindan cevap / kaynak / hata cikarir."""
    cevap = kaynak = hata = ""
    for code in olaylar:
        try:
            if code.startswith("BasakUI.bitir("):
                ic = code[code.index("(") + 1: code.rindex(")")]
                degerler = json.loads("[" + ic + "]")
                cevap = str(degerler[0] or "")
                if len(degerler) > 1:
                    kaynak = str(degerler[1] or "")
            elif code.startswith("BasakUI.error("):
                ic = code[code.index("(") + 1: code.rindex(")")]
                hata = str(json.loads("[" + ic + "]")[0] or "")
        except Exception:
            # Bozuk olay probu durdurmasin; ham metni tanik olarak sakla.
            if code.startswith("BasakUI.error("):
                hata = code
            elif code.startswith("BasakUI.bitir(") and not cevap:
                cevap = code
    return cevap, kaynak, hata


def _durum_bul(kosulan, beklenen, hata):
    """Bir senaryonun sonucunu siniflandirir (ag YOK; saf karar).

    ARAC       = beklenen gercek arac kostu
    TARIF      = model araci cagirmadi, anlatti (README 9 sorunu)
    TEMIZ      = arac gerekmiyordu ve hic kosmadi
    FAZLA_ARAC = arac gerekmiyordu ama model yine de cagirdi
    HATA       = tur hata ile bitti
    """
    if hata:
        return "HATA"
    if beklenen:
        return "ARAC" if any(ad in beklenen for ad in kosulan) else "TARIF"
    return "TEMIZ" if not kosulan else "FAZLA_ARAC"


def _senaryo_kos(brain, tools, etiket, mesaj, beklenen):
    """Tek senaryoyu gercek mesaj_isle hattindan kosar."""
    from chat.flow import mesaj_isle
    from chat import context as ctx
    import tools as tools_mod
    from chat import oturum as oturum_mod

    kosulan = []
    gercek_calistir = tools_mod.calistir

    def kayitli_calistir(ad, args):
        kosulan.append(ad)
        return gercek_calistir(ad, args)

    tools_mod.calistir = kayitli_calistir
    eski_oturum = oturum_mod.kaydet_cift
    oturum_mod.kaydet_cift = lambda *a, **k: None
    olaylar = []
    try:
        with tempfile.TemporaryDirectory() as td:
            ctx.HISTORY_FILE = os.path.join(td, "gecmis.json")
            ctx.SETTINGS_FILE = os.path.join(td, "ayar.json")
            ctx._hafiza = False
            mesaj_isle(mesaj, brain, "Sen Basak'sin. Turkce konus.",
                       olaylar.append, tools)
    finally:
        tools_mod.calistir = gercek_calistir
        oturum_mod.kaydet_cift = eski_oturum

    cevap, kaynak, hata = _olaylari_ayikla(olaylar)

    durum = _durum_bul(kosulan, beklenen, hata)

    return {"etiket": etiket, "mesaj": mesaj, "durum": durum, "kaynak": kaynak,
            "kosulan": kosulan, "hata": hata, "cevap": cevap[:120]}


def _yaz(metin):
    try:
        print(metin, flush=True)
    except UnicodeEncodeError:
        print(metin.encode("ascii", "replace").decode("ascii"), flush=True)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    from brain.brain import Brain
    from tools import TOOLS

    brain = Brain()
    if not brain._bulut_zinciri(tools=True, tool_required=True):
        _yaz("Hicbir ajan saglayici hazir degil; prob kosulamaz.")
        return 1

    secilen = SENARYOLAR
    if "--senaryo" in argv:
        i = argv.index("--senaryo")
        if i + 1 < len(argv) and argv[i + 1].isdigit():
            n = int(argv[i + 1]) - 1
            if not 0 <= n < len(SENARYOLAR):
                _yaz("Gecersiz senaryo numarasi.")
                return 1
            secilen = (SENARYOLAR[n],)

    _yaz("Arac disiplini probu — GERCEK kota harcar (%d senaryo)"
         % len(secilen))
    _yaz("")
    sonuclar = []
    for etiket, mesaj, beklenen in secilen:
        s = _senaryo_kos(brain, TOOLS, etiket, mesaj, beklenen)
        sonuclar.append(s)
        _yaz("%-5s %-16s kaynak=%-10s kosulan=%s"
             % (s["durum"], etiket, s["kaynak"] or "-",
                ", ".join(s["kosulan"]) or "yok"))
        if s["durum"] == "TARIF":
            _yaz("      -> model araci tarif etti, cagirmadi: %s"
                 % s["cevap"])
        if s["hata"]:
            _yaz("      -> hata: %s" % s["hata"])

    basarili = sum(1 for s in sonuclar if s["durum"] in ("ARAC", "TEMIZ"))
    _yaz("")
    _yaz("OZET: %d/%d beklenen davranis"
         % (basarili, len(sonuclar)))
    _yaz("  ARAC=%d  TARIF=%d  TEMIZ=%d  FAZLA_ARAC=%d  HATA=%d"
         % (sum(1 for s in sonuclar if s["durum"] == "ARAC"),
            sum(1 for s in sonuclar if s["durum"] == "TARIF"),
            sum(1 for s in sonuclar if s["durum"] == "TEMIZ"),
            sum(1 for s in sonuclar if s["durum"] == "FAZLA_ARAC"),
            sum(1 for s in sonuclar if s["durum"] == "HATA")))
    if any(s["durum"] == "TARIF" for s in sonuclar):
        _yaz("  TARIF = README 9'daki acik sorun (araci cagirmak yerine"
             " tarif etmek).")
    return 0 if basarili == len(sonuclar) else 1


if __name__ == "__main__":
    sys.exit(main())
