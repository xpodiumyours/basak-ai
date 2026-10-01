# BAŞAK HARİTA MASTER PLANI — SIFIR MALİYET

**Tarih:** 2026-10-01 · **Durum:** PLAN — kod yazılmadı
**Dal:** `preview` (iş başlarken `main`den kısa dal açılır — AGENTS.md §10)
**Kural:** adım başına bir commit; tek dev commit kabul edilmez
**Kapsam kilidi:** Bu dosyada yazmayan hiçbir iş yapılmaz. Kapsamı Casper büyütür.
Emin olunmayan yerde **durulur ve sorulur**.

---

# BÖLÜM A — ÇERÇEVE

## A1. "Maliyetsiz" tanımı

| Var | Yok |
|---|---|
| Para ödenmeyen API'ler | Kart/faturalandırma hesabı zorunlu her hizmet |
| Anahtarsız ücretsiz servisler | Aşımda **otomatik ücretlendiren** her şey |
| Kartsız kayıtla verilen ücretsiz anahtar (yalnız 1 hizmet) | Kendi sunucu kurulumu gerektiren çözümler |
| OSM verisini kendi tarafımızda saklamak (ODbL atıfla) | Google Maps Platform verisi (saklama yasak) |

**Kota/limit maliyet değildir** — sıfır lira ödenir, hizmet politikasına uyulur.

## A2. Ölçülmüş mevcut durum (2026-10-01)

| Parça | Yer | Durum |
|---|---|---|
| Şehir → koordinat | `tools/hava.py:15` (Open-Meteo geocoding) | Var — yalnız hava durumu için kullanılıyor |
| Adres metni çıkarma | `tools/katalog.py:1483` `sirket_ara` | Var — **koordinat yok, haritada gösterilemez** |
| `adres_kontrol` | `tools/__init__.py:214` | URL erişilebilirliği; adres değil |
| Coğrafi kodlama aracı | — | **Yok** |
| Harita katmanı | — | **Yok** |
| POI / işletme araması | — | **Yok** |
| Rota / mesafe | — | **Yok** |

**Kayıt defteri ölçümü (çalıştırıldı):**

```
validate_registry() → {'ok': True, 'tool_count': 55, 'namespace_count': 14,
                       'missing': [], 'unknown': [], 'duplicates': []}
```

