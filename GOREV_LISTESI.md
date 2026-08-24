# BAŞAK ANA PLAN — Bağlayıcı Yol Haritası (21 Ağustos 2026)

> ⚠️ **Bu belge eski ana plandır (22 Ağustos itibarıyla).** P1-P3 geçerli; P4 yerine
> ÖLÇÜ+POTA hattı, P5 yerine E-1..E-4 fazları geldi. Program yönetimi ve sıra artık
> **`ANA-PLAN.md`**'de yürür (24 Ağustos itibarıyla); bu dosya özellik biriktiricisidir
> — katman tanımları ve P4-P6 yönleri burada yaşar, sıra oradan gelmez.
> Aşağıdaki P4/P5 satırlarını okurken bu notu hesaba kat.

Casper'ın 20 katmanlı mimarisi + Jarvis kararları + öğrenme karar defterinin birleşmiş kesin hali.
Üç uyarı işlendi: (1) TencentDB bulutu reddedildi → yerel SQLite+sqlite-vec+BM25, (2) Terminal aracı en sıkı kuralla en son açılır, (3) faz kanıtı olmadan sıradaki faza geçilmez.

**Durum işaretleri:** ✅ yapıldı · 🔧 kısmen · 📌 planlı (faz etiketiyle) · ⛔ reddedildi · 🕐 uyuyor (anahtar var, hesap hazır değil) · ❓ dış koşul bekler

---

## KATMAN DURUMLARI

### 1. Ana Çalışma Katmanı — 🔧
- Agent Core çekirdeği ✅ (chat.py: bağlam → araç → sonuç akışı).
- Session Manager (konuşma kimliği, çoklu oturum, yarım görev) → **P3**.
- Task Manager: tek seferlik ✅; uzun/zamanlanmış/tekrar eden → **P5**.

