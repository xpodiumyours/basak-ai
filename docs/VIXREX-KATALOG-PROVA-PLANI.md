# VIXREX KATALOG PROVASI — İLK ADIM PLANI

Tarih: 2026-10-01 · Durum: **PLAN — kod yazılmadı**
Dal: `preview` · Dayanak: bu tarihte ölçülen mevcut hat (`tools/katalog.py`) +
`ARAC-PLANI.md` §2 İş 4 (sır sızıntısı kapısı)

**Kapsam kilidi:** Bu dosyada yazmayan hiçbir iş yapılmaz. Kapsamı Casper
büyütür. Emin olunmayan yerde durulur, sorulur — tahminle kod yazılmaz.

---

## 0. Amaç — tek cümle

Başak'ın ürettiği **Vixrex toplu yükleme dosyasını gerçek Vixrex paneline
verip kabul/ret yanıtını ölçmek** — iki depodan hiçbirini diğerine
bağlamadan.

**Neden ilk adım bu:** Canlı kullanıcı yok, katalog hattı zaten yazılı ve
tek eksik halka gerçek platform yanıtı. Bugün kod yazmadan ölçülebilen tek
şey bu. Yeni özellik eklemek bu adımın kapsamı **değildir**.

---

## 1. Karışmama sözleşmesi (değişmez)

| Kural | Dayanak |
|---|---|
| Başak vixrex'e **YAZMAZ** — ne dosya, ne HTTP | `tools/katalog.py:1010` — "Vixrex toplu API'si sahip oturumu istediği için Başak doğrudan ürün basamaz… Vixrex'e yazma yok" |
| vixrex deposunda bu iş için **tek satır değişmez** | İki ayrı depo, iki ayrı klasör; vixrex tarafı Casper'ın alanı |
| **Ortak paket / ortak kütüphane yok** | `requirements.txt`'e dokunulmaz (yeni bağımlılık yasağı) |
| Vixrex'in sırları Başak'a **girmez** | `read_file` kara listesi + `icerik_ara` maskeleme — `ARAC-PLANI` §2 İş 4, kanıtlı |
| Vixrex erişimi **salt okuma** kalır | `tools/olcum.py:24` — `PROJELER` beyaz listesi |
| `testleri_kos`'a vixrex **eklenmez** | `tools/testkos.py:8` — "vixrex KASITLI yok (işlem yasağı)" |

**Tek temas noktası: dosya (CSV/JSON).** Başka hiçbir bağ kurulmaz.

---

## 2. Ölçülmüş mevcut durum

Hattın tamamı **zaten yazılı ve testli**; bu iş yeni hat kurmuyor, mevcut
hattı gerçek platformla sınıyor.

| Parça | Yer | Durum |
|---|---|---|
| Fatura/ürün fotoğrafı kaydı | `tools/katalog.py:354` `fatura_kaydet_b64` (şemasız; UI/Telegram girişi) | Var |
| Görsel okuma (+ aday satır, üstbilgi) | `tools/katalog.py:522` `fatura_oku` | Var |
| Doğrulama + aile birleştirme + kart kurma | `tools/katalog.py:663` `katalog_kur` | Var |
| Ürün kimliğini webde çözme (barkod/GTIN/SKU) | `tools/katalog.py:1303` `urun_eslestir` | Var |
| Marka kullanım izni | `tools/katalog.py:1172` `yetki_belgesi_ekle` | Var |
| Çıktı üretimi → CSV + JSON | `tools/katalog.py:922` `katalog_onayla` | Var |
| **Ön denetim (Vixrex kuralları)** | `tools/katalog.py:1051` `yayin_paketi` | Var — 5 MB sınırı, başlık denetimi, satır denetimi, iş uyarıları (fiyatsız / izinsiz / düşük güven) |
| Çıktı okuma | `tools/katalog.py:989` `cikti_oku` | Var |
| Veri klasörleri | `gelen/` (staging), `katalog/`, `yetki/` — durum kökü altı | Var |

**Biçim eşleşmesi iddiasının kaynağı (kodda yazılı):**