**⚠️ Ölçülen tuzak (ilk tahmin 12'ydi — gerçek 22):** araç sayısı **22 test
satırında**, yetenek alanı sayısı **3 satırda** kilitli. Her yeni araçta hepsi
güncellenmeli, yoksa test kırmızıya döner.

| Dosya | Satırlar (`55` → `56`) | Alan (`14` → `15`) |
|---|---|---|
| `tests/test_agent_protocol.py` | 22, 25, 41, 85, 418, 432, 557, 558, 589, 597, 598 | 22, 595 |
| `tests/test_p2_canli_oncesi.py` | 216, 380, 381, 452 | 449 |
| `tests/test_seviye0_sozlesme.py` | 162, 163, 176, 402, 540 | — |
| `tests/test_uc_yer.py` | 77, 78 | — |

Ayrıca **test fonksiyon adları** sayı taşır (`test_55_arac_...`,
`test_14_namespace_55_araci_...`) — onlar da yeniden adlandırılmalı, yoksa
belge ile kod çelişir. `test_seviye0_sozlesme.py:540` çarpım kilidi de var:
`len(KAPSAM) × 55 = 385` → `× 56 = 392`.

**Z1 yeniden ölçümü (56 → 57, 2026-10-01):** aynı 22 satır + bu kez **6 test
fonksiyon adı** (`test_57_arac_...`, `test_15_namespace_57_araci_...`) ve
`test_seviye0_sozlesme.py:540` → `× 57 = 399`. Alan satırları (15) değişmedi:
yeni araç mevcut `harita` alanına girdi. Belge/README/kabul planı sayaçları da
güncellendi (`README.md` 4/140/200, `knowledge/kabul-plani-web-gate.md`,
`docs/p2-canli-oncesi-12-risk.md`, `docs/p2-platform-ortak-mimari.md`).

**Yeniden kullanılacak koruma (yazılmayacak, çağrılacak):**
`tools/web_search.py` → `_guvenli_adres`, `_engelli_ip_nedeni`, `_GuvenliYonlendirme` (SSRF).

## A3. Maliyetsiz araç seti (kaynaklı)

| Katman | Araç | Anahtar | Sınır | Resmî kaynak |
|---|---|---|---|---|
| Yol tarifi bağlantısı | Google Maps URLs | **YOK** | Kota yok | developers.google.com/maps/documentation/urls/get-started — *"You don't need a Google API key to use Maps URLs"* |
| Adres → koordinat | **Photon** (komoot/OSM) | Yok | `include`/`exclude` kategori filtresi + `bbox` | github.com/komoot/photon |
| Şehir → koordinat | Open-Meteo — **Başak'ta var** | Yok | Şehir seviyesi | `tools/hava.py:15` |
| Adres katalogu | Nominatim (OSM) | Yok | **1 istek/sn**, toplu yasak, User-Agent zorunlu | operations.osmfoundation.org/policies/nominatim |
| İşletme / POI | **Overpass API** | Yok | Fair use; genel sunucu yoğun olabilir | dev.overpass-api.de |
| Rota + süre | **OpenRouteService** (Standard) | Ücretsiz, **kartsız** | ~2.000 `/directions`/gün | openrouteservice.org + ask.openrouteservice.org/t/5806 |
| Harita görseli | **OpenFreeMap** + Leaflet/MapLibre | Yok | *"no limits on map views or requests… no API keys"* | openfreemap.org |

## A4. Zincirin DIŞI (maliyetsiz değil — yazılmayacak)

| Neden dışı | Kanıt |
|---|---|
| Google Places / Geocoding / Routes | Kart zorunlu; SKU aşımında ücret |
| Google Navigation SDK (sesli turn-by-turn) | Enterprise SKU; hedef başına ücret; **billing zorunlu** |
| OSRM demo sunucu | *"should not be used in production as it may be offline or overloaded"* |
| OSRM / Valhalla kendi kurulumu | TR extract ~1 GB, ön işleme bellek ağır; **Oracle planın 1 OCPU/1 GB kaldırmaz** |
| Google Places ile analiz | `place_id` dışında saklama yasak; *"Customer will not create content based on Google Maps Content"* |

> **Zincirin tavanı:** rota + mesafe + süre + haritada gösterme + POI analizi.
> **Sesli otomatik navigasyon maliyetsiz değildir.**

## A5. Değişmez kurallar (AGENTS.md'ye bağlı)

1. **Yeni pip paketi yok** — `requests` + stdlib (`urllib.parse`, `math`, `json`). `requirements.txt` değişmez.
2. **Her yeni araç dört yerin dördünde** (Bölüm D'de tablo) — biri eksikse araç sessizce ölür.
3. **Kelime tetikleyicisi yazılmaz**; araç açıklamasına davranış koçluğu yazılmaz — yalnız ne yaptığı, hangi parametreyi aldığı, **ne döndürdüğü**, sınırı.
4. **Model çıktısına dokunulmaz** (temizleme, ek satır, emoji silme, tavan).
5. **SSRF savunması yeniden yazılmaz**, mevcut çağrılır.
6. **Atıfsız OSM verisi kullanılmaz/saklanmaz** → `© OpenStreetMap katkıda bulunanlar`.
7. **Hizmet politikası ≠ model kısıtı.** Nominatim 1 istek/sn kuralı yüzünden **araç turu sınırı / turda araç kapatma yazılmaz** (AGENTS.md §0/5 yasağı).
8. **Anahtar `ayarlar.json`'a girer**, commit'e girmez (pre-commit hook denetler).

---

# BÖLÜM B — KARARLAR (Casper — kod başlamadan)

| # | Karar | Seçenekler | Durum |
|---|---|---|---|
| **D1** | Öncelik sırası | (a) Z0→Z1→Z2→Z3→Z4a→Z4b→Z5 (b) başka sıra | ⏳ bekliyor |
| **D2** | Z4b anahtarı | (a) OpenRouteService ücretsiz kayıt açılır (b) açılmaz | ✅ **(a) — 2026-10-01 Casper: "ücretsiz her şeyi kullanabiliriz"**. Anahtar kartsız olacak; kart isteyen hizmet yine yasak (A1). |
| **D3** | Z5 yazma yolu | (a) `episodik_kaydet` (b) **dosya + semantic indeks** (c) ayrı tablo (d) yazma yok | ⏳ **öneri (b)** — gerekçe B2'de, ölçülmüş tuzak dahil |
| **D4** | Görünüm yüzeyi | (a) `ui/` masaüstü (b) `web/` Vercel (c) ikisi | ✅ **(b) `web/` — 2026-10-01 Casper kararı.** ⚠️ Bu karar korunan bir gizlilik sözünü tetikliyor → **B3'ü okuyun**; Z2 başlamadan A/B/C seçilmeli. |

**D1, D3, D4 onaylanmadan FAZ 1'e geçilmez.**

---

## B2. Karar gerekçeleri (ölçülmüş)

### D4 — `ui/` ile `web/` nedir, ayrım ne?

| | `ui/` | `web/` |
|---|---|---|
| Kim görür | **Yalnız Casper'ın kendi bilgisayarı** | **Herkes** (Vercel'de yayında) |
| Nasıl açılır | `basak_app.py:52` `UI_DIR` → `:527` `webview.create_window` (**masaüstü pencere**) | `app.py:1176` `app.mount("/", _Statik(directory=WEB, html=True))` (FastAPI → tarayıcı) |
| Dosyalar | `index.html`, `app.js`, `style.css`, `head.js`, `three.min.js` (Three.js orb) | `index.html`, `app.js`, `chat.css`, `styles.css` + hukuki sayfalar (`gizlilik`, `sartlar`, `cerez`, `sorumluluk`, `bilgilendirme`), `reklam-ver.html`, `lab.html` |
| İnternet | Kapalı — yerel pencere | Açık — canlı site |
| Önbellek | — | `_Statik` HTML'e `no-store` koyar, **CSS/JS'e koymaz** → `?v=` sürüm kilidi bu yüzden var (`chat.css?v=11`) |

**Ayrım özeti: `ui/` = kişisel pencere, `web/` = vitrin.** İki ayrı arayüz,
**ortak Python çekirdeği** (`chat/`, `brain/`, `tools/`). ⚠️ `index.html` ve
`app.js` **iki kopya**: biri değişince diğeri değişmez.

**Harita için öneri: ilk sürüm `ui/`.** Gerekçe: (1) harita görsel doğrulama
ister, masaüstünde anında test edilir; (2) `web/` canlıdır — hata maliyeti
yüksek; (3) **konum verisi KVKK'da kişisel veridir**, canlı siteye konum
özelliği koymak gizlilik beyanı güncellemesi ister. Not: **Z0 ve Z1 hiçbir
yüzeye bağlı değil** (Z0 URL üretir, Z1 koordinat döner) → ilk iki faz D4'ten
bağımsız başlayabilir.

### D3 — Analiz verisi nereye yazılır?

Ölçülen gerçekler:

- `memory/engine.py:52` → **`EPISODIK_LIMIT = 5000`** ve satır 46'daki not:
  *"En eskiler otomatik budanır — dosyalardan türetilen semantic kayıtlar
  (knowledge/defter/obsidian) bu sınıra girmez."*
- `chat/context.py:294-305` → indekslenen klasörler: **`casper` oturumunda**
  global `knowledge/` + Obsidian; **diğer kullanıcılarda** yalnız
  `data/<uid>/knowledge/`.
- `memory/engine.py:519` → `indeksle_klasor(..., uzantilar=(".md",))`:
  **yalnız `.md` indekslenir.** Bir `.json` dosyası yazmak indekslenmez.
- `data/` içinde kullanıcı kökleri (`u<id>/`) **gitignore'dadır** (commit
  `7a98b72`) — kişi başı web verisi commit'e girmez.

| Seçenek | Kalıcı mı | Değerlendirme |
|---|---|---|
| (a) `episodik_kaydet` | ❌ **HAYIR** | 5000 sınırında **en eskiler budanır** → analiz sessizce silinir. **Tuzak.** |
| **(b) `.md` dosya + mevcut semantic indeks** | ✅ **EVET** | Semantic kayıtlar budanmaz (kodda yazılı); motor değişmez; normal hafıza aramasıyla bulunur |
| (c) Ayrı tablo | ✅ | `memory/engine.py` şeması değişir — gereksiz risk, motor dokunulmaz kalsın |
| (d) İndekssiz düz dosya | ✅ | Kalıcı ama **Başak bulamaz** → hafıza işe yaramaz |

**Öneri (b), somut yol:**

