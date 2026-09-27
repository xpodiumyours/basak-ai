"""tools/product_resolver.py — Faturadaki urunu kamuya acik webde kanitla.

Amac:
- marka listesine bagli kalmadan firma / resmi kaynak adayi bulmak,
- barkod/GTIN > SKU/MPN > marka+varyant kanit sirasini kullanmak,
- Schema.org Product/ProductGroup verisini duz metinle birlikte okumak,
- pazar yeri / sosyal ag sonucunu "resmi kaynak" diye isaretlememek,
- kanit yetersizse tahmin etmek yerine dogrulanamadi demek.

Bu modul yayin izni vermez. Yalniz urun kimligi ve kaynak kaniti uretir.
"""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

_URL_RE = re.compile(r"https?://[^\s\"'<>]+")
_GTIN_RE = re.compile(r"^\d{8,14}$")
_URUN_YOL = ("urun", "product", "products", "p/", "item", "model")
_KATEGORI_YOL = ("kategori", "category", "search", "arama", "koleksiyon")
# "üretici/üretim" gibi tek kelimeler reseller/SEO sayfalarında da geçebilir.
# Resmî üretici kararı için birinci şahıs / sahiplik / tesis beyanı gerekir.
_GUCLU_URETIM_IPUCU = (
    "marka sahibi", "brand owner", "kendi markamız", "kendi markamiz",
    "markalarımız", "markalarimiz", "fabrikamız", "fabrikamiz",
    "üretim tesisimiz", "uretim tesisimiz", "üretim tesislerimiz",
    "uretim tesislerimiz", "kendi bünyemizde üreti", "kendi bunyemizde ureti",
    "firmamız üret", "firmamiz uret", "şirketimiz üret", "sirketimiz uret",
    "konfeksiyon fabrikalarımızda", "konfeksiyon fabrikalarimizda",
    "we manufacture", "our factory", "our factories", "our brands",
)
_URETIM_GENEL_IPUCU = (
    "üretici", "uretici", "üretim", "uretim", "manufacturer",
    "fabrika", "imalat", "üretmektedir", "uretmektedir",
)
_RESMI_SATIS_IPUCU = (
    "resmi satış", "resmi satis", "official store", "resmi mağaza",
    "resmi magaza", "resmi satış sitesi", "resmi satis sitesi",
)
_ENGELLI_HOST = (
    "trendyol.com", "hepsiburada.com", "n11.com", "amazon.",
    "pazarama.com", "ciceksepeti.com", "akakce.com", "cimri.com",
    "epey.com", "facebook.com", "instagram.com", "linkedin.com",
    "youtube.com", "tiktok.com", "pinterest.", "x.com", "twitter.com",
)
_TR = str.maketrans({
    "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "İ": "i",
    "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u",
})


def _norm(deger):
    return re.sub(r"[^a-z0-9]", "", str(deger or "").translate(_TR).lower())


def _host(url):
    try:
        return (urlparse(str(url or "")).hostname or "").lower().lstrip("www.")
    except ValueError:
        return ""


def _host_engelli(host):
    host = str(host or "").lower()
    return any(host == h or host.endswith("." + h) or h in host
               for h in _ENGELLI_HOST)


def gtin_gecerli(deger):
    """GTIN-8/12/13/14 check digit dogrulamasi."""
    s = re.sub(r"\D", "", str(deger or ""))
    if len(s) not in (8, 12, 13, 14) or not _GTIN_RE.fullmatch(s):
        return False
    govde = s[:-1]
    toplam = sum(
        int(rakam) * (3 if i % 2 == 0 else 1)
        for i, rakam in enumerate(reversed(govde))
    )
    kontrol = (10 - (toplam % 10)) % 10
    return kontrol == int(s[-1])


