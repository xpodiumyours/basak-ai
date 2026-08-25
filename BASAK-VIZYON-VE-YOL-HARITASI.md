# BAŞAK — Gerçek Vizyon ve Uçtan Uca Gelişim Planı

> **Tarih:** 24 Ağustos 2026
> **Durum:** ANA-PLAN Faz 0-5 büyük ölçüde tamamlandı; Faz 6-12 (profesyonel mimari) bekliyor
> **Bu belge:** Ne olduğunu, ne olabileceğini ve nasıl ulaşılacağını tanımlar

---

## 1. BAŞAK ŞU AN NE YAPABİLİYOR?

### Çalışan Özellikler (Kanıtlanmış)

| Özellik | Durum | Nasıl Çalışıyor |
|---------|-------|-----------------|
| **Sohbet** | ✅ | 9 bulut sağlayıcı + Ollama (yerel) — otomatik seçim, kota, fallback |
| **Dosya Okuma** | ✅ | `belgeler`→Documents, `masaustu`→Desktop, `indirilenler`→Downloads |
| **Dosya Yazma** | ✅ | `knowledge/` ve `research-engine/` içine yazma |
| **Web Arama** | ✅ | DuckDuckGo entegrasyonu |
| **Görev Yönetimi** | ✅ | Ekleme, listeleme, tamamlama |
| **Not Alma** | ✅ | `knowledge/` ve `defter/` üzerine kayıt |
| **Hafıza** | ✅ | SQLite + vektör arama + BM25 (episodik anılar) |
| **Sesli Konuşma** | ✅ | Piper TTS + faster-whisper STT (yerel) |
| **Model Seçimi** | ✅ | Kural tabanlı seçim + karne + kota |
| **Güvenlik** | ✅ | Araç izinleri, yetki tavani, SSRF savunması |
| **Ölçüm** | ✅ | [Ö]/[A]/[Ç]/[B] işaret sistemi + kapı denetimi |
| **Sistem Tepsisi** | ✅ | Arka plan çalışma, X=gizle |

### Temel Sorunlar (Hala Çözülmedi)

| Sorun | Kök Nedeni | Etkisi |
|-------|-----------|--------|
| **Tool sonrası doğal dil yok** | Model [Ö] formatına takılıyor, ham tool çıktısı basıyor | Kullanıcıya anlamsız çıktı |
| **Cloudflare 3B çok küçük** | Türkçe tool-calling ve doğal dil üretemiyor | Düşük kaliteli cevaplar |
| **GLM timeout** | Ağ yavaşlığı veya model aşırı yük | Bazen cevap alınamıyor |
| **Groq token bütçesi dolu** | 200K günlük limit aşıldı | 24 saat Groq kullanılamıyor |
| **Onay sistemi yok** | Hassas işlemler onaylanmadan çalışıyor | Güvenlik açığı |
| **Durum takibi yok** | Her tur izlenemiyor | Hata ayıklama zor |

---

## 2. BAŞAK NE OLABİLİR? — Gerçekçi Vizyon

### Kısa Vadeli (1-2 Hafta): "Çalışan Asistan"

**Hedef:** Basit sorularda doğal dil cevap veren, dosya okuyabilen, görev takip eden bir asistan.

**Ne yapar:**
- "Belgelerimde ne var?" → "Codex, Resimlerim, Vixrex-Secrets klasörleri var"
- "Bu dosyayı oku" → Dosya içeriğini gösterir
- "Yarın süt al" → Görev ekler
- "Hava nasıl?" → Web araması yapar
- "Not al: Favori çayım Çaykur" → Hafızaya kaydeder

**Nasıl çalışır:**
- Cloudflare/GLM bulut modelleri tool call üretir
- Tool sonucu doğal dille özetlenir
- Hafızadan ilgili bilgiler çekilir

### Orta Vadeli (1-3 Ay): "Güvenilir Asistan"

**Hedef:** Hassas işlemleri onaylayan, hata yaptığında bilen, kendini geliştiren bir asistan.

**Ek özellikler:**
- **Onay Sistemi:** "Bu dosyayı sil" → "Emin misin? [Evet]/[Hayır]"
- **Hata Bildirimi:** "Groq çalışmıyor, GLM kullanıyorum" gibi şeffaf iletişim
- **Kendini Ölçme:** "Bu hafta 45 soru cevapladım, %85 başarı"
- **Geri Alma:** "Son işlemi geri al" → Yapılan değişikliği iptal etme

