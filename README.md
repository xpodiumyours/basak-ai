# Başak

Windows üzerinde çalışan, Türkçe konuşan kişisel yapay zeka asistanı.
Masaüstü arayüzü (Jarvis tarzı), kalıcı hafıza, 52 araç, sesli giriş/çıkış
ve fatura fotoğrafından satış kataloğu üreten bir hat içerir.

> **Bu dosya 2026-09-19'da yazıldı.** O güne kadar README yoktu; projeye
> dışarıdan bakan biri (ya da bir yıl sonraki Casper) ne kurulacağını,
> hangi anahtarın gerektiğini ve nerede bozulduğunu bilemiyordu.

---

## 1. Ne yapar

| Yetenek | Durum |
|---|---|
| Türkçe sohbet (kelime kelime akan cevap) | ✅ |
| İnternette arama, sayfa okuma, haber, görsel, kitap | ✅ |
| Kalıcı hafıza (konuşulanları hatırlar, `knowledge/` notlarını indeksler) | ✅ |
| Fatura fotoğrafı → Vixrex'e hazır ürün kataloğu (CSV + JSON) | ✅ |
| Masaüstü kontrolü (dosya oku/listele, uygulama aç, görev/hatırlatma) | ✅ |
| Tablo (matris) yönetimi, doküman arama, GitHub durumu | ✅ |
| Sesli konuşma (Türkçe TTS) ve sesli komut (Whisper STT) | ✅ |
| Görüntü okuma (fatura/fotoğraf) | ✅ |
| Kendi modelini eğitmek | ❌ — bulut zinciri kullanılır (bkz. §5) |

## 2. Ne yapmaz (dürüst sınırlar)

- **Kendi beynini eğitmez.** Hazır bulut modellerini ücretsiz katmanlardan
  kullanır. Bu yüzden sağlayıcı kotaları ve zaman aşımları hızı etkiler.
- **GPU'suz makinede yerel büyük model koşmaz.** Ölçüldü: `qwen2.5:7b`
  CPU'da ~13 sn, DeepSeek sınıfı modeller 16 GB RAM'e sığmaz.
- **Araçları model kendi seçer.** Kodda "şu kelime geçerse şu aracı aç"
  mantığı YOKTUR ve bilerek yoktur (bkz. §9). Bunun bedeli: zayıf bir
  model araç çağırmayı atlayabilir.
- **Verin bilgisayarından çıkar.** Beyin bulutta çalıştığı için mesajın
  sağlayıcının sunucusuna gider; neyin nerede kaldığı §12'dedir.

## 3. Hızlı başlangıç

### 3.1 Gereksinimler

- Windows 10/11, Python **3.12**
- İnternet (bulut beyin için zorunlu)

### 3.2 Kurulum

```powershell
cd C:\Users\<kullanici>\basak-ai
python -m pip install -r requirements.txt
```

### 3.3 Anahtarlar

`ayarlar.json` git'e girmez. Şablondan kopyala ve **en az bir** anahtar yaz. **Anahtarlar ve ayarlar dosyanın EN ÜST SEVİYESİNDE durmalı** — iç içe `_` grupları yalnız açıklamadır, kod onları okumaz (2026-09-22 düzeltmesi; bekçisi `doktor.py`):

```powershell
Copy-Item ayarlar.ornek.json ayarlar.json
notepad ayarlar.json
```

Desteklenen sağlayıcılar (hepsi ücretsiz katmanlı):

| Anahtar alanı | Sağlayıcı | Ölçülen gecikme |
|---|---|---|
| `groq_key` | Groq | **0.42 sn** |
| `gemini_key` | Google Gemini | 1.31 sn |
| `openrouter_key` | OpenRouter (`:free` modeller) | 1.49 sn |
| `zai_key` | Z.ai (GLM) | zaman aşımı |
| `nvidia_key` | NVIDIA NIM | 44.08 sn |

Boş bıraktığın sağlayıcı **zincire girmez** ve hata vermez — "boş yuva"
sayılır. Zaman aşımları ve sıralama: bkz. §5.

### 3.3.1 2026-09-22'de eklenen platformlar

Adresler ve varsayılan modeller kodda gömülüdür; `mistral_api_url`,
`hf_api_url`, `chutes_api_url` alanlarıyla değiştirilebilir (kod değişmez).

| Anahtar alanı | Platform | Durum |
|---|---|---|
| `mistral_key` | Mistral | ✅ Bedava "Experiment": ~1 milyar token/ay, ~1 istek/sn. **Telefon doğrulaması ister**, kart istemez |
| `hf_token` | Hugging Face | ⛔ **Kapalı**: ücretsiz kredisi ayda yalnızca 0,10 dolar. Anahtar yazmak tek başına yetmez |
| `chutes_key` | Chutes | ⛔ **Kapalı**: ücretlidir (1M token 0,0245 dolardan). Anahtar yazmak tek başına yetmez |

