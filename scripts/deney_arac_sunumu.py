"""DENEY: Araclar modele nasil sunulmali? (canli / P2 / aday)

Uc duzen, AYNI gorevlerle, AYNI gercek saglayicilarda olculur:

  CANLI  main'deki duzen: ilk turda yalniz `yetenek_ac`; model alan secer,
         o alanin araclari acilir (chat/agent_protocol.py, AJAN_SOZLESMESI).
  P2     preview/p2-arac-ara-profesyonel@8b3fd4b duzeni: 53 aracin tamami
         ilk turda (chat/agent_runtime.py AGENT_CONTRACT).
  ADAY   Anthropic "custom tool search" deseni: ilk turda yalniz
         `arac_ara`; MODEL bir sorgu yazar, katalogda aranir, bulunan en
         fazla 5 arac acilir. Kod kullanici cumlesine bakmaz; yalniz
         modelin yazdigi sorguyu katalogda arar. Sozlesme P2 ile ayni,
         yalniz arac sunumu farkli (tek degisken).

Olculen: modelin ilk GERCEK arac cagrisi beklenen kumede mi? Arac
gereken iste aracsiz cevap (ezber) orani, gereksiz arac, hata, cagri
sayisi, giris token'i.

Gorevler ve "dogru" kumeleri OLCUMDEN ONCE sabitlendi (asagida). Gercek
araclar CALISTIRILMAZ; olculen yalniz modelin karari.

Kosum: python scripts/deney_arac_sunumu.py [--sahte]
  --sahte: anahtarsiz, sahte saglayiciyla boru hattini dogrular.
"""

import json
import os
import re
import sys
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)

RAPOR_MD = "deney-arac-sunumu.md"
RAPOR_JSON = "deney-arac-sunumu.json"

KIMLIK = "Sen Başak'sın. Türkçe konuş."

# preview/p2-arac-ara-profesyonel@8b3fd4b chat/agent_runtime.py
# AGENT_CONTRACT — birebir kopya (P2 dali bu dalda yok).
P2_SOZLESME = (
    "AJAN CALISMA SOZLESMESI:\n"
    "- Sana sunulan araclar Basak'in GERCEK capability registry'sidir.\n"
    "- Dis dunya, guncel durum, dosya/proje durumu veya gercek bir eylem "
    "gerekiyorsa uygun GERCEK araci cagir; arac adini tarif etmek is "
    "yapilmis sayilmaz.\n"
    "- Arac sonucunu gordukten sonra ayni ajan dongusunde yeniden karar ver; "
    "gerekirse baska gercek arac cagir.\n"
    "- Basarili arac sonucu olmadan bir eylemi yapilmis gibi soyleme.\n"
    "- Arama sonucu adaydir; okunmus/olculmus kaynak kanittir.\n"
    "- Hafizadaki eski Basak cevaplari kanit degildir; guncel arac sonucu "
    "ile celisirse arac sonucu ustundur."
)

# (gorev metni, kabul edilen gercek araclar). Bos kume = arac gerekmez.
GOREVLER = [
    ("İstanbul'da şu an hava nasıl?", {"hava_durumu"}),
    ("Şu an saat kaç, bugün günlerden ne?", {"simdi"}),
    ("1250 liranın yüzde 18 KDV'si ne kadar eder?", {"hesapla"}),
    ("Yarın için 'tedarikçiyi ara' diye bir görev ekle.", {"add_task"}),
    ("https://www.vixrex.com sayfasını aç ve ne anlattığını özetle.",
     {"sayfa_oku", "derin_oku"}),
    ("Yapay zekâ ile ilgili bu haftanın haberlerini bul.",
     {"haber_ara", "zamanli_ara", "web_search"}),
    ("Başak projesinin git durumunu göster: hangi daldayız, son commit ne?",
     {"git_durum", "git_gecmis"}),
    ("Hafızamda Vixrex hakkında ne kayıtlı?", {"hafiza_ara"}),
    ("Merhaba, nasılsın?", set()),
]

SAGLAYICILAR = (
    "groq", "gemini", "cloudflare", "kilo", "nvidia", "glm",
    "openrouter", "cohere", "mistral",
)
# Gunluk ucretsiz kotayi canli Basak'a birakmak icin saglayici basina
# cagri tavani (tavan dolunca kalan olcum "kota-tavani" diye raporlanir).
CAGRI_TAVANI = {"gemini": 14, "openrouter": 24}
VARSAYILAN_TAVAN = 60
BEKLEME_SN = float(os.environ.get("DENEY_BEKLEME_SN", "2"))
EN_FAZLA_TUR = 3

