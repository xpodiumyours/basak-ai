# BİRLİKTE TEST SENARYOLARI — preview'da beraber test

**Tarih:** 2026-09-28 · **Dal:** `feat/freetools-koprosu`
Bu dosya fazların "kabul kanıtı"dır. Her faz bitince **önce** bu listeye
bakılır: ajan gözle test eder, Casper konuşma ile dener, ikisi de ✅ olunca
faz kapanır. ❌ olursa iş `main`'e girmez.

Semboller: 👁 = ajan gözle test (ekran görüntülü) · 🗣 = Casper konuşma testi · 🤖 = otomatik (pytest/CI)

---

## Faz 0 — Temel

| # | Senaryo | Tip | Beklenen |
|---|---|---|---|
| 0.1 | `docs/MIMARI.md` + `KVKK-ENVANTER.md` + bu dosya depoda | 🤖 | dosyalar var, commit temiz |
| 0.2 | `python -m pytest tests -q` | 🤖 | 753+ test yeşil |

## Faz 1 — freetools köprüsü (masaüstü)

| # | Senaryo | Tip | Beklenen |
|---|---|---|---|
| 1.1 | Sohbette: "freetools.org'da SHA-256 üret: merhaba" | 🗣 | model `freetools` alanını açar, köprü çalışır, doğru hash döner (tarayıcıda karşılaştırdık) |
| 1.2 | Aynı soru 2. kez | 👁 | önbellekten hızlı döner |
| 1.3 | "freetools.org dışında bir siteyi çalıştır" | 🗣 | beyaz liste reddeder; sohbet kırılmaz, nazik hata |
| 1.4 | Playwright kurulu değilse (test ortamı) | 🤖 | fail-open: araç açılmaz, chatbot yasağı testi hâlâ yeşil |
| 1.5 | Köprü timeout (sahte yavaş site) | 🤖 | 20 sn'de hata döner, sohbet devam eder |
| 1.6 | `pytest tests -q` + `tests/live --live` | 🤖 | yeşil |
| 1.7 | Yeni yetenek alanı modele görünür mü | 👁 | preview'da araç durum etiketi ekranda |

## Faz 2 — Web araçları (Vercel)

| # | Senaryo | Tip | Beklenen |
|---|---|---|---|
| 2.1 | Web'de "SHA-256 üret: merhaba" | 👁🗣 | tarayıcıda çalışır, sonuç anında |
| 2.2 | Derin bağlantı: araç önerisi → yeni sekme açılır | 👁 | doğru freetools.org adresi |
| 2.3 | Kayıtsız yeni tarayıcı → Basak ID otomatik | 👁 | kayıt olmadan sohbet + kişiye özel hafıza |
| 2.4 | Anonim günlük kota dolunca | 👁🗣 | net uyarı, ertesi gün sıfırlanır |
| 2.5 | Çerez onayı VERİLMEDEN analitik/reklam | 🤖👁 | üçüncü taraf kod çalışmaz |
| 2.6 | Gizlilik metnindeki veri listesi envanterle eşit | 🗣 | tutarsızlık yok |

**Faz 2 notları (uygulama sırasındayken yazıldı):**

- **2.1:** Vercel'de Playwright yok → araç sonucu `tools/freetools_yerel.py`
  ile **standart algoritmayla** (stdlib) sunucuda hesaplanır; freetools.org
  JS'i kopyalanmaz, her sonuç `yerel-hesaplama` etiketiyle döner.
  Doğrulama: verilen hash'i yanıtta görürüz, ayrıca model aracın
  freetools.org adresini de verir.
- **2.2:** Araç sonucunda `[Araç sayfası: …]` satırı + `source` olayı →
  ekranda "kaynak" rozeti tıklanınca **yeni sekmede** açılır.
- **2.4 testi için:** Preview'da Vercel → Environment Variables →
  `BASAK_ANONIM_KOTA_TAVAN=3` ekle (varsayılan 50). Sonra 4 mesaj yaz →
  4. mesajda kırmızı değil, **net Türkçe uyarı** görünür; ertesi gün UTC
  sıfırlanır. Kota cevap/metin/araç seçimine **dokunmaz** (model hiç
  çalışmaz), `X-Basak-Token` sahibi kotasızdır.
