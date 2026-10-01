"""tools/freetools_kopru.py — freetools.org canli arac koprusu (Faz 1).

freetools.org araclari tarayicida (JS) calisir; API yoktur. Bu kopru
araci gercek bir headless Chromium icerisinde acar, formu doldurur,
sonucu okur. Masaustu icindir; Vercel'e SIQMAZ (playwright yoksa
fail-open).

Guvenlik ve nazik erisim:
- Beyaz liste: yalniz *.freetools.org (SSRF savunmasi web_search.
  _guvenli_adres ile ayni; dis siteye cikilmaz).
- 20 sn zaman asimi; sure dolarsa hata doner, sohbet devam eder.
- Sonuc onbellegi (ayni girdi icin TTL) — siteyi tekrar uzmaz.
- Gunluk istek siniri (nazik eristem; saygi gostergesi).
- Playwright kurulu degilse/yoksa fail-open: arac hata doner,
  Basak'in diger araclari ve sohbet hic etkilenmez (MIMARI ilke 4).

Kod lisansi: freetools.org'un JS/kodu KOPYALANMAZ (lisansi acik degil);
bu modul yalnizca sayfayi tarayiciyla acar ve sonucu okur.
"""

import logging
import threading
import time

logger = logging.getLogger(__name__)

# ── Sabitler ──────────────────────────────────────────────────────────

IZINLI_YONETICILER = ("freetools.org", "www.freetools.org")
ZAMAN_ASN = 20           # sayfa acilis + calisma icin ust sinir (sn)
ONBELLEK_TTL = 1800      # ayni girdi sonucu yarim saat saklanir
GUNLUK_TAVAN = 60         # gunluk istek siniri (nazik erisim)
IZINLI_PORTLAR = (80, 443)

# Dugme secimi — SAYFA ARAYUZU mekanigi (kullanici metni SINIFLANDIRMAZ).
# CHATBOT-YASAGI.md'deki "kelimeye bakip karar veren kod" burada gecersiz:
# orada kullanici cumlesi arac secer; burada model ZATEN araci secti, biz
# yalnizca yabanci bir sayfanin hangi DUGMESINE basilacagini teknik olarak
# seciyoruz (CSS/role secicisi gibi). Karar modelin, mekanik burada.
_ROL_ATLA = ("combobox", "checkbox", "menuitem", "menu", "radio",
             "switch", "listbox", "option", "tab")
# Sonrasi sonucu bozar: sifirlama/kopyalama/indirme/rapor
_ETIKET_ATLA = ("clear", "reset", "copy", "load file", "download",
                "share", "submit report", "report an issue", "print",
                "cancel", "close", "back")
# Aksiyon etiketleri: bu sayfanin "is yapan" dugmesi (Oncecelik sirasiyla)
_ETIKET_ONCELIK = (
    "generate", "encode", "decode", "convert", "calculate", "compute",
    "check", "analyze", "analyse", "format", "beautify", "minify",
    "validate", "sort", "count", "replace", "reverse", "split", "merge",
    "preview", "run", "start", "search", "lookup", "test", "apply",
)

# ── Durum (thread guvenli) ────────────────────────────────────────────

_kilit = threading.Lock()
_onbellek = {}            # anahtar -> (zaman, sonuc)
_gun_sayaci = {"gun": None, "adet": 0}


def _bugun():
    return time.strftime("%Y-%m-%d")


def _kota_kontrol():
    """Gunluk limiti kontrol eder; asim varsa hata metni doner."""
    with _kilit:
        if _gun_sayaci["gun"] != _bugun():
            _gun_sayaci["gun"] = _bugun()
            _gun_sayaci["adet"] = 0
        if _gun_sayaci["adet"] >= GUNLUK_TAVAN:
            return ("Gunluk freetools istek siniri doldu (%d). "
                    "Yarin tekrar deneyebilirsin." % GUNLUK_TAVAN)
        _gun_sayaci["adet"] += 1
        return None


def _onbellek_al(anahtar):
    with _kilit:
        kayit = _onbellek.get(anahtar)
        if not kayit:
            return None
        zaman, sonuc = kayit
        if time.time() - zaman > ONBELLEK_TTL:
            _onbellek.pop(anahtar, None)
            return None
        return sonuc


def _onbellek_koy(anahtar, sonuc):
    with _kilit:
        # Bellek tasiarsa eski kayitlari temizle (cok basit GC)
        if len(_onbellek) > 256:
            for k in list(_onbellek)[:64]:
                _onbellek.pop(k, None)
        _onbellek[anahtar] = (time.time(), sonuc)


