# ARAŞTIRMA — GLM VARSAYILANI 4.7-FLASH YÜKSELTME

Tarih: 2026-09-12
Durum: KANITLANDI — KOD DENEYİNE İZİN
Risk sınıfı: Düşük (tek varsayılan dizesi; geri dönüş tek satır)

## 1. Hedef

`brain/glm.py` varsayılanı `glm-4.5-flash` → `glm-4.7-flash`.

## 2. Kabul kriteri

- Canlı tek çağrıda ldap: auth + tool_call + geçerli argüman (YAPILDI,
  2026-09-12: 9.0 sn, `finish_reason=tool_calls`,
  `{"query":"İstanbul hava durumu güncel"}`).
- `pytest tests -q` yeşil.

## 3. Mevcut durum kanıtı

- Resmi fiyatlandırma (`docs.z.ai/guides/overview/pricing`): GLM-4.7-Flash
  giriş/çıkış/önbellek Free; Z.ai web-arama $0.01/kullanım (KAPALI kalır).
- Canlı prob: yukarıda. thinking=disabled ile çağrıldı (mevcut hız politikası
  korunur; açık düşünme ayrı ölçüm ister).
- Aile çözümleyici `glm-4.7-flash` → `glm-flash` verir (kural tabanlı,
  alt-dizgi); kapasite güçlüde kalır.

## 4. Sorun kanıtı

4.5-Flash eski nesil; 4.7-Flash ücretsiz katmanda güncel önerilen modeldir.
Değişiklik tek dizedir.

## 5. Dış referans

Yukarıdaki fiyatlandırma sayfası + canlı prob çıktısı.

## 6. Doğrulanan gerçekler

- `brain/harness.py:156` yeni adı da yakalar (`glm`+`flash` kolu) — değişiklik
  gerekmez.
- Aile/kapasite testlerindeki `4.5-flash` dizgileri ÇÖZÜCÜ test verisidir;
  varsayılanla ilişkisizdir, korunur.

## 7. DOĞRULANAMADI

- 4.7-Flash'in uzun vadeli kota davranışı (karne izleyecek).
- Z.ai web-arama (ücretli — kapalı kalır).

## 8. İzin verilen kapsam

- `brain/glm.py` MODELLER iki dizesi + modül docstring model adı.

## 9. Yasak kapsam

- Timeout, thinking politikası, sıcaklık, tavan, sıra — dokunulmaz.

## 10. Korunacak davranışlar

- Tool şeması akışı, fallback zinciri, karne aynen.

## 11. Risk sınıfı

Düşük.

## 12. Kabul sensörleri

Canlı prob + `pytest tests -q` + auditte ilk 24 saat izleme.

## 13. Geri alma koşulu

401/404/429 artışı veya araç-bozukluğu görülürse tek satır geri alınır.

## 14. Sonuç (2026-09-12 uygulandı)

- Varsayılan `glm-4.7-flash` oldu; tam paket 616 geçti / 0 hata.
- KANITLANDI → paket tamamlandı (commit bekliyor).
