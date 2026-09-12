# ARAŞTIRMA — HEDEF-DIŞI MUHAKEME ORGANLARININ SÖKÜLMESİ

Tarih: 2026-09-12
Durum: KANITLANDI — KOD DENEYİNE İZİN
Risk sınıfı: Orta (7 test dosyası + 4 modül silinir; canlı yol etkilenmez — kanıtı aşağıda)

## 1. Hedef

"Kendi muhakeme algoritması" programının (DENEY/FAY/DÜNYA/EVRİM + Ö-2/Ö-3 bayat/karne) ölü parçalarını sök; hedefe ("modeli geliştirme, modelleri kullan") aykırı kodu ve her prompta enjekte edilen ölü "İnançlar" gürültüsünü kaldır:
1. SİL (modül): `tools/deney.py`, `tools/fay.py`, `tools/evrim.py`, `tools/dunya.py`.
2. SİL (test): `test_deney.py`, `test_fay0.py`, `test_fay1_juri.py`, `test_evrim.py`, `test_e2e_beyin.py`, `test_dunya.py` (konuları kalkan organlar + onlara bağımlı entegrasyon).
3. `_model_baglami` içindeki `dunya_ozet(DEFTER_DIR)` bloğunu kaldır (defter yokken kalıcı "Dünya modeli boş" gürültüsü üretir); ardından boşa düşen `DEFTER_DIR` sabitini ve `chat/__init__` aktarımını kaldır.
4. `test_faz3b.py::test_inanc_ozeti_tavanli` güncellenir (gerekçe §11 kaydıyla): defter yokken İnançlar bölümü enjekte edilmediğini doğrular.
5. KAPSAM DÜZELTMESİ (uygulama sırasında): `tools/bayat.py` KALIR — `tools/aktarici.py:17` (`from tools import bayat`, FAZ-3b onaylı zamanlayıcı yolu) ona bağlı çıktı. `test_o2.py`/`test_o3.py` de korunur. Bayat/karne ayrıştırması ayrı paket konusudur.

## 2. Kabul kriteri

- `pytest tests -q`: kalan paket yeşil; fark yalnız silinen 6 dosyanın test sayısı + güncellenen 1 test; sıfır YENİ hata.
- `py_compile` temiz; `tools.(deney|fay|evrim|dunya)` canlı referansı sıfır (`tools.bayat` aktarici yoluyla canlıdır — kapsam dışı).
- Kapsam notu (uygulama sırasında eklendi): `test_dunya.py`, `tools.bayat`'a (`_KARNE_DOSYASI`) göbekten bağlı çıktı; `tools/dunya.py`'nin tek canlı çağrısı da bu pakette kalkıyor. Bağımsız `test_dunya` yaşatılamazdı — modül + test birlikte silinir (§11: öncülü kalkan test).

## 3. Mevcut durum kanıtı

- 4 modülün (deney/fay/evrim/dunya) canlı importçusu YOK (repo geneli grep — yalnız yukarıdaki test dosyaları; `tools/__init__` dinamik yükleyicisi `execute`/`FUNCTION_NAME` arar, bu modüllerde yoktur).
- `tools/deney.py`'deki `deney_yurut` legacy `deney_kos` tarafından KULLANILMAZ (legacy:844-854 doğrudan tool döngüsünü koşturur).
- `dunya_ozet` tek canlı çağrısı `_model_baglami` (`_chat_legacy.py:924`); defter yokken `inanclari_topla` boş döner → kalıcı `"Dünya modeli boş (defterde kayıt yok.)"` dizesi HER prompta eklenir (gürültü kanıtı: kod yolu okundu).
- `defter/` dizini `a359d8b` ("defter kaldirildi") ile zaten silinmiş — inanç özetinin veri kaynağı onaylı şekilde kalkmıştır; çağrının öncülü boşa düşmüştür.
- `gerilim`/`is_kuyrugu`/`aktarici`/`zamanlayici`/`olcum` bu pakette KALIR: zamanlayıcı günlük kartına (`_gunluk_ekler`) ve executor tool'larına (`is_ac/is_liste/is_onayla`) bağlı, onaylı özelliktir (E-3/FAZ-3b).

