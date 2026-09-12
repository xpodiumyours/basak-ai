# ARAŞTIRMA — ADAPTÖR STANDARDI: MODEL AİLESİ + 403/429 AYRIMI

Tarih: 2026-09-12
Durum: KANITLANDI — KOD DENEYİNE İZİN
Risk sınıfı: Orta (provider routing + fallback zinciri etkilenir; davranış değişikliği küçük ve observed)

## 1. Hedef

Tek zincirin "ücretsiz ve kesintisiz" çalışması için iki eksik kapatılacak:
1. **Model ailesi kimliği:** harness araştırmasının kritik bulgusu — provider adı model ailesi değildir (`research/2026-09-12-model-gorev-harness-mimarisi.md` §"Kritik mevcut kusur"). Yeni saf modül `brain/model_family.py`: `(provider, model_id) → family`. Davranış değiştirmez; P4 (kapasite) ve harness dalı tüketir, audit satırına teşhis bilgisi olarak girer.
2. **403/429 ayrımı:** `brain.py` bugün 429 ve timeout'u cooldown'a sokar; 403/401 (Cloudflare paid-model, geçersiz anahtar, yetkisiz) her turda yeniden denenir — ölü sağlayıcıya her tur 1 çağrı + gecikme. 403 uzun cooldown (1 saat) alır; anahtar/model değişince temizlenir.

## 2. Kabul kriteri

