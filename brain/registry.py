"""brain/registry.py — Model Registry (P3).

Her saglayicinin statik teknik karti: ucretsiz mi, tool calling destekliyor
mu, gozlemsel yetenek etiketleri ve yayinlanan kota bilgisi. Saglik durumu
(cooldown) burada degil, kota.py'de tutulur.

Limit kartlari 2026-09-20 resmi saglayici belgeleriyle guncellendi.
Hesaba/model katmanina gore degisen limitler burada uydurulmaz; 429 ve
saglayici basliklari calisma aninda hakikat sayilir.
"""

# Gucleri yalniz durum/arayuz metadata'sidir; runtime siralamasi veya
# kullanici niyeti secimi icin okunmaz.

# Veri saklama durumu (2026-09-30, Casper karari) — SADECE SEFFAFLIK.
# Bu alan karar/zincir siralamasini ETKILEMEZ: ne kullanici cumlesine
# bakar ne de bir saglayiciyi otomatik kapatir (AGENTS.md yasak listesi,
# madde 1 ve 6). Amac tek: kullaniciya dogru bilgiyi gosterebilmek.
#
# Degerler:
#   "kaydetmez"              -> saglayici gonderilen metni saklamadigini
#                               resmen bildiriyor (belge + tarih zorunlu).
#   "kaydeder"               -> gonderilen metni saklayabilir.
#   "egitime_kullanilir"     -> model gelistirme/egitim icin kullanabilir.
#   "dogrulanmadi"           -> resmi veri karti bu oturumda OKUNMADI.
#                               BILINMEYEN bilinmeyen olarak kalir; asla
#                               "kaydetmez" varsayilmaz.
#
# Kural: bu alan yalniz RESMI VERI KARTINDAN dogrulanmis bilgi tasir.
# Guvenilmeyen bir kaynaktan deger yazilmaz.
VERI_SAKLAMA_DEGERLER = (
    "kaydetmez", "kaydeder", "egitime_kullanilir", "dogrulanmadi",
)
_VERI_SAKLAMA_BILINMEYEN = "dogrulanmadi"