ARAC_ARA_ADI = "arac_ara"
ARAC_ARA = {
    "type": "function",
    "function": {
        "name": ARAC_ARA_ADI,
        "description": (
            "Basak'in arac katalogunda arar. Sorgu: ihtiyac duyulan yetenegin "
            "dogal dille tarifi. Doner: en uygun en fazla 5 aracin adi ve "
            "aciklamasi; donen araclar bir sonraki adimda cagrilabilir olur."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sorgu": {"type": "string",
                          "description": "Aranan yetenek"},
            },
            "required": ["sorgu"],
        },
    },
}


# ── Katalog arama (ADAY) ──────────────────────────────────────────────
_ASCII = str.maketrans("çğıöşüâîû", "cgiosuaiu")


def _kucuk(s):
    # Arac aciklamalari ASCII ("Hafizada"), kullanici/model Turkce
    # ("Hafızamda") yazar; karsilastirma harf-sadelestirilmis yapilir.
    s = str(s or "").replace("İ", "i").replace("I", "ı").lower()
    return s.translate(_ASCII)


def _kokler(metin):
    kelimeler = re.findall(r"[a-z0-9]+", _kucuk(metin))
    return {k[:4] for k in kelimeler if len(k) >= 2}


def _arac_metni(arac):
    f = arac["function"]
    parca = [f["name"].replace("_", " "), f.get("description", "")]
    for ad, ozellik in ((f.get("parameters") or {}).get("properties")
                        or {}).items():
        parca.append(ad)
        parca.append(str(ozellik.get("description", "")))
    return " ".join(parca)


def katalog_ara(tum_araclar, sorgu, adet=5):
    """Modelin sorgusunu katalogda arar (BM25 benzeri basit ortusme)."""
    sorgu_k = _kokler(sorgu)
    puanlar = []
    for sira, arac in enumerate(tum_araclar):
        puan = len(sorgu_k & _kokler(_arac_metni(arac)))
        if puan:
            puanlar.append((-puan, sira, arac))
    puanlar.sort(key=lambda x: (x[0], x[1]))
    return [a for _, _, a in puanlar[:adet]]


# ── Yardimcilar ───────────────────────────────────────────────────────
def _argumanlar(cagri):
    ham = (cagri.get("function") or {}).get("arguments")
    if isinstance(ham, dict):
        return ham
    try:
        return json.loads(ham or "{}")
    except Exception:
        return {}


def _ad(cagri):
    return (cagri.get("function") or {}).get("name") or ""


def _asistan_mesaji(yanit):
    m = {k: v for k, v in yanit.items() if not str(k).startswith("_")}
    m["role"] = "assistant"
    m.setdefault("content", "")
    return m


class KotaDoldu(Exception):
    pass


class Olcer:
    def __init__(self, beyin, istemci, ad, bitis=None):
        self.beyin, self.istemci, self.ad = beyin, istemci, ad
        self.cagri = 0
        self.tavan = CAGRI_TAVANI.get(ad, VARSAYILAN_TAVAN)
        self.bitis = bitis

    def cagir(self, mesajlar, araclar):
        if self.cagri >= self.tavan:
            raise KotaDoldu("kota-tavani")
        if self.bitis and time.time() > self.bitis:
            raise KotaDoldu("sure-siniri")
        self.cagri += 1
        if BEKLEME_SN:
            time.sleep(BEKLEME_SN)
        try:
            yanit = self.beyin._tek_cagri(
                self.istemci, self.ad, mesajlar, araclar, None, None,
                tool_choice="auto")
        except Exception as e:
            metin = str(e)
            if "429" in metin or "rate" in metin.lower():
                raise KotaDoldu("429: " + metin[:160])
            raise
        return yanit if isinstance(yanit, dict) else {"content": str(yanit)}


def _giris_token(yanit):
    k = yanit.get("_kullanim") or {}
    return int(k.get("giris") or 0)


