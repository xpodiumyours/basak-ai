# FREEBUFF ORTAM KURULUMU — gelişim ile canlı arasındaki farkı kapatma

**Tarih:** 2026-10-05 · **Karar:** Casper · **Amaç:** Freebuff'ta geliştirirken
preview'da Başak'ı canlı gibi test edebilmek; "zincir boş / cevap yok" döngüsünü
her proje ve her yeni sohbette yeniden yaşamamak.

---

## 0. Sorun — ölçülmüş

Freebuff sandbox'ı **kodu** git'ten alır, **sırları almaz**:

| Varlık | Senin makinende | Vercel'de (canlı) | Freebuff sandbox'ında |
|---|---|---|---|
| Kod | ✅ | ✅ | ✅ |
| `ayarlar.json` (anahtarlar) | ✅ | — | ❌ (git'e girmez, gitignore'da) |
| Sağlayıcı env anahtarları | — | ✅ | ❌ (`freebuff-env list` → boş) |
| Zincirdeki sağlayıcı | 10+ | 10+ | **1 (kilo)** |

Tek sağlayıcı kalınca zincir dayanıklılığı biter: kilo 429 verip cooldown'a
girdiği an `brain/brain.py` "Hiçbir model calismadi (bulut zinciri bos)"
üretir ve ekran "Bir sorun oluştu" gösterir. Kanıt kalıbı
`data/audit/audit.log` içinde durur: `HATA kaynak=... 429` satırından hemen
sonra `TAM BASARISIZLIK: bulut zinciri bos`.

OpenCode akışında bunun yaşanmamasının nedeni: preview Vercel'de açılır ve
**production env'ini devralır** — anahtarlar oradaydı. Yani kod farkı değil,
**ortam farkı**.

## 1. Kalıcı yöntem — proje başına BİR KEZ

### A) Gelişim (Freebuff sandbox + preview)

1. Freebuff'te projeni aç → **Settings → Environment**.
2. Aşağıdaki env adlarından **en az 2-3 tanesini** ekle (değerleri sağlayıcı
   panellerinden alırsın; Freebuff bu değerleri proje kapsamında saklar ve
   terminal + preview + VS Code süreçlerine otomatik enjekte eder —
   `export` yapmana gerek yok):

| ENV adı (kodun okuduğu) | Sağlayıcı | Not (README §3.3 ölçümü) |
|---|---|---|
| `GROQ_API_KEY` | Groq | **0.42 sn** — ilk öneri |
| `GEMINI_API_KEY` | Gemini | 1.31 sn |
| `OPENROUTER_API_KEY` | OpenRouter (`:free`) | 1.49 sn |
| `NVIDIA_API_KEY` | NVIDIA NIM | 44 sn ölçüldü — derin yedek |
| `KILO_API_KEY` | Kilo | zaten zincirde |
| `COHERE_API_KEY` / `MISTRAL_API_KEY` / `SAMBANOVA_API_KEY` / `OVH_AI_ENDPOINTS_ACCESS_TOKEN` | — | kartı açık sağlayıcılar |
| `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN` | Cloudflare | ikisi birlikte |
| `DASHSCOPE_API_KEY` / `DEEPSEEK_API_KEY` / `KIMI_API_KEY` / `ZAI_API_KEY` / `HF_TOKEN` / `CHUTES_API_KEY` | — | kart durumu README §3.3.1 |

3. **Kod değişikliği GEREKMEZ:** adaptörler `os.environ`'ı önce okur,
   bulamazsa `ayarlar.json`'a bakar (örn. `brain/brain.py:327`).
4. Doğrula:

```bash
freebuff-env list     # yalnız İSİMLERİ gösterir, değerleri asla
python3 doktor.py     # çevrimdışı, kota harcamaz
```

`doktor.py` çıktısında kritik satır **"Beyin zinciri"**dir: 1'den çok
sağlayıcı görünüyororsa preview canlı gibi davranır (kota dolunca diğeri
devralır). Sandbox'ta "ayarlar.json yok" hatası beklenebilir ve zararsızdır —
zincir env anahtarlarıyla kurulur.

**Önerilen hız üçlüsü:** `GROQ_API_KEY` + `GEMINI_API_KEY` +
`OPENROUTER_API_KEY` (0.42 + 1.31 + 1.49 sn; üç sağlayıcı = gerçek yedek
derinliği).

> **Dikkat — kart kapalı sağlayıcılar:** `HF_TOKEN` / `CHUTES_API_KEY`
> anahtarla girse bile registry kartı kapalıysa zincire girmez (⛔, README
> §3.3.1). Anahtar eklemek yetmez; kart ölçümle açılır. Anahtarı boşa harcama.

### B) Canlı

- Canlı şu an **Vercel'de** → anahtarlar Vercel env'inde, dokunma. Vercel
  preview'lar production env'ini devraldığı için test linkleri sağlıklıdır.
- Freebuff hosting'e geçilirse (deploy edilirse):

```bash
freebuff-deploy env set '{"GROQ_API_KEY":"..."}'   # deploy config'inde kalıcı
freebuff-deploy env list                            # yalnız isimler
```

Sandbox env'i ile production env'i **ayrıdır**; ikisini de doldurmak gerekir.

## 2. Zincir durumu — her yeni sohbette 10 saniye

```bash
python3 doktor.py    # "Beyin zinciri: N saglayici" satırına bak
```

`N > 1` ise test güvenlidir. `N = 1` ise kota biter bitmez hata yersin —
önce §1-A'yı tamamla. Tek sağlayıcıyı ölçmek için:

```bash
python3 -c "from brain import Brain; print([a for a,_ in Brain()._bulut_zinciri()])"
```

## 3. "Kırıldı mı?" ayrımı — her seferinde

| Sinyal | Anlam | Ne yap |
|---|---|---|
| "bulut zinciri bos" / "429" / "rate limit" | **Ortam + kota** — kod değil | §1'i tamamla; kota tazelenmesini bekle |
| `python3 -m pytest tests -q` kırmızı | **Kod kırılmış** | Dalı düzelt (Windows'a özgü `test_path_guvenligi.py` junction/büyük-harf testleri Linux sandbox'ta kırmızı çıkar — platform farkı, kod değil) |
| `git diff main...HEAD` boş | Main'e göre sapma yok | Birleştirilecek iş yok demektir |
| `data/audit/audit.log` `HATA kaynak=` satırları | Hangi sağlayıcı neyle düştü | Tek gerçek kanıt |

## 4. Diğer projeler (vixrex, numeramatch, xses)

- **Settings → Environment** proje kapsamlıdır: her Freebuff projesinde bir
  kez yapılır, yeni sohbetlerde kalır.
- Bu dokümanı ilgili repoya kopyala; anahtar adları o projenin kodunun
  okuduğu `os.environ` adlarıdır (grep: `os.environ.get`).

## 5. Neden `.env.example` değil

`.gitignore` içindeki `.env*` kalıbı kasıtlıdır ve örnek-şablon dosyaları da
kapsar — repoya sızacak bir env dosyası riski sıfırlanır. Şablon işini bu
doküman görür: anahtar adları §1-A tablosundadır ve koddan ölçülmüştür.
