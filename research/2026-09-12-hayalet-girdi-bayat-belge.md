# ARAŞTIRMA — HAYALET GİRDİ + BAYAT BELGE (sıfır-davranış paketi)

Tarih: 2026-09-12
Durum: KANITLANDI — KOD DENEYİNE İZİN
Risk sınıfı: Düşük (çıktı birebir aynı; kanıtı aşağıda)

## 1. Hedef

1. `_load_knowledge` içindeki `AGENTS.md` girdisini listeden çıkarmak.
2. `AGENTS.md §0` içindeki bayat model adını (`llama-3.3-70b`) güncellemek.

## 2. Kabul kriteri

- `_load_knowledge()` çıktısı değişiklik öncesi/sonrası BİREBİR aynı (testle pinlenir).
- `pytest tests -q` yeşil.

## 3. Mevcut durum kanıtı

- `knowledge/` dosyaları: INDEX 936 + casper-hakkinda 3296 + takvim 478 = 4710
  harf; bütçe `KNOWLEDGE_EMBED_CHARS=2000`. Okuma sırası: INDEX (936, kalan
  1064) → casper-hakkinda (1064 harfe kırpılır, kalan 0) → DÖNGÜDEN ÇIKILIR.
  `takvim-*.md` ve `AGENTS.md` satırına HİÇ GELİNMEZ. Yani AGENTS girdisi
  ölüdür; çıkarılması çıktıyı değiştiremez.
- `AGENTS.md §0`: "Groq'a (ücretsiz, `llama-3.3-70b`) kaçış" — kodda
  (`brain/groq.py` MODELLER) `openai/gpt-oss-20b/120b` var. Belge bayat.

## 4. Sorun kanıtı

Ölü girdi + bayat belge = yeni ajanı/kodu yanlış yönlendirme riski. Davranış
etkisi yok (yukarıdaki aritmetik).

## 5. Dış referans

Gerekmez (iç aritmetik + kod okuma yeterli).

## 6. Doğrulanan gerçekler

Dosya boyları diskten okundu; okuma sırası koddan izlendi.

## 7. DOĞRULANAMADI

Yok.

## 8. İzin verilen kapsam

- `_chat_legacy.py`: `for ad_ek in ("AGENTS.md",)` bloğunun silinmesi.
- `AGENTS.md §0`: model adı düzeltmesi.
- YENİ test: `_load_knowledge` çıktısının AGENTS içermediği + beklenen
  parçaları içerdiği (sahte knowledge diziniyle).

## 9. Yasak kapsam

- Okuma SIRASI değişikliği (casper-hakkinda öne alma) — FAZ2 paketi, YOK.
- Bütçe (`2000`) değişikliği — YOK.
- `context.py`, promptlar, tool seti — dokunulmaz.

## 10. Korunacak davranışlar

- Açılış knowledge önbelleği birebir aynı (test pinler).
- `chat/__init__` dışa aktarımı değişmez.

## 11. Risk sınıfı

Düşük.

## 12. Kabul sensörleri

Yeni ünite testi + `pytest tests -q` + `py_compile`.

## 13. Geri alma koşulu

Önbellek çıktısı farklılaşırsa veya test kızarırsa geri alınır.

## 14. Sonuç (2026-09-12 uygulandı)

- AGENTS girdisi kalktı; §0 model adları güncellendi (qwen2.5:7b + gpt-oss zinciri).
- Yeni `tests/test_knowledge_kapsama.py` 2/2 yeşil (koleksiyon sırası + README
  detayı ilk denemede yakalanıp düzeltildi).
- Tam paket 571 geçti / 0 hata. Önbellek çıktısı birebir aynı.
- KANITLANDI → paket tamamlandı (commit bekliyor).