⛔ işaretlilerin **kayıt kartı** açılmadan zincire girmez; bu bilerek
böyledir — bedava düzen bozulmaz. Yeni platformun sırası ölçümden sonra
`brain/registry.py` içinde gerekçesiyle belirlenir (bkz. §6 kuralı):
şu an listenin **sonundadır**, çünkü canlı hız ölçümü henüz yok.

> **2026-09-22:** glhf.chat adayı ölçümde ölü çıktı (HTTP 522) ve koddan
> tamamen kaldırıldı. Ölü sağlayıcı tutulmuyor.

⛔ işaretlilerin **kayıt kartı** açılmadan zincire girmez; bu bilerek
böyledir — bedava düzen bozulmaz. Yeni platformların sırası ölçümden sonra
`brain/registry.py` içinde gerekçesiyle belirlenir (bkz. §6 kuralı):
şu an ikisi de listenin **sonundadır**, çünkü canlı hız ölçümleri henüz yok.

> **Gizlilik notu:** Mistral'in ücretsiz katmanında veri, panelden
> kapatılmazsa model geliştirmesinde kullanılabilir
> (Mistral panel → Settings → Privacy).

### 3.4 Ses modeli (unutulursa Başak KONUŞMAZ)

`piper-tts` paketi ses modelini içermez. Türkçe ses modelini proje köküne
indir:

```powershell
$u = "https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/dfki/medium/tr_TR-dfki-medium.onnx"
Invoke-WebRequest "$u"      -OutFile "tr_TR-dfki-medium.onnx"
Invoke-WebRequest "$u.json" -OutFile "tr_TR-dfki-medium.onnx.json"
```

Dosyalar `.gitignore`'da (63 MB, tekrar indirilebilir). Eksikse TTS
kurulurken hata verir ve ses düğmesi sessiz kalır.

### 3.5 Çalıştırma

```powershell
.\Basak-Baslat.cmd      # ya da: python basak_app.py
```

## 4. Mimari

```
basak_app.py          masaüstü pencere + JS köprüsü (pywebview)
├── ui/               arayüz: index.html · app.js · style.css · head.js (3B kafa)
├── chat/             sohbet akışı
│   ├── flow.py       mesaj → bağlam + araç şeması → akış → cevap
│   ├── prompts.py    kimlik bloğu (yalnız kimlik; davranış talimatı yok)
│   ├── context.py    geçmiş penceresi + kalıcı hafıza bağlantısı
│   ├── tools.py      araç çağırma döngüsü + durum etiketleri
│   └── gate.py       tip güvenliği (çıktıya dokunmaz)
├── brain/            BEYİN: sağlayıcı zinciri, kota, yedekleme
│   ├── brain.py      ana sınıf: zincir kur, sırayla dene, düşerse devret
│   ├── registry.py   sağlayıcı kartları + VARSAYILAN_SIRA (ölçümle dizili)
│   ├── secici.py     sıra kararı (registry sırasını korur, oyun kurmaz)
│   ├── yayin.py      akan cevap (streaming) + araç isteği
│   └── adapters/     her sağlayıcı için ince adaptör
├── tools/            52 araç (şema + çalıştırma dalı)
├── memory/           SQLite hafıza motoru
├── voice/            Piper TTS + Whisper STT + konuşmacı tanıma
├── data/             çalışma verisi (git dışı): fatura, katalog, audit
└── tests/            pytest paketi
```

Cevap yolu:

```
mesaj → bağlam (kimlik + hafıza + geçmiş) + araç şemaları
      → beyin zinciri (sırayla dene)
      ├─ düz sohbet  → kelime kelime akar → ekran
      └─ araç gerekiyorsa → araç koşar → sonuç modele döner → cevap
```

## 5. Sağlayıcı zinciri ve hız

Başak bir sağlayıcıya bağlı değildir: zincir sırayla dener, biri düşerse
sıradakine geçer. Sıra **tahminle değil ölçümle** dizilir
(`brain/registry.py` → `VARSAYILAN_SIRA`).

2026-09-19 ölçümü (`python hiz_olcum.py`):

| Sağlayıcı | Süre | Durum |
|---|---|---|
| groq | **0.42 sn** | ✅ |
| gemini | 1.31 sn | ✅ |
| openrouter | 1.49 sn | ✅ |
| kilo | 16.17 sn | ✅ |
| glm | 20.62 sn | zaman aşımı |
| nvidia | 44.08 sn | ✅ |

