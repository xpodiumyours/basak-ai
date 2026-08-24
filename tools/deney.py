"""tools/deney.py — Deney motoru tohumu (DENEY-0, kilitli hedef).

Felsefe (Casper'in vizyonu): LLM "bence X daha iyi" dediginde bunun
hicbir degeri yoktur. Hipotez OLCULEBILIR deneye donusur, arac gercekten
kosturulur, KURAL karar verir.

Deney tanimi:
    {"iddia":   "VixRex main dalindadir",
     "arac":    "git_durum",
     "arguman": {"proje": "vixrex"},
     "kural":   "icerir",
     "beklenen": "Dal: main"}

Kurallar:
- icerir   : cikti, beklenen metni birebir icermeli
- yok      : cikti, beklenen metni ICERMEMELI
- esik_ust : ciktaki ilk sayi >= beklenen (orn "%87.3" >= 80)
- esik_alt : ciktaki ilk sayi <= beklenen

Guvenlik: yalnizca beyaz listeli SALT-OKUNUR olcum araclarina izin verilir;
executor'un kendi permission katmani ustune ekstra kilittir.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Deney kosulabilen SALT-OKUNUR araclar (yazma/sistem/internet-yazma yok)
IZINLI_DENET_ARACLARI = frozenset((
    "git_durum", "belge_ara", "dosya_bilgi", "web_search",
    "sayfa_oku", "list_files", "read_file", "list_tasks",
    "get_reminders", "model_stats",
))

_KURALLAR = frozenset(("icerir", "yok", "esik_ust", "esik_alt"))
_SAYI_DESENI = re.compile(r"-?\d+(?:[.,]\d+)?")


def _ilk_sayi(metin):
    """Metindeki ilk sayiyi float olarak dondurur; yoksa None."""
    m = _SAYI_DESENI.search(metin or "")
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", "."))
    except ValueError:
        return None


def _degerlendir(deney, cikti):
    """Kurala gore ciktiyi degerlendirir: (desteklendi, aciklama)."""
    kural = deney.get("kural")
    beklenen = deney.get("beklenen")

    if kural == "icerir":
        return (str(beklenen) in cikti,
                'ciktida "%s" aranadi' % str(beklenen)[:60])
    if kural == "yok":
        return (str(beklenen) not in cikti,
                'ciktida "%s" OLMAMASI istendi' % str(beklenen)[:60])
    if kural in ("esik_ust", "esik_alt"):
        deger = _ilk_sayi(cikti)
        if deger is None:
            return None, "ciktada sayi bulunamadi"
        sinir = float(beklenen)
        if kural == "esik_ust":
            return deger >= sinir, "%s >= %s" % (deger, sinir)
        return deger <= sinir, "%s <= %s" % (deger, sinir)
    return None, "bilinmeyen kural: %s" % kural


def deney_yurut(deneyler, calistir):
    """Deneyleri sirayla kosturur; rapor dondurur.

    deneyler: yukaridaki bicimde sozluk listesi.
    calistir: tools.executor.calistir imzali fonksiyon
              (uretimde executor.calistir, testte sahte).
    Donus: [{"iddia", "arac", "durum", "kanit"}]
      durum: desteklendi | elenmis | hata | reddedildi
      kanit: ham cikti/hata/aciklamanin ilk 200 karakteri
    """
    rapor = []
    for deney in (deneyler or []):
        iddia = (deney.get("iddia") or "").strip()
        arac = (deney.get("arac") or "").strip()
        arguman = deney.get("arguman") or {}

        kayit = {"iddia": iddia, "arac": arac}

        if arac not in IZINLI_DENET_ARACLARI:
            kayit["durum"] = "reddedildi"
            kayit["kanit"] = "'%s' araci deney icin beyaz listede degil" % arac
            rapor.append(kayit)
            continue
        if deney.get("kural") not in _KURALLAR:
            kayit["durum"] = "hata"
            kayit["kanit"] = "bilinmeyen kural"
            rapor.append(kayit)
            continue

        try:
            sonuc = calistir(arac, arguman)
        except Exception as e:
            kayit["durum"] = "hata"
            kayit["kanit"] = str(e)[:200]
            rapor.append(kayit)
            continue

        if not isinstance(sonuc, dict) or sonuc.get("error"):
            kayit["durum"] = "hata"
            kayit["kanit"] = str(sonuc.get("error", "bos sonuc"))[:200]
            rapor.append(kayit)
            continue

        cikti = str(sonuc.get("result", ""))
        tamam, aciklama = _degerlendir(deney, cikti)

        if tamam is None:
            kayit["durum"] = "hata"
            kayit["kanit"] = aciklama[:200]
        elif tamam:
            kayit["durum"] = "desteklendi"
            kayit["kanit"] = ("%s | %s | %s" % (aciklama, cikti[:120],
                                                ""))[:200].strip()
        else:
            kayit["durum"] = "elenmis"
            kayit["kanit"] = ("%s | %s" % (aciklama, cikti[:140]))[:200]

        rapor.append(kayit)
        logger.info("Deney [%s] %s: %s", kayit.get("arac"),
                    kayit.get("durum"), iddia[:60])
    return rapor