def kart_kimligi(kart):
    kart = kart if isinstance(kart, dict) else {}
    barkodlar = []
    for v in kart.get("varyantlar") or []:
        if not isinstance(v, dict):
            continue
        b = re.sub(r"\D", "", str(v.get("barkod") or ""))
        if b and b not in barkodlar:
            barkodlar.append(b)
    return {
        "marka": str(kart.get("marka") or "").strip(),
        "sku": str(kart.get("kod") or "").strip(),
        "ad": str(kart.get("ad") or "").strip(),
        "kategori": str(kart.get("kategori") or "").strip(),
        "barkodlar": barkodlar,
        "gtinler": [b for b in barkodlar if gtin_gecerli(b)],
        "renkler": sorted({str(v.get("renk") or "").strip()
                           for v in (kart.get("varyantlar") or [])
                           if isinstance(v, dict) and v.get("renk")}),
        "bedenler": sorted({str(v.get("beden") or "").strip()
                            for v in (kart.get("varyantlar") or [])
                            if isinstance(v, dict) and v.get("beden")}),
    }


def _arama_kayitlari(metin):
    """web_search BASLIK/URL/METIN bloklarini yapiya cevirir."""
    sonuc = []
    for blok in re.split(r"\n\s*\n", str(metin or "")):
        satirlar = [s.strip() for s in blok.splitlines() if s.strip()]
        if not satirlar:
            continue
        url = next((s for s in satirlar if s.startswith(("http://", "https://"))), "")
        if not url:
            continue
        i = satirlar.index(url)
        baslik = " ".join(satirlar[:i])
        ozet = " ".join(satirlar[i + 1:])
        sonuc.append({"url": url, "baslik": baslik, "ozet": ozet})
    return sonuc


def _kimlik_metinleri(kimlik):
    degerler = []
    degerler.extend(kimlik.get("gtinler") or [])
    sku = str(kimlik.get("sku") or "").strip()
    if sku:
        degerler.append(sku)
    return degerler


def _kod_metin_de(kod, metin):
    """SKU/MPN'yi substring ile değil normalize edilmiş tam token ile ara."""
    hedef = _norm(kod)
    if not hedef:
        return False
    tokenlar = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9][A-Za-zÇĞİÖŞÜçğıöşü0-9._/-]*",
                          str(metin or ""))
    return any(_norm(t) == hedef for t in tokenlar)


def _gtin_metin_de(gtin, metin):
    hedef = re.sub(r"\D", "", str(gtin or ""))
    if not hedef:
        return False
    return bool(re.search(r"(?<!\d)%s(?!\d)" % re.escape(hedef),
                          str(metin or "")))


def _firma_sorgulari(kimlik):
    marka = str(kimlik.get("marka") or "").strip()
    sku = str(kimlik.get("sku") or "").strip()
    gtin = (kimlik.get("gtinler") or [""])[0]
    kategori = str(kimlik.get("kategori") or "").strip()
    ad = str(kimlik.get("ad") or "").strip()
    baglam = " ".join(x for x in (kategori, ad[:60]) if x).strip()
    q = []
    if gtin:
        q.append('"%s" "%s"' % (gtin, marka) if marka else '"%s"' % gtin)
    if marka and sku:
        q.append('"%s" "%s" %s' % (marka, sku, baglam or "ürün"))
    if marka:
        q.append('"%s" %s üretici resmi site' % (marka, kategori or "ürün"))
        q.append('"%s" %s üretim iletişim' % (marka, kategori or "ürün"))
    return list(dict.fromkeys(x.strip() for x in q if x.strip()))[:4]


def _kaynak_sinifi(host, metin, marka):
    """Kaynağın rolünü sınıflandırır; resellerı üretici diye yükseltmez."""
    h = _norm(host)
    m = _norm(marka)
    t = str(metin or "").lower()
    marka_var = bool(m and (m in _norm(metin) or m in h))
    if marka_var and any(k in t for k in _GUCLU_URETIM_IPUCU):
        return "uretici_adayi", ["marka", "guclu_uretim_beyani"]
    if marka_var and any(k in t for k in _RESMI_SATIS_IPUCU):
        return "resmi_satis_adayi", ["marka", "resmi_satis_beyani"]
    if marka_var and m and m in h:
        return "marka_alani_adayi", ["marka", "marka_domaini"]
    if marka_var and any(k in t for k in _URETIM_GENEL_IPUCU):
        return "ticari_kaynak", ["marka", "zayif_uretim_ifadesi"]
    return "ticari_kaynak", (["marka"] if marka_var else [])


