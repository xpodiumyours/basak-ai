"""brain/registry.py — Model Registry (P3).

Her saglayicinin statik karti: ucretsiz mi, tool calling destekliyor mu,
gucleri ne, gunluk istek limiti kac. Saglik durumu (cooldown) burada degil,
kota.py'de tutulur.

Limit kartlari 2026-09-20 resmi saglayici belgeleriyle guncellendi.
Hesaba/model katmanina gore degisen limitler burada uydurulmaz; 429 ve
saglayici basliklari calisma aninda hakikat sayilir.
"""

# Gucleri etiketleri secici motorunun anladigi standart degerlerdir:
# hiz, kod, arastirma, genel, uzun-baglam
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
        "not": "Trial key: ayda 1000 soru; Command A tool destekli.",
    },
    "deepseek": {
        "ad": "DeepSeek",
        "ucretsiz": False,
        "tools": True,
        "gucleri": ["kod", "genel"],
        "gunluk_istek": None,
        "not": "UCRETLI + KARTSIZ KAPALI — veri karti + deepseek_acik olmadan zincire girmez.",
    },
    "genel": {
        "ad": "Ozel Saglayici",
        "ucretsiz": False,
        "tools": True,
        "gucleri": ["genel"],
        "gunluk_istek": None,
        "not": "Casper'in kendi bileti (ucretli/ozel). Anahtar yoksa zincire "
               "girmez; varsa EN SONDA yedek durur — bedava duzen degismez.",
    },
    "kimi": {
        "ad": "Kimi (Moonshot)",
        "ucretsiz": False,
        "tools": True,
        "gucleri": ["genel", "kod"],
        "gunluk_istek": None,
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
        "not": "NVIDIA Developer free endpointleri prototipleme icin; sabit kota resmi olarak yayinlanmiyor.",
    },
    "kilo": {
        "ad": "Kilo Gateway",
        "ucretsiz": True,
        "tools": True,
        # Kilo Gateway API ToolChoice semasi required destekli.
        "ajan_tool_mode": "required",
        "gucleri": ["genel", "kod"],
        "gunluk_istek": None,   # sinir saatlik (200 istek/saat/IP), gunluk degil
        # Resmi davranis: saatte 200 soru/IP. Gunluk karta islenmez.
        "saatlik_istek": 200,
        "yerel_kota_koru": True,
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
        "not": "Free hesap: 50 istek/gun; yalniz :free ve tool destekli modeller.",
    },
}

# Varsayilan oncelik sirasi (secici yeniden SIRALAMAZ — bu sira korunur).
# Ucretli saglayici sonda: kazayla cagrilmasin.
#
# 2026-09-19 OLCUM (hiz_olcum.py, bu bilgisayar, ayni kisa soru):
#   groq 0.42 sn OK · gemini 1.31 sn OK · openrouter 1.49 sn OK
#   kilo 16.17 sn OK · glm 20.62 sn ZAMAN ASIMI · nvidia 44.08 sn OK
# Sira bu olcume gore dizildi: cevap veren hizli saglayici one.
# Eski sira (glm, cloudflare, groq, ...) "GLM onde" diyordu; olcum bunu
# curuttu — GLM her istekte zaman asimina ugruyor ve her mesaja 20 sn
# olu bekleme ekliyordu (olculen toplam: 21 sn; groq gelince 0.42 sn).
# Cloudflare/Cohere/Qwen anahtar girilene kadar bos yuvadir; yeri
# davranisi degistirmez, orta blokta dururlar.
# DeepSeek karti asagida durur (ucretli oldugu bilinsin) ama zincire
# HIC girmez — adaptoru yok, testler ucretli oldugunu dogrular.
VARSAYILAN_SIRA = [
    # Guclu + genis ucretsiz hatlar once; dar aylik/gunluk havuzlar
    # son care olarak saklanir. Bu semantik router degildir: kullanici
    # mesajina bakmaz, yalniz resmi kapasite + canli olcum gercegidir.
    "groq", "gemini", "cloudflare", "kilo", "nvidia", "glm",
    "openrouter", "cohere",
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
            "not": "Registry'de kaydi yok; otomatik kullanima kapali.",
        },
    )


def ucretli_mi(ad):
    return not kart(ad)["ucretsiz"]


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
