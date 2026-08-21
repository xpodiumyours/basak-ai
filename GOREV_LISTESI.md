# Başak — Görev Listesi (Yol Haritası)

19-20 Ağustos 2026. Referans: [OpenClaw](https://github.com/openclaw/openclaw) (380k+ yıldız) — SADECE genel yaklaşımından ilham alınıyor (gerçek hafıza + yeni yetki eklerken onay isteme). OpenClaw'un sınırsız/sandbox'sız komut çalıştırma yaklaşımı BİLİNÇLİ OLARAK ALINMIYOR — Başak'ın güvenlik sınırı (Faz 2) geçerliliğini koruyor.

**Sıra artık kilitli.** Fazlar sırayla açılır. Bir faz gerçekten çalıştığı kanıtlanmadan (AGENTS.md §6 — gerçek çalıştırma kanıtı) bir sonrakine geçilmez. Kod yazan ajana (Claude Code, Kilo Code, OpenCode, Codebuff) her seferinde **sadece o anki faz** verilir — tüm liste birden verilmez, kapsam taşmasın diye.

## Faz 0 — Bilinen 3 hata (ÖNCELİKLİ, henüz düzeltilmedi)

Kod incelemesiyle bulundu (2026-08-20), son commit'lerde (`52e667d`, `c2774f6`) dokunulmamış:

1. `chat.py` → `mesaj_isle()` her mesajda `TOOLS` listesini `brain.cevapla()`'ya geçiyor. `brain.py` → `cevapla()` içindeki `if tools and self.bulut_musait(): Groq'a git` satırı bu yüzden HER mesajda (selamlaşma dahil) tetikleniyor. Sonuç: yerel Ollama (`qwen2.5:3b`) pratikte hiç kullanılmıyor, "sadece zor sorularda buluta kaç" hedefi (AGENTS.md §1) bozulmuş. `qwen2.5:3b` zaten tool-calling destekliyor (`ollama.py`'deki "Ollama tool calling desteklemez" yorumu yanlış) — önce yerelde dene, gerçekten gerekiyorsa (gucle_mod açık / soru uzun) buluta düş.
2. Bulut modeli `openai/gpt-oss-20b` Türkçe'de zayıf — "SADECE TÜRKÇE yaz" talimatına rağmen karışık dil üretebiliyor. Madde 1 düzelince azalır ama ek önlem: cevapta çoğunlukla İngilizce tespit edilirse yerel modele düş.
3. `basak_app.py` → `Api._chat()` metodu `mesaj_isle()`'yi hiçbir try/except olmadan çağırıyor, thread `daemon=True`. Beklenmeyen bir hata olursa thread sessizce ölüyor, UI'da "düşünüyor" durumu sonsuza kadar takılı kalıyor (kullanıcı "cevap vermiyor" olarak görüyor). `_chat()` içine try/except eklenmeli, hata olursa mutlaka `js_callback("BasakUI.error(...)")` çağrılmalı.

Bitince: gerçekten çalıştır (`basak.cmd`), 5-6 farklı mesajla dene (selamlaşma, hava durumu, görev ekleme, uzun/karmaşık bir soru), hangi kaynağın (yerel/groq) cevap verdiğini ve dilin tutarlı Türkçe kaldığını göster.

## Faz 1 — Gerçek hafıza sistemi (kısmen yapılmış)

`knowledge/INDEX.md` zaten var, `chat.py` onu önceliklendiriyor — iyi başlangıç. Eksik: `save_note` yeni not eklerken `INDEX.md`'yi otomatik güncellemiyor (elle senkron kalıyor, dosya sayısı artınca INDEX bayatlar). OpenClaw dersi: konuşma sırasında öğrenilen kalıcı bilgi otomatik ilgili nota bağlanmalı — `save_note` çağrıldığında `INDEX.md`'ye tek satırlık özet eklensin.

## Faz 2 — Bilgisayarda iş yapma (araç kullanımı, whitelist'li)

Casper'ın onayladığı kapsam: (a) belirlenmiş klasörlerde dosya okuma/yazma (`knowledge/` ve benzeri, sistemin geneli değil), (b) izin verilen belirli uygulamaları açma (tarayıcı, not defteri vb. — beyaz liste). **Kesinlikle yok:** sınırsız komut çalıştırma, sistem dosyalarına erişim, onaysız silme — OpenClaw'daki sandbox'sız yaklaşım burada ALINMIYOR.

Uygulama notu: Ollama/qwen2.5'in tool-calling desteğini Faz 0 zaten doğrulayacak. Her araç çağrısı loglanır (ayrı bir `arac.log`); beyaz listeye yeni klasör/uygulama eklemek Casper onayı gerektirir (bkz. Faz 5).

## Faz 3 — Web arama (YAPILDI, doğrulandı)

`tools/web_search.py` mevcut: hava durumu (Open-Meteo API) + genel arama (DuckDuckGo). Çalışıyor, `gecmis.json`'da gerçek örnek var. Ekstra iş gerekmiyor.

## Faz 4 — Görev takibi (YAPILDI, doğrulandı)

`tools/tasks.py` mevcut: `add_task`/`list_tasks`/`complete_task`, tarih tespiti ("yarın", "bu hafta"). Çalışıyor. Ekstra iş gerekmiyor.

## Faz 5 — AGENTS.md'ye yeni güven sınırı

Faz 2 hayata geçince: yeni bir izinli klasör/uygulama eklemek ya da mevcut aracın kapsamını genişletmek **Casper onayı gerektirir** kuralı `AGENTS.md`'nin ilgili bölümüne işlenecek — ödeme/auth gibi hassas alanlarla aynı muamele.

---

**Not:** Bu liste artık sıralı bir yol haritası, serbest dökümlü aday listesi değil. Ajana bir sonraki fazı vermeden önce mevcut fazın gerçekten çalıştığını gör (screenshot/konsol çıktısı). Hangi faz açılırsa `AGENTS.md` §2'ye "şu an neredeyiz" olarak işlenir.
