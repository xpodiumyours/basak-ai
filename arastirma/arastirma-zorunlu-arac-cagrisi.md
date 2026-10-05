# Zorunlu Araç Çağrısı (tool_choice) Araştırması — 8 Sağlayıcı

Tarih: 2026-09-25
Not: **Bu dosya araştırmadır, karar değildir.** Kod değiştirilmedi, hiçbir uygulama kararı verilmedi.

Kaynak kuralı: yalnız resmi birincil kaynak (sağlayıcının kendi API dokümanı/OpenAPI/SDK/changelog) kullanıldı.
Blog, forum, üçüncü taraf özet kullanılmadı. Bulunamayan yerler "bulunamadı" olarak işaretlendi, tahmin yapılmadı.

---

## 1. Özet Tablo

| Sağlayıcı | Zorunlu parametre | Streaming ile birlikte | Belirli araca zorlama | Ücretsiz katman kısıtı |
|---|---|---|---|---|
| Groq | `tool_choice: "required"` | Belgede açık kısıt/uyarı yok | `{"type":"function","function":{"name":"..."}}` destekleniyor — ama `disable_tool_validation:true` iken zorlanamıyor | Genel rate limit var (RPM/RPD, modele göre); tool use'a özel kısıt bulunamadı |
| Google Gemini | `tool_choice.allowed_tools.mode: "any"` (güncel REST dokümanı) | Belgede açık kısıt/uyarı yok | `allowed_tools.tools: [...]` ile belirli fonksiyon(lar)a kısıtlama var | Free tier'a özel tool-use kısıtı bulunamadı |
| OpenRouter | `tool_choice: "required"` (aggregator; alt sağlayıcıya göre destek değişir) | Genel kısıt yok; ancak Anthropic modellerinde "thinking" açıkken forced tool_choice hata veriyor | `{"type":"function","function":{"name":"..."}}` — `require_parameters:true` ile destekleyen sağlayıcıya zorlanabilir | Kendi ücretsiz katmanına özel kısıt bulunamadı; destek sağlayıcıya göre değişiyor |
| Z.ai GLM | Yalnızca `"auto"` destekleniyor — `required`/`none` yok | Belgede yok | Yok — belge açıkça "no way to force a specific named function" diyor, prompt ile yönlendirme öneriyor | Belgede yok |
| Cloudflare Workers AI | Belgede `tool_choice` alanı bulunamadı | Belgede yok | Belgede yok | 10.000 Neuron/gün (genel limit, tool-use'a özel kısıt yok) |
| Cohere | `tool_choice: "REQUIRED"` (v2 Chat, yalnız Command-r7b ve sonrası) | Belgede özel not yok | Yalnız "en az bir araç" zorluyor; belirli TEK araca isimle zorlama belgede bulunamadı | Trial key: Chat 20 istek/dk, aylık 1000 çağrı (genel limit, tool-use'a özel kısıt yok) |
| Kilo (kilocode) | `tool_choice: "none" \| "auto" \| "required"` veya belirli fonksiyon (gateway/aggregator) | Belgede özel kısıt yok | Destekleniyor (ToolChoice tipi) | Ücretsiz katmana özel kısıt bulunamadı (kredi bakiyesi sistemi var, 402 hata kodu) |
| NVIDIA NIM | `tool_choice: "none" \| "auto"` veya named tool (OpenAI uyumlu format) | Belgede yok | Destekleniyor: `{"type":"function","function":{"name":"..."}}`, `type` alanı opsiyonel (varsayılan `function`) | Resmi kaynak bulunamadı (build.nvidia.com fiyat/limit sayfası 404 verdi) |

---

## 2. Sağlayıcı Detayları

### Groq

Kaynak: https://console.groq.com/docs/api-reference.md (Chat Completions — `tool_choice` alanı)

> "Controls which (if any) tool is called by the model. `none` means the model will not call any tool and instead generates a message. `auto` means the model can pick between generating a message or calling one or more tools. `required` means the model must call one or more tools."

Belirli araca zorlama formatı: `{"type": "function", "function": {"name": "my_function"}}`

`disable_tool_validation` alanı ile ilgili kısıtlama notu (aynı sayfa):

> "If set to true, groq will return called tools without validating that the tool is present in request.tools. `tool_choice=required/none` will still be enforced, but the request cannot require a specific tool be used."

Yani bu kısıtlama yalnızca `disable_tool_validation: true` ayarlandığında geçerli — genel durumda belirli araca zorlama çalışıyor.

Streaming alanı notu (aynı sayfa):

> "If set, partial message deltas will be sent. Tokens will be sent as data-only server-sent events as they become available, with the stream terminated by a `data: [DONE]` message."

`tool_choice=required` ile `stream:true`'nun birlikte kullanımına dair açık bir kısıt/uyarı cümlesi bulunamadı.

Ücretsiz katman: https://console.groq.com/docs/rate-limits sayfasında modele göre RPM/RPD/TPM/TPD tabloları var (örnek: bazı modeller 30 RPM / 1K RPD / 8K TPM / 200K TPD). Tool use'a özel bir kısıt cümlesi bulunamadı.

---

### Google Gemini

Kaynak: https://ai.google.dev/gemini-api/docs/function-calling

ANY modunun tanımı:

> "Model is constrained to always predict a function call."

Belirli fonksiyona kısıtlama örneği (aynı sayfa):

> `"tool_choice": { "allowed_tools": { "mode": "any", "tools": ["get_current_temperature"] } }`

Not: Bu, güncel dokümanda kullanılan format. Eski `functionCallingConfig.mode: "ANY"` + `allowedFunctionNames` alanları REST referans sayfasında (https://ai.google.dev/api/generate-content) da geçiyor ama sayfa çok uzun olduğu için `FunctionCallingConfig` şemasının tam enum listesi ve `allowedFunctionNames` alan tanımı bu araştırmada tam doğrulanamadı — kısmen "ANY"/"AUTO" değerleri görüldü, tam şema metni alınamadı.

Streaming: Aynı sayfada `streamFunctionCallArguments` diye AYRI bir özellik var (Gemini 3+ modellerde fonksiyon çağrısı argümanlarının parça parça akıtılması) — bu, "ANY modu + genel streaming" sorusuyla aynı konu değil. ANY modu ile `generateContentStream`'in birlikte kullanılamayacağına dair açık bir kısıt/uyarı bulunamadı.

Ücretsiz katman: https://ai.google.dev/gemini-api/docs/rate-limits sayfasında şu cümle var:

> "Rate limits depend on a variety of factors (such as your usage tier) and can be viewed in Google AI Studio."

Free tier'a özel, function-calling'e özgü bir kısıt cümlesi bulunamadı.

---

### OpenRouter

Kaynak: https://openrouter.ai/docs/guides/features/tool-calling

Belirli araca zorlama:

```json
{
  "tool_choice": {
    "type": "function",
    "function": {"name": "search_database"}
  }
}
```

Kaynak: https://openrouter.ai/docs/guides/routing/provider-selection

`require_parameters` tanımı:

> "With the default routing strategy, providers that don't support all the LLM parameters specified in your request can still receive the request, but will ignore unknown parameters. When you set `require_parameters` to `true`, the request won't even be routed to that provider."

tool_choice ile sağlayıcı seçimi ilişkisi:

> "When you send a request with `tools` or `tool_choice`, OpenRouter makes a best effort to route to providers known to support tool use."

> "a small set of parameters is used as a soft preference when choosing between providers of the same model: `tools`, `response_format` (including structured outputs), and `verbosity`."

Not: OpenRouter kendisi bir aggregator — `tool_choice: "required"` desteği nihayetinde altta yönlendirilen sağlayıcıya bağlı. Streaming ile ilgili genel bir kısıt bulunamadı; ancak arama sırasında (resmi sayfa dışı bir kaynaktan, bu yüzden kaynak olarak sayılmıyor ve alıntılanmıyor) Anthropic modellerinde "thinking" açıkken zorunlu tool_choice'ın hata verdiği bilgisine rastlandı — bu iddia resmi OpenRouter sayfasından birebir doğrulanamadı, o yüzden tabloya "genel kısıt yok" olarak not düşüldü, iddia ayrıca doğrulanmadı damgasıyla burada anılıyor.

---

### Z.ai GLM

Kaynak: https://docs.z.ai/guides/capabilities/function-calling

> "`tool_choice`: Controls function calling strategy, default is `auto` (only supports `auto`)"

Bu, `required`/`none` değerlerinin ve isimle belirli bir fonksiyona zorlamanın **desteklenmediğini** gösteriyor. Streaming veya ücretsiz katıma dair bir not bu sayfada bulunamadı.

---

### Cloudflare Workers AI

Kontrol edilen resmi sayfalar:
- https://developers.cloudflare.com/workers-ai/features/function-calling/
- https://developers.cloudflare.com/workers-ai/features/function-calling/embedded/
- https://developers.cloudflare.com/workers-ai/features/function-calling/traditional/

Bu üç sayfada da `tool_choice` parametresi, belirli araca zorlama veya streaming ile ilgili özel bir bilgi **bulunamadı**. Sayfalar yalnızca:

> "Function calling enables people to take Large Language Models (LLMs) and use the model response to execute functions or interact with external APIs."

> "There are open-source models which have been fine-tuned to do function calling." (örnek: `@hf/nousresearch/hermes-2-pro-mistral-7b`)

gibi genel açıklamalar içeriyor.

Ücretsiz katman kaynak: https://developers.cloudflare.com/workers-ai/platform/pricing/

> "Our free allocation allows anyone to use a total of 10,000 Neurons per day at no charge."

> "Workers Free | 10,000 Neurons per day | N/A - Upgrade to Workers Paid"

> "All limits reset daily at 00:00 UTC."

Bu, tüm model tipleri (text, image, embedding) için ortak bir havuz — tool-use'a özel bir kısıt cümlesi yok.

`/traditional/get-started/` alt sayfası denendi, 404 döndü (bkz. Ulaşılamayanlar).

---

### Cohere

Kaynak: https://docs.cohere.com/reference/chat (v2 Chat API referansı)

> "Used to control whether or not the model will be forced to use a tool when answering."

> **REQUIRED**: "the model will be forced to use at least one of the user-defined tools, and the `tools` parameter must be passed in the request"

> **NONE**: "the model will be forced **not** to use one of the specified tools, and give a direct response"

> "This parameter is only compatible with models Command-r7b and newer."

Kaynak: https://docs.cohere.com/docs/tool-use-usage-patterns

> "Alternatively, you can force the model to respond directly, i.e. to not make tool call(s), by setting the `tool_choice` parameter to `NONE`."

Belirli TEK bir aracı isimle çağırmaya zorlama (Groq/OpenAI/Anthropic'teki gibi `{"type":"function","name":"..."}` formatı) Cohere dokümanlarında **bulunamadı** — `REQUIRED` yalnızca "tanımlı araçlardan en az birini" zorluyor, hangisi olacağını seçtirmiyor.

Kaynak: https://docs.cohere.com/docs/rate-limits

> "Cohere offers two kinds of API keys: evaluation keys (free but limited in usage), and production keys (paid and much less limited in usage)."

Chat endpoint trial key limiti: 20 istek/dakika (production: 500 istek/dakika). Tool use'a özel bir kısıt cümlesi bulunamadı. Streaming ile tool_choice birlikte kullanımına dair bir not da bulunamadı.

---

### Kilo (kilocode)

Kaynak: https://kilo.ai/docs/gateway/api-reference

> `"tool_choice?: ToolChoice"` — değerler: `"none" | "auto" | "required"` veya belirli fonksiyon seçimi.

> "The gateway supports function/tool calling with automatic repair for common issues like duplicate tool calls and orphan cleanup."

Kilo bir gateway/aggregator — model kimlikleri farklı sağlayıcıları gösteriyor (örnek: `anthropic/claude-sonnet-4.5`, `mistralai/codestral-2508`).

Streaming: `"When stream: true, the response is a series of SSE events"` — tool_choice ile birlikte kullanımına dair özel bir kısıt bulunamadı.

Ücretsiz katman: Sayfada açık bir "free tier" ifadesi yok; 402 hata kodu için "Insufficient balance -- add credits to continue" notu var — bu, kredi bakiyesi tükenince isteğin reddedildiğini gösteriyor, ücretsiz kullanım kotasının tam tanımı bulunamadı.

---

### NVIDIA NIM

Kaynak: https://docs.nvidia.com/nim/large-language-models/1.10.0/function-calling.html

> `"none"`: "Disables the use of tools."

> `"auto"`: "Enables the model to decide whether to use tools and which ones to use."

Named tool choice formatı:

```json
{
  "type": "function",
  "function": {
    "name": "name of the tool goes here"
  }
}
```

> "The type field is optional and defaults to function if not specified."

Streaming ile ilgili bir not bu sayfada bulunamadı. `tool_choice: "required"` (OpenAI'daki gibi genel zorunlu mod) bu spesifik sayfada açıkça görülmedi — yalnızca `none`/`auto`/named tool değerleri doğrulandı; `required` değerinin NVIDIA NIM'de var olup olmadığı bu araştırmada netleşmedi (bulunamadı).

Ücretsiz katman: Resmi kaynak (build.nvidia.com fiyatlandırma/limit sayfası) denendi, 404 döndü. Resmi bir free-tier sayfası bulunamadı (bkz. Ulaşılamayanlar).

---

## 3. Final Cevap Aracı Deseni (exit tool / final-answer tool)

### OpenAI

Kaynak: https://developers.openai.com/api/docs/guides/function-calling (eski adres `platform.openai.com/docs/guides/function-calling`'den 301 ile buraya yönleniyor)

Sayfada "final answer tool" / sahte bitirme aracı deseni **resmi olarak tanımlanmış veya önerilmiş bir desen olarak bulunamadı**. `tool_choice` değerleri (`none`/`auto`/`required`/belirli fonksiyon) dokümante edilmiş, ama zorunlu modda modelin "araca gerek yok" diyebilmesi için resmi önerilen bir yöntem (ör. sahte bir "bitir" aracı tanımlama) sayfada açıkça yazmıyor.

### Anthropic

Kaynak: https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools ("Forcing tool use" bölümü)

`tool_choice` dört değer alıyor:

> "`auto` allows Claude to decide whether to call any provided tools or not. This is the default value when `tools` are provided."
> "`any` tells Claude that it must use one of the provided tools, but doesn't force a particular tool."
> "`tool` forces Claude to always use a particular tool."
> "`none` prevents Claude from using any tools. This is the default value when no `tools` are provided."

Önemli davranış notu:

> "Note that when you have `tool_choice` as `any` or `tool`, the API prefills the assistant message to force a tool to be used. This means that the models will not emit a natural language response or explanation before `tool_use` content blocks, even if explicitly asked to do so."

Modelin metinle açıklama yapmasını istiyorsanız önerilen resmi yöntem, zorunlu modu KAPATIP `auto` kullanmak ve kullanıcı mesajında açıkça istemek:

> "If you would like the model to provide natural language context or explanations while still requesting that the model use a specific tool, you can use `{"type": "auto"}` for `tool_choice` (the default) and add explicit instructions in a `user` message. For example: `What's the weather like in London? Use the get_weather tool in your response.`"

Yani Anthropic'in resmi önerisi, "final cevap aracı" (sahte bitirme aracı) deseni değil — `auto` moduna dönüp prompt ile yönlendirmek. Sahte bir "bitirme aracı" (exit tool) deseni sayfada tanınan/önerilen bir desen olarak **geçmiyor** (bulunamadı).

Ayrıca modele/ayara göre zorunlu araç kullanımının hiç desteklenmediği durumlar var (önemli, "required modda model bazen çağrı yapamaz" ile ilgili):

> Manuel extended thinking (`thinking: {type: "enabled"}`) açıkken: "`any` and `tool` are not supported and result in an error" — kullanılacak yerine: `auto` veya `none`.

> Claude Opus 5.5, Claude Fable 5.1 ve Claude Mythos 5.1 modellerinde: "`any` and `tool` return a 400 error" — önerilen alternatif: "`auto` with strict tool use ... or structured outputs ... `none` is also supported."

Streaming ile `tool_choice: any` birlikte kullanımına dair açık bir kısıt/uyarı cümlesi bu sayfada bulunamadı.

**Sonuç:** Ne OpenAI ne Anthropic dokümanlarında "final cevap aracı / exit tool" resmi olarak tanınan, adlandırılmış bir desen değil. İkisi de zorunlu modda modelin "araca gerek yok" diyebilmesi için resmi çözüm olarak **zorunlu modu kapatıp `auto`'ya dönmeyi ve prompt ile yönlendirmeyi** öneriyor (Anthropic bunu açıkça yazıyor; OpenAI'de bu spesifik öneri metni bulunamadı).

---

## 4. Ulaşılamayan / Doğrulanamayan

- **Cloudflare** `/workers-ai/features/function-calling/traditional/get-started/` — 404 döndü, içerik görülemedi.
- **NVIDIA** `build.nvidia.com/pricing` — 404 döndü; NVIDIA'nın resmi free-tier/rate-limit sayfası bulunamadı, bu yüzden NVIDIA ücretsiz katman kısıtı satırı "bulunamadı" olarak işaretlendi.
- **NVIDIA** `tool_choice: "required"` değerinin var olup olmadığı — fetch edilen `function-calling.html` sayfasında yalnız `none`/`auto`/named tool görüldü, `required` adında bir değer açıkça doğrulanamadı.
- **Google Gemini** `FunctionCallingConfig` şemasının tam enum listesi ve `allowedFunctionNames` alanının tam tanımı — `ai.google.dev/api/generate-content` sayfası çok uzun, tam şema metni bu araştırmada görülemedi (kısmi bilgi alındı).
- **Google Gemini** ANY modu + `generateContentStream` arasında resmi bir kısıt/uyarı cümlesi var mı — bulunamadı (yalnız alakasız bir özellik olan `streamFunctionCallArguments` bulundu, bu ayrı bir konu).
- **OpenRouter** — Anthropic modellerinde "thinking + forced tool_choice" çakışması iddiası resmi OpenRouter sayfasından birebir doğrulanamadı (yalnızca aramada üçüncü kaynaklı bir özet olarak görüldü, alıntı olarak kullanılmadı).
- **Kilo (kilocode)** — ücretsiz katmanın (varsa) tam tanımı ve limitleri resmi sayfada bulunamadı; yalnız kredi bakiyesi/402 hata mekanizması görüldü.
- **Cohere** — belirli TEK bir aracı isimle çağırmaya zorlama (named tool forcing) desteği var mı yok mu — resmi dokümanlarda açık bir cevap bulunamadı; `REQUIRED` yalnız "tanımlı araçlardan biri" diyor.
- **OpenAI** — `tool_choice: required` + `stream: true` birlikte kullanımına dair açık bir kısıt/uyarı cümlesi resmi sayfada birebir bulunamadı (genel olarak "kısıt yok" izlenimi var ama net bir onay cümlesi görülmedi).
