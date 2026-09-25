# P2 — Platformlar Arasi Ortak Ajan Mimarisi

Tarih: 2026-09-25
Dal: `preview/p2-arac-ara-profesyonel`

## Resmi referanslar

- OpenAI Agents SDK / Tools:
  https://openai.github.io/openai-agents-python/tools/
- OpenAI Tool Search:
  https://developers.openai.com/api/docs/guides/tools-tool-search
- OpenAI tool_choice:
  https://openai.github.io/openai-agents-python/agents/
- Anthropic Tool Use / deferred MCP tools:
  https://docs.anthropic.com/
- Google Gemini Function Calling:
  https://ai.google.dev/gemini-api/docs/function-calling
- LangGraph agent state / checkpoints / interrupt-resume:
  https://docs.langchain.com/oss/javascript/langgraph/thinking-in-langgraph

## Ortak karar

### 1. Capability discovery yetki kapisi degildir

OpenAI ve Anthropic buyuk tool yuzeylerinde deferred loading/tool search
kullanir. Bu, araci Basak'tan saklayan bir niyet siniflandiricisi degil,
context/token optimizasyonudur.

P2 ortak tabani: provider native discovery desteklemiyorsa 53 gercek arac
eager olarak modele verilir. Hidden resolver aktif akista kullanilmaz.

### 2. Tool policy acik run sozlesmesidir

`auto`: model araca ihtiyac olup olmadigina karar verir.
`required`: run en az bir gercek tool-call olmadan final olamaz.
`none`: arac yuzeyi bilincli kapatilir.

Policy kullanici metninden regex/kelime/niyet motoruyla tahmin edilmez.

### 3. Compositional loop tek state'tir

Gemini compositional function calling ve diger agent SDK'lar gibi:
model -> tool_call -> tool_result -> ayni model run'i -> sonraki tool/final.

Tool sonucundan sonra ilk `required` sonsuza kadar tasinmaz; sonraki tur
`auto` devam ederek final yazabilir.

### 4. Run state UI'dan ayridir

Canonical run state provider, tool calls ve evidence kaydini tutar. UI
`thinking/toolStatus/source/parca/bitir` olaylarini bunun gorunumu olarak
kullanir; UI metni run gerceginin kaynagi degildir.

### 5. Evidence ayri katmandir

Search result adaydir. Final kaynak/evidence ancak gercekten okunan veya
olculen tool sonucundan gelir. Hafizadaki eski Basak cevabi evidence degildir.

### 6. Context tam veri ile model penceresini ayirir

Kalici transcript kaybolmaz. Modele giden working context butceye gore
duzenlenir. Buyuk tool sonucu cursor ile parcalanir; sessiz truncation yoktur.

### 7. Streaming provider gercegidir

Provider token/event stream'i ana yol; frontend kelime animasyonu yalniz
fallback olabilir. finish_reason/max_tokens sessiz final sayilmaz.

### 8. Interrupt/resume durable state gerektirir

Frontend'in "yeniden gonder" davranisi gercek resume degildir. Gercek
checkpoint/resume icin run state kalici store'a yazilmali ve thread/run ID ile
yeniden acilmalidir. P2 sonraki kabul adiminda staging kalici store ile bu
katman E2E kurulmadan "resume" denmeyecektir.

## P2 aktif ilk uygulama

- Hidden resolver flow'dan cikti.
- 53 arac full registry.
- Acik `tool_policy`.
- AgentRunState canonical runtime kaydi.
- Cache aracli run'i bypass edemez.
- Mevcut evidence/context/stream/failover sertlestirmeleri korunur.

## Canli kabul

Kod + unit test yeterli degildir. Ayrica:
1. Provider basina 53 arac schema kabul testi.
2. Cok-alanli compositional gorev.
3. `auto` modda guncel veri hallucination eval'i.
4. `required` modda toolsuz final reddi.
5. Gercek token stream.
6. Provider failover.
7. Staging DB checkpoint/resume.
8. Preview mobil/desktop E2E.


## 2026-09-25 — provider-neutral runtime v2

- 53 gerçek araç tek runtime capability kataloğudur.
- Gizli ikinci araç seçici silinir.
- 2026-09-25 (Casper kararı, AGENTS.md §0): katalog modele tek seferde
  dökülmez. İlk turda yalnız `yetenek_ac` sunulur; model bir veya birkaç
  alanı açar, açılan alan run boyunca açık kalır. 13 alan, her biri 10'dan az
  araç (OpenAI tool search/namespace ve Anthropic tool search önerileri).
- Tool sonucu aynı run içinde modele döner; sonraki final/tool-call gerçek
  provider stream yolundan devam eder.
- Provider `length/max_tokens` ile durursa ham cevap değiştirilmez.
  `truncated` + run state `incomplete` olarak ayrı taşınır.
- Uygulama modele sahte teknik devam system mesajı göndermez.
- `resumable=false`: gerçek checkpoint/resume yapılmadan varmış gibi davranılmaz.