### 2. Hafıza — 🔧 → P2 ANA İŞ
- Working ✅ (sohbet bağlamı). Episodic 🔧 (gecmis.json düz dosya). Semantic 🔧 (kütüphane "ilk 4000 karakter" ile okunuyor — yetersiz).
- Memory Engine: **yerel SQLite + sqlite-vec + BM25 + nomic-embed gömme (Ollama'da hazır, ücretsiz)** → **P2**. Önem puanı/tekrar temizleme/sıkıştırma P4'te olgunlaşır.
- Procedural Memory → P4. File Memory (PDF/görsel) → P6+.
- ⛔ TencentDB Agent Memory REDDEDİLDİ: bulut servisi "her şey bana ait" kuralını bozar.

### 3. Model Router — ✅ çekirdek / 📌 P3
- Sabit öncelik zinciri ✅: Groq→Gemini→GLM→DeepSeek(🕐)→Qwen(🕐)→NVIDIA→Ollama.
- Model Registry (context limiti, kota, rate limit, özellikler, sağlık durumu) → **P3**.

### 4. Yerel Fallback — ✅ Ollama son çare; internet/kota bitse bile Başak çalışır.

### 5. Model Seçim Motoru — ❌ → P3
- Görev sınıflandırma önce kural tabanlı (şeffaf); dinamik skorlar audit verisi birikince **P4**'te açılır.

### 6. Kota/Limit Yönetimi — ❌ → P3
- Sağlayıcı başına günlük kullanım sayacı, 429 geri çekilme, **ücretli çağrı varsayılan engelli**, günlük öğrenme bütçesi (karar #6).

### 7. Araçlar — 🔧
- Var: web arama, notlar, görevler, hatırlatmalar, whitelist'li dosya işlemleri, uygulama açma (shell kaldırıldı, sonda ile doğrulandı).
- P5: web sayfası okuma, git-okuma, izinli terminal (**en sıkı kural**), zamanlayıcı.
- P6+: browser otomasyonu (onayla), API client.
- ⛔ Python kodu çalıştırma: ŞİMDİLİK YASAK — sandbox kararı ayrıca Casper onayıyla alınır.

### 8. Tool Permission Layer — ❌ → P3
- Her araca etiket: read-only / write / sistem / internet / hassas. Model kendi yetkisini veremez/artıramaz.

### 9. Güvenlik / Policy Core — 🔧 ilkeler AGENTS.md'de → kod olarak P1
- Secrets ayrımı (env öncelik), kill switch (tepsi "Durdur" + acil durdurma), dosya/ağ/süre sınırları.
- 21 Ağustos'ta komut enjeksiyonu açığı kapatıldı (sonda ile kanıtlandı) — bu standart düşürülmez.

### 10. Audit/Log — 🔧 → P1 zenginleştirme
- Var: arac.log. Eklenecek: hangi model, neden seçildi, token, failover olayları, güvenlik engelleri.

### 11. Öğrenme/Gelişim Katmanı — ❌ → P4 (Karar Defteri ile birlikte)
- Görev analizi, başarılı/başarısız yol kaydı, model skor güncelleme, müfredat, doğrulama, onay kuyusu.
- Kural: ana güvenlik politikasını ASLA değiştiremez.

### 12. Model Keşif Sistemi — ❌ → P3 sonrası bonus
- HF/OpenRouter/NIM duyurularından yeni ücretsiz model bulur; test eder; uygunsa registry'ye ekler; Casper'a bildirir.

### 13. GPU/Ağır İş — 🕐 düşük öncelik
- Colab/Kaggle "sürekli yaşamaz" — sadece ileride isteğe bağlı ağır-job worker. Şimdilik yok.

### 14. Job Queue — ❌ → P5-P6 (zamanlayıcı ve arka plan işleriyle birlikte).

### 15. Veri Katmanı (/data) — ❌ → P1 iskeleti
- data/memory, conversations, tasks, files, model_stats, provider_limits, audit. Secrets ayrı (ayarlar.json gitignore'da).

### 16. Adapter Katmanı — ✅ fiilen var (groq/gemini/glm/deepseek/qwen/nvidia/ollama aynı arayüzde).

### 17. Başak API — ❌ → P6 (pywebview js_api bugün köprü görevi görüyor).

### 18. Web Arayüzü — 🔧 → v2 P6
- Ekranlara eklenecek: onay kuyusu, müfredat paneli, kalan kotalar, audit görüntüleme, sistem durumu.

### 19. Watchdog — ❌ → P1 mini (J1): tepside yaşama + çözerse yeniden başlatma + açılışta otomatik başlatma.

### 20. Çalışma Akışı — mevcut akış zincirin genişletilmiş hali yukarıdaki fazlarla oturur.

---

## FAZ SIRASI (kanıt kapılı)

| Faz | İçerik | Kabul ölçütü (kanıtsız geçilmez) |
|---|---|---|
| **P1** | ✅ TAMAMLANDI (22 Ağustos): tepsi ikonu + X=gizle + kill switch; otomatik başlatma (Basak.lnk); audit log (data/audit/audit.log — her çağrıda kaynak/süre/hata); /data iskeleti (memory, conversations, tasks, model_stats) | Kanıt: Casper görsel onay verdi + audit dosyası canlı: `OK kaynak=groq | 0.3 sn` |
| **P2** | ✅ TAMAMLANDI (22 Ağustos, Casper onaylı) — Hafıza Motoru: `memory/engine.py` (SQLite `data/memory/basak.db` + sqlite-vec vektör arama + FTS5/BM25 anahtar kelime, hibrit RRF birleşim). Her sorudan önce ilgili anılar bağlama eklenir (`chat.py` `_ilgili_anilar`); her cevaptan sonra episodic anı kaydedilir; eski `gecmis.json` aktarıldı; `knowledge/` + Obsidian defteri (`Basak/`) mtime takibiyle indekslenir. Ollama/embedding düşerse BM25-only devam eder. Kanıt: knowledge'da olmayan bilgi yalnız hafızaya eklenip soruldu → doğru cevap; 44/44 test yeşil; Casper canlı onayı verdi. | "Geçen hafta konuştuğumuz X" sorusuna doğru hatırlama; büyük kütüphanede ilgili notu bulma |
| **P3** | 🔧 KOD TAMAMLANDI (22 Ağustos), Casper canlı onayı bekleniyor — Router v2: `brain/registry.py` (sağlayıcı kartları: ücretsiz/ücretli, tool desteği, güçler, günlük limit), `brain/secici.py` (kural tabanlı seçim + şeffaf gerekçe), `brain/kota.py` (günlük sayaç `data/provider_limits/`, 429 sonrası otomatik soğuma, **ücretli çağrı varsayılan engelli**), `tools/permissions.py` (araç izin etiketleri; etiketsiz araç güvenlik engeline takılır), Session kimliği (`chat.py` OTURUM_ID, geçmişe işlenir). Seçim UI'da görünür ("Nemotron · kod işi"), audit'e gerekçe + istek sayısı yazar. | Görev türüne göre model seçimi görünür; kota dolunca otomatik geçiş; ücretli çağrı engelli |
| **P4** | Öğrenme döngüsü: müfredat + paralel doğrulama + resmi kaynak + onay kuyusu + bütçe + Procedural/Dinamik skor | Bir konuyu 2+ kaynakla doğrulayıp onaya sunar; bütçe bitince durur; reddedilen bilgi kalıcılaşmaz |
| **P5** | Yetki genişletme: sayfa okuma, git-okuma, izinli terminal, zamanlayıcı | Her yeni araç ayrı Casper onaylı; enjeksiyon sondası tekrar koşar ve temiz çıkar |
| **P6** | Başak API + Web UI v2 + File Memory + Job Queue | Harici basit istemciden /chat çalışır; UI'dan kota/onay/müfredat görünür |
| **P7** | Sesli Jarvis (eski J2): wake word + sürekli dinleme + hep sesli cevap | Eller serbest: "Başak" de → sor → sesli cevap al |

## REDDİLENLER / UYUYANLAR / BEKLEYENLER

- ⛔ TencentDB Agent Memory (bulut) — taşınabilirlik ihlali. Yerel ikamesi P2.
- ⛔ Python çalıştırma, sandbox'suz terminal — güvenlik.
- 🕐 DeepSeek (bakiye bekliyor), QwenCloud (model etkinleşmesi bekliyor) — kod hazır, canlanınca zincire otomatik girer.
- ❓ Ox Alpha — herkese açık API yok; açıldığında adapter deseniyle dakikalar içinde eklenir.
- 🕐 GPU katmanı — sadece ileride isteğe bağlı ağır işler için.

## DEĞİŞMEYECEK PARÇALAR (Casper'ın mülkiyet listesi)

Başak kimliği · hafızası · görev geçmişi · araçları · dosyaları · güvenlik politikası · izin sistemi · öğrenilmiş akışlar · arayüzü · audit kayıtları. Model yalnızca beyin sağlayıcısıdır; bunların hepsi yerel dosyalarda, klasör kopyasıyla taşınır.

---

**Not:** Bu liste sıralı yol haritasıdır. Her faz bittiğinde `AGENTS.md` §2'ye "neredeyiz" yazılır; kanıt olmadan faz kapanmaz.