# ── Uc duzen ──────────────────────────────────────────────────────────
def _meta_dongu(olcer, sistem, gorev, ilk_araclar, meta_adi, genislet,
                tum_adlar):
    """Meta-arac (yetenek_ac / arac_ara) ile en fazla EN_FAZLA_TUR tur."""
    mesajlar = [{"role": "system", "content": sistem},
                {"role": "user", "content": gorev}]
    araclar = list(ilk_araclar)
    token = 0
    meta_cagri = []
    for tur in range(1, EN_FAZLA_TUR + 1):
        yanit = olcer.cagir(mesajlar, araclar)
        token += _giris_token(yanit)
        cagrilar = yanit.get("tool_calls") or []
        if not cagrilar:
            return {"secim": None, "tur": tur, "token": token,
                    "meta": meta_cagri}
        gercek = [_ad(c) for c in cagrilar if _ad(c) != meta_adi]
        if gercek:
            sunulan = {(a.get("function") or {}).get("name")
                       for a in araclar}
            return {"secim": gercek[0], "tur": tur, "token": token,
                    "meta": meta_cagri,
                    "sunulmayan": gercek[0] not in sunulan,
                    "katalog_disi": gercek[0] not in tum_adlar}
        mesajlar.append(_asistan_mesaji(yanit))
        yeni = []
        for c in cagrilar:
            arg = _argumanlar(c)
            meta_cagri.append(arg)
            sonuc, acilan = genislet(arg)
            yeni.extend(acilan)
            mesajlar.append({"role": "tool", "tool_call_id": c.get("id"),
                             "name": meta_adi,
                             "content": json.dumps(sonuc, ensure_ascii=False)})
        adlar = set()
        araclar = []
        for a in yeni + list(ilk_araclar):
            n = a["function"]["name"]
            if n not in adlar:
                adlar.add(n)
                araclar.append(a)
    return {"secim": None, "tur": EN_FAZLA_TUR, "token": token,
            "meta": meta_cagri, "tur_bitti": True}


def duzen_canli(olcer, gorev, tum):
    from chat.agent_protocol import (
        AJAN_SOZLESMESI, YETENEK_AC_ADI, YETENEK_ALANLARI,
        alan_araclari, baslangic_araclari)

    def genislet(arg):
        alan = arg.get("alan")
        acilan = [a for a in alan_araclari(tum, alan)
                  if a["function"]["name"] != YETENEK_AC_ADI]
        return ({"acilan_alan": alan,
                 "kullanilabilir_araclar": [a["function"]["name"]
                                            for a in acilan]}, acilan)

    return _meta_dongu(olcer, KIMLIK + "\n\n" + AJAN_SOZLESMESI, gorev,
                       baslangic_araclari(), YETENEK_AC_ADI, genislet,
                       {a["function"]["name"] for a in tum})


def duzen_p2(olcer, gorev, tum):
    mesajlar = [{"role": "system", "content": KIMLIK + "\n\n" + P2_SOZLESME},
                {"role": "user", "content": gorev}]
    yanit = olcer.cagir(mesajlar, tum)
    cagrilar = yanit.get("tool_calls") or []
    return {"secim": _ad(cagrilar[0]) if cagrilar else None, "tur": 1,
            "token": _giris_token(yanit), "meta": []}


def duzen_aday(olcer, gorev, tum):
    def genislet(arg):
        bulunan = katalog_ara(tum, arg.get("sorgu", ""))
        return ([{"ad": a["function"]["name"],
                  "aciklama": a["function"].get("description", "")}
                 for a in bulunan], bulunan)

    return _meta_dongu(olcer, KIMLIK + "\n\n" + P2_SOZLESME, gorev,
                       [ARAC_ARA], ARAC_ARA_ADI, genislet,
                       {a["function"]["name"] for a in tum})


DUZENLER = (("CANLI", duzen_canli), ("P2", duzen_p2), ("ADAY", duzen_aday))


def sinifla(sonuc, beklenen):
    secim = sonuc.get("secim")
    if not beklenen:
        return "DOGRU" if secim is None else "GEREKSIZ_ARAC"
    if secim is None:
        return "TUR_BITTI" if sonuc.get("tur_bitti") else "ARACSIZ"
    if sonuc.get("katalog_disi") or sonuc.get("sunulmayan"):
        return "SUNULMAYAN_ARAC"
    return "DOGRU" if secim in beklenen else "YANLIS_ARAC"