def sifirla():
    """Testler icin durumu sifirlar."""
    with _kilit:
        _onbellek.clear()
        _gun_sayaci["gun"] = None
        _gun_sayaci["adet"] = 0


# ── Adres denetimi ───────────────────────────────────────────────────

def _adres_denetle(adres):
    """Yalniz *.freetools.org; digeri hemen reddedilir. Hata metni doner."""
    from urllib.parse import urlparse
    k = urlparse(str(adres or "").strip())
    if k.scheme not in ("http", "https"):
        return "Yalnizca http/https URL'leri calistirilabilir"
    if not k.hostname:
        return "Gecersiz adres: sunucu adi yok"
    if k.hostname not in IZINLI_YONETICILER:
        return ("Guvenlik engeli: yalnizca freetools.org uzerindeki "
                "arac sayfalari calistirilabilir (verilen: %s)" % k.hostname)
    if k.port is not None and k.port not in IZINLI_PORTLAR:
        return "Guvenlik engeli: yalnizca standart portlar (80/443) aciktir"
    # IP cozumleme/ic-adres kontrolu — mevcut SSRF savunmasiyla ayni
    try:
        from tools.web_search import _guvenli_adres
        engel = _guvenli_adres(str(adres))
        if engel:
            return engel
    except Exception:
        # Savunma modulu yuklenemedigi icin yalnizca alan adi adiyla
        # devam ediliyor. Bu bir guvenlik acigi olabilir; ustelik sessiz
        # olmamali — en azindan gorunur olmali.
        logger.warning("SSRF kontrolu yuklenemedi, alan adi adiyla "
                       "devam: %s", adres, exc_info=True)
    return None


# ── Tarayici adimi (playwright ic zaten zayif bagimlilik) ────────────