def _firma_ilk_skor(kayit, kimlik):
    metin = "%s %s" % (kayit.get("baslik", ""), kayit.get("ozet", ""))
    host = _host(kayit.get("url"))
    skor = 0
    kanit = []
    marka = _norm(kimlik.get("marka"))
    if marka and marka in _norm(host):
        skor += 15
        kanit.append("marka_domaini")
    if marka and marka in _norm(metin):
        skor += 8
        kanit.append("marka_arama_sonucu")
    for kimlik_degeri in _kimlik_metinleri(kimlik):
        if _norm(kimlik_degeri) and _norm(kimlik_degeri) in _norm(metin):
            skor += 10
            kanit.append("urun_kimligi_arama_sonucu")
            break
    # Arama snippetindeki genel "üretici" sözü resmi kaynak kanıtı değildir.
    t = metin.lower()
    if any(k in t for k in _GUCLU_URETIM_IPUCU):
        skor += 12
        kanit.append("guclu_uretim_beyani")
    elif any(k in t for k in _URETIM_GENEL_IPUCU):
        skor += 3
        kanit.append("zayif_uretim_ifadesi")

    # Aynı marka adının farklı sektörlerde kullanılmasına karşı fatura
    # bağlamı (kategori/ürün adı) yalnız aday sıralamasında destek kanıtıdır.
    baglam = " ".join((str(kimlik.get("kategori") or ""),
                       str(kimlik.get("ad") or "")))
    baglam_kelimeleri = [
        x for x in re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]{4,}", baglam)
        if _norm(x) not in {_norm(kimlik.get("marka")),
                            _norm(kimlik.get("sku"))}
    ][:8]
    ortak = [x for x in baglam_kelimeleri if _norm(x) in _norm(metin)]
    if ortak:
        skor += min(8, 2 * len(ortak))
        kanit.append("urun_baglami")
    if any(k in t for k in _RESMI_SATIS_IPUCU):
        skor += 4
        kanit.append("resmi_satis_beyani")
    return skor, kanit


def firma_bul(kart_veya_kimlik, ws=None, deadline=None):
    """Turkiye odakli web aramasindan firma / birincil kaynak adaylari bulur.

    Sabit firma listesi gerektirmez. Sonuc kanitli aday listesidir; firma
    bulunamamasi urun kimligini uydurma yetkisi vermez.
    """
    if ws is None:
        from tools import web_search as ws
    kimlik = (kart_veya_kimlik if isinstance(kart_veya_kimlik, dict)
              and "gtinler" in kart_veya_kimlik
              else kart_kimligi(kart_veya_kimlik))
    sorgular = _firma_sorgulari(kimlik)
    if not sorgular:
        return []
    deadline = float(deadline or (time.monotonic() + 45.0))

    kayitlar = []
    def _ara(q):
        if time.monotonic() >= deadline:
            return []
        r = ws.web_search(q, adet=10)
        return [] if r.get("error") else _arama_kayitlari(r.get("result", ""))

    with ThreadPoolExecutor(max_workers=min(3, len(sorgular))) as havuz:
        for gelecekte in as_completed([havuz.submit(_ara, q) for q in sorgular]):
            try:
                kayitlar.extend(gelecekte.result())
            except Exception:
                continue

    hostlar = {}
    for kayit in kayitlar:
        host = _host(kayit["url"])
        if not host or _host_engelli(host):
            continue
        skor, kanit = _firma_ilk_skor(kayit, kimlik)
        mevcut = hostlar.get(host)
        if mevcut is None or skor > mevcut["skor"]:
            hostlar[host] = {
                "host": host, "site": "https://" + host,
                "kaynak": kayit["url"], "skor": skor,
                "kanitlar": list(kanit),
            }

    adaylar = sorted(hostlar.values(), key=lambda x: x["skor"], reverse=True)[:6]
    sonuc = []
    for aday in adaylar:
        if time.monotonic() >= deadline:
            break
        okuma = ws.urun_sayfasi_oku(aday["kaynak"])
        if okuma.get("error"):
            continue
        try:
            veri = json.loads(okuma["result"])
        except (TypeError, ValueError):
            continue
        metin = str(veri.get("metin") or "")
        tur, ek = _kaynak_sinifi(aday["host"], metin, kimlik.get("marka"))
        skor = aday["skor"]
        if tur == "uretici_adayi":
            skor += 25
        elif tur == "marka_alani_adayi":
            skor += 18
        elif tur == "resmi_satis_adayi":
            skor += 8
        sonuc.append({
            **aday, "kaynak_turu": tur, "skor": skor,
            "kanitlar": list(dict.fromkeys(aday["kanitlar"] + ek)),
        })
    return sorted(sonuc, key=lambda x: x["skor"], reverse=True)[:4]


