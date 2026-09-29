# KVKK ENVANTERİ — Başak Web (taslak)

**Tarih:** 2026-09-28 · **Durum:** TASLAK — yayın öncesi avukata gösterilecek
**Dayanak:** 6698 sayılı Kişisel Verilerin Korunması Kanunu (KVKK) m.10
(aydınlatma yükümlülüğü) ve m.4 (veri sorumlusu).

> Bu envanter, Başak'ın **web sürümünde** (Vercel) hangi kişisel verileri
> işlediğini dürüstçe listeler. Amaç: avukatın çalışacağı gerçek envanter
> olsun; pazarlama metni değil.

## 1. Veri sorumlusu

- **Sahip:** Casper (xpodiumyours) — iletişim: depo üzerinden.
- **İşleyen:** Vercel Inc. (barındırma, ABD), sağlayıcı AI şirketleri (aş. 3).

## 2. İşlenen veriler

| Veri | Nerede tutuluyor | Süre | Yasal dayanak | Not |
|---|---|---|---|---|
| **Basak ID** (kayıtsız, cihaz/tarayıcıya bağlı `u` ile başlayan 16 haneli anonim kimlik) | Kullanıcının tarayıcısı + geçici sunucu deposu | Oturum + hafıza süresince | Hukuka uygunluk / meşru menfaat | Kişi adı E-posta **istemez**; anonimleştirilmiş tanımlayıcıdır |
| **Sohbet geçmişi** | Vercel geçici dosya sistemi + tarayıcı | geçici (kalıcı değil) | Açık rıza (hizmetin ifası) | Silinirse sohbet biter |
| **Kalıcı hafıza notları** | memory/ (sunucuda geçici; masaüstünde kalıcı) | Kullanıcı silene kadar | Açık rıza | Kullanıcı "hafızayı temizle" diyebilir |
| **Görsel ekler (fatura/fotoğraf)** | Geçici dosya | iş bitince | Açık rıza | analiz sonrası saklanmaz (varsayılan) |
| **IP / günlük verisi** | Vercel altyapısı | kısa süre (Vercel politikası) | Meşru menfaat (güvenlik, kota) | Başak tarafından ayrı saklanmaz |
| **Anonim günlük kota sayacı** (Basak ID + sayaç) | basak_kota tablosu (Postgres) / bellek | gün sonunda sıfırlanır | Meşru menfaat (hizmetin sürdürülebilirliği) | Mesaj içeriği değil, yalnız sayaç |
| **Sağlayıcıya giden mesaj** | AI sağlayıcısının sunucusu | sağlayıcının politikası | Açık rıza | **Ayrıntı:** hangi sağlayıcı, nereye gidiyor → README §12 + s.3 |

## 3. Yurt dışına veri aktarımı (KVKK m.9)

Mesaj, beyin için **AI sağlayıcılarının sunucularına** gider (ABD/uluslararası).
Dayanak: açık rıza (m.9/2-a). Sağlayıcı listesi ve veri kartları:

| Sağlayıcı | Ücretsiz katman | Not |
|---|---|---|
| Groq | var | ölçülen en hızlı |
| Google Gemini | var | |
| Cloudflare Workers AI | var | |
| Kilo Gateway | var | kayıt tutabilir (README §12'de açıkça belirtildi) |
| NVIDIA NIM · GLM · OpenRouter · Cohere · Mistral | var | sırayla yedek |

Kullanıcı, sohbet ekranındaki "Ayrıntılar" bağlantısından bu listeyi görür.

## 4. Çerez ve izleme (plan Faz 3)

| Amaç | Durum |
|---|---|
| Zorunlu çerez (oturum/Basak ID) | hizmetin çalışması için şart |
| Analitik (ör. Google Analytics) | **onay sonrası** — onaysız yüklenmez |
| Reklam (AdSense) | **onay sonrası** — onaysız reklam kodu çalışmaz |

Kural: **çerez onay kutusu → sonra üçüncü taraf kod.** Onay geri alınabilir
(alt bilgide "çerez tercihleri").

## 5. Kullanıcı hakları (KVKK m.11)

Kullanıcı şunları isteyebilir: hangi veri işleniyor, düzeltme, silme,
işlemeye itiraz, aktarım. Başak web'inde bu talepler için:

- **Hafıza temizleme** → sohbet panelinde (mevcut "temiz hafıza" işi).
- **Tam silme talebi** → iletişim adresi (depo/iletişim) — 30 gün içinde
  yanıtlanır (KVKK süresi).

## 6. Güvenlik önlemleri (m.12)

- Anahtarlar git'te değil; Vercel ortam değişkeni.
- `.env`/`ayarlar.json` dosya kara listesi (`YASAK_DOSYA_KALIPLARI`).
- Çıktı maskeleme (`_kirmala`): api_key/token/parola desenleri `***`.
- SSRF beyaz listesi; yol güvenlik testleri (`tests/test_path_guvenligi.py`).
- Denetim kaydı (`data/audit/audit.log`).

## 7. Yapılacaklar (yayın öncesi kapı)

1. Bu envanterin avukat tarafından onaylanması/güncellenmesi.
2. Türkçe **Aydınlatma Metni** sayfası (Faz 3 taslağı — bu dosyadan üretilir).
3. **Çerez politikası + onay kutusu** (Faz 3).
4. Yurt dışı aktarım bölümünün sağlayıcı kartlarıyla eşitlenmesi.
5. Veri ihlali prosedürü (kiminle iletişime geçilir, 72 saat) — küçük bir
   bölüm olarak eklenmeli.
