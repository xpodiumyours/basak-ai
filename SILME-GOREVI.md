# SİLME GÖREVİ — Başak'ı çekirdeğe indir

**Tarih:** 2026-09-13 · **Karar:** Casper · **Taban commit:** `27b03a9`

## 0. Hedef — tek cümle

Başak'tan araç, ölçü kapısı ve orkestra katmanlarını sök; geriye **sohbet ekranı + ücretsiz model zinciri + kalıcı hafıza** kalsın.

Casper ekrandan konuşacak. Modeller kendi özellikleriyle cevap verecek. Bir sağlayıcının limiti bitince zincir sıradakine geçecek. Başka hiçbir şey olmayacak.

## 1. Kapsam kilidi

Bu dosyada yazmayan hiçbir şeyi silme, ekleme veya "iyileştirme". Kapsamı büyütmek Casper'ın kararıdır. Emin olmadığın yerde **dur ve sor** — tahminle silme.

---

## 2. KALACAK — dokunma

| Klasör / dosya | Neden |
|---|---|
| `brain/` (orkestra.py hariç) | Ücretsiz model zinciri. 12 adaptör, sıra motoru, kota sayacı, soğuma. **İşin kendisi bu.** |
| `memory/` | Kalıcı hafıza + profil. Casper'ı tanımaya devam edecek. |
| `ui/` | Sohbet ekranı. |
| `voice/` | Ses. Bu görevin kapsamı dışında — Casper ayrıca karar verecek. |
| `knowledge/` | Silme. Hafıza motoru bu klasörü indeksliyor; araçlar gidince notlara erişim **hafıza araması üzerinden** sürecek. |
| `data/audit/` | Zincir kaydı. Hangi sağlayıcı ne zaman devraldı — geçişi doğrulamanın tek yolu. |

**Ölçülmüş kolaylık:** `brain/` ve `memory/` klasörleri projenin geri kalanına bağlı değil. Tek istisna `brain/orkestra.py` — o da silinecek. Yani silme işi `chat/` + `basak_app.py` içinde toplanıyor.

## 3. GİDECEK

| Silinecek | Not |
|---|---|
| `tools/` (tüm klasör, 23 dosya) | 21 araç, izin katmanı, zamanlayıcı, hatırlatmalar |
| `olcu.py` | Ölçü çıkış kapısı — zaten `_SOZLESME_MODU="kapali"` ile devre dışı |
| `brain/orkestra.py` | 10 durumlu muhakeme iskeleti, ayarla kapalı |
| `chat/tools.py` | Araç döngüsü |
| `chat/approval.py` | Onay sistemi |
| `chat/gate.py` içindeki araç kısımları | `temizle()` ve dil kontrolü KALIR (aşağıda) |
| `_chat_legacy.py` | Ancak `chat/flow.py` kendi ayakları üstünde durduktan **sonra** |
| `gorevler.json` | Görev listesi aracı gidiyor |
| `tests/` içinde silinen şeyleri test edenler | Kalanların testi kalır |
| `telegram_bot.py` | `TOOLS` import ediyor. Ya araçsız çalışacak şekilde sadeleştir ya sil — Casper'a sor. |

---

## 4. Tavanları kaldır — "modeller kendileri olsun"

Şu an 12 adaptörün hepsi modeli kısıtlıyor. Casper'ın isteği modellerin **kendi özellikleriyle** çalışması:

| Ayar | Şu an | Olacak | Neden |
|---|---|---|---|
| `max_tokens` | 1024 | **4096** | Model uzun cevabı yarıda kesmesin |
| `temperature` | 0.5 sabit | **kaldır** | Sağlayıcının kendi varsayılanı geçerli olsun |
| `timeout` | 3 sn | **20 sn** | 3 sn modelin düşünmesine yetmiyor. Tamamen kaldırma — takılan sağlayıcı sırayı tıkar. |