SAGLAYICILAR = {
    "groq": {
        "ad": "Groq",
        "ucretsiz": True,
        "tools": True,
        # Duzey 1 kaniti (2026-09-19 23:59, canli): gpt-oss modelleri
        # tool_choice="required" altinda INATLA 400 veriyor ("model did
        # not call a tool"), hem 120b hem 20b; auto/None'da ise ayni istek
        # dogal olarak GERCEK tool_call uretiyor. Ajan modu auto_enforced'a
        # alindi — duz metin zaten Brain'de basari sayilmaz.
        "ajan_tool_mode": "auto_enforced",
        "gucleri": ["hiz", "genel"],
        # Groq resmi free-limit tablosu (2026-09-20): gpt-oss 20b/120b
        # icin 30 RPM, 1000 RPD, 8K TPM, 200K TPD.
        "dakikalik_istek": 30,
        "gunluk_istek": 1000,
        "dakikalik_token": 8000,
        "gunluk_token": 200000,
        # Resmi tablo yuksek-seviye tabandir; org'a ozel limit farkli
        # olabilir. Yerelde sert kesme yapma, 429 + reset basligi hakikattir.
        "yerel_kota_koru": False,
        # RESMI VERI KARTI (2026-09-30, groq.com/privacy-policy):
        # API/Customer Data icin Groq "data processor" rolunu ustlenir;
        # isleme Groq Services Agreement + Data Processing Addendum
        # (DPA) cercevesinde yurur. Bu, sirketin kendi hizmetine ait
        # (kaydetmez anlamina GELMEZ; islenme sarti Sozlesme/DPA'da).
        "veri_saklama": "dogrulanmadi",
        "veri_karti": "https://groq.com/privacy-policy (2026-09-30 okundu; "
                      "DPA kapsami teyit edilmedi)",
        "not": "Ucretsiz ve cok hizli; 20b hizli, 120b guclu. Exact limit org bazli degisebilir.",
    },
    "gemini": {
        "ad": "Gemini",
        "ucretsiz": True,
        "tools": True,
        # OpenAI-uyumlu Gemini ucunda auto resmen belgeli; Basak
        # ajan turunda duz metni basari saymayip tool-call zorunlulugunu
        # uygulama katmaninda uygular.
        "ajan_tool_mode": "auto_enforced",
        "gucleri": ["arastirma", "uzun-baglam"],
        # Gemini limitleri model + proje + kullanim katmanina gore degisir;
        # resmi belge kesin rakam icin AI Studio Limits sayfasini isaret eder.
        "gunluk_istek": None,
        "yerel_kota_koru": False,
        # RESMI VERI KARTI (2026-09-30, ai.google.dev/gemini-api/terms,
        # "Data Collection and How Google Uses Your Data"):
        # Google, prompt + baglam + uretilen icerigi 30 GUN saklayabilir
        # (belgede Maps Grounding amli). AYRICA: ayni sartname ucretsiz
        # katmanin AB'de API Client olarak sunulmasini ve yalniz PAID
        # servislerin AB'de kullanilmasini sart koşuyor. Bu iki madde
        # kullaniciya acikca bildirilmelidir; siddet bilinmeyen olarak
        # isaretlenir.
        "veri_saklama": "kaydeder",
        "veri_karti": "ai.google.dev/gemini-api/terms — 30 gun depolama "
                      "(Maps Grounding); AB'de yalniz Paid (sartname)",
        "not": "Ucretsiz katman; kota model/proje bazli, 429 anlik hakikat.",
    },
    "glm": {
        "ad": "GLM",
        "ucretsiz": True,
        "tools": True,
        # Z.ai chat/completions arac protokolunde auto resmen belgeli.
        # Basak duz metni ajan turunda reddederek tool-call'i uygular.
        "ajan_tool_mode": "auto_enforced",
        "gucleri": ["kod", "genel"],
        "gunluk_istek": None,
        # RESMI VERI KARTI (2026-09-30, docs.z.ai/legal-agreement/privacy-policy,
        # Data Processing Addendum for API Services, madde 4b):
        # ACIK BEYAN: "The Company do not store any of the content the
        # Customer or its End Users provide or generate while using our
        # Services ... processed in real-time ... and is not saved on our
        # servers."
        # Yani yazdiginiz metin SAKLANMAZ. Baska turveri (hesap vb.)
        # gecici tutulur ve sozlesme bitince silinir.
        "veri_saklama": "kaydetmez",
        "veri_karti": "docs.z.ai/legal-agreement/privacy-policy DPA 4b — "
                      "icerik gercek zamanli islenir, sunucularda saklanmaz "
                      "(2026-09-30 okundu)",
        "not": "Z.ai ucretsiz: 4.7-flash (~200K, kod+ajan) + 4.5-flash.",
    },
    "cloudflare": {
        "ad": "Cloudflare",
        "ucretsiz": True,
        "tools": True,
        # Resmi Workers AI model semasi: none/auto/required.
        # Varsayilan glm-4.7-flash Free planda tool calling destekli.
        "ajan_tool_mode": "required",
        "gucleri": ["genel", "hiz"],
        "gunluk_istek": None,
        "gunluk_neuron": 10000,
        "yerel_kota_koru": False,
        # RESMI VERI KARTI (2026-09-30, developers.cloudflare.com/workers-ai/privacy):
        # "Cloudflare does not use your Customer Content to (1) train any AI
        # models ... or (2) improve any Cloudflare or third-party services,
        # and would not do so unless we received your explicit consent."
        # Yani: EGRITIM/INSA KULLANIMI ACIKCA YOK. Saklama yalniz
        # kullanicinin AYRI bir depolama servisi (R2/KV/...) kullanmasiyla
        # olur — Basak oyle bir sey yapmiyor.
        "veri_saklama": "kaydetmez",
        "veri_karti": "developers.cloudflare.com/workers-ai/privacy "
                      "(2026-09-30 okundu)",
        "not": "Workers Free: 10.000 neuron/gun; GLM-4.7-Flash tool calling destekli.",
    },
    "cohere": {
        "ad": "Cohere",
        "ucretsiz": True,
        "tools": True,
        # Cohere V2: tool_choice="REQUIRED" desteklenir.
        "ajan_tool_mode": "required",
        "gucleri": ["genel", "arastirma"],
        "gunluk_istek": None,
        # Resmi belge (docs.cohere.com/docs/rate-limits): deneme bileti
        # ayda toplam 1000 soru + dakikada 20 soru. Gunluk degil AYLIK.
        "aylik_istek": 1000,
        "yerel_kota_koru": True,
        "veri_saklama": _VERI_SAKLAMA_BILINMEYEN,
        "veri_karti": "Trust Center'da SOC2/ISO27001/DPA var; deneme anahtari "
                      "icin saklama/egitim maddesi 2026-09-30'da acikca "
                      "yayimlanmadi (belge imzali NDA ile isteniyor)",
        "not": "Trial key: ayda 1000 soru; Command A tool destekli.",
    },
    "deepseek": {
        "ad": "DeepSeek",
        "ucretsiz": False,
        "tools": True,
        "gucleri": ["kod", "genel"],
        "gunluk_istek": None,
        "veri_saklama": _VERI_SAKLAMA_BILINMEYEN,
        "veri_karti": "ucretsiz degil + zincire kapali; belge okunmadi",
        "not": "UCRETLI + KARTSIZ KAPALI — veri karti + deepseek_acik olmadan zincire girmez.",
    },
    "genel": {
        "ad": "Ozel Saglayici",
        "ucretsiz": False,
        "tools": True,
        "gucleri": ["genel"],
        "gunluk_istek": None,
        "veri_saklama": "dogrulanmadi",
        "veri_karti": "kisisel ozel bileti — kullanicinin kendi saglayicisi; "
                      "veri akisi tamamen o saglayiciya ait",
        "not": "Casper'in kendi bileti (ucretli/ozel). Anahtar yoksa zincire "
               "girmez; varsa EN SONDA yedek durur — bedava duzen degismez.",
    },
    "kimi": {
        "ad": "Kimi (Moonshot)",
        "ucretsiz": False,
        "tools": True,
        "gucleri": ["genel", "kod"],
        "gunluk_istek": None,
        "veri_saklama": _VERI_SAKLAMA_BILINMEYEN,
        "veri_karti": "ucretsiz degil + zincire kapali; belge okunmadi",
        "not": "UCRETLI + KARTSIZ KAPALI — veri karti + kimi_acik olmadan zincire girmez.",
    },
    "qwen": {
        "ad": "QwenCloud",
        "ucretsiz": True,
        "otomatik_ucretsiz": False,
        "tools": True,
        "gucleri": ["genel"],
        "gunluk_istek": None,
        # Alibaba Model Studio yeni-kullanici ucretsiz kotasi surelidir.
        # Anahtar bulunmasi kalici sifir maliyet kaniti degildir.
        "etkin": False,
        "veri_saklama": _VERI_SAKLAMA_BILINMEYEN,
        "veri_karti": "otomatik zincirde kapali; belge okunmadi",
        "not": "Sureli ucretsiz kota olabilir; otomatik sifir-maliyet zincirinde kapali.",
    },
    "nvidia": {
        "ad": "NVIDIA NIM",
        "ucretsiz": True,
        "tools": True,
        # NVIDIA NIM guncel dokumani required degerini desteklemiyor;
        # auto + Basak uygulama-katmani zorunlulugu kullanilir.
        "ajan_tool_mode": "auto_enforced",
        "gucleri": ["kod", "goruntu", "video"],
        "gunluk_istek": None,
        # RESMI KAYNAK (2026-09-30, NVIDIA API Trial Terms of Service,
        # madde 2.2/2.3 + NVIDIA Developer Forum'da resmi temsilci
        # Sophwats'in 10.06.2025 tarihli aciklamasi):
        # 2.2: icerik OTURUM BOYUNCA yalniz hizmet vermek icin kullanilir.
        # 2.3: "NVIDIA will not store or use User or Generated Content at
        # the end of each API session" — oturum sonunda saklanmaz/kullanilmaz.
        # Madde 3.3: yalniz oturum metrikleri ve hata loglari toplanir.
        # NOT: 2.7 "may, but is not obligated to, block, monitor, scan or
        # review" der — yani TEORIK olarak inceleme yetkisi var; siz yazmiyor.
        # Bu yuzden "kaydetmez" degil, oturum sonrasi kalici saklama yok
        # anlaminda "kaydeder" isaretlendi: denetim acik bir belirsizlik.
        "veri_saklama": "kaydeder",
        "veri_karti": "NVIDIA API Trial ToS 2.3 (oturum sonu saklanmaz) + "
                      "2.7 (inceleme yetkisi) — forum 2025-06-10 (2026-09-30 okundu)",
        "not": "NVIDIA Developer free endpointleri prototipleme icin; sabit kota resmi olarak yayinlanmiyor.",
    },
    "kilo": {
        "ad": "Kilo Gateway",
        "ucretsiz": True,
        "tools": True,
        # Kilo Gateway API ToolChoice semasi required destekli.
        "ajan_tool_mode": "required",
        "gucleri": ["genel", "kod", "goruntu"],
        "gunluk_istek": None,   # sinir saatlik (200 istek/saat/IP), gunluk degil
        # Resmi davranis: saatte 200 soru/IP. Gunluk karta islenmez.
        "saatlik_istek": 200,
        "yerel_kota_koru": True,
        # Mevcut kart notu bunu zaten yaziyordu: ucretsiz katman gonderilen
        # yazilari kaydedebilir; Casper 2026-08-23'te BILEREK onayladi.
        "veri_saklama": "kaydeder",
        "veri_karti": "registry notu (Casper onayi 2026-08-23); belge "
                      "bu oturumda yeniden okunmadi",
        "not": "Anahtarsiz calisir; 200 istek/saat/IP. Basari dusuk "
               "(%25, 2026-09 gozlemi) — one alinmaz, yedek durur. "
               "Ucretsiz katman gonderilen yazilari kaydedebilir — "
               "Casper 2026-08-23'te bunu bilerek onayladi.",
    },
    "openrouter": {
        "ad": "OpenRouter",
        "ucretsiz": True,
        "tools": True,
        # OpenRouter'da tools/tool_choice model bazinda desteklenir.
        # Basak yalniz katalogda ikisini de destekleyen :free modeli
        # ajan icin kabul eder; duz metni ajan turunda basari saymaz.
        "ajan_tool_mode": "auto_enforced",
        "gucleri": ["genel"],
        "gunluk_istek": 50,
        "yerel_kota_koru": True,
        # RESMI VERI KARTI (2026-09-30, openrouter.ai/privacy, 31.08.2026):
        # Politika, saglayicinin girdi metinlerini ("Inputs") KENDISININ
        # topladigini ve "for Model training and improvement by Model
        # Providers" kullandigini acikca yaziyor. Yani zincirdeki bu hatta
        # gonderilen mesaj icerigi egitim amaciyla ISLENEBILIR.
        "veri_saklama": "egitime_kullanilir",
        "veri_karti": "openrouter.ai/privacy — Inputs toplanir; model "
                      "egitimi/iyilestirme icin saglayici kullanimi acik",
        "not": "Free hesap: 50 istek/gun; yalniz :free ve tool destekli modeller.",
    },
    "mistral": {
        "ad": "Mistral",
        "ucretsiz": True,
        "tools": True,
        # OpenAI-uyumlu uc; function calling resmi olarak destekli.
        "ajan_tool_mode": "auto_enforced",
        "gucleri": ["genel", "kod"],
        # Dogrulama 2026-09-22 (console.mistral.ai + freellm.net):
        # Experiment plani ~1 milyar token/ay, ~1 istek/sn, 500K token/dk.
        # Kart istemez; TELEFON DOGRULAMASI ister.
        "dakikalik_istek": 60,
        "gunluk_istek": None,
        "yerel_kota_koru": False,
        # Mevcut kart notu bunu zaten yaziyordu; yalniz SEFFAFLIK icin
        # makine-okunur alana tasindi. Bu oturumda yeni belge okunmadi.
        "veri_saklama": "egitime_kullanilir",
        "veri_karti": "registry notu (2026-09-22): panelden kapatilmazsa "
                      "model gelistirmede kullanilabilir — belge dogrulanmadi",
        "not": "Ucretsiz Experiment: ~1 milyar token/ay, ~1 istek/sn. "
               "Telefon dogrulamasi ister. Veri, panelden kapatilmazsa "
               "model gelistirmesinde kullanilabilir (Settings > Privacy). "
               "Sira olcumden sonra kesinlesir.",
    },
    "huggingface": {
        "ad": "Hugging Face",
        "ucretsiz": False,
        # Aylik ucretsiz kredi 0,10 dolar (PRO 2 dolar). Sinirsiz bedava
        # saglayici DEGILDIR; otomatik zincire kendiliginden girmez.
        "otomatik_ucretsiz": False,
        "tools": True,
        "gucleri": ["genel"],
        "gunluk_istek": None,
        "veri_saklama": _VERI_SAKLAMA_BILINMEYEN,
        "veri_karti": "otomatik kullanima kapali; belge okunmadi",
        "not": "Router: tek HF jetonuyla 18+ saglayiciya gider. Ucretsiz "
               "kredi ayda yalnizca 0,10 dolar — otomatik zincire KAPALI "
               "(kart acilmadan cagrilmaz).",
    },
    "chutes": {
        "ad": "Chutes",
        "ucretsiz": False,
        "tools": True,
        "gucleri": ["genel"],
        "gunluk_istek": None,
        "veri_saklama": _VERI_SAKLAMA_BILINMEYEN,
        "veri_karti": "ucretli; TEE icinde calisir, belge okunmadi",
        "not": "UCRETLI (kullanim basina odeme): 1M token 0,0245 dolardan "
               "baslar. Modeller donanim dogrulamali TEE icinde calisir. "
               "Anahtar yoksa zincire girmez; otomatik bedava duzen degismez.",
    },
    "ovh": {
        "ad": "OVHcloud AI Endpoints",
        # 2026-10-01 resmi billing (docs.ovhcloud.com ai-endpoints-billing):
        # anahtarli kullanim pay-as-you-go'dur (Public Cloud + odeme
        # yontemi, $200 trial kredi). Anonim 2 istek/dk bedava ama standart
        # OpenAI istemcisi basliksiz istek ATAMAZ (httpx bos Bearer'i
        # LocalProtocolError ile reddeder, olcum 2026-10-01) — yani
        # adapter'in calistigi tek mod ucretlidir. Sifir-maliyet zincirine
        # otomatik girmez; anahtar + kart acilimi bilincli tercihtir.
        "ucretsiz": False,
        "otomatik_ucretsiz": False,
        "tools": True,
        # Resmi (ai-endpoints-function-calling): OpenAI SDK orneginde
        # tools + tool_choice="auto"; tool_choice degerleri belgelenmemis
        # — auto_enforced (Basak zorunlu ajan turunda duz metni basari
        # saymaz, siradaki saglayiciya gecer).
        "ajan_tool_mode": "auto_enforced",
        "gucleri": ["kod", "genel"],
        # Resmi (ai-endpoints-capabilities): anahtarlI 400 istek/dk;
        # kullanim/token tavanı YOK (tavan fiyatlandirma).
        "dakikalik_istek": 400,
        "gunluk_istek": None,
        "yerel_kota_koru": False,
        # RESMI VERI KARTI (2026-10-01, docs.ovhcloud.com capabilities):
        # "Data is not stored or shared during or after model use";
        # getting-started: "we do not store user data"; altyapi
        # Fransa (Gravelines), AB veri korumasi. Ayrica free-ai-api
        # sayfasi: "Your proprietary data is never used to train or
        # optimise our models."
        "veri_saklama": "kaydetmez",
        "veri_karti": "docs.ovhcloud.com ai-endpoints-capabilities — "
                      "'Data is not stored or shared during or after "
                      "model use' (2026-10-01 okundu)",
        "not": "UCRETLI (trial kredi + pay-as-yo-go); otomatik bedava "
               "zincire KAPALI — anahtar + kart acilinca satir devreye "
               "girer. Hiz: 400 istek/dk; kullanim tavani yok. Model "
               "varsayilani gpt-oss-120b (emeklilik listesinde degil).",
    },
    "sambanova": {
        "ad": "SambaNova",
        "ucretsiz": True,
        "tools": True,
        # 2026-10-01 resmi (docs.sambanova.ai function-calling):
        # tool_choice auto/required/none resmen belgeli — Basak zorunlu
        # ajan turunda dogrudan required gonderir.
        "ajan_tool_mode": "required",
        "gucleri": ["genel", "kod"],
        # RESMI FREE TIER (2026-10-01, docs.sambanova.ai rate-limits):
        # odeme yontemi YOK hesaplar: 20 istek/dk, 20 istek/gun,
        # 200.000 token/gun (model basi uretim listesi: DeepSeek-V3.1,
        # Llama-3.3-70B, gpt-oss-120b).
        "dakikalik_istek": 20,
        "gunluk_istek": 20,
        "gunluk_token": 200000,
        "yerel_kota_koru": False,
        # RESMI VERI KARTI (2026-10-01, community.sambanova.ai
        # /t/data-handling-and-retention/1314 — SambaNova personeli
        # yanimdi): "input tokens and prompts sent to the API are not
        # stored or archived and are not used for training or
        # fine-tuning"; Cloud Terms of Service referansli.
        "veri_saklama": "kaydetmez",
        "veri_karti": "community.sambanova.ai/t/data-handling-and-"
                      "retention/1314 (2025-08-18, SambaNova personeli; "
                      "Cloud ToS referansli)",
        "not": "Ucretsiz Katman (odeme yontemi yok): 20 istek/gun + "
               "200K token/gun. Hiz olcumu YOK — mistral'deki gibi "
               "sirada son baslar; olcumle yukselir.",
    },
    "llm7": {
        "ad": "LLM7.io",
        "ucretsiz": True,
        "tools": True,
        # RESMI (docs.llm7.io/guides/function-calling.md):
        # "Function calling depends on the selected model. Use the
        #  Models API to find models with `tools_calling: true`."
        # "`tool_choice: \"auto\"`: Lets the model decide whether to
        #  call your tool or answer directly."
        # BELGELENEN TEK tool_choice DEGERI "auto" — "required"/"none"
        # hicbir resmi sayfada belgelenmemis; openapi.json'da
        # /chat/completions yolu ve tool_choice alani YOK. Bu yuzden
        # auto_enforced: zorunlu ajan turunda duz metin basari sayilmaz,
        # siradaki saglayiciya gecer. Duz metne dokunulmaz.
        "ajan_tool_mode": "auto_enforced",
        "gucleri": ["genel"],
        # RESMI UCRETSIZ KATMAN (docs.llm7.io/limits.md):
        #   "| Free token | 1 | 60 | 250 |"  -> 1 istek/sn, 60 istek/dk,
        #   250 istek/saat
        #   "| Free token | 100,000 tokens per 24 hours |"
        # Gunluk ISTEK limiti YOK — yalniz 24 saatlik token kotasi var.
        "dakikalik_istek": 60,
        "dakikalik_token": None,
        "gunluk_istek": None,
        "gunluk_token": 100000,
        # limits.md: "Free-token quotas are provided at no charge and
        # may be reduced without notice based on demand, service
        # capacity, model availability, fair-use calculations,
        # abuse-prevention controls, and other operational factors."
        # Yani 100K SABIT BIR TAAHHUT DEGIL, talebe gore dusurulebilir.
        # Yerelde sert kesme yapma; resmi 429 + reset basligi hakikat.
        "yerel_kota_koru": False,
        # RESMI VERI KARTI: BULUNAMADI. 19 URL'lik sitemap ve 49 KB
        # llms-full.txt taranmasi rağmen privacy/retention/training
        # kelimeleri sifir; llm7.io ana sitesinde de yasal sayfa YOK.
        # Bu yuzden "kaydetmez" DEGIL "dogrulanmadi" — bilinmeyen
        # bilinmeyen kalir (registry.py basligindaki kural). Kullanan
        # kullanicya bu durum gosterilir; saglayici otomatik KAPATILMAZ
        # (AGENTS.md madde 6).
        "veri_saklama": "dogrulanmadi",
        "veri_karti": "BULUNAMADI — docs.llm7.io + llm7.io taranmasi "
                      "(2026-10-02): privacy policy / tos sayfasi "
                      "yok. Bilinmeyen, kaydetmez varsayilmadi.",
        "not": "Ucretsiz: 100K token/24sa, 1 istek/sn, kart/telefon "
               "sarti resmi metinde YOK. Model DeepSeek-V4-Flash-0731 "
               "(tier=turbo, tools_calling=true, 400K baglam; canli "
               "/v1/models 2026-10-02). Hiz olcumu YOK.",
    },
}

