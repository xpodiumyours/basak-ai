# ARAŞTIRMA — İŞE-GÖRE-AÇMA (kişisel kapı)

Tarih: 2026-09-12
Durum: KANITLANDI — KOD DENEYİNE İZİN
Risk sınıfı: Düşük (tek koşul; kişisel sorularda yol aynen açık)

## 1. Hedef

Kişisel profil bloğu yalnız kişisel-soruda modele gitsin:
- Kural tabanlı `_kisisel_gerekli_mi(text)` (anahtar kelime, model çağrısı YOK)
  VEYA aynı turda öğrenme/silme olduysa (`ogrenme_notu` doluysa) profil eklenir.
- Değilse profil bloğu eklenmez; anılar, geçmiş, araçlar, KISILIK aynen kalır.

## 2. Kabul kriteri

- Yeni testler yeşil: kapı birim tablosu + akış seviyesinde
  ("masaüstünde ne var" → profil YOK; "benim hakkımda ne biliyorsun" → profil VAR).
- `pytest tests -q` yeşil; `test_profil.py` DEĞİŞMEDEN yeşil.
- KISILIK'taki "sana liste verilir" cümlesi kalkar (liste yokken yalan söyler);
  blok varken aynı talimat bloğun kendi başlığında zaten vardır.

## 3. Mevcut durum kanıtı

- `chat/flow.py:187-194`: `_profil_blogu` varsa KOŞULSUZ eklenir.
- `chat/flow.py:67-94`: öğrenme/silme her turda çalışır, `ogrenme_notu` yalnız
  öğrenilince dolar.
- `memory/profil.py:blok`: başlığı "bunlari tekrar sorma" talimatını taşır
  (KISILIK'taki cümlenin karşılığı).
- `basak_app.py:71-73`: "Sana ayrıca ... liste verilir" — liste gelmeyen
  turda yanlış öncül.
- Akışta profil varlığını pinleyen test YOK (grep kanıtı).

## 4. Sorun kanıtı

Profil bloğu tavansız (0-~5000 harf) ve her tura girer; kişisel-olmayan
soruda (dosya/web/sohbet) saf yük + gizlilik sızıntısıdır. Çizgi (soru başına
kişisel tavan) bunu yasaklar.

## 5. Dış referans

- OpenAI prompt-eng: ilgili bağlamı al-koy (RAG); sabit başta, değişken sonda.
- Kimi best practice: her turda yalnız gereken araç/bilgi.
- Mem0/Letta deseni: karar kodda, modelde değil.

## 6. Doğrulanan gerçekler

- Öğrenme kalıpları (`ogren`/`unut`) profil yazma yoludur; tetiklenmeleri
  kişisel tur demektir → VEYA kuralı kaçakları kapatır.
- Anılar (episodik) bu pakette AÇIK kalır (görev sürekliliğine yarar;
  kapatılması ayrı ölçüm ister).

## 7. DOĞRULANAMADI

- Anahtar listesinin kapsama oranı (kişisel soru ıskalarsa model yanıtsız
  kalmaz — profil yokluğunda genel cevap verir; canlı FAZ2 bataryası ölçecek).

## 8. İzin verilen kapsam

- `chat/flow.py`: `_kisisel_gerekli_mi` yardımcısı + ekleme koşulu +
  öğrenme-VEYA kuralı.
- `basak_app.py` KISILIK: 2 cümle silinir (liste-vaadi).
- YENİ `tests/test_kisisel_kapi.py`.

## 9. Yasak kapsam

- `memory/profil.py`, anılar bloğu, geçmiş penceresi, tool seti, secici,
  KISILIK'ın geri kalanı — dokunulmaz.
- Az-göster seçici (0-3), unutma kanıtı — sonraki paketler.

## 10. Korunacak davranışlar

- Kişisel soruda profil aynen gelir (blok + başlık talimatı).
- Öğrenme/silme yazma yolu her turda çalışır.
- `TOOL_YONLENDIRME` + `KIMLIK` ilk mesajda kalır.

## 11. Risk sınıfı

Düşük.

## 12. Kabul sensörleri

Yeni testler + `pytest tests -q` + `py_compile`.

## 13. Geri alma koşulu

Kişisel soruda profil düşerse veya paket-dışı test kızarırsa geri alınır.

## 14. Sonuç (2026-09-12 uygulandı)

- `_kisisel_gerekli_mi` + VEYA kuralı `flow.py`'de; KISILIK liste-vaadi kalktı
  (blok başlığı talimatı korur).
- Yeni `tests/test_kisisel_kapi.py` 21/21 yeşil; tam paket 592 geçti / 0 hata.
- Anılar bloğu bilerek açık bırakıldı (görev sürekliliği; ayrı ölçüm ister).
- KANITLANDI → paket tamamlandı (commit bekliyor).