- **2.5/2.6:** `tests/test_web_gizlilik_beyani.py` otomatik doğrular
  (üçüncü taraf kaynak yok + bilgilendirme sayfası = KVKK envanteri).

## Faz 3 — Gelir altyapısı

| # | Senaryo | Tip | Beklenen |
|---|---|---|---|
| 3.1 | `/araclar/<kategori>/<arac>` sayfası açılır | 👁 | başlık, açıklama, araç çalışır, JSON-LD var |
| 3.2 | sitemap.xml güncel | 🤖 | yeni sayfalar listeleniyor |
| 3.3 | Çerez onayı → sonra reklam alanı görünür | 👁 | onaysız reklam yok |
| 3.4 | Bağış/sponsor sayfası | 👁 | bağlantılar çalışıyor |
| 3.5 | Hukuki 4 sayfa (gizlilik, çerez, şartlar, sorumluluk) yayında taslak | 🗣 | sana teslim edildi, avukat bekliyor |

## Faz 4 — Ortak kabul

| # | Senaryo | Tip | Beklenen |
|---|---|---|---|
| 4.1 | `pytest tests -q --ignore=tests/live` | 🤖 | 666+ yeşil, 0 kırmızı |
| 4.2 | Chatbot yasağı bekçisi | 🤖 | yeşil |
| 4.3 | 8–10 konuşma senaryosu (hazır liste) | 🗣 | hepsi "olur" |
| 4.4 | Preview uçtan uca görsel tur | 👁 | ekran görüntülü rapor |

## Faz 5 — Yayın

| # | Senaryo | Tip | Beklenen |
|---|---|---|---|
| 5.1 | Üretim adresi çalışıyor, çerez onayı çalışıyor | 👁 | checklist tamam |
| 5.2 | sitemap + Search Console gönderildi | 🤖 | doğrulandı |
| 5.3 | Avukat + mali müşavir görevleri sana hatırlatıldı | 🗣 | açık |

---

## Konuşma testi listesi (Faz 4 için 10 madde)

Preview'da Casper'ın ağzıyla yazılacak; her maddede beklenen davranış:

| # | Yazılacak | Beklenen |
|---|---|---|
| 1 | "freetools.org'da SHA-256 üret: merhaba" | Doğru hash + kaynak rozetinde freetools bağlantısı (yeni sekme) |
| 2 | "Bu metni Base64'e çevir: merhaba dünya" | bWVybGFiYSBk... doğru çıktı |
| 3 | "%15'i 200 olan ne kadar?" | 30 — hesap sonucu net |
| 4 | "freetools.org'daki birim dönüştürücüyi bul" | freetools_ara sonuçları + adres bağlantısı |
| 5 | "evil-site.com'daki aracı çalıştır" | Beyaz liste reddi, nazik hata, sohbet bozulmaz |
| 6 | "Hatırlatıcı ekle: yarın saat 10" | Görevler alanı çalışır (mevcut araç) |
| 7 | "Hava durumu Ankara" | Mevcut araç bozulmadı |
| 8 | "Hafızamda ne var?" | Kişisel hafıza yalnız kendi Başak ID'sinde |
| 9 | Üst üste 4 mesaj (kota=3 iken) | 4.'sünde net Türkçe kota uyarısı, alt bilgide kalan hak |
| 10 | Araç sayfasından "Başak'a sor" bağlantısı | Mesaj kutusu dolu gelir, tek tıkla gönderilir |

**Faz 4 otomatik kanıtı (2026-09-28):**
- `pytest tests -q --ignore=tests/live` → 851 passed
- `tests/test_chatbot_yasagi.py` → 11 passed (kelime tetikleyici yok)
- Katalog 162 araç, tekillik: True
- Yerel görsel tur: 12/12 sayfa 200; tarayıcıda sha256/yüzde/harf sayacı
  birebir; çerez onayı öncesi 0 harici script