def _urun_sorgulari(kimlik, firma_adaylari):
    gtin = (kimlik.get("gtinler") or [""])[0]
    sku = str(kimlik.get("sku") or "").strip()
    marka = str(kimlik.get("marka") or "").strip()
    sorgular = []
    for firma in (firma_adaylari or [])[:3]:
        host = firma.get("host")
        if not host:
            continue
        if gtin:
            sorgular.append('site:%s "%s"' % (host, gtin))
        if sku:
            sorgular.append('site:%s "%s"' % (host, sku))
    if gtin:
        sorgular.append('"%s" "%s"' % (gtin, marka) if marka else '"%s"' % gtin)
    if marka and sku:
        sorgular.append('"%s" "%s"' % (marka, sku))
    return list(dict.fromkeys(sorgular))[:8]


def _structured_degerler(urunler, alan):
    sonuc = []
    for u in urunler or []:
        if not isinstance(u, dict):
            continue
        deger = u.get(alan)
        if isinstance(deger, list):
            adaylar = deger
        else:
            adaylar = [deger]
        for a in adaylar:
            if isinstance(a, dict):
                a = a.get("name") or a.get("@id") or a.get("url")
            if a is not None:
                s = str(a).strip()
                if s and s not in sonuc:
                    sonuc.append(s)
    return sonuc


def _varyant_kaniti(kimlik, veri):
    """Faturadaki renk/bedeni urun sayfasinda ayri bir kanit olarak olcer.

    Urun kimligi ile varyant kimligi birbirine karistirilmaz. Bir urun
    dogru bulunup renk/beden sayfada kanitlanamiyorsa durum acikca
    "dogrulanamadi" kalir; fotograf varyanta aitmis gibi sunulmaz.
    """
    urunler = veri.get("urunler") or []
    metin = str(veri.get("metin") or "")[:15000]
    yap_renk = {_norm(x) for x in _structured_degerler(urunler, "color")
                if _norm(x)}
    yap_beden = {_norm(x) for x in _structured_degerler(urunler, "size")
                 if _norm(x)}

    istenen_renk = [x for x in kimlik.get("renkler") or [] if _norm(x)]
    istenen_beden = [x for x in kimlik.get("bedenler") or [] if _norm(x)]

    renk_eslesen = []
    for renk in istenen_renk:
        n = _norm(renk)
        if n in yap_renk or (len(n) >= 3 and n in _norm(metin)):
            renk_eslesen.append(renk)

    beden_eslesen = []
    for beden in istenen_beden:
        n = _norm(beden)
        if n in yap_beden or _kod_metin_de(beden, metin):
            beden_eslesen.append(beden)

    istek_sayisi = len(istenen_renk) + len(istenen_beden)
    eslesen_sayisi = len(renk_eslesen) + len(beden_eslesen)
    if istek_sayisi == 0:
        durum = "faturada_yok"
    elif eslesen_sayisi == istek_sayisi:
        durum = "uyumlu"
    elif eslesen_sayisi:
        durum = "kismi"
    else:
        durum = "dogrulanamadi"

    # Schema.org hasVariant icinde renk/beden + image bulunan kayit,
    # varyanta ozel fotograf icin en guclu generic kanittir.
    varyant_gorseller = []
    for u in urunler:
        if not isinstance(u, dict):
            continue
        renk = _norm(u.get("color"))
        beden = _norm(u.get("size"))
        renk_ok = not istenen_renk or any(
            renk == _norm(x) for x in istenen_renk)
        beden_ok = not istenen_beden or any(
            beden == _norm(x) for x in istenen_beden)
        if not (renk_ok and beden_ok):
            continue
        imgs = u.get("image")
        imgs = imgs if isinstance(imgs, list) else [imgs]
        for img in imgs:
            if isinstance(img, str) and img and img not in varyant_gorseller:
                varyant_gorseller.append(img)

    return {
        "durum": durum,
        "fatura_renkler": istenen_renk,
        "fatura_bedenler": istenen_beden,
        "renk_eslesen": renk_eslesen,
        "beden_eslesen": beden_eslesen,
        "varyant_gorseller": varyant_gorseller[:10],
    }


