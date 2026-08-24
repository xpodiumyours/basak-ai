"""tools/fay.py — FAY-0: tek konu, üç tanık, jürisiz çarpıştırıcı.

Kilitli hedef / FAY-MOTORU.md §FAY-0 (ilk hedef):
- Taniklar: belge, git, dosya — UCTAN UCA OLCEM; yapay zeka uretmez.
- Carpistirma: TEK yerel model; juri yok (FAY-1'de gelecek).
- Cikti: tek kart (Basak sohbetinde).

Karar hirsizligina karsi iki savunma:
1. Tanik iddialari yalnizca olcum arac ciktisindan gelir — model uretmez.
2. Modelin isaret ettigi tanik adi tanik listesinde yoksa yanit REDDEDILIR
   (uydurma celiski karta giremez).

Motor hicbir seyi duzeltmez; gosterir ve sorar. Karar Casper'in.
"""

import logging
import threading

logger = logging.getLogger(__name__)

# FAY-0 tanik araclari — hepsi salt-okunur olcum (permissions.py ile uyumlu)
_FAY_ARACLARI = frozenset(("git_durum", "belge_ara", "dosya_bilgi"))

_TANIK_ETIKET = {"git_durum": "git", "belge_ara": "belge",
                 "dosya_bilgi": "dosya"}


def tanik_iddialari(proje, belge_sorgu, kritik_dosya, calistir,
                    kanit_siniri=160):
    """Uc olcen taniktan iddia toplar; basarisiz tanik sessizce atlanir.

    Donus: [{"tanik": "git|belge|dosya", "iddia": str, "kanit": str}]
    """
    istekler = (
        ("git", "git_durum", {"proje": proje}),
        ("belge", "belge_ara",
         {"proje": proje, "sorgu": belge_sorgu}),
        ("dosya", "dosya_bilgi",
         {"proje": proje, "yol": kritik_dosya}),
    )

    iddialar = []
    for etiket, arac, arguman in istekler:
        try:
            sonuc = calistir(arac, arguman)
        except Exception as e:
            logger.warning("FAY tanigi hata verdi (%s): %s", etiket, e)
            continue
        if not isinstance(sonuc, dict) or sonuc.get("error"):
            logger.info("FAY tanigi vermedi (%s)", etiket)
            continue
        metin = str(sonuc.get("result", "")).strip()
        if not metin:
            continue
        iddialar.append({
            "tanik": etiket,
            "iddia": metin[:150],
            "kanit": metin[:300],
        })
    return iddialar


def _yanit_coz(yanit_metni, tanik_adlari):
    """Model yanitindan catismayi ayiklar; uydurmaya kapali.

    Donus: (tanik1, tanik2, gerekce) veya None.
    """
    metin = (yanit_metni or "").strip()
    if "[celisiyor]" not in metin.lower():
        return None                      # sorun yok / anlasilamadi -> catlak yok
    satir = next((s for s in metin.splitlines()
                  if "[celisiyor]" in s.lower()), "")
    # tanik adlarinin hepsi gercek listede mi?
    adlar = [t for t in tanik_adlari if t in satir.lower()]
    if len(adlar) < 2:
        return None                      # uydurma/yarim tanik adi -> reddet
    t1, t2 = adlar[0], adlar[1]
    gerekce = satir.split(":", 1)[-1].strip()[:200]
    return t1, t2, gerekce