Değişmeyecek olanlar: GLM zaten 12 sn (20'ye çıkar), yerel Ollama 120 sn (aynı kalır), NVIDIA büyük modelleri 10 sn (20'ye çıkar), Kilo `max_tokens=1500` (4096'ya çıkar — düşünme metni bütçeden yiyor).

**Kilo uyarısı:** `brain/registry.py` kartında yazıyor — Kilo ücretsiz katmanı gönderilen yazıları kaydedebilir. Casper bunu 2026-08-23'te bilerek onayladı. Kart notu **silinmeyecek**, aynen kalacak.

## 5. Zincir mantığına dokunma

Bunlar kalacak, çünkü "limiti bitince diğerine geçsin" tam olarak bunlar:

- `brain/registry.py` — kota kartları (Groq 200.000 jeton/gün, Gemini 20 istek/gün, Cohere 1.000/ay, Kilo 200/saat, OpenRouter 50/gün)
- `brain/secici.py` — sıra motoru, karne (72 saatte %50 altına düşen sona atılır), genel sohbette ilk 3'ü karıştırma
- `brain/brain.py` — 429'da 2 dakika, zaman aşımında 1 dakika soğuma; sağlayıcı düşünce sıradakinin devralması
- `brain/stats.py` + `brain/kullanim.py` — gerçek jeton sayacı. **Bu olmadan geçiş körleme olur:** GLM ve Cloudflare kotalarının bittiğini söylemiyor.

## 6. Sadeleşecek dosyalar

**`chat/prompts.py`** — `KIMLIK_BLOGU` ve `BIKIMLONDIRME_YONLENDIRME` kalır. `TOOL_YONLENDIRME` silinir (araç kalmadı). `OLCU_YONLENDIRME` kalır — "görmediğin sayıyı yazma, bilmiyorsan bilmiyorum de" kuralı araçtan bağımsız, dürüstlük kuralı.

**`chat/gate.py`** — `temizle()` kalır (`<think>` blokları, emoji, `badge::` temizliği). Dil kontrolü kalır (İngilizce sızıntı yakalama). `raw_tool_temizle` ve araç desenleri silinir.

**`chat/context.py`** — geçmiş penceresi (4.000 karakter / 20 mesaj) ve hafıza bağlantısı kalır. `load_knowledge` silinir — zaten çağrılmıyor.

**`chat/flow.py`** — ana akış. Araç bloğu, çekirdek araç seti seçimi, ham araç yakalama, kapasite kontrolü silinir. Kalan akış: mesaj → kimlik + kişilik + hafıza + profil + geçmiş → zincire ver → akan cevap → temizle → ekrana bas → hafızaya yaz.

**`chat/__init__.py`** — şu an `_chat_legacy.py`'den ~60 sembol yeniden dışa veriyor. Baştan yazılacak; yalnız kalan modüllerden gerçekten kullanılanlar.

**`basak_app.py`** — şu satırlar temizlenecek: `from tools import TOOLS`, `tools.reminders`, `tools.zamanlayici`, `chat.onay_ver`, `golge_kos` / `golge_mod_aktif_mi`. `KISILIK` metninden araçlarla ilgili kısımlar ("NEREYE BAKABILIRSIN", "YAZMA", araç listesi) çıkarılacak; kimlik, Türkçe kuralı, "sallamak yasaktır" kuralı kalacak.

---

## 7. Kabul ölçüsü — testin yeşil olması yetmez

Her madde **gerçekten koşturularak** kanıtlanacak. Ekran görüntüsü veya konsol çıktısı olmadan "bitti" denmeyecek.

1. **Uygulama açılıyor:** `python basak_app.py` → pencere açılır, ekran görünür.
2. **Sohbet çalışıyor:** ekrandan soru sorulur, cevap **kelime kelime akarak** gelir.
3. **Kaynak görünüyor:** cevabın altında hangi sağlayıcıdan geldiği yazar.
4. **Geçiş çalışıyor:** `data/audit/audit.log` içinde bir sağlayıcının `HATA` satırından sonra **başka bir adla** `OK kaynak=` satırı olmalı. Bu, "limiti bitince diğerine geçiyor"un tek kanıtı.
5. **Hafıza çalışıyor:** "benim adım X" denir → pencere kapatılır → yeniden açılır → "adım ne" sorulur → doğru cevaplar.
6. **Ölü bağlantı kalmadı:** `python -c "import basak_app"` hatasız çalışır. Silinen bir modülü import eden tek satır kalmayacak.
7. **Kalan testler yeşil:** `python -m pytest tests -q`.

## 8. Çalışma kuralları

- **Dal aç, main'e direkt inme.** `git checkout -B sadelestirme origin/master`.
- **Adım adım commit et.** Tek dev commit yapma: önce `tools/` sil + bağlantıları kopar, sonra `chat/` sadeleştir, sonra tavanları kaldır. Her adımdan sonra madde 6'yı koştur.
- **Aynı klasörde başka ajan çalıştırma.** Bu klasörde 13 Eylül gecesi 294 dosya kaydedilmeden silindi; `git restore` ile kurtarıldı. İki ajan aynı klasörde çalışırsa iş sessizce kaybolur.
- **Sır commit'e girmez.** `ayarlar.json`, `gecmis.json`, anahtar dosyaları — `.gitignore`'da kalacak.
- **Silmeden önce oku.** Bir dosyayı silmeden önce onu başka kimin import ettiğini ölç (`grep`), tahmin etme.