- CSV başlığı `Ürün Adı · Fiyat · Açıklama · Kategori · Stok Durumu ·
  Görsel URL` — `tools/katalog.py:71`, gerekçe: `vixrex
  bulk_product_upload_service.dart generateTemplateCsv`
- Stok etiketleri `Mevcut / Tükendi / Son birkaç adet` —
  `tools/katalog.py:76`, gerekçe: Vixrex `StockStatus` labelları

> ⚠️ Bu iki eşleşme **kodda birebir kopyalanmış**, ama gerçek panelle
> **henüz doğrulanmadı**. Bu planın tüm varlık sebebi o boşluk.

---

## 3. Adımlar

### Adım 0 — Hazırlık (Casper, kod yok)
1. Prova için bir **test işletmesi/vitrin** seçilir (canlı kullanıcıya
   dokunulmaz).
2. Prova ürünü seçilir. **Öneri: markasız veya Casper'ın kendi ürünü** —
   üçüncü taraf markada `yetki_belgesi_ekle` şartı çıkar, provayı
   karmaşıklaştırır.
3. Kaç ürünlük prova: **en az 1, önerilen 3–5 satır** (tek satır, toplu
   yüklemenin gerçek davranışını göstermez).

### Adım 1 — Başak tarafı uçtan uca koşum (kod değişmez)
Gerçek bir ürün fotoğrafı/faturası hattan geçirilir:
`fatura_kaydet_b64 → fatura_oku → katalog_kur → urun_eslestir →
katalog_onayla`.

**Çıktı kanıtı:** `katalog/<is_id>/` altında `vixrex_urunler.csv`,
`vixrex_batch.json`, `basak_katalog.json` dosyalarının **kendisi** (ekran
görüntüsü değil, dosya).

### Adım 2 — Ön denetim (Vixrex'e gitmeden)
`yayin_paketi(is_id, platform="vixrex")` koşulur.

**Çıktı kanıtı:** rapor metni — kabul kararı, şekil denetimi hataları, iş
uyarıları (fiyatsız / izinsiz / düşük güven). Buradaki hatalar daha paneli
görmeden yakalanmalı; yakalanmayan her hata Adım 4'te sınıflandırılır.

### Adım 3 — GERÇEK panel provası (Casper, elle)
CSV, Vixrex panelindeki **toplu ürün yükleme** ekranına verilir.

**Çıktı kanıtı:** panelin gerçek yanıtı — kabul ekranı veya hata mesajı.
Ekran görüntüsü veya panel metni; ikisi de olur, **tahmin olmaz**.

> Başak bu adımı yapamaz: Vixrex toplu API'si sahip oturumu istiyor
> (`tools/katalog.py:1010`). Bu yüzden aktarım elle ve bilinçli.

### Adım 4 — Yanıtı sınıflandır
Panelin yanıtı üç kovadan birine konur:

| Kova | Ne demek | Kim düzeltir |
|---|---|---|
| **Biçim hatası** | Başlık, sütun, etiket, kodlama, boyut | Başak tarafı — `tools/katalog.py` tek dosya, ayrı commit |
| **İş kuralı** | Fiyat/kategori/görsel zorunluluğu, mağaza ayarı | Casper kararı; Vixrex koduna **dokunulmaz** |
| **Platform hatası** | Vixrex tarafı hata/kısıt | Kaydedilir, Başak tarafında değişiklik yapılmaz |

### Adım 5 — Kanıt kaydı
Prova sonucu tek dosyada toplanır (öneri: `docs/VIXREX-KATALOG-PROVA-SONUC.md`):
tarih, işletme, ürün sayısı, panel yanıtı, sınıflandırma, yapılan düzeltme
(varsa), kalan sınır. Kod değiştiyse **adım başına bir commit**.

---

## 4. Kabul ölçüsü

