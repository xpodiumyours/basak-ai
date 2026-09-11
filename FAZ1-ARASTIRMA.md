# BAŞAK — FAZ 1 HARNESS ARAŞTIRMASI

Durum: **BAŞLADI**  
Tarih: **12 Eylül 2026**  
Maliyet kuralı: **0 TL — araştırma ve deneylerde ücretli model/API zorunlu değil**

## 1. Araştırma sorusu

Küçük/ücretsiz/yerel model hangi çağrı düzeninde Başak'ın araçlarını daha güvenilir kullanıyor?

Karşılaştırma:

- A: mevcut Başak — önce araçsız streaming
- B: doğrudan tool-aware istek
- C: minimum harness
- D: yalnız gerektiğinde 0–3 kişisel gerçek

## 2. Qwen resmi dokümanından doğrulananlar

Qwen function calling / tool use özelliğini ayrı bir araç-kullanım düzeni olarak tanımlıyor.

Resmi Qwen dokümanı function calling için dedicated function-calling chat template / framework desteğinin önemli olduğunu belirtiyor. Ollama da uygun model/template ile function calling yolu olarak sayılıyor. Her OpenAI-uyumlu sunucunun Qwen function calling davranışını otomatik desteklediği varsayılmamalı.

Qwen2.5-7B-Instruct model kartı ayrıca instruction following ve structured output / JSON üretiminde Qwen2'ye göre gelişim bildirmektedir.

Kaynaklar:
- https://qwen.readthedocs.io/en/v2.0/framework/function_call.html
- https://huggingface.co/Qwen/Qwen2.5-7B-Instruct

## 3. Başak koduyla karşılaştırma

Bugünkü `master` kodunda:

### A — streaming yolu

`chat/flow.py` önce `brain.cevapla_yayin(...)` çağırır.

Yerel Ollama streaming uygulaması `brain/yayin.py::ollama_akit(...)` içinde `/api/chat` isteğine:

- model
- messages
- stream=true

verir.

**Tool şemaları bu isteğe verilmez.**

Sonuç: model bu ilk turda structured tool call üretmek için gerekli araç şemalarını görmez. Ancak araç adını düz metin olarak yazarsa Başak'ın `ham_tool_call_ayir` koruması bunu yakalamaya çalışabilir.

### B — tam/tool-aware yol

`brain/ollama.py::OllamaClient.cevapla(...)` `tools` parametresi geldiyse bunu Ollama `/api/chat` payload'ına doğrudan ekler.

Sonuç: Başak kodunda yerel Qwen için structured tool kullanımını gerçekten destekleyen yol zaten vardır; fakat mevcut akış önce toolsuz streaming cevabı denediği için bu yol her araç gerektiren görevde kullanılmayabilir.

## 4. Araştırma kararı

**KANITLANDI — yapısal:** A ve B aynı değildir. A yolu araç şemasını modele vermez; B yolu verir.

**KANITLANDI — referans:** Qwen'in resmi function-calling yaklaşımı modelin araç tanımlarını/function-calling formatını görmesini gerektirir.

**KANITLANMADI — canlı oran:** qwen2.5:7b üzerinde A'nın kaç kez düz metinle kaçtığı ve B'nin doğru aracı kaç kez seçtiği henüz güncel A/B koşumuyla sayısallaştırılmadı.

Bu nedenle ürün koduna doğrudan değişiklik henüz alınmaz. Önce yerel maliyetsiz benchmark sonucu istenir.

## 5. Maliyetsiz deney altyapısı

Güvenli deney dalı:

`experiment/faz0-streaming-tool-ab-20260912`

Bu dalda:

- `tests/test_faz0_streaming_tool_ab.py` — yapısal A/B testi
- `scripts/faz0_local_ab.py` — yalnız `127.0.0.1:11434` Ollama kullanan canlı yerel A/B benchmark
- `.github/workflows/faz0-no-cost-gate.yml` — public repo standart runner üzerinde API anahtarsız kritik regresyon kapısı

bulunmaktadır.

Benchmark hiçbir bulut anahtarı kullanmaz ve tool'ları çalıştırmaz; yalnız modelin araç seçme davranışını ölçer.

## 6. DeepSeek referansından alınan ek ilke

DeepSeek'in güncel resmi API dokümanı `tools` verildiğinde tool calling; `tool_choice=auto|required` seçeneklerini tanımlar. Ayrıca model tarafından üretilen tool argumentlerinin her zaman geçerli olmayabileceğini, uygulamanın parametreleri doğrulaması gerektiğini açıkça belirtir.

Bu ilke Başak için sağlayıcı bağımsızdır:

**Model araç çağrısını üretir; kod izin, şema ve argüman doğrulamasının son hakemidir.**

Başak'taki `tools/permissions.py`, executor sanitization ve deterministik kontrol yaklaşımı korunur.

Kaynak:
- https://api-docs.deepseek.com/guides/tool_calls/
- https://api-docs.deepseek.com/api/create-chat-completion/

DeepSeek ücretli API'si maliyetsiz ana yolun parçası değildir; yalnız mimari referanstır.

## 7. Sıradaki karar kapısı

Yerel qwen2.5:7b benchmark sonucunda:

1. B doğru araç kullanımını artırır ve sohbet kontrol görevini bozmazsa → araç gerektiği güvenilir biçimde bilinen mesajlarda streaming bypass için küçük deney hazırlanır.
2. Fark yoksa → streaming değiştirilmez; prompt/harness yüküne geçilir.
3. B gerilerse → deney reddedilir.

**Çalışan Başak kanıt olmadan değiştirilmeyecek.**
