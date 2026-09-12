# ARAŞTIRMA — MODEL + GÖREV ODAKLI HAFİF HARNESS

Tarih: 2026-09-12
Durum: ARAŞTIRMA / GÜVENLİK KAPSAMI
Ürün kodu değişikliği: 0

## Soru
Başak’ın ücretsiz sağlayıcı zincirinde tek büyük genel prompt/harness yerine nasıl daha güvenli ve daha hafif bir çalışma yüzeyi kurulmalı?

## Mevcut koddan doğrulanan gerçekler

1. `chat/flow.py` bugünkü ana yolda kimlik + KISILIK + TOOL_YONLENDIRME + OLCU_YONLENDIRME + BIKIMLONDIRME_YONLENDIRME bloklarını tur başında birleştiriyor. Profil bloğu varsa ayrıca ekleniyor.
2. `brain/kapasite.py` iki sınıf kullanıyor: güçlü / küçük. `kaynaklar` verildiğinde havuzdaki herhangi bir güçlü sağlayıcı bütün turu güçlü saydırabiliyor. Bu, fiilen seçilecek modeli temsil etmiyor.
3. Provider adı model ailesi değildir. Özellikle NVIDIA NIM aynı sağlayıcı altında GPT-OSS, Nemotron, Kimi ve isteğe bağlı DeepSeek modellerini barındırıyor.
4. Groq varsayılanı `openai/gpt-oss-20b`; Cloudflare varsayılanı `llama-3.2-3b-instruct`; GLM varsayılanı `glm-4.5-flash`; Gemini varsayılanı `gemini-2.5-flash`; Cohere varsayılanı `command-a-03-2025`.
5. Registry tüm bu sağlayıcılara topluca `tools=True` dese de gerçek tool davranışı model ve API biçimine göre farklı olabilir.

## Resmi kaynaklardan doğrulanan ilkeler

### Open Interpreter
Open Interpreter provider / model / harness katmanlarını ayrı tutuyor. Qwen, Kimi, DeepSeek gibi model ailelerine farklı harness seçebiliyor. Gerekçe: tek generic harness düşük maliyetli/open modellerin eğitim/RL ortamıyla uyuşmayıp performansı düşürebilir.

Sonuç: Başak da provider adını harness saymamalı; gerçek model ailesini ayrı bir değişken olarak ele almalı.

### Groq
Groq local tool-calling dokümanı tool şemalarının modele istek sırasında verilmesini şart koşuyor. Ayrıca çok araç vermemeyi öneriyor: tipik optimum 3–5 araç; daha büyük modellere 10–15’e kadar çıkılabilir. Büyük tool kütüphanesi için sorguya göre routing öneriliyor.

Sonuç: Başak’ın küçük-model 4 araçlık core seti prensip olarak makul. Asıl eksik, göreve göre daha da daraltma ve model seviyesinde request shaping.

### Google Gemini
Gemini function calling modelin araç çağrısını üretmesi, uygulamanın aracı çalıştırması ve sonucu tekrar modele vermesi şeklinde yapılandırılmış. Parallel/compositional function calling destekliyor.

Sonuç: Gemini’ye toolsuz generic sohbet promptu ile araç beklemek yerine görev tool gerektiriyorsa gerçek function declaration’lar verilmelidir.

### Cohere
Cohere v2 Chat `tools`, `tool_choice=REQUIRED|NONE` ve `strict_tools` destekliyor. Yani aynı promptu tüm modellere vermek yerine adapter düzeyinde provider/model özelliği kullanılabilir.

### Cloudflare Workers AI
Function calling istek içinde tool tanımlarıyla çalışıyor. Gelen tool_calls uygulamada çalıştırılıp modele geri veriliyor.

### Qwen
Qwen3 resmi kaynakları canonical function calling için Qwen-Agent/template/parser yaklaşımını gösteriyor; bazı Qwen3 deployment’larında model sunucusunun özel `qwen3_coder` parser’ı öneriliyor. Open Interpreter da Qwen/QwQ/DashScope ailesini `qwen-code` harness’a eşliyor.

Sonuç: Qwen aktif olduğunda generic OpenAI prompt biçimini zorlamak yerine Qwen uyumlu adapter/harness davranışı ayrı ölçülmelidir.

## Ana mimari kararı

Harness tek parça olmayacak. İki katman olacak:

1. **Görev Profili (task profile)** — modelden bağımsız olarak bu turda ne gerektiğini söyler.
2. **Model Adapterı (model-family adapter)** — seçilen gerçek modelin prompt/tool/message biçimini ayarlar.

Formül:

`HarnessSpec = TaskProfile + ModelFamilyAdapter`

Provider yalnız endpoint/auth/fallback bilgisidir. Harness seçiminin tek kaynağı değildir.

## Önerilen TaskProfile v1

### chat-lite
- normal sohbet
- tool yok
- kısa kimlik + gerekli biçim
- kişisel bilgi yalnız gerçekten gerekiyorsa
- streaming açık

### read-lite
- dosya/klasör/repo okuma
- yalnız gerekli 1–3 salt-okunur tool
- uzun kişisel profil yok
- kanıt/tahmin etmeme talimatı kısa
- tool sonucu sonrası doğal cevap

### web-lite
- web arama / sayfa okuma
- yalnız `web_search` + gerekiyorsa `sayfa_oku`
- kaynak doğrulama talimatı
- kişisel bağlam varsayılan 0

