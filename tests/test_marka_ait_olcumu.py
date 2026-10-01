"""tests/test_marka_ait_olcumu.py — marka-ait eşleşmesinin ÖLÇÜLMÜŞ sınırları.

Bu dosya bir düzeltme değil, **ölçüm kaydıdır**. 2026-10-01'de yapılan
araştırmanın sonucu: `_host_markaya_uyuyor` ALT DİZE karşılaştırması
kullanıyor ve bu ölçülebilir bir zayıflık yaratıyor. Düzeltmesi DENENDİ
ve **GÜVENLİ ÇIKMADI** (aşağıda kanıtı); bu yüzden kod değiştirilmedi.

## Bulgu 1 — `kimin.net.tr` NEDEN "ait" sayılmadı (aslında sayılmıyor)

Soru: Trendyol aramasında `kimin.net.tr` neden markaya ait kabul
edildi? Ölçülen cevap: **sayılmadı.**

    k._host_markaya_uyuyor('trendyol', 'https://kimin.net.tr/iletisim')
    -> False        (3 canlı koşumda da aynı)
    k._sayfa_markaya_ait(...)  -> False

`kimin.net.tr`'nin tek gerçek bloğu `{"ad": "myblog"}` — markaya ait
değil, `_gercek_markaya_ait` de `False` dönüyor. Yani **eşleştirme
doğru çalışıyor**; ilk ölçümde görülen bozuk kart **karşılaştırma
hatasıydı** (aşağıya bak).

## Bulgu 2 — Önceki "erken çıkış kartı bozdu" kaydı YANLIŞTI

`_sirket_ara_erken_cikis.py` her koşuda `firma_bul`'u YENİDEN
çağırıyordu; arama sonuçları koşular arası değiştiği için A ve B
**farklı aday listeleriyle** çalıştı. Dondurulmuş liste ile tekrar
ölçüldü (`_erken_cikis_dondurulmus.py`): kart **AYNI** çıktı.

Bu düzeltme önemli: "erken çıkış güvenli değil" kararı **geçersiz**
bir ölçüme dayanıyordu.

## Bulgu 3 — GERÇEK zayıflık: alt dize karşılaştırması

`_host_markaya_uyuyor` içinde `anahtar in etiket_anahtar` var; yani
marka, etiketin HERHANGİ bir yerinde geçerse eşleşiyor. Ölçülen
yanlış pozitifler:

    _host_markaya_uyuyor('trendyol', 'https://trendyol-korsan.com/x')  -> True
    _host_markaya_uyuyor('vestel',   'https://vestel-isyeri.com/x')    -> True

Bu, sahte marka sitelerinin markaya ait sayılması demektir.

## Neden düzeltilmedi (ölçülen çelişki)

Sıkı bir kelime-sınırı kuralı denendi:

  KABUL edilmesi gerekenler (mevcut testler bunları kilitliyor):
    `tutku` ↔ `tutkuelit.com.tr`   (marka etiketin İÇİNDE)
    `YeniMarka` ↔ `yeni.com`       (etiket markanın İÇİNDE)
  Reddedilmesi gerekenler (ölçümde yanlış pozitif çıktı):
    `trendyol-korsan.com`, `vestel-isyeri.com`

`_norm` ayraçları (`.`, `-`, `://`) SİLİYOR — `tutkuelit`, `yeni`,
`trendyolkorsan`, `vestelisyeri` tek birer *token* oluyor. Bu yüzden
"marka etiketin içinde ama etiket alakasız bir kelimeyle birlikte
uzamış" ayrımı YAPILAMAZ: `tutku` ⊂ `tutkuelit` ile
`vestel` ⊂ `vestelisyeri` aynı biçimsel yapıdadır.

Denenen üç kuralın üçü de en az bir meşru eşleşmeyi kırdı:

| Kural | tutkuelit | yeni.com | korsan.com |
|---|---|---|---|
| baştan/başa `startswith` | kırık | kırık | geçer |
| ek sözlüğü (`grup`, `holding`) | geçer | kırık | **yanlış pozitif** |
| `in` + ek kontrolü | kırık | kırık | **yanlış pozitif** |

Sonuç: **düzeltme güvenli değil, kod değiştirilmedi.** Kalıcı çözüm
tokenları ayıran bir normalizasyon (`tutku` + `elit`, `vestel` + `isyeri`
olarak ayrıştırma) gerektirir; bu ayrıştırma için doğru ek sözlüğü
gerekir ve bu bir **TÜREKÇE marka sözlüğü** işidir — tek oturumda
uydurulmaz. Bu dosya o işe kadar ölçümü kilitler.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import katalog as k
from tools.product_resolver import _norm

TRENDYOL = "trendyol"


class TestKiminNettrReddediliyor:
    """Bulgu 1: kimin.net.tr markaya AİT DEĞİL. Eşleştirme doğru çalışıyor."""

    def test_host_eslesmesi_yok(self):
        assert not k._host_markaya_uyuyor(
            TRENDYOL, "https://kimin.net.tr/iletisim")

    def test_yapisal_blok_eslesmesi_yok(self):
        """Canlı sayfanın gerçek hali: ad='myblog', Trendyol değil."""
        assert not k._gercek_markaya_ait(
            TRENDYOL, {"ad": "myblog",
                       "url": "https://kimin.net.tr/person"})

    def test_sayfa_karari_reddediyor(self):
        sayfa = {"metin": "iletisim", "gercekler": [
            {"ad": "myblog", "url": "https://kimin.net.tr/person"}]}
        assert not k._sayfa_markaya_ait(
            TRENDYOL, "https://kimin.net.tr/iletisim", sayfa)

    def test_yabanci_kurum_blogu_reddediliyor(self):
        """Sayfanın içinde başka bir kurumun bloğu varsa o da elenir."""
        sayfa = {"metin": "x", "gercekler": [
            {"ad": "Kimin Market", "url": "https://kimin.net.tr"}]}
        assert not k._sayfa_markaya_ait(
            TRENDYOL, "https://kimin.net.tr/iletisim", sayfa)


class TestGercekMarkalarEslesiyor:
    """Bulgu 3 düzeltilirken bunlar KIRILMAMALI."""

    @pytest.mark.parametrize("marka,site", [
        ("Trendyol", "https://trendyol.com.tr/x"),
        ("Trendyol", "https://trendyol.sa/x"),
        ("Trendyol", "https://partner.trendyol.com/x"),
        ("Trendyol", "https://www.trendyol.com/x"),
        ("Trendyol", "https://trendyolgrup.com/x"),
        ("Arçelik", "https://arcelik.com.tr/x"),
        ("Bosch", "https://bosch.com.tr/x"),
        ("Vestel", "https://vestel.com.tr/x"),
        # Kısa etiket / marka içinde — mevcut testler bunları kilitliyor
        ("Tutku", "https://tutkuelit.com.tr/x"),
        ("YeniMarka", "https://yeni.com/x"),
    ])
    def test_dogru_pozitif(self, marka, site):
        assert k._host_markaya_uyuyor(k._marka_anahtari(marka), site), site


class TestBilinenZayiflik:
    """Bulgu 3: ölçülmüş yanlış pozitifler. Düzeltilmedi — kayıt kilidi.

    Bu test ŞU AN GEÇİYOR ama `True` bekliyor. Yani bugünün davranışını
    kilitler: kural değişirse kırmızıya döner ve o zaman bilinçli bir
    karar verilmiş olur.
    """

    @pytest.mark.parametrize("marka,site", [
        ("Trendyol", "https://trendyol-korsan.com/x"),
        ("Vestel", "https://vestel-isyeri.com/x"),
        ("Trendyol", "https://milyontrendyol.com/x"),
    ])
    def test_yanlis_pozitif_olculdu(self, marka, site):
        """BUGÜN: eşleşiyor (kötü). Kural değişirse kırmızıya döner."""
        assert k._host_markaya_uyuyor(k._marka_anahtari(marka), site), (
            "Bu davranış değişti — ya düzeltildi (iyi) ya da geri alındı "
            "(kötü). Değişiklik bilinçli yapılmalı.")

    @pytest.mark.parametrize("marka,site", [
        ("Trendyol", "https://kimin.net.tr/x"),
        ("Trendyol", "https://alibabagroup.com/x"),
        ("Trendyol", "https://eticaretlink.com.tr/x"),
        ("Vestel", "https://hurriyet.com.tr/x"),
    ])
    def test_bu_alanlar_dogru_cevriliyor(self, marka, site):
        assert not k._host_markaya_uyuyor(k._marka_anahtari(marka), site), site


class TestNedenDuzeltilemez:
    """Çelişkiyi teste bağla: sıkı kural her iki tarafı da tutamıyor."""

    def test_norm_ayiraclari_siler(self):
        """Kök neden: normalizasyon ayraçları yok ediyor.

        `tutku` ⊂ `tutkuelit` ile `vestel` ⊂ `vestelisyeri` bu
        yüzden AYNI biçimsel yapıda — ayrılamazlar.
        """
        assert _norm("tutkuelit") == "tutkuelit"
        assert _norm("trendyol-korsan.com") == "trendyolkorsancom"
        # Ayraç yok olduğu için etiket tek parça:
        assert "." not in _norm("trendyol-korsan.com")

    def test_etiketler_ayristirilamiyor(self):
        """Kabul edilmesi gerekenler ve reddedilmesi gerekenler aynı
        biçimde — bu yüzden tek dize kuralı ikisini birden tutamaz."""
        # YÖN 1: marka etiketin İÇİNDE
        #   kabul: tutku ⊂ tutkuelit        red: trendyol ⊂ trendyolkorsan
        for etiket, marka in (("tutkuelit", "tutku"),):
            assert k._marka_anahtari(marka) in k._marka_anahtari(etiket), \
                "kabul edilen bu bicimde olmali: %s" % etiket
        for etiket, marka in (("trendyolkorsan", "trendyol"),
                              ("vestelisyeri", "vestel")):
            assert k._marka_anahtari(marka) in k._marka_anahtari(etiket), \
                "reddedilenler de AYNI bicimde olmali: %s" % etiket

        # YÖN 2: etiket markanın İÇİNDE (marka uzun, etiket kısa)
        #   kabul: yeni ⊂ yenimarka
        assert k._marka_anahtari("yeni") in k._marka_anahtari("yenimarka")

        # SONUÇ: her iki yönde de 'biri diğerinin içinde' ilişkisi var.
        # Ayırt edici olan YÖN değil, EK'in anlamı — o da sözlük ister.
        # (tutku+elit MEŞRU, vestel+isyeri ALAKASIZ: aynı dize kalıbı)


class TestYapisalBlokYolu:
    """`_sayfa_markaya_ait` içindeki `any(...)` — tek blok yeterli."""

    def test_tek_yeterli_blok_tum_sayfayi_sahipliyor(self):
        """Ölçülen davranış: bir blok eşleşirse sayfa 'ait' sayılır."""
        sayfa = {"metin": "x", "gercekler": [
            {"ad": "Başka Kurum", "url": "https://baska.com"},
            {"ad": "myblog", "url": "https://trendyol.com/blog"}]}
        assert k._sayfa_markaya_ait(
            TRENDYOL, "https://baska.com/iletisim", sayfa)

    def test_kimliksiz_blok_sahipleniyor(self):
        """ÖLÇÜLEN davranış: kimlik alanı boşsa blok 'başkasının' denenmez
        ve sayfa AİT sayılır. Bu fail-open bir varsayılan.

        Neden önemli: `alibabagroup.com` gibi alakasız bir sayfada
        JSON-LD bloğu kimliksiz çıkarsa (ad/url boş), sayfa markaya ait
        kabul edilir. Ölçümde gerçekten böyle sayfalar var.
        """
        assert k._sayfa_markaya_ait(
            TRENDYOL, "https://baska.com/x",
            {"metin": "x", "gercekler": [{"adres_metni": "X Cad. 1"}]})

    def test_yabanci_kimlikli_blok_sahiplenmiyor(self):
        """Ama kimlik alanı DOLU ve yabancıysa elenir (asıl koruma)."""
        assert not k._sayfa_markaya_ait(
            TRENDYOL, "https://baska.com/x",
            {"metin": "x", "gercekler": [{"ad": "Baska Sirket"}]})

    def test_kisa_anahtar_daraltma_yalapilmaz(self):
        assert k._gercek_markaya_ait("ab", {"ad": "Başka Kurum"})


class TestKirilimKaydi:
    """Kayıt dosyası: ölçülen bulgular tek yerde, iddia değil veri."""

    def test_rapor_dosyasi_yapisi(self):
        yol = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "erken-cikis-dondurulmus.json")
        if not os.path.exists(yol):
            pytest.skip("olcum raporu bu kosuda uretilmedi")
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
        for alan in ("marka", "adaylar", "A", "B", "ayni", "okuma_sn"):
            assert alan in veri, "rapor eksik alan: %s" % alan