def carpistir(iddialar, beyin_cevapla):
    """Tek yerel modele iddialari gonderir; catisma bulursa ciftini dondurur.

    beyin_cevapla(messages) -> {"content": str} benzeri donus beklenir
    (uretimde brain._ollama.cevapla sarilir).
    Donus: {"cift": (t1, t2), "gerekce": str} veya None.
    """
    if len(iddialar) < 2:
        return None
    tanik_satirlari = "\n".join(
        "- %s: %s" % (i["tanik"], i["iddia"]) for i in iddialar)
    talimat = (
        "Ayni konu hakkinda farkli olcum kaynaklarinin soyledikleri:\n"
        + tanik_satirlari + "\n\n"
        "Gorev: birbiriyle CELISEN ilk ikiliyi bul.\n"
        "Yalnizca yukarida verilen kaynak adlarini kullan; yeni kaynak "
        "uydurma. Kendi bilgini katma.\n"
        "Cevap bicimi (ZORUNLU):\n"
        "[CELISIYOR] <kaynak1> vs <kaynak2>: tek cumlelik gerekce\n"
        "Celisme yoksa: [SORUN YOK]"
    )
    messages = [{"role": "user", "content": talimat}]
    try:
        yanit = beyin_cevapla(messages)
    except Exception as e:
        logger.warning("FAY carpistirici hatasi: %s", e)
        return None
    icerik = yanit.get("content") if isinstance(yanit, dict) else str(yanit)
    cozum = _yanit_coz(icerik, [i["tanik"] for i in iddialar])
    if cozum is None:
        return None
    return {"cift": (cozum[0], cozum[1]), "gerekce": cozum[2]}


# ---------------------------------------------------------------------------
# FAY-1: Paralel jüri (2026-08-24, kilitli hedef)
#
# Organ 2'nin tam hali: çelişki sorusu AYNI ANDA birden fazla ücretsiz
# sağlayıcıya gider (kotalar ayrı olduğundan paralel maliyet = sıfır).
# Oylar sayılır:
#   - tum uyeler CELISIYOR  -> "kesin" catlak
#   - cogunluk celisiyor ama bolum var -> "bolunme" — insan kararı
#     tam olarak burada gerekir; karsi oy gerekcesiyle kayda gecer
#   - cogunluk SORUN YOK    -> sessizce atilir
# Uydurma savunmasi uye basina devam eder: tanik adi uyduran oy SAYILMAZ.
# ---------------------------------------------------------------------------


def _juri_oyu(uye_adi, beyin_cevapla, iddialar):
    """Tek jüri üyesinin oyunu toplar; uydurma/hata oyu atılır."""
    tanik_adlari = [i["tanik"] for i in iddialar]

    def cevapla(messages):
        return beyin_cevapla(messages)

    try:
        yanit = cevapla([{"role": "user",
                          "content": _juri_talimat(iddialar)}])
    except Exception as e:
        return {"uye": uye_adi, "oy": None, "gerekce": str(e)[:120]}

    icerik = yanit.get("content") if isinstance(yanit, dict) else str(yanit)
    cozum = _yanit_coz(icerik, tanik_adlari)
    if cozum is None:
        # [SORUN YOK] mu, yoksa anlasilamayan/uydurma mi?
        if "[sorun yok]" in (icerik or "").lower():
            return {"uye": uye_adi, "oy": False,
                    "gerekce": "tutarli buldu"}
        return {"uye": uye_adi, "oy": None,
                "gerekce": "yanit ayristirilamadi/uydurma"}
    t1, t2, gerekce = cozum
    return {"uye": uye_adi, "oy": True,
            "cift": (t1, t2), "gerekce": gerekce}


def _juri_talimat(iddialar):
    tanik_satirlari = "\n".join(
        "- %s: %s" % (i["tanik"], i["iddia"]) for i in iddialar)
    return (
        "Ayni konu hakkinda farkli olcum kaynaklarinin soyledikleri:\n"
        + tanik_satirlari + "\n\n"
        "Gorev: birbiriyle CELISEN ilk ikiliyi bul.\n"
        "Yalnizca yukarida verilen kaynak adlarini kullan; yeni kaynak "
        "uydurma. Kendi bilgini katma.\n"
        "Cevap bicimi (ZORUNLU):\n"
        "[CELISIYOR] <kaynak1> vs <kaynak2>: tek cumlelik gerekce\n"
        "Celisme yoksa: [SORUN YOK]"
    )


