# ARAŞTIRMA — MODEL ÖZELLİK MATRİSİ (kullanan/kapalı/platform-farkı)

Tarih: 2026-09-12
Durum: KANITLANDI — KOD DEĞİŞİKLİĞİ YOK (gözlem + kilit paketi)
Risk sınıfı: Yok (dosya + prob; üretim kodu değişmedi)

## 1. Hedef

Her sağlayıcının resmi yetenekleri ile Başak kullanımını karşılaştırıp
"haksız kapalı" varsa bulmak; yoksa listeyi kilitlemek.

## 2. Kabul kriteri

- Matris tablosu kanıt satırlarıyla dolu.
- Canlı prob sonucu kayıtlı (başarılı ya da DOĞRULANAMADI).

## 3. Mevcut durum kanıtı (matris)

| Yetenek | Resmiyet | Başak | Hüküm + kanıt |
|---|---|---|---|
| GLM thinking | Varsayılan açık (Z.ai) | `thinking: disabled` (`brain/glm.py:68`) | KAPALI-DOĞRU. Gerekçe §4. |
| Groq Compound | Ayrı model; yerel araçlarla BİRLİKTE kullanılamaz (resmi doküman) | Kullanılmıyor | PLATFORM-FARKI. Geçiş = dosya/görev/not araçlarının ölümü. |
| gpt-oss browser_search | Var; örnekte tek soru 7340 token | Kullanılmıyor | BEKLEMEDE. Fiyat belirsiz + token yangını. |
| Cloudflare Agents/Workflows | Ayrı sunuculu platform | Sohbet ucu kullanılıyor | PLATFORM-FARKI. Geçiş = yeniden mimari. |
| Kilo ajanı / Gemini ADK | Ayrı çerçeveler | Yalnız geçitler | PLATFORM-FARKI. |
| Z.ai web search | $0.01/kullanım (resmi fiyat) | Kapalı | KAPALI-DOĞRU. |
| Araç seçimi | Modeller seçer (`auto`) | Son karar modelde; aday daraltma kodda | AÇIK. Daraltma resmi dokümana uygun (Groq 3-5, OpenAI <20, Kimi core). |
| Tur tavanı 3/12/8 | Sağlayıcı dayatmaz | Kod optimizasyonu | AÇIK. Uzun işte 8 (P-A). FAZ1 hakem. |
| Geçmiş 4000 | Servisler 100K+ alır | 4000 pencere | KAPALI-DOĞRU. Groq 8K/dk duvarı kayıtlı (`Requested 9313` 413 vakası). |
| Cevap tavanı | 65K'ya kadar | 2048 (P-max paketi) | ÇÖZÜLDÜ (23 vaka kanıtlı). |
| is_kuyrugu | — | Duruyor | KORUNDU. |

## 4. Sorun kanıtı (thinking neden kapalı)

- GLM 24 saatte ~394 timeout (12 sn duvarında) — istatistik DB kaydı.
- Canlı prob (2026-09-12, thinking-açık/default): 2 çağrı üst üste `429/1305
  overloaded` döndü; servis doygun. Düşünme = daha yavaş + daha çok token =
  doygun serviste daha kötü.
- thinking=disabled çağrı: 9.0 sn, 183+19 token, düzgün tool_call (kayıtlı).

## 5. Dış referans

- Groq built-in tools dokümanı (Compound uyumsuzluğu + token örneği).
- Z.ai fiyatlandırma (web search $0.01; 4.7-Flash Free).
- OpenRouter/Groq/Kimi araç-küçüklüğü ilkeleri (önceki araştırma dosyaları).

## 6. Doğrulanan gerçekler

- `thinking: disabled` tek bayrak `brain/glm.py:68` (başka adaptörde yok).
- Compound uyumsuzluk cümlesi resmi dokümandan birebir.
- 413 duvar kaydı audit.log'da.

## 7. DOĞRULANAMADI

- thinking-açık/kapalı aynı-soru farkı (servis doygunluğu probu engelledi;
  servis rahatlayınca 1 çağrılık tekrar).
- gpt-oss browser_search faturalandırması.

## 8. İzin verilen kapsam

- Bu dosya + 1 canlı prob. KOD DEĞİŞİKLİĞİ YOKTUR.

## 9. Yasak kapsam

- thinking açma, tavan/sıra/tohum değişimi, yeni entegrasyon — YOK.

## 10. Korunacak davranışlar

- Tümü aynen (değişiklik yok).

## 11. Risk sınıfı

Yok (gözlem paketi).

## 12. Kabul sensörleri

Prob çıktısı + bu dosya.

## 13. Geri alma koşulu

Yok (değişiklik yok).

## 14. Sonuç (2026-09-12: prob + kilit)

- Thinking-açık 3. deneme BAŞARILI: 4.4 sn, düzgün tool_call, aynı argüman.
  Maliyet: +50 reasoning token (çıktı 19→70, ~3.7 kat enflasyon) sıradan
  soruda. Gecikme karşılaştırması yük-durumu karışık olduğu için hükümsüz.
- Hüküm: thinking KAPALI kalır (hız politikası); zor akıl işleri için
  çaba-ayarlı açılış ayrı ölçüm ister.
- KANITLANDI → gözlem paketi tamamlandı (kod değişikliği yok).