### personal-lite
- tool yalnız görev ayrıca gerektiriyorsa
- bütün profil yerine 0–3 ilgili doğrulanmış gerçek
- alakasız kişisel bilgi gönderilmez

### action-gated
- yazma / dış dünya etkisi / hesap / mesaj gibi işler
- mevcut onay kapısı korunur
- yalnız gerekli action tool’ları
- kullanıcı onayı olmadan execute yok

## Önerilen ModelFamilyAdapter v1

### gpt-oss
Groq varsayılanı ve NVIDIA varsayılanı aynı `openai/gpt-oss-20b` ailesine düşebilir. Provider değişse de aynı temel model adapterı kullanılabilir.

### llama-small
Cloudflare varsayılan `llama-3.2-3b-instruct`. En kısa sistem promptu, en az araç ve kısa tool döngüsü gerekir. Bu bir provider kararı değil, gerçek model kimliği kararıdır.

### glm-flash
Başak `glm-4.5-flash` kullanıyor. Mevcut OpenAI-uyumlu endpoint üzerinden generic structured tool adapterıyla başlanabilir; ZCode harness doğrudan kopyalanmamalı çünkü Başak bugün Messages endpoint kullanmıyor.

### gemini-flash
`gemini-2.5-flash`; function-calling özellikleri adapter tarafından kullanılmalı.

### command-a
Cohere `command-a-03-2025`; native Cohere tool seçenekleri (`tool_choice`, gerekirse `strict_tools`) adapter düzeyinde değerlendirilebilir.

### qwen
QwenCloud aktif olduğunda Qwen’e özel function-call parser/template davranışı ölçülmeden generic adaptera zorlanmamalı.

### nvidia-dynamic
NVIDIA provider tek adapter olamaz. `NvidiaClient.model` gerçek kimliği okunup gpt-oss / nemotron / kimi / deepseek ailesine yönlendirilmelidir.

### unknown
Tanımlanamayan model güvenli varsayımla `generic-lite` alır. “Güçlüdür” varsayımı yapılmaz.

## Kritik mevcut kusur

`brain/kapasite.py` provider havuzuna bakarak `guclu/kucuk` kararı verebiliyor. Örneğin havuzda GLM veya Groq bulunması, fiilen Cloudflare 3B ya da NVIDIA’daki farklı bir model kullanılacak olsa bile ağır yolu açabilir.

Bu nedenle yeni sistemde kapasite kararı:

`mevcut provider havuzu` üzerinden değil,
`o denemede gerçekten çağrılacak provider + gerçek model id` üzerinden verilmelidir.

Fallback başka model ailesine geçtiğinde adapter yeniden seçilmelidir.

## En güvenli entegrasyon noktası

Harness seçimini yalnız `chat.flow` içinde bir kez yapmak yeterli değildir; provider fallback sırasında model ailesi değişebilir.

Bu yüzden iki aşama önerilir:

1. `chat.flow` yalnız nötr bir `TaskProfile` üretir: görev tipi, izinli tool listesi, ilgili kişisel gerçekler, risk sınıfı.
2. `Brain.cevapla` provider döngüsünde her gerçek istemci çağrısından önce `provider + istemci.model + TaskProfile` ile `ModelFamilyAdapter` seçer.

Böylece GLM başarısız olup Cloudflare/Groq/NVIDIA’ya düşülürse aynı yanlış harness devam etmez.

## Uygulama sırası

1. `TaskProfile` salt veri yapısı; davranış değiştirmeden üretilebilsin.
2. Gerçek model kimliği çözücü: provider + `client.model` -> model_family.
3. `HarnessSpec` üretici: TaskProfile + model_family.
4. İlk deney yalnız iki profil: `chat-lite` ve `read-lite`.
5. İlk model aileleri yalnız mevcut ana ücretsiz hat: `gpt-oss`, `llama-small`, `glm-flash`.
6. Sonuç iyiyse `gemini-flash`, `command-a`, NVIDIA dinamik modeller ve ileride Qwen eklenir.

## İlk değişiklik paketi için izin verilen kapsam

- yeni görev profili / model-family çözümleme modülü
- mevcut prompt bloklarını kopyalamadan seçmeli birleştirme
- provider fallback sırasında gerçek model id’ye göre harness seçimi için gerekli dar bağlantı

## İlk pakette yasak

- provider sırasını değiştirmek
- yeni provider eklemek
- yeni memory mimarisi
- browser eklemek
- Vixrex müşteri akışına geçmek
- tüm promptları baştan yazmak
- tüm model ailelerini tek seferde desteklemek
- mevcut izin/onay sistemini değiştirmek

## Doğrulama kapısı

Test bataklığına girilmez. İlk deneyde yalnız şu üç davranış karşılaştırılır:

1. normal sohbet gereksiz tool almıyor mu,
2. açık dosya okuma doğru tool yüzeyini alıyor mu,
3. fallback farklı model ailesine geçtiğinde harness yeniden seçiliyor mu.

Ayrıca prompt karakter sayısı ve gönderilen tool sayısı önce/sonra kaydedilir. Büyük regresyon varsa paket reddedilir.

## Karar

**KANITLANDI — model/görev odaklı hafif harness mimarisi Başak için araştırma açısından destekleniyor.**

Ancak doğru birim provider değil; **TaskProfile + gerçek ModelFamilyAdapter** olmalıdır.