# ── Kosum ─────────────────────────────────────────────────────────────
def _saglayici_kos(beyin, istemci, ad, tum, yaz, gorevler=None, bitis=None):
    """Tek saglayici, sirali ve beklemeli (kendi kotasi korunur)."""
    kayitlar = []
    olcer = Olcer(beyin, istemci, ad, bitis)
    durdu = ""
    for gorev, beklenen in (gorevler if gorevler is not None else GOREVLER):
        for duzen_adi, fonk in DUZENLER:
            kayit = {"saglayici": ad, "duzen": duzen_adi,
                     "gorev": gorev, "beklenen": sorted(beklenen)}
            if durdu:
                kayit.update(sinif="OLCULMEDI", hata=durdu)
            else:
                try:
                    sonuc = fonk(olcer, gorev, tum)
                    kayit.update(sonuc)
                    kayit["sinif"] = sinifla(sonuc, beklenen)
                except KotaDoldu as e:
                    durdu = str(e)
                    kayit.update(sinif="OLCULMEDI", hata=durdu)
                except Exception as e:
                    kayit.update(sinif="HATA", hata=str(e)[:300])
            kayitlar.append(kayit)
            yaz(kayit)
    return kayitlar


def parca_olc(beyin, tum, saglayici, bas, son):
    """Tek saglayici, GOREVLER[bas:son] — Vercel istek suresine sigsin diye.

    Donus: kayit listesi. Istemci yoksa tek 'istemci-yok' kaydi."""
    mevcut = dict(beyin._bulut_zinciri(tools=True))
    if saglayici not in mevcut:
        return [{"saglayici": saglayici, "durum": "istemci-yok"}]
    return _saglayici_kos(beyin, mevcut[saglayici], saglayici, tum,
                          lambda _k: None, GOREVLER[bas:son])


def _gunluge_yaz(kayit):
    # Vercel runtime log'una: istek zaman asimina ugrasa da sonuc kaybolmaz.
    print("DENEY_KAYIT " + json.dumps(kayit, ensure_ascii=False), flush=True)


def coklu_olc(beyin, tum, adlar, bas, son, sure_sn):
    """Birden cok saglayici PARALEL, GOREVLER[bas:son], sure sinirli."""
    from concurrent.futures import ThreadPoolExecutor
    mevcut = dict(beyin._bulut_zinciri(tools=True))
    bitis = time.time() + sure_sn
    kayitlar = []
    isler = {}
    with ThreadPoolExecutor(max_workers=max(1, len(adlar))) as havuz:
        for ad in adlar:
            if ad not in mevcut:
                kayitlar.append({"saglayici": ad, "durum": "istemci-yok"})
                continue
            isler[ad] = havuz.submit(
                _saglayici_kos, beyin, mevcut[ad], ad, tum,
                _gunluge_yaz, GOREVLER[bas:son], bitis)
        for ad in adlar:
            if ad in isler:
                kayitlar.extend(isler[ad].result())
    return kayitlar


def kos(beyin, mevcut, tum):
    """Saglayicilar PARALEL olculur: kotalari birbirinden bagimsiz,
    her saglayici kendi icinde sirali ve beklemeli kalir.
    DENEY_SAGLAYICILAR=groq,gemini ile alt kume secilebilir."""
    import threading
    from concurrent.futures import ThreadPoolExecutor

    secili = [s.strip() for s in os.environ.get(
        "DENEY_SAGLAYICILAR", "").split(",") if s.strip()]
    adlar = [a for a in SAGLAYICILAR if not secili or a in secili]
    kilit = threading.Lock()

    def yaz(kayit):
        with kilit:
            print(json.dumps(kayit, ensure_ascii=False), flush=True)

    kayitlar = []
    isler = {}
    with ThreadPoolExecutor(max_workers=max(1, len(adlar))) as havuz:
        for ad in adlar:
            if ad not in mevcut:
                kayitlar.append({"saglayici": ad, "durum": "istemci-yok"})
                continue
            isler[ad] = havuz.submit(
                _saglayici_kos, beyin, mevcut[ad], ad, tum, yaz)
        for ad in adlar:
            if ad in isler:
                kayitlar.extend(isler[ad].result())
    return kayitlar