def _tarayici_kos(adres, form):
    """Headless Chromium'da sayfayi acar, formu doldurur, sonucu okur.

    Sonuc cikarma FARK tabanlidir: doldurma/tiklamadan ONCE ve SONRA
    sayfa metni karsilastirilir; yalnizca YENI EKLENEN satirlar sonuc
    sayilir. Boylece her arac sayfasi icin ayni kural gecerlidir
    (sonuc karti hangi HTML'de olursa olsun). Seciciler bos donerse
    fark bossa sayfanin gorunur metni doner (model zaten yorumlar).
    """
    from playwright.sync_api import sync_playwright

    def _govde_metni(sayfa):
        """Gorunur govde metni + form alani DEGERLERI (value).

        Bazi araclar sonucu readonly textarea/input icerigine yazar;
        inner_text onu gormez — bu yuzden JS ile degerler toplanir
        (doldurdugumuz giris alani HARIC: o bizim girdimizdir, sonuc
        degildir; value'su bizim doldurdugumuz degerle ayniysa atlanir).
        """
        try:
            js = """() => {
                const parcalar = [];
                for (const sel of ['main', 'body']) {
                    const kok = document.querySelector(sel);
                    if (!kok) continue;
                    parcalar.push(kok.innerText || '');
                    for (const el of kok.querySelectorAll('textarea, input')) {
                        const v = (el.value || '').trim();
                        if (v) parcalar.push(v);
                    }
                    break;
                }
                return parcalar.join(String.fromCharCode(10));
            }"""
            m = sayfa.evaluate(js)
            if m and m.strip():
                return m
        except Exception:
            # Bu cozumleyici calismadi; asagidaki locator'lara dusulur.
            logger.debug("icerik JS cozucusu calismadi", exc_info=True)
        for k in ("main", "body"):
            try:
                m = sayfa.locator(k).first.inner_text(timeout=1500)
                if m and m.strip():
                    return m
            except Exception:
                continue
        return ""

    def _yeni_satirlar(once, sonra, girdiler=()):
        """sonra'da olup once'de olmayan satirlar (sirayla, tekrarsiz).

        Kendi doldurdugumuz giris degerleri HARIC tutulur — onlar sonuc
        degil, bizim girdimizdir.
        """
        once_kumesi = set(once.splitlines())
        girdi_kumesi = {str(g).strip() for g in girdiler if str(g).strip()}
        eklenen = []
        for satir in sonra.splitlines():
            s = satir.strip()
            if not s or satir in once_kumesi or s in eklenen:
                continue
            if s in girdi_kumesi:
                continue
            eklenen.append(satir)
        return "\n".join(eklenen)

    with sync_playwright() as p:
        tarayici = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        try:
            sayfa = tarayici.new_page()
            sayfa.set_default_timeout(ZAMAN_ASN * 1000)
            sayfa.goto(adres, wait_until="domcontentloaded",
                       timeout=ZAMAN_ASN * 1000)
            # JS hydration icin kisa bekleme (tavan ZAMAN_ASN ile sinirli)
            sayfa.wait_for_timeout(1500)

            once = _govde_metni(sayfa)

            # 1) Form alanlarini doldur (girdi sirasiyla)
            # Genis secici: text/number/tel/url/search + textarea.
            # HARIC: email (rapor formu), checkbox/radio (isaret kutusu),
            # select (acilir menu = arac modu, varsayilan dogru) —
            # rapor formunun alanlarina ASLA yazilmaz.
            doldurulan = 0
            alanlar = sayfa.locator(
                "main input[type=text]:not([id*=inline]), "
                "main input[type=number]:not([id*=inline]), "
                "main input[type=search]:not([id*=inline]), "
                "main input[type=url]:not([id*=inline]), "
                "main input[type=tel]:not([id*=inline]), "
                "main textarea:not([id*=inline]), "
                "form input[type=text]:not([id*=inline]), "
                "form input[type=number]:not([id*=inline]), "
                "form textarea:not([id*=inline])")
            adet = alanlar.count()
            for i in range(min(adet, len(form))):
                deger = str(form[i] or "")
                if deger:
                    alanlar.nth(i).fill(deger, timeout=3000)
                    doldurulan += 1

            # 2) Calistir dugmesine secili olarak bas — SAYFA ARAYUZU
            # mekanigi (bkz. _ETIKET_ONCELIK notu; kullanici metni degil):
            # - role=combobox/checkbox olanlar (acilir menu/isaret kutusu)
            #   atlanir — tiklarsak menu acilir, is yapilmaz (olculdu:
            #   base64 sayfasinda Encode acilir menusu ilk dugmeydi).
            # - sifirla/kopyala/rapor etiketliler atlanir (sonucu bozar).
            # - kalanlarda "is yapan" etiketi tercih edilir (Convert,
            #   Generate...); yoksa ilk adaya basilir.
            basildi = False
            try:
                adaylar = []
                dugmeler = sayfa.locator("main button")
                for i in range(min(dugmeler.count(), 16)):
                    d = dugmeler.nth(i)
                    try:
                        if not (d.is_visible(timeout=500)
                                and d.is_enabled(timeout=500)):
                            continue
                        etiket = (d.inner_text(timeout=300) or "").strip()
                        if not etiket:
                            continue
                        rol = (d.get_attribute("role") or "").lower()
                        if rol in _ROL_ATLA:
                            continue
                        if d.get_attribute("aria-haspopup"):
                            continue
                        tl = etiket.lower()
                        if any(s in tl for s in _ETIKET_ATLA):
                            continue
                        adaylar.append((i, d, tl))
                    except Exception:
                        continue
                if not adaylar:
                    # form ici tek dugme (input[type=submit] gibi) — son care
                    try:
                        submit = sayfa.locator(
                            "main input[type=submit], main button[type=submit]"
                            ).first
                        if submit.count():
                            submit.click(timeout=3000)
                            basildi = True
                    except Exception:
                        # Gonder dugmesi bulunamadi/tiklanamadi; asagida
                        # aday adresler denenir.
                        logger.debug("gonder dugmesi tiklanamadi",
                                     exc_info=True)
                if not basildi:
                    hedef = None
                    for _i, d, tl in adaylar:
                        if any(s in tl for s in _ETIKET_ONCELIK):
                            hedef = d
                            break
                    if hedef is None and adaylar:
                        hedef = adaylar[0][1]
                    if hedef is not None:
                        hedef.click(timeout=3000)
                        basildi = True
            except Exception:
                basildi = False

            # sonuc uretimi icin bekle (tiklama ya da doldurma tetikler)
            if basildi or doldurulan:
                sayfa.wait_for_timeout(1500)

            # 3) FARK: yeni eklenen satirlar sonuctur (kendi girdimiz haric)
            sonra = _govde_metni(sayfa)
            eklenen = _yeni_satirlar(once, sonra, form)
            if eklenen.strip():
                return {"sonuc": eklenen[:8000],
                        "kaynak": "freetools.org",
                        "adres": adres}

            # 4) Fark yoksa sonuc nitelikli secicileri dene
            for secici in (
                "[data-testid=tool-result]", "output", "#result",
                ".result", "pre", "code",
            ):
                try:
                    loc = sayfa.locator(secici).first
                    if loc.count() and loc.is_visible(timeout=800):
                        metin = loc.inner_text(timeout=1500).strip()
                        if metin and metin != "":
                            return {"sonuc": metin[:8000],
                                    "kaynak": "freetools.org",
                                    "adres": adres}
                except Exception:
                    continue

            metin = (sonra or "").strip()
            if not metin:
                return {"error": "Sayfa acildi ama sonuc metni okunamadi"}
            return {"sonuc": metin[:8000], "kaynak": "freetools.org",
                    "adres": adres}
        finally:
            tarayici.close()


