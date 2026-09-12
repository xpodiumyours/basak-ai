# ARAŞTIRMA — SABİT DAVRANIŞ KURALLARI (kişisel kapı düzeltmesi)

Tarih: 2026-09-12
Durum: KANITLANDI — KOD DENEYİNE İZİN
Risk sınıfı: Düşük (3 kısa cümle; her turda zaten var olan talimatın garantisi)

## 1. Hedef

Kullanıcı itirazı doğrulandı: profil SADECE olgu değildir; davranış kuralları
(kısa-net, teknik-terimsiz, sonucu-önce, ücretsiz-önce) her turda lazımdır ve
bugün modele GÜVENİLMEZ yoldan gidiyordu (knowledge önbelleğinde kesinti
piyangosu: 2000 harf bütçe INDEX+casper parçasıyla dolar, kural bölümü
dışarıda kalabilir). Çözüm (Letta-persona deseni): 3 sabit cümle KISILIK'e
yazılır — her turda gider, değişmez, önbellek dostudur. Olgu listesi kapılı
kalmaya devam eder.

## 2. Kabul kriteri

- Kişisel-olmayan turda davranış cümleleri mesajlardadır (test pinler).
- Olgu bloğu kapısı aynen çalışır (`test_kisisel_kapi` yeşil kalır).
- `pytest tests -q` yeşil.

## 3. Mevcut durum kanıtı

- `knowledge/casper-hakkinda.md` "Nasıl konuşulmalı" + "Çalışma ilkeleri"
  bölümleri: kısa-net-Türkçe, teknik-terimsiz, sonucu-önce, ücretsiz-önce,
  ekleme-yapma.
- `_load_knowledge` bütçe aritmetiği: 936 + ~1064 kesit → kural bölümleri
  güvenilmez (dışarıda kalabilir).
- Üretim profil deposu BUGÜN küçüktür (ad + 1 tercih) — kapı bugünkü yükü
  değil, büyüme yönünü kilitler; davranış kuralları ise bugünden lazımdır.
- Letta: persona bloğu küçük-sabit-pinned; human bloğu retrieved. OpenAI:
  sabit içerik başta.

## 4. Sorun kanıtı

Kapı, olguyla birlikte davranış kurallarının TEK güvenilmez yolunu da
kesmedi (yol zaten kesikti) — ama kullanıcı itirazı haklı: kurallar garanti
altına alınmadan kapı eksik kalır. Bu paket garantiyi verir.

## 5. Dış referans

Letta core-memory (persona pinned), OpenAI sabit-başta kuralı, Kimi az-bilgi
deseni (önceki araştırma dosyaları).

## 6. Doğrulanan gerçekler

Yukarıdaki dosya/satır okumaları + üretim DB profil içeriği (ad+1 tercih).

## 7. DOĞRULANAMADI

- Kural cümlelerinin her model ailesinde aynı etkiyi vereceği (FAZ2
  bataryası ölçecek; cümleler kısa ve sade tutuldu).

## 8. İzin verilen kapsam

- `basak_app.py` KISILIK: 3 kısa cümle eklenir.
- `tests/test_kisisel_kapi.py`: kişisel-olmayan turda davranış cümlesi
  iddiası (gerçek KISILIK ile).

## 9. Yasak kapsam

- Kapı mantığı, profil deposu, anılar, kısa-uzun dengesi (`YETERINCE
  DETAYLI` ↔ kısa-net gerilimine DOKUNULMAZ — ayrı konu).
- `casper-hakkinda.md` dosyası — dokunulmaz.

## 10. Korunacak davranışlar

- Olgu kapısı, öğrenme yolu, tool seti, KISILIK'ın geri kalanı aynen.

## 11. Risk sınıfı

Düşük.

## 12. Kabul sensörleri

Yeni iddia + `pytest tests -q` + `py_compile`.

## 13. Geri alma koşulu

Normal turlarda ton/uzunluk gerilerse (canlı FAZ2 bataryası) cümleler
geri alınır.

## 14. Sonuç (2026-09-12 uygulandı)

- KISILIK'e 3 sabit cümle eklendi; kapı/olgu yolu aynen duruyor.
- Yeni iddia dahil `test_kisisel_kapi.py` 22/22; tam paket 593 geçti / 0 hata.
- KANITLANDI → paket tamamlandı (commit bekliyor).