def _sayfa_skor(kimlik, url, veri, firma):
    metin = str(veri.get("metin") or "")
    urunler = veri.get("urunler") or []
    norm_metin = _norm(metin)
    marka = _norm(kimlik.get("marka"))
    sku = _norm(kimlik.get("sku"))
    gtinler = {_norm(x) for x in kimlik.get("gtinler") or []}
    yap_sku = {_norm(x) for x in _structured_degerler(urunler, "sku")}
    yap_mpn = {_norm(x) for x in _structured_degerler(urunler, "mpn")}
    yap_gtin = {_norm(x) for x in _structured_degerler(urunler, "gtin")}
    yap_marka = {_norm(x) for x in _structured_degerler(urunler, "brand")}
    kanit = []
    skor = 0
    kimlik_kaniti = False

    gtin_sayfa_tam = any(_gtin_metin_de(g, metin)
                          for g in kimlik.get("gtinler") or [])
    sku_sayfa_tam = _kod_metin_de(kimlik.get("sku"), metin)

    if gtinler and gtinler & yap_gtin:
        skor += 60; kanit.append("gtin_yapilandirilmis"); kimlik_kaniti = True
    elif gtinler and gtin_sayfa_tam:
        skor += 38; kanit.append("gtin_sayfa_tam"); kimlik_kaniti = True

    if sku and (sku in yap_sku or sku in yap_mpn):
        skor += 45; kanit.append("sku_yapilandirilmis"); kimlik_kaniti = True
    elif sku and sku_sayfa_tam:
        skor += 26; kanit.append("sku_sayfa_tam"); kimlik_kaniti = True

    if marka and marka in yap_marka:
        skor += 20; kanit.append("marka_yapilandirilmis")
    elif marka and marka in norm_metin:
        skor += 10; kanit.append("marka_sayfa")

    if urunler:
        skor += 10; kanit.append("schema_product")

    yol = (urlparse(url).path or "").lower()
    if any(k in yol for k in _URUN_YOL):
        skor += 5; kanit.append("urun_yolu")
    if any(k in yol for k in _KATEGORI_YOL):
        skor -= 12; kanit.append("kategori_yolu")

    kaynak_turu = (firma or {}).get("kaynak_turu", "ticari_kaynak")
    if kaynak_turu == "uretici_adayi":
        skor += 20; kanit.append("uretici_kaynagi")
    elif kaynak_turu == "marka_alani_adayi":
        skor += 15; kanit.append("marka_alani")
    elif kaynak_turu == "resmi_satis_adayi":
        skor += 6; kanit.append("resmi_satis_adayi")

    # Varyant urun kimliginden ayri izlenir. Eslesen renk/beden yalniz
    # ek kanittir; eslesmemesi baska SKU'yu dogru urun diye secmez.
    varyant = _varyant_kaniti(kimlik, veri)
    if varyant["renk_eslesen"]:
        skor += 3; kanit.append("renk")
    if varyant["beden_eslesen"]:
        skor += 3; kanit.append("beden")

    # "Resmî doğrulandı" yalnız güçlü üretici/sahiplik kaynağında ve
    # ürün kimliği ayrıca kanıtlıysa verilir. Marka adını taşıyan domain,
    # reseller/official-store iddiası veya pazar yeri tek başına yeterli değil.
    gtin_yapisal = bool(gtinler and gtinler & yap_gtin)
    gtin_metin = bool(gtinler and gtin_sayfa_tam)
    sku_yapisal = bool(sku and (sku in yap_sku or sku in yap_mpn))
    sku_metin = bool(sku and sku_sayfa_tam)
    marka_yapisal = bool(marka and marka in yap_marka)
    marka_sayfa = bool(marka and marka in norm_metin)

    # Üretici hostu bağımsız kurumsal kanıtla doğrulandıysa ürün sayfasının
    # Schema.org alanları eksik olsa bile tam SKU/GTIN + marka metni yeterlidir.
    # Bu, Seher gibi gerçek üretici sitelerinde Product JSON-LD'nin yalnız
    # name/image/url taşıdığı durumları doğru işler.
    guclu_urun_kimligi = (
        gtin_yapisal or
        (sku_yapisal and (marka_yapisal or marka_sayfa)) or
        (gtin_metin and (marka_yapisal or marka_sayfa)) or
        (sku_metin and (marka_yapisal or marka_sayfa))
    )
    resmi = bool(kaynak_turu == "uretici_adayi" and guclu_urun_kimligi)
    if resmi:
        kanit.append("resmi_uretici_urun_kimligi")
    return skor, kimlik_kaniti, resmi, kanit