def rapor(kayitlar):
    satirlar = [
        "## Deney: araç sunumu — CANLI / P2 / ADAY", "",
        "Aynı %d görev (%d araç gereken + %d sohbet), aynı sağlayıcılar. "
        "Gerçek araçlar çalıştırılmadı; ölçülen modelin kararı." % (
            len(GOREVLER), sum(1 for _, b in GOREVLER if b),
            sum(1 for _, b in GOREVLER if not b)), "",
        "| Sağlayıcı | Düzen | Doğru | Araçsız (ezber) | Yanlış | "
        "Sunulmayan | Gereksiz | Hata | Ölçülmedi | Ort. giriş token |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    toplam = {}
    for ad in SAGLAYICILAR:
        for duzen_adi, _ in DUZENLER:
            k = [x for x in kayitlar if x.get("saglayici") == ad
                 and x.get("duzen") == duzen_adi]
            if not k:
                continue
            say = lambda s: sum(1 for x in k if x.get("sinif") == s)
            olculen = [x for x in k if x.get("sinif") != "OLCULMEDI"]
            tok = [x.get("token", 0) for x in olculen if x.get("token")]
            ort = int(sum(tok) / len(tok)) if tok else 0
            satirlar.append("| %s | %s | %d/%d | %d | %d | %d | %d | %d | %d | %s |" % (
                ad, duzen_adi, say("DOGRU"), len(olculen), say("ARACSIZ"),
                say("YANLIS_ARAC"), say("SUNULMAYAN_ARAC"),
                say("GEREKSIZ_ARAC"), say("HATA") + say("TUR_BITTI"),
                say("OLCULMEDI"), ort or "-"))
            t = toplam.setdefault(duzen_adi, [0, 0])
            t[0] += say("DOGRU")
            t[1] += len(olculen)
    satirlar += ["", "**Toplam doğru:** " + " · ".join(
        "%s %d/%d" % (d, t[0], t[1]) for d, t in toplam.items()), ""]
    yok = [x["saglayici"] for x in kayitlar if x.get("durum") == "istemci-yok"]
    if yok:
        satirlar.append("İstemcisi olmayan: " + ", ".join(yok))
    hatalar = [x for x in kayitlar if x.get("sinif") in ("HATA",)]
    if hatalar:
        satirlar += ["", "### Hatalar", ""]
        for x in hatalar[:40]:
            satirlar.append("- %s/%s/%s: %s" % (
                x["saglayici"], x["duzen"], x["gorev"][:30], x.get("hata")))
    return "\n".join(satirlar) + "\n"


class _SahteIstemci:
    """Anahtarsiz boru hatti dogrulamasi: beklenen yolu izleyen model."""

    def __init__(self):
        self.sayac = 0

    def cevapla(self, messages, tools=None, **_):
        self.sayac += 1
        adlar = [t["function"]["name"] for t in (tools or [])]
        gorev = next(m["content"] for m in messages if m["role"] == "user")
        beklenen = dict(GOREVLER)[gorev]
        if not beklenen:
            return {"content": "İyiyim."}
        hedef = sorted(beklenen)[0]
        if hedef in adlar:
            ad, arg = hedef, {}
        elif "yetenek_ac" in adlar:
            from chat.agent_protocol import YETENEK_ALANLARI
            alan = next(a for a, l in YETENEK_ALANLARI.items() if hedef in l)
            ad, arg = "yetenek_ac", {"alan": alan}
        else:
            ad, arg = ARAC_ARA_ADI, {"sorgu": gorev}
        return {"content": "", "tool_calls": [{
            "id": "c%d" % self.sayac, "type": "function",
            "function": {"name": ad, "arguments": json.dumps(arg)}}],
            "_kullanim": {"giris": 100, "cikis": 5}}


def main():
    from tools import TOOLS
    sahte = "--sahte" in sys.argv
    if sahte:
        global BEKLEME_SN
        BEKLEME_SN = 0

        class _SahteBeyin:
            def _tek_cagri(self, istemci, ad, m, t, *_a, **_k):
                return istemci.cevapla(m, tools=t)

        beyin = _SahteBeyin()
        mevcut = {"groq": _SahteIstemci()}
    else:
        from brain import Brain
        beyin = Brain()
        mevcut = dict(beyin._bulut_zinciri(tools=True))
    kayitlar = kos(beyin, mevcut, TOOLS)
    metin = rapor(kayitlar)
    with open(RAPOR_MD, "w", encoding="utf-8") as f:
        f.write(metin)
    with open(RAPOR_JSON, "w", encoding="utf-8") as f:
        json.dump(kayitlar, f, ensure_ascii=False, indent=1)
    print(metin)


if __name__ == "__main__":
    main()