# Varsayilan oncelik sirasi (secici yeniden SIRALAMAZ — bu sira korunur).
# Ucretli saglayici sonda: kazayla cagrilmasin.
#
# 2026-09-20: sira hem canli hiz olcumunu hem resmi ucretsiz kapasiteyi
# korur. Groq/Gemini onde; Cloudflare genis gunluk free havuzuyla erken
# yedek; Kilo 200/saat ile genis yedek. OpenRouter 50/gun ve Cohere
# 1000/ay oldugu icin dar havuzlari gereksiz yere yakmamak uzere sonda.
# GLM'nin onceki canli olcumde 20 sn zaman asimi vermesi de one alinmama
# nedenidir. Kullanici metnine gore semantik siniflandirma YOKTUR.
VARSAYILAN_SIRA = [
    # Guclu + genis ucretsiz hatlar once; dar aylik/gunluk havuzlar
    # son care olarak saklanir. Bu semantik router degildir: kullanici
    # mesajina bakmaz, yalniz resmi kapasite + canli olcum gercegidir.
    "groq", "gemini", "cloudflare", "kilo", "nvidia", "glm",
    "openrouter", "cohere",
    # 2026-09-22 eklendi: Mistral. Yeri KASITLI olarak sonda, cunku
    # henuz canli hiz olcumu yok (hesap onay bekliyor). README kurali:
    # "Yeni bir saglayici eklersen once hiz_olcum.py ile olc, sonra
    # sirayi gerekcesiyle birlikte yorumda belirt."
    "mistral",
    # 2026-10-01 eklendi: SambaNova (resmi free tier: 20 istek/gun +
    # 200K token/gun, tool_choice=required belgeli). Hiz olcumu yok —
    # dar gunluk havuz + olcumsuzluk yuzunden mistral'den de sona,
    # son care olarak.
    "sambanova",
    # 2026-10-02 eklendi: LLM7.io (resmi: 100K token/24sa, 1 istek/sn,
    # gunluk istek limiti yok, kart/telefon sarti resmi metinde YOK).
    # Hiz olcumu YOK — README kurali geregi son care; olcumsuzlik
    # gerekcesiyle mistral/sambanova'dan da sona eklenir. NOT: 100K
    # token sabit taahhut degil ("may be reduced without notice").
    # Veri karti BULUNAMADI -> "dogrulanmadi"; bu bir hata degil,
    # bilinmeyenin bilinmeyen olarak kalmasidir.
    "llm7",
]