| Oturum | Yazılacak yer |
|---|---|
| Casper (masaüstü) | `knowledge/harita/<bölge>.md` |
| Diğer kullanıcı (web) | `data/<uid>/knowledge/harita/<bölge>.md` |

Dosya başlığında **zorunlu atıf** satırı olur: `© OpenStreetMap katkıda bulunanlar`
(ODbL). Dosya `.md`'dir çünkü indeksleyici yalnız `.md` okur.

⚠️ `knowledge/` git'te izlenir; **web kullanıcılarının analizi oraya yazılmaz**
(o yol yalnız `casper` oturumunda indekslenir ve commit'e girebilir).

### B3 — D4 = `web/` seçildi: bunun bedeli (ölçülmüş)

**Bulgu:** `web/` arayüzü "hiçbir üçüncü taraf kaynağı yüklemez" sözüyle
kilitli. `tests/test_web_gizlilik_beyani.py` (dosya başlığı: *"Faz 2 kabul 2.5
ve 2.6"*) bunu üç testle zorluyor:

| Test | Ne yasaklıyor |
|---|---|
| `test_html_ve_js_tamami_yerel_kaynak` | `web/*.html` + `web/*.js` içinde `<script\|link\|img\|iframe\|object\|embed src/href="//...">` — **harici kaynak yok** |
| `test_reklam_analitik_imzasi_yok` | reklam/analitik imzaları (`googletagmanager`, `adsbygoogle`, `hotjar`…) |
| `test_ucuncu_taraf_cagri_api_yok` | `fetch("https://…")` — **yalnız aynı origin** |

Aynı söz `docs/KVKK-ENVANTER.md` ↔ `web/bilgilendirme.html` eşleşmesiyle de
korunuyor (`TestGizlilikMetniEslestigi`): gizlilik metni ile veri envanteri
**aynı verileri** söylemek zorunda.

**Neden önemli:** harita karosu (OpenFreeMap) yüklemek, ziyaretçinin
**IP'sini + hangi bölgeye baktığını** üçüncü tarafa gösterir — bu
**yaklaşık konumdur**, KVKK'da kişisel veridir. Testin var olma sebebi tam
budur.

> ⚠️ **Dürüst uyarı — testi kandırmak yasak:** karo adresi JS içinde düz metin
> olarak durursa iki regex de onu **yakalamaz** ve test **sessizce yeşil
> kalır**. Bu, sözün bozulduğu ama kapının görmediği durumdur. AGENTS.md §9
> "sahte kabul" yasağı bunu kapsar — **bu yolu kullanmayacağız.**

**Seçenekler (Z2 başlamadan biri seçilecek):**

| | Ne | Görsel | Söz/KVKK |
|---|---|---|---|
| **A** | Karo yükle, **sözü bilinçli değiştir**: KVKK envanteri + `bilgilendirme.html` + ilgili test aynı commit'te güncellenir ("harita karosu için OpenFreeMap'e istek gider, IP görünür") | ✅ gerçek harita | ⚠️ Söz değişir — **Ay'dırılır ve avukat onayı gerektirir** (FAZ5 §4) |
| **B** | Karo **yok**: `web/` yalnız Z0 **bağlantısını** ve Z1 **koordinatını** gösterir; "Haritada aç" düğmesi kullanıcıyı Google Maps'e götürür | ❌ gömülü harita yok | ✅ Söz aynen kalır, KVKK değişmez |
| **C** | Hibrit: varsayılan B; karo **kullanıcı tıklayınca** yüklenir (açık onay) | ✅ tıklayınca | ⚠️ Söz yine değişir (daha zayıf, ama değişir) |

**Öneri: ilk sürüm B.** Z0 + Z1 zaten asıl faydayı veriyor (bağlantı +
koordinat) ve **hiçbir söz/KVKK işi doğurmuyor**. Görsel harita isteniyorsa C,
sonra A.

**✅ Avantaj (web kararının iyi tarafı):** `web/` Freebuff önizlemesinde
(`app.py`, port 8000) **gerçekten açılabilir** ve ekran görüntüsü alınabilir —
masaüstü penceresinde bu yok.

---

# BÖLÜM C — TODO LIST

> Her `[ ]` bağımsız bir iştir. Faz sonunda **tek commit**; commit mesajı hangi
> adım olduğunu yazar. Commit öncesi Bölüm D kapıları koşulur.

## FAZ 0 — Hazırlık — ✅ TAMAMLANDI (2026-10-01)

- [x] **T0.1** Dal: ⚠️ **sapma — yeni dal açılmadı.** Oturum boyunca çalışılan **`preview`** dalı kullanıldı (yerleşik akış: fazlar `preview`da ilerler, sonra `main`e alınır). Yeni dal açmak Freebuff çalışma alanının dalını değiştirirdi; kapsam büyütmemek için yapılmadı.
- [x] **T0.2** **D1 onaylandı:** Z0→Z1→Z2→Z3→Z4a→Z4b→Z5 sırası kabul edildi.
- [x] **T0.3** **D2 — ONAYLANDI (2026-10-01):** ücretsiz hizmetler kullanılabilir. Faz 6'da **OpenRouteService kartsız ücretsiz anahtarı** alınacak. **Kart isteyen hizmet yasağı (A1) aynen durur** — "ücretsiz" serbestliği kart zorunluluğunu kaldırmaz.
- [x] **T0.4** **D3 onaylandı:** (b) **`.md` dosya + mevcut semantic indeks** — motor değişmez, `episodik_kaydet` kullanılmaz (budama tuzağı, B2).
- [x] **T0.5** **D4 onaylandı:** yüzey **`web/`** (Casper kararı) + **D4b = B** — gömülü harita karosu **yok**; `web/` yalnız Z0 bağlantısını ve Z1 koordinatını gösterir. ⚠️ `web/` kararının gizlilik sözü bedeli **B3**'te.
- [x] **T0.6** **Ölçüm kaydı — dürüst not:** değişiklik **öncesi** tam koşu alınmadı. Yerine değişiklik **sonrası** koşu, kayıtlı tabanla karşılaştırıldı ve fark tam açıklandı:
  - Kayıtlı taban (plan): **954 passed**, 19 skipped, 1F+3E
  - Koşum sonrası: **980 passed**, 19 skipped, 1F+3E
  - Fark: **+26** = `tests/test_harita_z0.py`'deki 26 test. Başka hiçbir testin sonucu değişmedi.
  - `ruff check .` → *All checks passed*
  - `validate_registry()` → `ok=True, tool_count=56, namespace_count=15`
  - 1F+3E: `tests/test_path_guvenligi.py` — Linux'ta normal taban (`cmd` yok + normcase), **yeni bir kırık değil**.
- [x] **T0.7** Kaynak kullanım sözleşmesi: **Z0'da ağ çağrısı yok** → User-Agent/timeout konusu Z1'de uygulanır; karar: mevcut emsallere uyulur (`tools/olcum.py` `_git` `timeout=10`).

**Faz kapısı:** ✅ Yalnız `docs/` yazıldı (plan belgeleri). Uygulama kodu FAZ 1'de değişti.

---

## FAZ 1 — Z0: `harita_goster` (bağlantı üretir — HTTP yok, anahtar yok)

**Neden ilk:** sıfır maliyet, sıfır kota, sıfır taraf bağımlılığı; "şuraya nasıl
giderim" gerçekten çalışır.

- [x] **T1.1** Yeni modül `tools/harita.py` — yalnız stdlib (`json`, `urllib.parse`).
  - [x] **T1.1.1** `harita_goster(konum, mod="yol")`: `yol` → `/maps/dir/?api=1&destination=`; `ara` → `/maps/search/?api=1&query=`.
  - [x] **T1.1.2** `urllib.parse.quote(..., safe="")` — Türkçe karakter ve boşluk testli.
  - [x] **T1.1.3** Boş/whitespace/`None` konum → hata; bilinmeyen mod → hata; **hata yolunda `result` yok** (uydurma bağlantı yazılmaz).
  - [x] **T1.1.4** Dönüş `konum, mod, baglanti, kaynak` alanlarını taşır.
- [x] **T1.2** `tools/definitions.py` — `HARITA_GOSTER` şeması + `TOOLS` listesine eklendi; docstring sayısı 55→56.
- [x] **T1.3** `tools/__init__.py` → `calistir()` dalı: `if tool_name == "harita_goster":`; docstring "Elli üç tane" → "Elli altı tane" (bayattı).
- [x] **T1.4** `chat/agent_protocol.py`:
  - [x] **T1.4.1** `YETENEK_ALANLARI` → `"harita": ("harita_goster",)`.
  - [x] **T1.4.2** `ALAN_ACIKLAMALARI` → `"harita": "adres/yer icin harita baglantisi ve yol tarifi"`.
- [x] **T1.5** `chat/tools.py` → `DURUM_METNI["harita_goster"] = "Harita bağlantısı hazırlanıyor"`; `DURUM_ALANI`'na `"konum"` eklendi.
- [x] **T1.6** `tools/capabilities.py`: `ok=True`, `tool_count` 55→**56**, `namespace_count` 14→**15**, docstring güncellendi.
- [x] **T1.7** **Kilit güncellendi — ölçülen 22+3 satır** (A2 tablosu). Test fonksiyon adları da yeniden adlandırıldı (`test_56_arac_...`, `test_15_namespace_56_araci_...`). İlk tahmin (12) **yanlıştı**, ölçümle 22 çıktı.
- [x] **T1.8** Yeni test `tests/test_harita_z0.py` — **26 test**:
  - [x] İki modda URL biçimi + varsayılan mod.
  - [x] Türkçe kaçış (`Şişli/İstanbul` → yüzde kodlamalı).
  - [x] **Parametre kaçışı yapılamaz** (`&`/`=` kodlanır — `destination=` sayısı 1).
  - [x] Boş/`None`/aşırı uzun/güdüm dışı mod → hata; hata yolunda bağlantı yok.
  - [x] **Dört yer denetimi** + `ALAN_ACIKLAMALARI` eşleşmesi + `validate_registry`.
  - [x] **Ağ çağrısı yok** (statik: `requests`/`urllib.request`/`urlopen`/`socket`/`httpx`/`aiohttp` yok).
- [x] **T1.9** Belge güncellemeleri: `README.md` (4, 140, 200 — üstelik bayat "üç yeri" → **dört yeri**), `knowledge/kabul-plani-web-gate.md` (56 araç, 15 alan, 7×56=392), `docs/p2-canli-oncesi-12-risk.md`, `docs/p2-platform-ortak-mimari.md`.
- [x] **T1.10** **Canlı kanıt (gerçek dispatcher):**
  - `Tuzla, İstanbul` (yol) → `https://www.google.com/maps/dir/?api=1&destination=Tuzla%2C%20%C4%B0stanbul`
  - `Kadıköy Moda Sahili` (ara) → `https://www.google.com/maps/search/?api=1&query=Kad%C4%B1k%C3%B6y%20Moda%20Sahili`
  - Yüzey kontrolü: 56 araç, `harita_goster` yüzeyde **var**.
- [x] **T1.11** Commit (tek adım, Türkçe düz cümle).

**Faz kapısı:** ✅ Bölüm D'nin 7 kapısı da yeşil.

**Faz kapısı:** Bölüm D'nin 7 kapısı da yeşil.

---

## FAZ 2 — Z1: `konum_coz` (adres → koordinat)

**Neden:** `sirket_ara` bugün adres metni üretiyor ama **ölü metin** — haritada
gösterilemiyor.

- [x] **T2.1** `tools/harita.py` → `konum_coz(adres)`.
  - [x] **T2.1.1** Photon: `https://photon.komoot.io/api/?q=<adres>&limit=5` — **sapma:** `requests` değil, `urllib` + SSRF denetimli ortak hat kullanıldı; `requests` `_GuvenliYonlendirme` yönlendirme denetimini atlardı (yeni bağımlılık zaten yasak).
  - [x] **T2.1.2** **SSRF zorunlu:** `_guvenli_adres` + `_GuvenliYonlendirme` `tools/web_search.py`'den çağrılır; yeni savunma yazılmadı (testle kanıtlı).
  - [x] **T2.1.3** `timeout=10` + User-Agent (`Mozilla/5.0 … Basak/1.0`).
  - [x] **T2.1.4** Dönüş: `adres, enlem, boylam, gosterim_adi, kaynak ("photon"/"open-meteo"), aday_sayisi, adaylar`.
  - [x] **T2.1.5** Sonuç yoksa **hata döner**; hata yolunda `result` yok, koordinat **uydurulmaz**.
  - [x] **T2.1.6** Photon başarısızsa `/api/?q=` Open-Meteo geocoding hattı denenir (`tools/hava.py:_GEOCODING` çağrılır, `_git` kopyalanmaz — SSRF'li hattan geçer); `kaynak` hangi hat olduğunu söyler.
  - [x] **T2.1.7** ⚠️ **Canlı ölçüm bulgusu:** `lang=tr` Photon'da **HTTP 400** veriyor (yalnız de/en/fr/it kabul ediyor) ve tüm birincil hat sessizce yedeğe düşüyordu. `lang` parametresi kaldırıldı; test `lang=` gönderilmediğini kilitler.
- [x] **T2.2** Dört yer: şema (`KONUM_COZ`), dal (`calistir`), yetenek alanı (`"harita"`), durum etiketi (`"Konum koordinatı çözülüyor"` + `DURUM_ALANI`'na `adres`).
- [x] **T2.3** Kilit 56→**57**: 22 satır + 6 test fonksiyon adı + `test_seviye0_sozlesme.py:540` çarpım kilidi (`7×57=399`). **namespace 15 sabit kaldı** (yeni araç aynı `harita` alanında).
- [x] **T2.4** Test `tests/test_harita_z1.py` — **30 test**:
  - [x] Gerçek adres → koordinat **dünya aralığında** (−90..90 / −180..180).
  - [x] **GeoJSON sırası** (`coordinates=[boylam, enlem]`) ters yazılırsa yakalanır.
  - [x] Türkçe/adres sorgusu yüzde kodlamalı gider; `limit=5` var, geçersiz `lang` yok.
  - [x] Bulunamayan adres → hata, **koordinat yok**; aralık dışı koordinat (enlem 300) kabul edilmez; bozuk gövde çökmez; bulanık eşleşme gizlenmez.
  - [x] SSRF: loopback/özel ağ/8080 portu/`file://` **ağa çıkmadan** reddedilir (sahte `build_opener` patlar); korumanın `web_search`'ten çağrıldığı kaynak denetimiyle sabit.
  - [x] Fallback: Photon sahte-hatalıyken Open-Meteo denenir ve `kaynak="open-meteo"` döner.
- [x] **T2.5** Uçtan uca + canlı kanıt (aşağıda).
- [x] **T2.6** Commit (tek adım, Türkçe düz cümle).

### FAZ 2 canlı kanıt (2026-10-01, gerçek dispatcher, gerçek ağ)

| Girdi | Çıktı |
|---|---|
| `Kadıköy Moda Sahili, İstanbul` | `photon` · 40.981169 / 29.025471 · `Moda, Caferağa, Kadıköy, İstanbul, 34710, Türkiye` · 5 aday |
| `Tuzla, İstanbul` | `photon` · 40.816173 / 29.303419 · `Tuzla, İstanbul, Türkiye` · 5 aday |
| `Çiçek Pasajı, Beyoğlu` | `photon` · 41.0341 / 28.977921 · `Çiçek Pasajı, Hüseyinağa, Beyoğlu, İstanbul, 34435` · 2 aday |
| SSRF (canlı `_json_al`) | `127.0.0.1`, `192.168.1.10` → "ic/ağ adresine cozuldu"; `:8080` → "yalnizca standart web portlari"; `file://` → "Yalnizca http/https" |

**Ölçüm:** `tests/test_harita_z1.py` = **30 test**; geniş koşu **1010 geçti / 19 atlandı** (Z0 sonrası taban 980 → **+30**); `ruff check .` yeşil. Windows'a özel `tests/test_path_guvenligi.py` (1F+3E) taban çizgisiyle aynı, bu işten bağımsız.

**⚠️ Dürüst sınırlar (canlı ölçüldü, gizlenmiyor):**

1. **Photon bulanık eşleştirir.** `zzz bilinmeyen yer zzz` gibi saçma sorguya
   sıfır sonuç değil, en yakın adayı döndürdü (ölçüm: `BA20 9ZZ, Yeovil, England`).
   Araç bunu **gizlemez**: servisin kendi `gosterim_adi`'nı, `aday_sayisi`'nı ve
   `adaylar` listesini döndürür — uyuşmazlık modelin gözünde görünür kalır. Koda
   benzerlik eşiği/regex süzgeci **yazılmadı** (kelime kuralı olurdu).
2. **`sirket_ara` adres üretmiyordu** (aşağıdaki düzeltme turunda kapatıldı; ölçüm:
   3 markada `eksik` içinde `adres` vardı).

---

## FAZ 2.5 — GERÇEK KUSUR TURU (2026-10-01, Casper talebi)

"Diğer fazlara geçmeden ortaya çıkan gerçek kusurları düzelt, MVP yamasıyla
ilerlemeyelim." Bu bölüm, Z1 canlı ölçümünün çıkardığı kusurların kapanışıdır:
kök neden → düzeltme → kanıt.

### K1 — `sirket_ara` adresi HİÇ bulamıyordu (kök neden: yapısal veri yok sayılıyor)

- **Ölçüm:** `tutkuelit.com.tr/iletisim` ham HTML'i 185.099 karakter; adres YALNIZ
  JSON-LD `PostalAddress` içinde (`Musalla Bağları Mahallesi Sesigür Sokak No 30,
  Selçuklu, Konya, TR`), aynı blokta `vatID` ve `telephone` de var. Kart yalnız düz
  metne baktığı için `adres` ve `unvan` boş dönüyordu.
- **İkinci kusur (aynı kök):** `sayfa_oku` sayfa metnini **tek dev satıra** indiriyor;
  satır bazlı adres sezgisi gerçek çalışmada neredeyse hiç tetiklenemezdi. Testler
  bunu görmedi çünkü sahte `sayfa_oku` çok satırlı sahte metin döndürüyordu (test ↔
  gerçek boşluğu).
- **Düzeltme:** `tools/web_search.py` → `kurum_sayfasi_oku` (tek indirme; metin +
  schema.org `Organization/LocalBusiness` gerçekleri) + `_kurum_gercekleri` /
  `_adres_alani`. Ölçümden gelen satır: blok etiketleri satır sonu, satır içi
  etiketler boşluk → **satır yapısı korunur**. `urun_sayfasi_oku` ile **aynı korumalı
  indirme** (`_ham_sayfa_getir`) paylaşılır; yeni SSRF savunması yazılmadı.
- **`sirket_ara` sırası:** yapısal gerçekler önce, düz metin yedek. `vergi_no`
  `vatID`ten rakam süzülerek (10/11 hane kuralı korunur), `unvan` `legalName`den.
- **Kanıt (canlı, aynı marka):** `adresler = ["Musalla Bağları Mahallesi Sesigür
  Sokak No 30, Selçuklu, Konya, TR"]`, `unvan = "HALİL YILDIRIM GIDA … LTD. ŞTİ"`,
  `vergi_no = 4550047841`, `eksik = []` (öncesi: `eksik = ["adres"]`).

### K2 — Hata sebebi yutuluyordu (sessiz bozulma)

- **Ölçüm:** `lang=tr` Photon'da HTTP 400 üretiyordu; `_json_al` bunu "servise
  ulasilamadi" diye yutuyor, birincil hat bozuk olduğu halde **yedeğe düşüyor** ve
  kusur görünmüyordu.
- **Düzeltme:** `_json_al` artık `HTTP 400 Bad Request` gibi sebebi döndürür;
  `konum_coz` her çağrıda `denenen_hatlar` (hat, durum, aday sayısı / hata) döndürür;
  hiçbir hat sonuç bulamazsa hata mesajı denenen hatları yazar.
- **Kanıt:** `tests/test_harita_z1.py::TestDenenenHatlar` (HTTP 400 sebebi artık
  yutulmuyor) + canlı hata metni: `Denenen hatlar: photon: 0 aday; open-meteo: 0 aday`.

### K3 — Aynı sayfa iki kez indiriliyordu

- Eski akış adayları okuduktan sonra **en iyi adayı ikinci kez** indiriyordu
  (N+1 istek). Artık her aday bir kez okunur; metin ve gerçekler aynı okumadan gelir.
- **Kanıt:** `TestSirketAra::test_bilinen_markada_iletisim_bulunur` → `len(cagrilar) ==
  len(set(cagrilar))` + `TestSirketAraUctanUca`.

### K4 — Skoru 0 olan sayfa "okunamadı" sayılıyordu

- Anahtar kelime geçmeyen ama gerçekten okunan iletişim sayfası için
  `"iletişim sayfası okunamadı"` dönüyordu. Artık **ilk okunabilen aday tabandır**.
- **Kanıt:** `test_skor_sifir_olsa_da_sayfa_okunmus_sayilir`.

### K5 — Adres sezgisi etiket ve kopya satır kabul ediyordu

- **Ölçüm:** canlı çıktıda `adresler` içinde `"Adres"` (menü/başlık satırı) ve aynı
  adresin iki yazımı vardı.
- **Düzeltme (kelime kuralı değil, biçim kuralı):** adres satırı ≥10 karakter olmalı ve
  **rakam** taşımalı (kapı/cadde numarası); aynı adresin iki kaynaktan yazımı ilk 25
  harf/rakam anahtarıyla tek satıra iner.
- **Kanıt:** `test_baslik_satiri_adres_sayilmaz`, `test_rakamsiz_adres_satiri_kabul_edilmez`,
  `test_ayni_adres_iki_kaynaktan_tek_satira_iner`, `test_farkli_adresler_birlesmez`.

### K6 — Ölü kod

- `en_iyi, en_skor, en_site = adres if False else aday, skor, aday` satırı (her zaman
  `aday` seçen, `adres` adını boş yere anan kod) K3 refactor'üyle kalktı.

### Ölçülen kapasite sınırı — açık veri kapı numarasını bilmiyor

| Sorgu biçimi | Photon | Nominatim |
|---|---|---|
| `Musalla Bağları Mahallesi Sesigür Sokak No 30, Selçuklu, Konya, TR` | **0 aday** | **0 aday** |
| `Sesigür Sokak No 30, Konya` | 1 yanlış ülke adayı (Konya Sokak 30, Lefkoşa) | 0 aday |
| `Musalla Bağları, Selçuklu, Konya` | **doğru** · 37.890234 / 32.498691 · `Musalla Bağları, Selçuklu/Konya, 42110, Türkiye` | ölçülmedi (aynı sokak sorgusunda 0) |

**Karar:** sağlayıcı değiştirilmedi — Nominatim de aynı adreste 0 döndürdü, yani kusur
Photon'a özel değil, **açık harita verisinin kapı-numarası kapsamı**. Sorguyu kodla
"kısaltma" (kelime atma) yazılmadı: model zaten `konum_coz`'u daha basit bir yer adıyla
çağırabilir ve sınır artık aracın açıklamasında + `denenen_hatlar` çıktısında yazıyor.

### Gözlem (düzeltilmedi, kapsam dışı)

`web_search.sayfa_oku` metni tek satıra indiriyor. Bu iş `sirket_ara` yolu için
düzeltildi (`kurum_sayfasi_oku`); `sayfa_oku`nun model-görünür biçimini değiştirmek
test kilitlerini ve diğer tüketicileri etkileyeceği için **bilinçli olarak** dokunulmadı.

**FAZ 2.5 kanıt:** `tests/test_sirket_karti_yapisal.py` = **27 test**; `tests/test_harita_z1.py`
30 → **39 test**; geniş koşu **1046 geçti / 19 atlandı** (FAZ 2 tabanı 1010 → **+36**);
`ruff check .` yeşil.

**Faz kapısı:** Bölüm D; ayrıca "uydurma koordinat yok" testi yeşil.

---

## FAZ 3 — Z2: Haritada gösterme (**yüzey: `web/`** — D4 onaylı)

- [ ] **T3.0** ⚠️ **B3 seçimi yapılmadan bu faz başlamaz:** A (karo + söz değişir), B (karo yok, yalnız bağlantı — öneri), C (tıklayınca karo).
- [ ] **T3.0b** Seçim **A** ya da **C** ise: `docs/KVKK-ENVANTER.md` + `web/bilgilendirme.html` **aynı commit'te** güncellenir ve `tests/test_web_gizlilik_beyani.py` sözüne göre revize edilir. **Testi kandıracak dolaylı yük yolu kullanılmaz.**
- [ ] **T3.1** `web/` yüzeyi: bağlantı düğmesi (Z0) + koordinat gösterimi (Z1); seçim A/C ise harita katmanı eklenir.
- [ ] **T3.2** Seçim A/C ise: **OpenFreeMap** (anahtarsız) + Leaflet veya MapLibre; markör `konum_coz` çıktısına konur.
- [ ] **T3.3** **Atıf zorunlu:** `© OpenStreetMap katkıda bulunanlar` görünür ve okunur.
- [ ] **T3.4** ⚠️ `web/` tarafı olduğu için: `web/chat.css` `?v=` **yükseltilir** ve kilitli test satırları güncellenir (`tests/test_vercel_stream.py` — şu an `?v=11` kilitli).
- [ ] **T3.4b** Yeni CSS/JS için `?v=` sürümlemesi `web/index.html` içinde tutarlı yapılır (`?v=` düzeni mevcut desene uyar).
- [ ] **T3.5** Test: harita görünümünün varlığı + atıf metni + `?v=` kilidi.
- [ ] **T3.6** **Canlı kanıt:** uygulama gerçekten çalıştırılır, **ekran görüntüsü** alınır; konsolda tile/ağ hatası yok; harita yüklenmeden beyaz ekran kalmıyor.
- [ ] **T3.7** Commit.

**Faz kapısı:** Bölüm D + görsel kanıt (pytest UI davranışını görmez).

---

## FAZ 4 — Z3: `poi_ara` (işletme/POI — Overpass)

> ### ⚠️ Bu fazın en kritik tasarım kuralı
> **Kodda kategori→OSM etiketi sözlüğü YAZILMAZ.** "kafe → amenity=cafe" gibi
> bir harita, modelin yerine karar veren koddur ve AGENTS.md §0 yasağıdır.
> **Etiketi model verir** (`amenity=cafe`, `shop=butcher`…). Kod yalnız
> parametreyi **biçim olarak doğrular** (güvenli karakter kümesi, `anahtar=değer`).

- [ ] **T4.1** `tools/harita.py` → `poi_ara(etiket, yer=None, enlem=None, boylam=None, yaricap_m=1500)`.
  - [ ] **T4.1.1** `etiket` biçim doğrulaması: `^[a-z_]+=[a-z_]+$` benzeri güvenli küme. Uymayan girdi → anlamlı hata.
  - [ ] **T4.1.2** Merkez: `yer` verilirse `konum_coz` ile çözülür; yoksa enlem/boylam alınır.
  - [ ] **T4.1.3** Yarıçaptan **bbox** üretimi (kod yapar — saf matematik).
  - [ ] **T4.1.4** Overpass sorgusu (`[out:json]`, `out center`), `timeout`, `User-Agent`.
  - [ ] **T4.1.5** Sonuç ayrıştırma: ad, koordinat, OSM tip/id, seçili etiketler. **Sonuç tavanı** (mevcut emsaller: `tools/olcum.py` `_MAX_ICERIK_ESLESME=8`).
  - [ ] **T4.1.6** Çıktıda **zorunlu atıf** alanı: `© OpenStreetMap katkıda bulunanlar`.
  - [ ] **T4.1.7** Sonuç yoksa "bu bölgede bulunamadı" — **eksik veriyi tam saymak yasak**.
- [ ] **T4.2** Dört yer (`harita` alanına eklenir).
- [ ] **T4.3** 55→**58** kilit güncellemesi.
- [ ] **T4.4** Test `tests/test_harita_z3.py`: etiket doğrulama, bbox matematiği (bilinen girdi → bilinen bbox), boş sonuç yolu, atıf varlığı, SSRF.
- [ ] **T4.5** **Bağımsız doğrulama:** dönen sayı ikinci bir sorguyla teyit edilir (kabul kapısı). Fark varsa kayda geçer.
- [ ] **T4.6** Belgeye **OSM kapsama sınırı** notu: TR POI verisi Google'ın altında; eksik sonuç beklenen davranıştır.
- [ ] **T4.7** Commit.

**Faz kapısı:** Bölüm D + bağımsız doğrulama kanıtı.

---

## FAZ 5 — Z4a: `mesafe_hesapla` (anahtarsız, ağsız)

- [ ] **T5.1** `tools/harita.py` → `mesafe_hesapla(enlem1, boylam1, enlem2, boylam2)` — haversine, `math` (stdlib), **ağ çağrısı yok**.
- [ ] **T5.2** Dönüş adı ve metni **"düz mesafe"** olarak sabitlenir — "yol mesafesi" diye sunulmaz. (Yanlış adlandırma = yalan.)
- [ ] **T5.3** Dört yer. 55→**59** kilit güncellemesi.
- [ ] **T5.4** Test: bilinen iki nokta arası bilinen mesafe **±%1**; aynı nokta → 0; kutup/antimeridyen uçları çökmez.
- [ ] **T5.5** Commit.

---

## FAZ 6 — Z4b: `rota_hesapla` (D2 kararına bağlı — ücretsiz, kartsız anahtar)

- [ ] **T6.1** Anahtar `ayarlar.json`'a `openrouteservice` alanı olarak eklenir; **commit'e girmez** (pre-commit hook doğrular).
- [ ] **T6.2** Anahtar yoksa: **anlamlı hata** ("rota için anahtar tanımlı değil") + zincir `mesafe_hesapla`ya düşer. Sessiz çökme yok.
- [ ] **T6.3** `POST /v2/directions/driving-car` — JSON gövde; SSRF + `timeout` + `User-Agent`.
- [ ] **T6.4** Dönüş: yol mesafesi (m/km), süre, adım özeti (ilk N), kaynak.
- [ ] **T6.5** **Kota ret yolu:** 429/403 gelirse **Türkçe, anlamlı ret** döner ve sohbet bozulmaz (mevcut kota retleriyle aynı üslup).
- [ ] **T6.6** Dört yer. 55→**60** kilit güncellemesi.
- [ ] **T6.7** Test: anahtarsız hata yolu, kota ret yolu (sahte yanıt), başarı yolu (sahte yanıt), SSRF.
- [ ] **T6.8** **Canlı kanıt:** iki gerçek adres → gerçek yol mesafesi/süresi; `mesafe_hesapla` ile karşılaştırılır (yol mesafesi > düz mesafe olmalı — mantık kapısı).
- [ ] **T6.9** Commit.

---

## FAZ 7 — Z5: Bölge analizi + kalıcı saklama (D3 kararına bağlı)

- [ ] **T7.1** D3 sonucu uygulanır. **"Yazma yok" seçildiyse bu faz iptal edilir.**
- [ ] **T7.2** Z3 sonucu **`.md` dosyasına** yazılır ve mevcut indeksleyici onu `semantic` anıya çevirir → aynı bölge sorusu ikinci kez **ağ çağrısı yapmadan** yanıtlanır.
  - [ ] **T7.2.1** Casper oturumu → `knowledge/harita/<bölge>.md`
  - [ ] **T7.2.2** Diğer kullanıcı → `data/<uid>/knowledge/harita/<bölge>.md` (**gitignore'da**, commit'e girmez)
  - [ ] **T7.2.3** Uzantı **`.md`** olmalı — `indeksle_klasor` yalnız `.md` okur (`memory/engine.py:519`). `.json` yazılırsa **indekslenmez ve Başak bulamaz.**
- [ ] **T7.3** ⚠️ `memory/engine.py` **değiştirilmez**; yazma **mevcut API** ile yapılır. ⚠️ **`episodik_kaydet` KULLANILMAZ** — `EPISODIC_LIMIT=5000` budaması analizi sessizce siler (B2).
- [ ] **T7.4** Dosya başlığında **zorunlu atıf**: `© OpenStreetMap katkıda bulunanlar` (ODbL, kayıtta da kalır).
- [ ] **T7.4b** ⚠️ Web kullanıcılarının analizi `knowledge/` altına **yazılmaz** — o yol yalnız `casper` oturumunda indekslenir ve commit'e girebilir.
- [ ] **T7.5** Test: yazma→okuma turu; atıf kayıtta; ağ çağrısı sayısı ikinci turda **0** (sahte istemci sayacıyla).
- [ ] **T7.6** Kanıt: aynı soru iki kez → ikincisi ağsız ve aynı sayı.
- [ ] **T7.7** Commit.

---

# BÖLÜM D — HER COMMIT'TE KOŞULACAK KAPILAR

| # | Kapı | Komut / yöntem | Kabul |
|---|---|---|---|
| 1 | Test paketi | `python3 -m pytest tests -q` | Taban düşmedi (954 yeşil, 19 skipped, Linux'ta 1F+3E normal) |
| 2 | Lint | `ruff check .` | Yeşil |
| 3 | Kayıt defteri | `validate_registry()` | `ok=True`; `missing`/`unknown`/`duplicates` boş |
| 4 | Dört yer | Test içinde denetlenir | Şema + dal + yetenek alanı + durum etiketi |
| 5 | SSRF | Test içinde denetlenir | Engelli adres reddedilir, ağa çıkılmaz |
| 6 | Bağımlılık | `git diff --stat requirements.txt` | **Değişiklik yok** |
| 7 | Sır | pre-commit hook | `ayarlar.json` commit'e girmemiş |

**Kapı kırmızıysa commit atılmaz.** `--no-verify` kullanılmaz (AGENTS.md §6).

---

# BÖLÜM E — KABUL ÖLÇÜSÜ (projenin tamamı)

| # | Kapı | Kabul |
|---|---|---|
| 1 | Maliyet | Zincir boyunca **0 lira**, kart girişi **0** |
| 2 | Sesli navigasyon iddiası | **Yok** — kapsam dışı olduğu yazılı |
| 3 | Uydurma yok | Bulunamayan konum/POI → "bulunamadı"; uydurma koordinat/sayı üretilmez |
| 4 | Ad doğruluğu | Düz mesafe "yol mesafesi" diye sunulmaz |
| 5 | Atıf | OSM verisi döndüren her çıktıda atıf var |
| 6 | Kanıt | Her faz **gerçek** çalıştırmayla kanıtlanır — simülasyon kabul edilmez |
| 7 | Karışmama | Vixrex deposunda **0 satır** değişiklik |

---

# BÖLÜM F — YASAKLAR (bu planda yapılmaz)

- Yeni pip paketi; `requirements.txt` değişikliği.
- Kart/faturalandırma isteyen hizmet.
- Kodda kategori/kelime → etiket/araç eşlemesi (AGENTS.md §0).
- Araç açıklamasına davranış koçluğu, prompt'a görev dayatması.
- Model çıktısına dokunan kod (temizleme, ek satır, emoji, tavan).
- SSRF savunmasını yeniden yazmak.
- Hizmet politikası gerekçesiyle araç turu sınırı / turda araç kapatma.
- Atıfsız OSM verisi kullanmak veya saklamak.
- Simüle kabul (sahte araç çıktısı, elle yazılmış "çalıştı" raporu).
- Vixrex deposuna erişim/dosya yazımı.

---

# BÖLÜM G — RİSKLER ve TETİKTE PLAN

| Risk | Etki | Tetikte plan |
|---|---|---|
| OSM/Nominatim politikası sıkılaşır veya hizmet kapanır | Z3/Z1 durur | Photon ↔ Nominatim ↔ Open-Meteo arasında **mevcut** fallback; hiçbiri yoksa araç "hizmet yok" der |
| Overpass genel sunucu yoğun/yavaş | Z3 gecikir | `timeout` + anlamlı hata; kendi sunucu kurma **kapsam dışı** |
| Photon sonuç kalitesi TR'de düşük | Y1 hatalı koordinat | Aday listesi + gösterim adı kullanıcıya döner; tek adaya zorlanmaz |
| TR POI kapsaması eksik | Analiz eksik çıkar | Raporda **kapsama uyarısı**; eksik sonuç tam sayılmaz |
| 55 kilidi güncellenmeden commit | Test kırmızı | T1.7/Bölüm D kapı 1 |
| `web/` `?v=` kilidi unutulur | Önbellek + test kırmızı | T3.4 |
| ORS kotası dolar (2.000/gün) | Z4b durur | `mesafe_hesapla`ya düşer; ücret **doğmaz** |
| Kapsam büyür ("madem harita var, navigasyon da olsun") | Maliyet doğar | Bu belge + Casper kararı olmadan yapılmaz |

---

# BÖLÜM H — KAYNAKÇA

| Konu | Kaynak |
|---|---|
| Maps URLs anahtarsız | developers.google.com/maps/documentation/urls/get-started |
| Places saklama/saklama yasağı, `place_id` istisnası | developers.google.com/maps/documentation/places/web-service/policies |
| Google Maps ToS — "No Creating Content" | cloud.google.com/maps-platform/terms (Maps Service Specific Terms) |
| SKU başına ücretsiz kota (10K/5K/1K) | mapsplatform.google.com/pricing + developers.google.com/maps/billing-and-pricing/pricing |
| Navigation SDK — Enterprise, hedef başına ücret | developers.google.com/maps/documentation/navigation/android-sdk/pricing |
| Navigation SDK Flutter eklentisi (Vixrex için) | github.com/googlemaps/flutter-navigation-sdk + developers.google.com/maps/documentation/cross-platform/navigation |
| OpenFreeMap — anahtarsız, limitsiz | openfreemap.org |
| Photon — kategori filtresi, `bbox`, search-as-you-type | github.com/komoot/photon (docs/api-v1.md) |
| Nominatim kullanım politikası — 1 istek/sn | operations.osmfoundation.org/policies/nominatim |
| OpenRouteService ücretsiz plan (~2.000/gün) | openrouteservice.org + ask.openrouteservice.org/t/5806 |
| OSRM demo sunucu "üretim için değil" | project-osrm.org + community.openstreetmap.org |
