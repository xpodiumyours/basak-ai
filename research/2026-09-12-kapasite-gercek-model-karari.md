# ARAŞTIRMA — KAPASİTE KARARI GERÇEK MODELE BAĞLANIYOR

Tarih: 2026-09-12
Durum: KANITLANDI — KOD DENEYİNE İZİN
Risk sınıfı: Orta (tool kısa listesi + embedding + tur tavanı etkilenir; mevcut testler kilit)

## 1. Hedef

`brain/kapasite.py` "havuzda güçlü sağlayıcı varsa tur güçlüdür" kuralını bırakır:
1. Yeni `aile` parametresi (P3'ün `model_family.coz` çıktısı) kararı verir.
2. `model_adi` aile çözücüyle sınıflanır (alt-dizgi tuzakları kapanır: `17b`→küçük hatası).
3. Provider setleri düzelir: `cloudflare` güçlüden çıkar (varsayılan 3B sınıfı), `openrouter` iki setten de çıkar (dinamik :free).
4. `chat/flow.py` seciciyle ucuz ön-seçim yapıp ilk adayın ailesini `mod_kapasite(aile=...)` olarak verir (secici saf + ağsızdır; brain cevabındaki gerçek seçimle birebir aynı olma garantisi YOKTUR — yaklaşıktır, belgelenir).

## 2. Kabul kriteri

- `tests/test_kapasite_kapi.py` DEĞİŞMEDEN yeşil (kilitli beklentiler korunur).
- Yeni `tests/test_kapasite_aile.py` yeşil (aile geçersiz kılar; 17b tuzağı; cloudflare-havuzu hafifler).
- `pytest tests -q` baseline ile aynı; `py_compile` temiz.

## 3. Mevcut durum kanıtı

- `brain/kapasite.py:26-29`: `GUCLU_KAYNAK` içinde `cloudflare/openrouter`; `KUCUK_KAYNAK` içinde `nvidia` (120B+ barındırır).
- `brain/kapasite.py:33-34`: `KUCUK_MODEL` alt-dizgi listesi (`"7b"` → `llama-4-scout-17b` küçük sayılır — YANLIŞ).
- `brain/kapasite.py:85-88`: havuzda tek güçlü sağlayıcı tüm turu güçlü saydırır.
- Çağrı noktaları: `chat/flow.py:121` (embedding + CORE/SMALL seçimi), `chat/tools.py:249` (tur tavanı), `_chat_legacy.py:451` (ölü yol).
- Harness araştırması "Kritik mevcut kusur" bölümü havuz-kararını kod kanıtıyla yanlışlar (`research/2026-09-12-model-gorev-harness-mimarisi.md`).
- Kilitli testler (`tests/test_kapasite_kapi.py`): havuz `[groq,ollama]`→güçlü, `[ollama]`→küçük, `qwen2.5:3b`→küçük, `llama-3.3-70b`→güçlü, `nvidia`→küçük, `groq`→güçlü, boş→güçlü, gate_modu geçersiz kılar.

## 4. Sorun kanıtı

- Fiilen Cloudflare-3B'nin cevaplayacağı tur, havuzda GLM/Groq var diye ağır şekillenir (9 araç + embedding) — ANA-PLAN §3 "modeli boğma" yasağına aykırı.
- Groq dokümanı küçük modele 3-5 araç önerir; OpenAI az fonksiyon önerir (P3 araştırma dosyası §5).

## 5. Dış referans

P3 araştırma dosyası §5 ile aynı (Groq/OpenAI tool-küçüklüğü ilkeleri).

## 6. Doğrulanan gerçekler

- `secici.sec` saf/senkron/ağsızdır (`brain/secici.py` — import + random dışında I/O yok).
- `brain._bulut_zinciri()` `(ad, istemci)` döner; tüm istemciler `.model` taşır (P3 grep kanıtı).
- Audit formatını test eden test yok.

## 7. DOĞRULANAMADI

- Secici ön-seçimi ile brain içi gerçek seçim her zaman aynı aileyi vermez (cooldown/karne/genel-karıştırma farkı) — bu yüzden aile YAKLAŞIK şekillendirmedir; yanlış ailede bile davranış güvenlidir (hafif şekil güçlü modeli bozmaz, testle korunur).

## 8. İzin verilen kapsam

- `brain/kapasite.py`: `aile` parametresi + set düzeltmeleri + havuz-kuralı değişimi (tekdüze-küçük havuz → küçük; diğer → varsayılan).
- `chat/flow.py`: aile ön-seçimi + `mod_kapasite(aile=...)` (try/except korumalı; hata → eski yol).
- YENİ `tests/test_kapasite_aile.py`.
- Varsayılan (belirsiz → güçlü) DEĞİŞMEZ (flip için ayrı ölçüm gerekir — gelecek hipotez olarak kaydedildi).

## 9. Yasak kapsam

- `test_kapasite_kapi.py` beklentileri değiştirilemez (§11).
- Tool setleri, prompt blokları, secici kuralları, embedding motoru — dokunulmaz.
- HarnessSpec entegrasyonu — harness dalının işi.

## 10. Korunacak davranışlar

- Yukarıdaki 8 kilitli beklenti birebir korunur.
- `TOOL_YONLENDIRME` her modelde promptta kalır (`test_kucuk_modelde_tool_yonlendirme_korunur`).

## 11. Risk sınıfı

Orta. Sensörler: kilitli kapasite testleri + yeni aile testleri + tam paket.

## 12. Kabul sensörleri

`pytest tests -q`, `py_compile`, aile ön-seçim try/except (hata loglanır, akış ölmez).

## 13. Geri alma koşulu

Kilitli testlerden biri kızarırsa veya tool kısa listesi beklenen setten saparsa paket geri alınır.

## 14. Sonuç (2026-09-12 uygulandı)

- `brain/kapasite.py`: `aile` parametresi + set düzeltmeleri + havuz-kuralı (tekdüze-küçük → küçük, diğer → varsayılan); `model_adi` aile çözücüyle sınıflanır; varsayılan (belirsiz → güçlü) korundu.
- `chat/flow.py`: secici ön-seçimiyle ilk adayın ailesi `mod_kapasite(aile=...)` olarak verilir (try/except korumalı).
- Sensörler: kilitli `test_kapasite_kapi.py` DEĞİŞMEDEN yeşil (10/10); yeni `test_kapasite_aile.py` 11/11; tam paket 603 geçti / 3 flake / 7 skip. Gerileme yok.
- KANITLANDI → paket tamamlandı.
