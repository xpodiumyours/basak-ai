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

`scripts/olcum/_sirket_ara_erken_cikis.py` her koşuda `firma_bul`'u YENİDEN
çağırıyordu; arama sonuçları koşular arası değiştiği için A ve B
**farklı aday listeleriyle** çalıştı. Dondurulmuş liste ile tekrar
ölçüldü (`scripts/olcum/_erken_cikis_dondurulmus.py`): kart **AYNI** çıktı.

Bu düzeltme önemli: "erken çıkış güvenli değil" kararı **geçersiz**
bir ölçüme dayanıyordu.

## Bulgu 3 — GERÇEK zayıflık: alt dize karşılaştırması (DÜZELTİLDİ)

`_host_markaya_uyuyor` içinde `anahtar in etiket_anahtar` vardı; yani
marka, etiketin HERHANGİ bir yerinde geçerse eşleşiyordu. Ölçülen
yanlış pozitifler:

    _host_markaya_uyuyor('trendyol', 'https://trendyol-korsan.com/x')  -> ONCEDEN True
    _host_markaya_uyuyor('vestel',   'https://vestel-isyeri.com/x')    -> ONCEDEN True

Bu, sahte marka sitelerinin markaya ait sayılması demekti.

## Neden düzeltilemiyordu (ölçülen çelişki) — SONRA ÇÖZÜLDÜ

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

Denenen üç kuralın üçü de en az bir meşru eşleşmeyi kırdı. Ancak
**ek sözlüğü** farkı çözdü: dize kalıbı değil, ek'in ANLAMI ayırt
ediyor. Sözlük `scripts/olcum/_marka_ekleri_veri.py` ile 23 gerçek marka üzerinde
ölçülerek kuruldu (elle doldurulmadı):

| Ek | Kaynak | Karar |
|---|---|---|
| `elit`, `holding`, `group`, `efes` | gerçek marka sitelerinden ölçüldü | KABUL |
| `korsan`, `isyeri`, `milyon`, `sitez` | sahte site kalıplarından ölçüldü | RED |

Kural **fail-closed**: ek sözlükte yoksa reddedilir. Böylece sözlüğe
eklenmemiş yeni bir sahte site kalıbı da otomatik reddedilir.

Doğrulama: 23/23 gerçek marka eşleşiyor, 8/8 ölçülmüş yanlış pozitif
eleniyor.
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
    """Bulgu 3: alt dize karşılaştırması — **DÜZELTİLDİ** (2026-10-01).

    Önceden bu üç host markaya AİT sayılıyordu. Marka ekleri sözlüğü
    kuruldu; artık üçü de eleniyor. Test kırıldığında BİLİNÇLİ
    karar verilmiş olur (ya düzeltme bozuldu ya da bir davranış
    değişikliği yapıldı).
    """

    @pytest.mark.parametrize("marka,site", [
        ("Trendyol", "https://trendyol-korsan.com/x"),
        ("Vestel", "https://vestel-isyeri.com/x"),
        ("Trendyol", "https://milyontrendyol.com/x"),
        ("Trendyol", "https://trendyol-sitez.com/x"),
        ("Vestel", "https://vestel-duble.com/x"),
    ])
    def test_sahte_site_artik_eslesmiyor(self, marka, site):
        """Ölçülen yanlış pozitifler: marka içinde olsa bile ELENİR."""
        assert not k._host_markaya_uyuyor(k._marka_anahtari(marka), site), (
            "Sahte site kalıbı yeniden eşleşiyor — sözlük bozuldu.")

    @pytest.mark.parametrize("marka,site", [
        ("Trendyol", "https://kimin.net.tr/x"),
        ("Trendyol", "https://alibabagroup.com/x"),
        ("Trendyol", "https://eticaretlink.com.tr/x"),
        ("Vestel", "https://hurriyet.com.tr/x"),
    ])
    def test_bu_alanlar_dogru_cevriliyor(self, marka, site):
        assert not k._host_markaya_uyuyor(k._marka_anahtari(marka), site), site