### Uzun Vadeli (3-6 Ay): "Profesyonel Ürün"

**Hedef:**güncellenebilir, kurtarılabilir, ölçülebilir gerçek bir ürün.

**Ek özellikler:**
- **Paketleme:** Tek dosya (PyInstaller) ile kurulum
- **Otomatik Güncelleme:** Güvenli güncelleme + geri alma
- **Veri Yedeği:** Otomatik 7 günlük yedek
- **Sürüm Takibi:** Her değişiklik izlenebilir
- **Kişisel SLO:** "Veri kaybı = 0, yanlış eylem = 0"

---

## 3. UÇTAN UCA GELİŞİM PLANI

### AŞAMA 1: Temel Düzeltmeler (Bu Hafta)

**Amaç:** Mevcut sistemi gerçekten çalışır hale getir

| Görev | Sorun | Çözüm | Süre |
|-------|-------|-------|------|
| **A1.1** Tool sonrası doğal dil | Model ham tool çıktısı basıyor | `_tool_calling_multi`'ye user mesajıyla doğal dil talimatı | ✅ Yapıldı |
| **A1.2** Klasör haritası | Türkçe isimler tanınmıyor | `file_ops.py`'ye kapsamlı harita | ✅ Yapıldı |
| **A1.3** badge:: temizliği | İç format kullanıcıya sızıyor | `_temizle` + `olcu.py` düzeltmeleri | ✅ Yapıldı |
| **A1.4** Cloudflare hatası | Mesaj formatı bozuk | `cloudflare.py` sanitizasyon | ✅ Yapıldı |
| **A1.5** GLM timeout | Model zaman aşımı | Timeout süresini artır + fallback | 🔧 Yapılacak |
| **A1.6** Groq durumu | Token bütçesi dolu | Groq'u devre dışı bırak veya bütçeyi artır | 🔧 Yapılacak |

**Kabul Ölçütü:** "Belgelerimde ne var?" sorusuna doğal dil cevap alınıyor

### AŞAMA 2: Güvenilirlik (2. Hafta)

**Amaç:** Hata yaptığında bilen, onay isteyen bir asistan

| Görev | İçerik | Çıktı |
|-------|--------|-------|
| **A2.1** Onay Sistemi | Hassas işlemler (yazma/silme/gönderme) için onay | Onay ekranı + reddetme |
| **A2.2** Hata Bildirimi | Model neden cevap veremediğini söylesin | Anlamlı hata mesajları |
| **A2.3** Geri Alma | Son işlemi iptal etme | `undo` fonksiyonu |
| **A2.4** Durum Gösterimi | "Şu an Groq kullanıyorum" | UI'da durum göstergesi |

**Kabul Ölçütü:** Hassas işlem onaylanmadan çalışmıyor

### AŞAMA 3: Zeka (3. Hafta)

**Amaç:** Öğrenen, kendini geliştiren bir asistan

| Görev | İçerik | Çıktı |
|-------|--------|-------|
| **A3.1** Öğrenme Döngüsü | Başarılı/başarısız işlemleri kaydetme | Karne sistemi |
| **A3.2** Bağlam Zenginleştirme | Daha iyi hafıza kullanımı | İlgili anıları bulma |
| **A3.3** Proaktif Davranış | "Bugün 3 görevin var" gibi hatırlatmalar | Otomatik bildirim |
| **A3.4** Kişiselleşme | Kullanıcı alışkanlıklarını öğrenme | Tercih takibi |

**Kabul Ölçütü:** Kullanıcı "geçen hafta konuştuğumuz X" dediğinde hatırlıyor

### AŞAMA 4: Profesyonellik (4. Hafta)

**Amaç:** Ölçülebilir, güncellenebilir, kurtarılabilir ürün

| Görev | İçerik | Çıktı |
|-------|--------|-------|
| **A4.1** Paketleme | PyInstaller onedir | Tek dosya kurulum |
| **A4.2** Yedekleme | Otomatik 7 günlük yedek | Veri koruması |
| **A4.3** Güncelleme | Güvenli güncelleme + geri alma | Sürüm yönetimi |
| **A4.4** İzleme | Tur bazlı metrik | SLO takibi |

**Kabul Ölçütü:** Temiz Windows profilinde kurulum/açılış çalışıyor

---

