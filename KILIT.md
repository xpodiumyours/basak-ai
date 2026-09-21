# DÜZLÜK KİLİDİ — Bozulmama Sözü

Casper kararı (2026-09-21): aşağıdaki imzalı hal, çalışan düzlük sayılır.
"Gelişim" vaadiyle bu hali bozan iş reddedilir.

## İmza (2026-09-21)

- Kayıt: `c480c1d` (dal: sadelestirme)
- Hız kilidi: uçtan uca ortanca 0.38 sn, alarm 2 sn üstü (`hiz_after.txt`)
- Test: 475 geçti, 1 eski hata (`test_web_kuyruk_sayi_ve_bitir_garantisi`)
- Misafir perdesi açık, vitrin tam genişlikte

## 5 kural (ajan bunları çiğneyemez)

1. CHATBOT-YASAGI ve AGENTS.md her işe başlamadan okunur.
2. Kelimeye bakıp araç seçen kod, cevaba dokunan kod, tavan ve
   küçük/büyük model ayrımı yazılmaz (bekçi: tests/test_chatbot_yasagi.py).
3. Ekrana dokunan işte önce Casper onayı alınır.
4. Beyne dokunan işte önce/sonra `hiz_olcum.py sohbet` ölçümü yapılır.
5. Testler yeşil olmadan commit yok; sır (`ayarlar.json`, anahtar) kayda girmez.

## Değişiklik kuralı

Bu dosya, Casper açıkça "değiştir" demeden değiştirilemez.
Gevşetme teklifi sessizce değil, gerekçesiyle yazılır.