- Yeni `tests/test_model_family.py` yeşil (aile tablosu + unknown-güvenliği: tanımsız model `unknown` döner, asla yükseltmez).
- Yeni `tests/test_erisim_engeli.py` yeşil (sahte 403 → sıradaki devralır; aynı tur içinde değil SONRAKİ turda ölü atlanır; `anahtar_ayarla`/`groq_model_ayarla` cooldown'u temizler).
- `pytest tests -q` baseline ile aynı (545/3-flake/7-skip; gerileme yok).
- Audit OK/HATA satırlarında `aile=` görülür; format öneki (`OK kaynak=`, `HATA kaynak=`) değişmez.

## 3. Mevcut durum kanıtı

- `brain/brain.py:83-98`: `_rate_limit_mi` + `_zaman_asimi_mi` var; 403 eşleşmesi YOK.
- `brain/brain.py:332-343` ve `:436-440`: iki except bloğunda da 403 dalı yok.
- `brain/brain.py:184-209`: `anahtar_ayarla`/`groq_model_ayarla` cooldown'a dokunmaz.
- İstemcilerin gerçek model kimlikleri: groq `openai/gpt-oss-20b|120b` (`brain/groq.py` MODELLER); glm `glm-4.5-flash` (`brain/glm.py`); cloudflare `@cf/meta/llama-3.2-3b-instruct`, `@cf/meta/llama-4-scout-17b-16e-instruct` (`brain/cloudflare.py` MODELLER); kilo `kilo-auto/free` (`brain/kilo.py:36`); openrouter çalışma anında `:free` seçer (`brain/openrouter.py:77-101`); nvidia hesap-açık listeden dener (`brain/nvidia.py:97-98,180-192`).
- Audit formatını test eden test YOK (tests/ içinde `audit` eşleşmesi sıfır — 2026-09-12 grep).

## 4. Sorun kanıtı

- Cloudflare dokümanı: bazı modeller Free planda 403 döner, paid ister (`developers.cloudflare.com/changelog/product/workers-ai` — 403 + `5035`). Başak bu 403'ü her turda yeniden dener.
- Qwen 403 tarihte zinciri kilitlemişti (`data/kota-gercek.md`: "403 Access denied"); o günkü çözüm bayrakla dışlamak oldu (`_QWEN_BEKLEMEDE`). Genel 403 kuralı yok — aynı sınıf hata tekrarlar.
- Harness araştırması kapasite kararının provider havuzundan değil gerçek modelden verilmesi gerektiğini kanıtladı; aile çözücü bunun önkoşuludur.

## 5. Dış referans

- Groq rate-limits: 429 + `retry-after`/`x-ratelimit-*` header'ları; RPD header'da YOK, istemci sayar (`console.groq.com/docs/rate-limits`).
- Kilo gateway: anon-free 200 istek/saat/IP, aşımda HTTP 429 (`kilo.ai/docs/gateway/usage-and-billing`).
- OpenRouter: `:free` kredisiz 50/gün, `Retry-After` + `X-RateLimit-*` (`openrouter.ai/docs/api_reference/limits`, `/faq`).
- Cloudflare OpenAI-uyumlu uç + function-calling'in model-bazlı olduğu (`developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/`, `/features/function-calling/`).
- Z.ai OpenAI-uyumlu `base_url=https://api.z.ai/api/paas/v4/` (`docs.z.ai/guides/develop/openai/python` — kodla birebir).
- LiteLLM Router: cooldown + fallback + deneme başına timeout (`docs.litellm.ai/docs/routing`).

## 6. Doğrulanan gerçekler

- Yukarıdaki tüm dosya/satır referansları bu dalda okundu.
- `getattr(istemci, "model", "")` tüm istemcilerde mevcuttur (grep ile doğrulandı: groq/glm/cloudflare/kilo/openrouter/nvidia/kimi/qwen/cohere/gemini `self.model` taşır).

## 7. DOĞRULANAMADI

- NVIDIA istemcisinin zincir-içi hangi alt modeli seçtiği dışarıdan görülemez (`_model_bul` iç döngü) — aile, yapılandırılmış `self.model` üzerinden çözülür; iç fallback görünmezliği belgeye işlenir.
- Groq dışı sağlayıcılarda çalışma-anı anahtar değişimi sonrası otomatik temizleme — yalnızca groq yolları (`anahtar_ayarla`, `groq_model_ayarla`) temizler; diğerleri Brain yeniden kurulumunda temizlenir.

## 8. İzin verilen kapsam

- YENİ `brain/model_family.py` (saf `coz(provider, model_id)` + testleri).
- `brain/brain.py`: `_erisim_engeli_mi` + `_ERISIM_COOLDOWN=3600`; iki except bloğuna elif dalı; `anahtar_ayarla`/`groq_model_ayarla`'da `_COOLDOWN` temizliği; OK/HATA audit satırlarına `| aile=` soneki.
- YENİ `tests/test_model_family.py`, `tests/test_erisim_engeli.py`.

## 9. Yasak kapsam

- Sağlayıcı sırası, secici kuralları, karne mantığı, tool seti, prompt blokları, izin sistemi — dokunulmaz.
- HarnessSpec entegrasyonu (harness dalının işi) — bu pakette YOK; yalnız çözücü + test.
- Qwen bekleme bayrağı, yapi self-healing — dokunulmaz.

## 10. Korunacak davranışlar

- Fallback sırası ve yerel son çare aynen çalışır; 429/timeout süreleri değişmez.
- Audit öneki formatı değişmez (soneke eklenir).
- Ücretli sağlayıcılar zincire girmez kuralı değişmez.

## 11. Risk sınıfı

Orta (routing/fallback). Sensörler: yeni ünite testleri + tam paket + audit grep.

## 12. Kabul sensörleri

`pytest tests -q` (baseline karşılaştırmalı), `py_compile`, audit.log `aile=` grep'i (canlı smoke hariç — kota koruması; sahte-istemcili testler yeterli).

## 13. Geri alma koşulu

Fallback sırası bozulursa, ücretli yol açılırsa veya paket-dışı test gerilerse `git checkout` ile geri alınır.

## 14. Sonuç (2026-09-12 uygulandı)

- YENİ `brain/model_family.py` + `tests/test_model_family.py` (31 vaka).
- `brain.py`: `_erisim_engeli_mi` + `_ERISIM_COOLDOWN=3600` iki except bloğunda; OK/HATA audit soneki `| aile=`; `anahtar_ayarla`/`groq_model_ayarla` cooldown temizliği.
- Yan bulgu + düzeltme: `anahtar_ayarla`/`groq_model_ayarla` `GroqClient` adını tanımsız kullanıyordu (NameError) — `from brain.groq import GroqClient, MODELLER` eklendi. Gerekçe: temizleme davranışının gerçek (dolu-anahtar) yolda çalışması için zorunluydu; ayrı paket açılmadı.
- Sensörler: yeni 47 test yeşil; `pytest tests -q` = 592 geçti / 3 hata / 7 skip — 3 hata pristine ile aynı sıra-bağımlı flake. Gerileme yok.
- KANITLANDI → paket tamamlandı.