**Bu ölçüm bir arızayı ortaya çıkardı:** eski sıra GLM'i başa koyuyordu.
GLM her istekte 20.62 sn'de zaman aşımına uğradığı için *her mesaja 20
saniyelik ölü bekleme* biniyordu; cevap aslında Groq'tan 0.42 sn'de
geliyordu.

**Önce / sonra (uçtan uca sohbet, `python hiz_olcum.py sohbet`):**

| | Önce | Sonra |
|---|---|---|
| Gecikme (ortanca) | **21.0 sn** | **0.39 sn** |
| Cevabı veren | groq (20 sn GLM beklemesinden sonra) | groq |

Aynı gün yapılan düzeltmeler:

1. `brain/registry.py` → `VARSAYILAN_SIRA` ölçüme göre yeniden dizildi
   (groq · gemini · openrouter öne; ölü glm geriye).
2. `brain/glm.py` → zaman aşımı 20→8 sn (cevap vermeyen uç zinciri 20 sn
   bekletmesin).
3. `brain/brain.py` → zaman aşımı soğuması 10→300 sn (ölü sağlayıcı her
   mesajda yeniden denenmesin; eskiden 10 sn'lik soğuma iki mesaj arasında
   dolduğu için ceza *her mesajda* yeniden ödeniyordu).

Yeni bir sağlayıcı eklersen: önce `hiz_olcum.py` ile ölç, sonra sırayı
gerekçesiyle birlikte yorumda belirt.

## 6. Araçlar

`tools/definitions.py` → `TOOLS` listesi (52 araç). Her aracın üç yeri
vardır ve üçü birden yapılmazsa araç **sessizce ölü kalır**:

1. `tools/definitions.py` — modele sunulan şema
2. `tools/__init__.py` → `calistir()` — çalıştırma dalı
3. `chat/tools.py` → `DURUM_METNI` — ekranda görünen durum etiketi

Kontrol komutu (şema ↔ dal uyumu):

```powershell
python -c "import re,sys; sys.path.insert(0,'.'); d=set(re.findall(r'tool_name == .([a-z_]+).', open('tools/__init__.py',encoding='utf-8').read())); from tools.definitions import TANINMIS_TOOLLAR as T; print('eksik dal:', sorted(T-d), '| fazla dal:', sorted(d-T))"
```

Beyaz liste dışı bir araç adı **asla koşmaz** — yetkiyi kod verir, model
kendine yetki yazamaz.

## 7. Ölçüm ve teşhis

| Araç | Ne yapar |
|---|---|
| `hiz_olcum.py` | Sağlayıcı gecikmelerini ölçer (kod değiştirmez) |
| `doktor.py` | Ortam kontrolü: paket · anahtar · ses modeli · hafıza — tek komut, kota harcamaz (`--canli` hariç) |
| `hafiza_olcum.py` | Hafıza arama doğruluğunu sabit setle ölçer; `--canli` ile anlam seti de ölçülür |
| `hata.log` | Çalışma günlüğü (5 MB × 3 döner) |
| `data/audit/audit.log` | Her beyin çağrısının denetim kaydı |
| `tools/saglik_raporu.py` | Sayaçlar + denetim özeti (araç olarak da koşar) |

## 8. Testler

```powershell
python -m pytest tests -q
```

Kök dizindeki `test_brain_cevapla.py` ve `test_tts_kontrol.py` **elle
koşulur** — canlı ağ çağrısı yaparlar, bu yüzden pakete dahil değildir:

```powershell
python test_brain_cevapla.py    # beyin gerçekten cevap veriyor mu?
python test_tts_kontrol.py      # ses modeli yerinde mi?
```

`tests/live/` altındaki testler **gerçek model ve kota** kullanır; normal
koşuda atlanırlar, yalnız şu komutla çalışırlar:

```powershell
python -m pytest tests/live -q --live
```

(2026-09-19: 8 canlı test geçti — açılış, bulut zinciri, `Api.boot()`
sözleşmesi, hafıza DB aç/kapa.)

GitHub Actions her push'ta `pytest tests -q --ignore=tests/live` koşar
(`.github/workflows/test.yml`).

## 9. Değiştirilemez kurallar

Bu proje iki belgeyle kendini disipline eder. Kod yazan herkes (insan ya
da ajan) işe başlamadan okur:

| Belge | Ne der |
|---|---|
| [AGENTS.md](AGENTS.md) | Ajan çalışma kuralları: hangi katman geri gelmez, doğrulama kapıları |
| [CHATBOT-YASAGI.md](CHATBOT-YASAGI.md) | Başak'ı chatbot'a çeviren her şey yasak |