def kart(ad):
    """Saglayici kartini dondurur; bilinmeyen isimde guvenli bos kart."""
    return SAGLAYICILAR.get(
        ad,
        {
            "ad": ad,
            "ucretsiz": False,
            "otomatik_ucretsiz": False,
            "tools": False,
            "gucleri": [],
            "gunluk_istek": None,
            "veri_saklama": _VERI_SAKLAMA_BILINMEYEN,
            "veri_karti": "registry'de kaydi yok",
            "not": "Registry'de kaydi yok; otomatik kullanima kapali.",
        },
    )


def ucretli_mi(ad):
    return not kart(ad)["ucretsiz"]


# ---------------------------------------------------------------------
# SEFFAFLIK (2026-09-30, Casper karari)
# ---------------------------------------------------------------------
# Bu blok YALNIZ gosterir, karar vermez. Dizenin sirasi, uygunlugu ve
# secimi bu fonksiyonlarla DEGISTIRILEMEZ — AGENTS.md yasak listesi
# madde 1 (kullanici metnine bakan kod) ve madde 6 (keyfi kapatan
# bayrak) burada da gecerlidir. Amac: kullaniciya dogru bilgiyi
# vermek, riski GIZLEMEK degil ACIKLAMAK.
#
# Kullanan kullanici bunu tercih edebilir; Basak bir saglayiciyi
# otomatik olarak devre disi birakmaz.