## 4. ALT AJAN GÖREV DAĞILIMI

### Ajan 1: Çekirdek (core)
**Sorumluluk:** Temel sohbet akışı, tool calling, doğal dil üretimi
- `_tool_calling_multi` optimizasyonu
- System prompt basitleştirme
- Model seçimi iyileştirme

### Ajan 2: Araçlar (tools)
**Sorumluluk:** Dosya işlemleri, web arama, görev yönetimi
- Klasör haritası genişletme
- Yeni araç ekleme (geri alma, onay)
- Güvenlik katmanı güçlendirme

### Ajan 3: Beyin (brain)
**Sorumluluk:** Model yönetimi, kota, karne
- GLM timeout düzeltme
- Groq bütçe yönetimi
- Yeni model entegrasyonu

### Ajan 4: Hafıza (memory)
**Sorumluluk:** Episodik hafıza, indeksleme, arama
- Hafıza kalitesini artırma
- Yeni veri sınıfları
- Dışa aktarma/silme

### Ajan 5: Güvenlik (policy)
**Sorumluluk:** İzinler, onay, denetim
- Onay sistemi kurma
- Red-team testleri
- Audit güçlendirme

---

## 5. BAŞAK'IN GERÇEK GÜCÜ

### Ne Değil:
- ❌ Siri/Alexa gibi her şeyi bilen
- ❌ Filmdeki Jarvis gibi otonom
- ❌ Sürekli internet bağlantısı gerektiren
- ❌ Ücretli abonelik bağımlısı

### Ne:
- ✅ **Yerel çalışan** — İnternet olmasa bile çalışır
- ✅ **Ücretsiz** — Bulut modelleri ücretsiz, Ollama yerel
- ✅ **Türkçe** — Doğal Türkçe iletişim
- ✅ **Kişisel** — Sadece senin için çalışıyor
- ✅ **Güvenilir** — Hassas işlemler onay istiyor
- ✅ **Öğrenen** — Seni tanıyor, alışkanlıklarını biliyor
- ✅ **Ölçülebilir** — Ne kadar başarılı olduğunu biliyorsun
- ✅ **Kurtarılabilir** — Hata yaparsa geri alabiliyorsun

### Senaryo: Bir Günün
```
08:00 - Başak selamla: "Günaydın Furkan, bugün 3 görevin var"
09:00 - "Belgelerimi listele" → "Codex, Resimlerim, Vixrex-Secrets"
10:00 - "Bu dosyayı oku" → Dosya içeriğini gösterir
11:00 - "Not al: Toplantı saat 14:00'te" → Hafızaya kaydeder
12:00 - "Bugün hava nasıl?" → "Ankara'da 28°C, güneşli"
14:00 - "Hatırlat: Toplantı başladı" → Otomatik hatırlatma
15:00 - "Bu dosyayı sil" → "Emin misin? [Evet]/[Hayır]"
16:00 - "Bugün ne yaptın?" → "4 görev tamamladın, 2 not aldın"
```

---

## 6. ÖLÇÜM KRİTERLERİ

### Kısa Vadeli (1 Hafta)
- [ ] "Belgelerimde ne var?" → Doğal dil cevap
- [ ] "Bu dosyayı oku" → İçerik gösterimi
- [ ] "Görev ekle" → Görev kaydı
- [ ] Hata durumunda anlamlı mesaj

### Orta Vadeli (1 Ay)
- [ ] Hassas işlem onayı
- [ ] Hafızadan hatırlama
- [ ] Otomatik hatırlatma
- [ ] Kullanıcı tercihlerini öğrenme

### Uzun Vadeli (3 Ay)
- [ ] Tek dosya kurulum
- [ ] Otomatik yedekleme
- [ ] Güvenli güncelleme
- [ ] SLO takibi

---

## 7. SONUÇ

Başak bir **kişisel yerel asistan**dır. Bulut şirketlerinin yapamayacağı şeyi yapar: **tamamen senin bilgisayarında çalışır, senin verilerini dışarıya göndermez, ücretsizdir ve seni tanır.**

Profesyonel seviyeye ulaşmak için büyük değişiklikler değil, **mevcut sistemin sağlam temeller üzerine inşa edilmesi** gerekir. Her adım ölçülür, her davranış denetlenir, her hata kaydedilir.

**Başak'ın sloganı:** *"Yerel, ücretsiz, güvenilir — senin dijital kardeşin."*