def _sarmalayici(adres, form):
    """Ayni is parcaciginda zaman asimi + hata sarmalayici."""
    sonuc = {"error": "bilinmeyen"}
    kutu = []

    def _gorev():
        try:
            kutu.append(_tarayici_kos(adres, form))
        except Exception as e:   # playwright yok / sayfa patladi
            kutu.append(_hata_cevir(e))

    ip = threading.Thread(target=_gorev, daemon=True)
    ip.start()
    ip.join(ZAMAN_ASN + 5)
    if kutu:
        return kutu[0]
    return {"error": "Zaman asimi: arac %d sn icinde bitmedi" % ZAMAN_ASN}


def _hata_cevir(e):
    """Playwright yoklugu ve bilinen hatalari acik metne cevirir."""
    ad = type(e).__name__
    metin = str(e)
    if ad in ("ImportError", "ModuleNotFoundError"):
        return {"error": ("Freetools koprusu kurulu degil (playwright). "
                          "Kurulum: pip install playwright && "
                          "playwright install chromium")}
    if "Timeout" in ad or "timeout" in metin.lower():
        return {"error": "Zaman asimi: sayfa %d sn icinde yanit vermedi"
                         % ZAMAN_ASN}
    return {"error": "Freetools araci calismadi: %s" % metin[:300]}


def _yerel_deneme(adres, form, hata):
    """Kopru dusunce yerel standart algoritmayla dener (Faz 2 / web).

    Vercel'de playwright yoktur; burada freetools.org'un JS'i degil,
    Python standart kutuphanesinin evrensel algoritmalari calisir.
    Sonuc "yerel-hesaplama" etiketiyle doner ve aracin freetools.org
    adresi (derin baglanti) eklenir. Bilinmeyen arac None doner.
    """
    try:
        from tools import freetools_yerel
    except Exception:
        return None
    sonuc = freetools_yerel.hesapla(adres, form)
    if not isinstance(sonuc, dict) or "sonuc" not in sonuc:
        return None
    sonuc = dict(sonuc)
    sonuc["not"] = (
        "Tarayıcı köprüsü çalışmadı (%s); sonuç standart algoritmayla "
        "yerelde hesaplandı." % str(hata)[:160]
    )
    return sonuc


# ── Dis kapisi ───────────────────────────────────────────────────────

def freetools_calistir(adres, form=None):
    """freetools.org aracini calistirir; sonuc veya hata doner.

    adres: arac sayfasi (yalniz *.freetools.org)
    form:  sirayla doldurulacak giris degerleri (liste)
    """
    adres = str(adres or "").strip()
    if not adres:
        return {"error": "Adres bos olamaz"}
    engel = _adres_denetle(adres)
    if engel:
        return {"error": engel}

    if not isinstance(form, (list, tuple)):
        form = [form] if form else []
    form = [str(f) for f in form][:8]   # en fazla 8 giris alani

    anahtar = "%s|%s" % (adres, "\x1f".join(form))
    onbeldekiler = _onbellek_al(anahtar)
    if onbeldekiler is not None:
        sonuc = dict(onbeldekiler)
        sonuc["onbellek"] = True
        return sonuc

    kota = _kota_kontrol()
    if kota:
        return {"error": kota}

    sonuc = _sarmalayici(adres, form)
    if "error" in sonuc:
        yerel = _yerel_deneme(adres, form, sonuc.get("error") or "bilinmiyor")
        if yerel is not None:
            sonuc = yerel
    if "error" not in sonuc:
        _onbellek_koy(anahtar, sonuc)
    return sonuc