_VERI_SAKLAMA_ACIKLAMA = {
    "kaydetmez": "Gönderilen metni saklamadığını resmen bildiriyor.",
    "kaydeder": "Gönderilen metni saklayabilir (kayıt süresi sağlayıcının "
                "veri kartında).",
    "egitime_kullanilir": "Gönderilen metni model geliştirme/eğitim için "
                           "kullanabilir.",
    "dogrulanmadi": "Resmî veri kartı henüz doğrulanmadı — bilinmiyor. "
                    "Güvenli varsayım yapılmaz.",
}


def veri_saklama(ad):
    """Saglayicinin veri saklama durumu. Bilinmiyorsa 'dogrulanmadi'.

    ASLA 'kaydetmez' varsaymaz: dogrulanmayan bilgi bilinmeyendir.
    """
    deger = kart(ad).get("veri_saklama")
    if deger not in VERI_SAKLAMA_DEGERLER:
        return _VERI_SAKLAMA_BILINMEYEN
    return deger


def veri_saklama_aciklama(ad):
    """Insan tarafindan okunabilir tek satirlik aciklama."""
    return _VERI_SAKLAMA_ACIKLAMA.get(veri_saklama(ad),
                                      _VERI_SAKLAMA_ACIKLAMA["dogrulanmadi"])