def urun_bul(kart, firma_adaylari=None, ws=None, deadline=None):
    """Bir katalog kartini kanitli dijital urun adayi ile eslestirir."""
    if ws is None:
        from tools import web_search as ws
    kimlik = kart_kimligi(kart)
    if not (kimlik["gtinler"] or kimlik["sku"] or kimlik["marka"]):
        return {"error": "Ürün kimliği için barkod, SKU veya marka yok."}
    deadline = float(deadline or (time.monotonic() + 60.0))
    firmalar = firma_adaylari
    if firmalar is None:
        firmalar = firma_bul(kimlik, ws=ws, deadline=deadline)

    firma_by_host = {f.get("host"): f for f in (firmalar or []) if f.get("host")}
    sorgular = _urun_sorgulari(kimlik, firmalar)
    kayitlar = []

    # Arama motoru bir üretici ürününü indekslememiş olabilir. Doğrulanmış
    # firma adaylarının sitemap'inde SKU/GTIN'i önce ara; sayfayı yine aynı
    # kanıt kapısından geçir. Sitemap sonucu tek başına doğrulama değildir.
    sitemap_kimlikleri = list(kimlik.get("gtinler") or [])
    if kimlik.get("sku"):
        sitemap_kimlikleri.append(kimlik["sku"])
    for firma in (firmalar or [])[:2]:
        host = firma.get("host")
        if not host:
            continue
        for kimlik_degeri in sitemap_kimlikleri[:2]:
            if time.monotonic() >= deadline:
                break
            sm = ws.site_haritasi_ara(host, kimlik_degeri, adet=4)
            if sm.get("error"):
                continue
            try:
                urller = json.loads(sm.get("result") or "[]")
            except (TypeError, ValueError):
                urller = []
            for url in urller:
                if isinstance(url, str):
                    kayitlar.append({
                        "url": url, "baslik": kimlik_degeri,
                        "ozet": "sitemap exact identity", "sitemap": True})
    for q in sorgular:
        if time.monotonic() >= deadline:
            break
        r = ws.web_search(q, adet=10)
        if not r.get("error"):
            kayitlar.extend(_arama_kayitlari(r.get("result", "")))

    adaylar = {}
    for kayit in kayitlar:
        url = kayit["url"]
        host = _host(url)
        if not host or _host_engelli(host):
            continue
        on = 25 if kayit.get("sitemap") else 0
        nm = _norm(kayit.get("baslik", "") + " " + kayit.get("ozet", ""))
        for x in _kimlik_metinleri(kimlik):
            if _norm(x) and _norm(x) in nm:
                on += 15
        if _norm(kimlik["marka"]) and _norm(kimlik["marka"]) in nm:
            on += 5
        if any(k in (urlparse(url).path or "").lower() for k in _URUN_YOL):
            on += 3
        onceki = adaylar.get(url)
        if onceki is None or on > onceki["on"]:
            adaylar[url] = {**kayit, "on": on}

    sirali = sorted(adaylar.values(), key=lambda x: x["on"], reverse=True)[:12]
    en_iyi = None
    for aday in sirali:
        if time.monotonic() >= deadline:
            break
        url = aday["url"]
        okuma = ws.urun_sayfasi_oku(url)
        if okuma.get("error"):
            continue
        try:
            veri = json.loads(okuma["result"])
        except (TypeError, ValueError):
            continue
        host = _host(url)
        firma = next((f for h, f in firma_by_host.items()
                      if h and (host == h or host.endswith("." + h))), None)
        if firma is None:
            tur, kanit0 = _kaynak_sinifi(host, veri.get("metin", ""),
                                         kimlik.get("marka"))
            firma = {"host": host, "kaynak_turu": tur, "kanitlar": kanit0}
        skor, kimlik_kaniti, resmi, kanit = _sayfa_skor(
            kimlik, url, veri, firma)
        if not kimlik_kaniti or skor < 45:
            continue
        urunler = veri.get("urunler") or []
        adlar = _structured_degerler(urunler, "name")
        markalar = _structured_degerler(urunler, "brand")
        skular = _structured_degerler(urunler, "sku")
        gtin = _structured_degerler(urunler, "gtin")
        guven = ("yuksek" if resmi and skor >= 85
                 else "orta" if kimlik_kaniti and skor >= 65
                 else "dusuk")
        varyant = _varyant_kaniti(kimlik, veri)
        varyant_gorseller = varyant.pop("varyant_gorseller")
        sayfa_gorselleri = [g for g in (veri.get("gorseller") or [])
                            if isinstance(g, str)]
        gorseller = list(dict.fromkeys(
            varyant_gorseller + sayfa_gorselleri))[:10]
        gorsel_dogrulama = (
            "varyant" if varyant_gorseller and varyant["durum"] == "uyumlu"
            else "urun" if resmi and gorseller
            else "aday" if gorseller
            else "yok")

        sonuc = {
            "cozucu_surumu": "urun-kimlik-v2",
            "kaynak": url,
            "kaynak_turu": firma.get("kaynak_turu", "ticari_kaynak"),
            "resmi_dogrulandi": resmi,
            "dogrulama_seviyesi": (
                "resmi" if resmi else
                "urun_kanitli" if kimlik_kaniti else "aday"),
            "skor": skor,
            "guven": guven,
            "urun_adi": adlar[0] if adlar else aday.get("baslik", ""),
            "marka": markalar[0] if markalar else kimlik["marka"],
            "sku": skular[0] if skular else kimlik["sku"],
            "gtin": gtin[0] if gtin else ((kimlik["gtinler"] or [""])[0]),
            "varyant_dogrulama": varyant,
            "gorsel_dogrulama": gorsel_dogrulama,
            "gorseller": gorseller,
            "kanitlar": list(dict.fromkeys(
                (firma.get("kanitlar") or []) + kanit)),
            "eksik": [],
        }
        if not resmi:
            sonuc["eksik"].append("resmi_kaynak")
        if not sonuc["gorseller"]:
            sonuc["eksik"].append("gorsel")
        if (kimlik.get("renkler") or kimlik.get("bedenler")) and                 varyant["durum"] not in ("uyumlu", "faturada_yok"):
            sonuc["eksik"].append("varyant")
        if not urunler:
            sonuc["eksik"].append("yapilandirilmis_urun_verisi")
        if en_iyi is None or (resmi, skor) > (
                bool(en_iyi["resmi_dogrulandi"]), en_iyi["skor"]):
            en_iyi = sonuc

    if en_iyi is None:
        return {"error": "Ürün kamuya açık kaynaklarda yeterli kanıtla doğrulanamadı."}
    return en_iyi