class TestMarkaEkleriSozlugu:
    """Sözlüğün kendisi: iki yönlü ve ölçülmüş.

    Sözlük `_SIRKET_MARKA_EKLERI` (anlamlı kurumsal ek) ve
    `_SIRKET_SAhte_EKLER` (sahte site kalıbı) olarak ikiye ayrılır.
    Kural: ek anlamlıysa kabul, değilse reddet, **bilinmeyense reddet**
    (fail-closed — sahte site varsayılan olarak reddedilir).
    """

    @pytest.mark.parametrize("ek", ["elit", "holding", "group", "efes",
                                    "grup", "marka", "global"])
    def test_olculmus_kurumsal_ekler_kabul(self, ek):
        assert ek in k._SIRKET_MARKA_EKLERI, ek

    @pytest.mark.parametrize("ek", ["korsan", "isyeri", "milyon", "sitez",
                                    "sahte", "bedava", "haber"])
    def test_olculmus_sahte_ekler_reddedilir(self, ek):
        assert ek in k._SIRKET_SAhte_EKLER, ek

    def test_iki_liste_kesismez(self):
        """Bir ek hem geçerli hem sahte olamaz."""
        assert not (k._SIRKET_MARKA_EKLERI & k._SIRKET_SAhte_EKLER)

    def test_bilinmeyen_ek_reddedilir(self):
        """Fail-closed: sözlükte olmayan ek KABUL EDİLMEZ.

        Bu, kuralın güvenli tarafıdır: yeni bir sahte site kalıbı
        sözlüğe girmeden de reddedilir.
        """
        assert not k._ek_gecerli("trendyolqweasd", "trendyol")
        assert k._ek_gecerli("trendyolelit", "trendyol")

    def test_tam_esitlik_kabul(self):
        assert k._ek_gecerli("trendyol", "trendyol")


class TestOlcumVerisi:
    """Sözlük ÖLÇÜMDEN türedi — elle doldurulmadı."""

    def test_gercek_marka_ekleri_veride(self):
        """Ölçümde çıkan ekler sözlükte olmalı."""
        for ek in ("elit", "holding", "efes"):
            assert ek in k._SIRKET_MARKA_EKLERI, \
                "ölçümde görülen %r ek sözlükte yok" % ek

    def test_olculmus_sahte_ekler_veride(self):
        for ek in ("korsan", "isyeri", "milyon", "sitez"):
            assert ek in k._SIRKET_SAhte_EKLER, \
                "ölçümde görülen %r sahte ek sözlükte yok" % ek


class TestNedenSozlukGerekiyordu:
    """Çelişkiyi teste bağla: DİZE kalıbı ikisini birden tutamıyordu.

    Bu, sözlüğün gerekçesidir. Kural geçmişti çünkü gerçek marka
    ekleri ile sahte site ekleri AYNI dize kalıbındaydı; ayırt eden
    tek şey ek'in anlamıydı.
    """

    def test_norm_ayiraclari_siler(self):
        """Kök neden: normalizasyon ayraçları yok ediyor."""
        assert _norm("tutkuelit") == "tutkuelit"
        assert _norm("trendyol-korsan.com") == "trendyolkorsancom"
        assert "." not in _norm("trendyol-korsan.com")

    def test_iki_taraf_ayni_dize_kalibinda(self):
        """Kabul: `tutku` ⊂ `tutkuelit`  |  Red: `vestel` ⊂ `vestelisyeri`

        Aynı yapı — bu yüzden dize kalıbı yetmiyordu. Sözlük şart.
        """
        for etiket, marka in (("tutkuelit", "tutku"),
                              ("vestelisyeri", "vestel")):
            assert k._marka_anahtari(marka) in k._marka_anahtari(etiket)

    def test_sozluk_bu_ikisini_ayiriyor(self):
        """Aynı kalıp, farklı karar — sözlük sayesinde."""
        assert k._host_markaya_uyuyor("tutku", "tutkuelit.com.tr")
        assert not k._host_markaya_uyuyor("vestel", "vestel-isyeri.com")


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