def juri_carpistir(iddialar, juri_uyeleri):
    """Paralel jüri: tüm üyeler aynı anda oy verir.

    juri_uyeleri: [(uye_adi, beyin_cevapla_fn), ...]
    Dönüş: {"karar": "kesin|bolunme|yok|belirsiz",
            "celisen_cift": (t1,t2)|None,
            "oylar": [{uye, oy, gerekce}, ...]}
      oy: True=çelişiyor, False=sorun yok, None=geçersiz/uydurma
    """
    iddialar = list(iddialar)
    if len(iddialar) < 2:
        return {"karar": "yok", "celisen_cift": None,
                "oylar": []}

    oylar = []
    kilit = threading.Lock()

    def uye_kos(uye):
        adi, fn = uye
        oy = _juri_oyu(adi, fn, iddialar)
        with kilit:
            oylar.append(oy)

    threads = [threading.Thread(target=uye_kos, args=(u,))
               for u in juri_uyeleri]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Oylari sirala (uye sirasiyla) — rapor deterministik olsun
    sira = {u[0]: i for i, u in enumerate(juri_uyeleri)}
    oylar.sort(key=lambda o: sira.get(o["uye"], 99))

    celisioran = [o for o in oylar if o["oy"] is True]
    reddedilen = [o for o in oylar if o["oy"] is None]
    gecerli = len(oylar) - len(reddedilen)

    # Karar tablosu (FAY-MOTORU.md Organ 2):
    #   tüm geçerli oylar çelişiyor          -> kesin
    #   çelişenler >= sorun-yoklar ve karışık -> bolunme (insan kararı)
    #   çelişenler azınlıkta / hiç yok        -> yok (sessizce atılır)
    # Geçersiz (uydurma/hata) oylar karara katılmaz.
    gelen_celis = [o for o in oylar if o["oy"] is True]
    gelen_yok = [o for o in oylar if o["oy"] is False]

    if gelen_celis and not gelen_yok:
        karar = "kesin"
    elif gelen_celis and len(gelen_celis) >= len(gelen_yok):
        karar = "bolunme"
    else:
        karar = "yok"

    celisen_cift = None
    for o in celisioran:
        if "cift" in o:
            celisen_cift = o["cift"]
            break

    sonuc = {"karar": karar, "celisen_cift": celisen_cift, "oylar": oylar}
    logger.info("FAY jürisi: %s (%d oy, %d geçersiz)", karar,
                len(celisioran), len(reddedilen))
    return sonuc


def kart_olustur(konu, iddialar, catisma=None):
    """Organ 5 sozlesmesinin FAY-0 hali: tek kart, kanitli."""
    satirlar = ["FAY — %s" % konu]
    for i in iddialar:
        satirlar.append("  %s diyor: %s" % (i["tanik"], i["iddia"]))
    if catisma:
        t1, t2 = catisma["cift"]
        satirlar.append("")
        satirlar.append("  CATISMA: %s <-> %s" % (t1, t2))
        satirlar.append("  Gerekce: %s" % catisma["gerekce"])
        satirlar.append("  Soru: hangisi dogru? Olcmek icin ne gerekiyor?")
    else:
        satirlar.append("  Belirgin catisma bulunamadi.")
    return "\n".join(satirlar)


def fay0_karti(proje, belge_sorgu, kritik_dosya, calistir,
               beyin_cevapla=None, konu=None):
    """FAY-0 ana girisi: uc tanik + carpistirma + tek kart.

    Donus: {"kart": str, "iddiar": [...], "catisma": {...}|None}
    """
    konu = konu or ("%s durum ozeti" % proje)
    iddialar = tanik_iddialari(proje, belge_sorgu, kritik_dosya, calistir)
    catisma = None
    if beyin_cevapla is not None:
        catisma = carpistir(iddialar, beyin_cevapla)
    kart = kart_olustur(konu, iddialar, catisma)
    return {"kart": kart, "iddialar": iddialar, "catisma": catisma}