**Özü:** Araçlar modele **her mesajda** sunulur, hangisini kullanacağına
**model karar verir**. "Şu kelime geçerse şu aracı aç" mantığı, cevaba
dokunan kod ve küçük/büyük model ayrımı yasaktır. Bunlar geçmişte
denendi, ölçüldü ve çürüdü; `tests/test_chatbot_yasagi.py` bekçiliğini
yapar.

> **Bilinen açık sorun (2026-09-19):** Araçlar modele sunuluyor ama model
> onları çağırmak yerine *tarif etmeyi* seçebiliyor (örnek: "bilgisayarımda
> dolaş" isteğine `list_files` çağırmak yerine "şu araçları
> kullanabilirim" demek). Kök sebep: modele araç sahibi olduğu hiçbir
> sistem mesajında söylenmiyor — yalnız kimlik bloğu veriliyor. Bu,
> §9'daki yasanın dar bir yerinden gevşetilmeden düzeltilemez; karar
> Casper'a aittir.

## 10. Bilinen tuzaklar

- **Türkçe karakterli dosyalarda** düzenleme aracı eşleşmezse dosya gizli
  kodlama farkı olabilir; PowerShell `.Replace` ile dosyanın kendi
  içeriği üzerinden değiştir ve `grep` ile doğrula.
- **`ayarlar.json` BOM'lu** okunur (`utf-8-sig`) — başka araçlarla
  düzenlerken BOM eklemek sorun değil.
- **Ses modeli dosyaları** `.gitignore`'da; yeni makinede tekrar indirilir.
- **`hata.log`** tanı için birincil kaynak: ekrandaki kısa mesaj yetmezse
  kök sebep oradadır.
- **Yerel görü (fatura okuma) GPU'suz makinede çok yavaş**: ölçüldü, yerel
  CPU modeli denemesi ~300 sn sürüyordu. `ayarlar.json` içinde
  `"yerel_goru_kapali": true` ile kapatılır (varsayılan öneri).

## 11. Lisans

Bu proje **GNU AGPL-3.0** ile lisanslıdır — tam metin: [LICENSE](LICENSE).
Telif hakkı: **Casper, 2026**.

**Düz Türkçe özeti:**

| Ne yapmak istiyorsun? | İzin var mı? |
|---|---|
| İndirip kendi bilgisayarında kullanmak | ✅ Serbest |
| Değiştirip kendine uyarlamak | ✅ Serbest |
| Arkadaşına vermek, paylaşmak, yaymak | ✅ Serbest |
| Alıp değiştirip **kendi sunucunda hizmet olarak sunmak** | ✅ Serbest — **ama kendi kodunu da AGPL ile açman gerekir** |
| Alıp kapalı kutuya çevirip satmak | ❌ Yasak |

**Ticari kullanım yasak değildir.** Tek şart: kodu açık tutmak. Amaç,
Başak'ı alıp kapalı bir servise çeviren birinin yaptığı iyileştirmeyi
topluma geri vermesini sağlamak.

Kendi bilgisayarına kurup kendi işinde kullanırsan (kodu dağıtmadığın
sürece) hiçbir yükümlülük doğmaz.

## 12. Gizlilik — verin nereye gidiyor?

**Dürüst cevap: yazdıkların bilgisayarından ÇIKIYOR.**

Başak'ın beyni yerel değildir; `brain/` katmanı ücretsiz bulut modellerini
kullanır (bkz. §5). Cevap üretilebilmesi için mesajın sağlayıcının
sunucusuna gitmek zorundadır.

| Ne | Nerede durur |
|---|---|
| Sohbet kayıtları, kalıcı hafıza, profil | **Senin bilgisayarında** (`data/`) — git'e girmez |
| Gönderdiğin mesaj + araç sonuçları | **Sağlayıcının sunucusuna gider** |
| API anahtarların | Senin bilgisayarında (`ayarlar.json`) — git'e girmez |
| Denetim kaydı (hangi sağlayıcı, kaç sn, hata var mı) | Senin bilgisayarında (`data/audit/audit.log`) |

**Sağlayıcı seçimi verini etkiler.** Kodda yazılı somut bir örnek:
Kilo Gateway'in ücretsiz katmanı gönderilen yazıları kaydedebilir
(`brain/registry.py`); bu, proje sahibi tarafından 2026-08-23'te bilerek
onaylandı. Genel kural `AGENTS.md` §8'de yazılı: *"eğitimde kullanılmıyor"
demek "saklanmıyor" demek değildir.* Hassas veriyle çalışacaksan
sağlayıcının veri kartını oku.

**Tamamen yerel çalıştırmak istersen** yerel bir model gerekir. Ölçüldü:
GPU'suz makinede koşmuyor (§2) — bu yüzden yerel model yolu şu an kapalıdır.