def veri_saklama_tablosu(sadece_zincirdeki=True):
    """Kullanicinin gorecegi tablo: [{ad, ad_guncel, durum, aciklama, kaynak}].

    Siralamayi TETIKLEMEZ; yalniz mevcut VARSAYILAN_SIRA uzerinden bilgi
    toplar. Sadece otomatik zincire girebilen saglayicilar gosterilir
    (ucretsiz + otomatik_ucretsiz degil) — kullaniciya yalniz calisan
    hatlar anlatilir.
    """
    satirlar = []
    for ad in VARSAYILAN_SIRA:
        k = kart(ad)
        if sadece_zincirdeki and (k.get("ucretsiz") is not True
                                  or k.get("otomatik_ucretsiz") is False):
            continue
        satirlar.append({
            "ad": ad,
            "ad_guncel": k.get("ad") or ad,
            "durum": veri_saklama(ad),
            "aciklama": veri_saklama_aciklama(ad),
            "kaynak": k.get("veri_karti", ""),
        })
    return satirlar


def veri_akisi_riski():
    """Zincirde verisini saklayabilen/en az bir hat var mi?

    YALNIZ arayuz/uyari icin. Brain bu degeri OKUMAZ; zincir sirasi ve
    saglayici secimi bu fonksiyona BAKMAZ (AGENTS.md madde 1 ve 6).
    """
    tablo = veri_saklama_tablosu()
    riskli = [s for s in tablo
              if s["durum"] in ("kaydeder", "egitime_kullanilir")]
    bilinmeyen = [s for s in tablo if s["durum"] == "dogrulanmadi"]
    return {
        "saklayanlar": [s["ad"] for s in riskli],
        "bilinmeyenler": [s["ad"] for s in bilinmeyen],
        "temiz": [s["ad"] for s in tablo if s["durum"] == "kaydetmez"],
    }


def otomatik_ucretsiz_mi(ad):
    """Saglayici otomatik sifir-maliyet zincirinde kullanilabilir mi?"""
    k = kart(ad)
    return bool(k.get("ucretsiz", False)
                and k.get("otomatik_ucretsiz", True))


def tool_destegi_var_mi(ad):
    return bool(kart(ad)["tools"])



def ajan_tool_modu(ad):
    """Saglayicinin Basak ajan turunda kullanacagi resmi arac modu.

    required: saglayici API'si en az bir tool-call'i zorlayabilir.
    auto_enforced: resmi API auto tool-calling destekler; Basak ajan
    turunda duz metni basari saymaz ve sonraki saglayiciya gecer.
    """
    return kart(ad).get("ajan_tool_mode")


def ajan_destegi_var_mi(ad):
    return ajan_tool_modu(ad) in ("required", "auto_enforced")


def ajan_tool_choice(ad):
    """Saglayiciya gonderilecek gercek tool_choice degeri."""
    return "required" if ajan_tool_modu(ad) == "required" else "auto"


def zorunlu_tool_destegi_var_mi(ad):
    """Geriye uyumluluk: Basak'in kati ajan protokolune uygun mu?"""
    return ajan_destegi_var_mi(ad)