| # | Kapı | Kabul |
|---|---|---|
| 1 | Başak hattı gerçek girdiyle koştu | Çıktı dosyaları diskte var, içerikleri okunabilir |
| 2 | Ön denetim çalıştı | `yayin_paketi` raporu üretildi, karar metni okunur |
| 3 | **Gerçek panel yanıtı alındı** | Kabul veya hata mesajı — **ekran görüntüsü/panel metni** |
| 4 | Karışmama korundu | vixrex deposunda bu iş için **0 satır** değişiklik; `requirements.txt` değişmedi |
| 5 | Sır kapısı korundu | Prova çıktısında/raporunda vixrex `.env` içeriği **yok** |
| 6 | Test tabanı düşmedi | `python3 -m pytest tests -q` — mevcut taban (954 yeşil, 19 skipped, Linux'ta Windows'a özel 1F+3E) |
| 7 | Lint | `ruff check .` yeşil |

> **Kabul edilmeyen kanıt:** simüle panel yanıtı, elle yazılmış "yüklendi"
> raporu, dosyanın varlığını göstermeyen anlatım. (AGENTS.md §9 — sahte
> kabul yasakları.)

---

## 5. Bu işte YASAK

- Vixrex deposunda **herhangi bir değişiklik** (dal, commit, dosya dahil)
- Başak'tan vixrex'e **HTTP/API yazma** — otomatik yükleme bu adımın işi değil
- Ortak paket, ortak kütüphane, ortak `.env`
- Yeni araç uydurma; gerçekten gerekirse **dört yerin dördü birden**
  (`tools/definitions.py` + `tools/__init__.py` `calistir()` +
  `chat/agent_protocol.py` `YETENEK_ALANLARI` + `chat/tools.py` durum metni)
- Kelimeye bakan tetikleyici, açıklamaya davranış koçluğu, modele görev
  dayatan prompt satırı (AGENTS.md §0)
- `testleri_kos`'a vixrex eklemek
- Panel/prova sonucunu **tahminle** yazmak

---

## 6. Riskler ve bilinen sınırlar

| Risk | Etki | Şimdi ne yapılır |
|---|---|---|
| CSV başlığı/stok etiketi Dart kaynağından kopya, panelde doğrulanmadı | Toplu yükleme reddeder | Adım 3'ün tek amacı bu — ölçülür |
| **Görsel URL** sütunu: Başak görselleri barındırmıyor | Satır "görsel adresi http(s) değil" ile reddedilir (`katalog.py:1046`) | Adım 1'de ölçülür; barındırma yoksa Casper kararı (Adım 7) |
| **Kategori** alanı: Vixrex'te serbest metin mi, sabit liste mi | Yanlış kategori reddi | Adım 3'te panel yanıtından okunur |
| Fiyat zorunluluğu / aralığı | Fiyatsız kart "hazır" CSV'ye girmiyor (`is_uyarilari`) | Adım 2'de görünür |
| Üçüncü taraf marka → izin belgesi şartı | Prova bloke olur | Adım 0'da markasız ürün seçilir |
| Panel davranışı sürüme bağlı değişebilir | Prova bir kez doğrular, sürekli garanti değil | Adım 5'te tarih + sürüm notu yazılır |

---

## 7. Casper kararı gereken noktalar (kod yazmadan önce)

1. **Prova işletmesi:** yeni bir test vitrini mi açılsın, mevcut bir tanesi mi
   kullanılsın? (Canlı kullanıcı yok, ama vitrin sayısı ve panel kirliliği
   kararı Casper'ın.)
2. **Prova ürünü ve markası:** markasız/kendi ürün mü, gerçek marka mı?
   (Gerçek marka ise `yetki_belgesi_ekle` şartı ve hukuki taraf devreye girer.)
3. **Görsel barındırma:** Başak görsel URL'si üretemiyor. Probe için
   (a) görselsiz satır denenir, (b) görseller ayrıca elle panele yüklenir,
   (c) barındırma çözümü ayrı iş olarak planlanır — hangisi?

Bu üçü netleşmeden Adım 1'e geçilmez.

---

## 8. Bu plandan sonra (kapsam dışı, sıraya girmez)

Sıradaki iş kolları ayrı karar gerektirir ve **bu planın parçası değildir**:
vitrin içeriği (metin/etiket) üretimi · vixrex "proje gözü" (salt okuma
raporu, kod gerekmiyor) · ziyaretçiye cevap veren asistan (trafik gelince).