## 4. Sorun kanıtı

- Hedef (Casper 2026-09-12 §1.1): model zekâsı geliştirilmez. 4 modül bu programın parçasıdır; hiçbiri canlı yolda değildir.
- Her prompta ~50 karakter ölü "İnançlar" bloğu girer — bağlam diyeti ve doğal akış hedefiyle çelişir.

## 5. Dış referans

P2/P3 araştırma dosyaları (resmi tool-calling akışında model-dışı muhakeme organı yoktur).

## 6. Doğrulanan gerçekler

- Tüm import grep'leri + `_model_baglami`/`_gunluk_ekler` kod okumaları bu dalda yapıldı.
- `test_fay2_gerilim.py` (gerilim) ve `test_faz3b.py`nin is_kuyrugu/juri testleri bu paketten ETKİLENMEZ (modülleri kalır).

## 7. DOĞRULANAMADI

Yok.

## 8. İzin verilen kapsam

Yukarıdaki 4 madde. `test_faz3b.py` değişikliği TEK testle sınırlıdır.

## 9. Yasak kapsam

- `tools/gerilim.py`, `tools/is_kuyrugu.py`, `tools/aktarici.py`, `tools/zamanlayici.py`, `tools/olcum.py`, executor TOOL_MAP, definitions, permissions — dokunulmaz.
- Secici B1 karne (`brain/stats` tabanlı) — ayrı paket konusu, dokunulmaz.
- `deftere_kaydet` tool'u — kullanıcı kararı gerekir, dokunulmaz.

## 10. Korunacak davranışlar

- Orkestra akışı, tool döngüsü, zamanlayıcı kartı, jüri-kapalı kota koruması (`test_juri_kapaliyken_kota_yemez`).

## 11. Test-değişiklik gerekçesi (§11 kaydı)

`test_inanc_ozeti_tavanli`, inanç özetinin EKLENMESİNİ pinler. Öncülü (`defter/` + onaylı silme `a359d8b`) kalkmış, çağrı kalıcı gürültü üretir hale gelmiştir. Test, yeni doğru davranışı (enjekte edilmeme) pinleyecek şekilde güncellenir; tavan iddiası anlamsızlaştığı için düşer. Diğer 6 dosya silinir (konuları kalkan modüller + bayat-bağımlı `test_dunya`; kept-behavior kapsamı daralmaz — gerilim/is_kuyrugu/bayat kapsamı kendi testlerinde durur).

## 12. Kabul sensörleri

`pytest tests -q` (baseline karşılaştırmalı), `py_compile`, canlı-referans grep'i.

## 13. Geri alma koşulu

Kalan testlerden biri kızarırsa veya zamanlayıcı/executor yolu bozulursa paket geri alınır.

## 14. Sonuç (2026-09-12 uygulandı)

- Silinen: `tools/{deney,fay,evrim,dunya}.py` + `test_{deney,fay0,fay1_juri,evrim,e2e_beyin,dunya}.py`; `tools/bayat.py` + `test_o2/o3` KORUNDU (aktarici bağımlılığı).
- `_model_baglami` inanç gürültüsü kalktı; `DEFTER_DIR` + aktarımı kalktı; `test_faz3b` inanç testi yeni davranışı pinler.
- Yan bulgu + düzeltme (2): suite-içi flake mekanizması çözüldü — global `_COOLDOWN` kirliliği + `secici` karıştırma-pinlemesi. `test_router` iki testi `tercih` ile deterministikleşti, `TestBrainRouterV2` + `test_yapi_threading` fixture'ına `_COOLDOWN` izolasyonu eklendi (assertion değişikliği YOK).
- Sensörler: `pytest tests -q` = **562 geçti / 0 hata / 7 skip, iki tur üst üste**. (Başlangıç: 545+3 flake; flake'ler de kapandı.)
- KANITLANDI → paket tamamlandı.
