# Canli triyaj tur 1 - ekran bulgulari ve duzeltmeler

- **kim:** opencode (mimar), Casper ekran resimleriyle
- **tarih:** 2026-08-24
- **konu:** Ilk canli sohbet triyaji — 4 bulgu, 3 duzeltme, 1 model stratejisi karari
- **tip:** duzeltme
- **omur:** sonsuz
- **kaynak:** tools/reminders.py, knowledge/casper-hakkinda.md, chat.py, arac.log

## Bulgu bulgu

1. **Dosya analizi turu (18:44):** Sunum duzeltmesi CALISIYOR (ayni mesajla
   read_file/list_files sunuldu — kanitli). qwen2.5:3b sunulan araci
   KULLANMADI; uydurma "guvenlik ve gizlilik kisitlamasi" metni uretti.
   Kapı isaretsiz iddialari temizledi + YEDEK ekledi — kapı dogru davrandi.
   **Ders: zayif model + sunulan arac = hala kullanmayabilir.** Kalico
   cozum FAZ 4; ara yama adayi: dosya-sinyalli sorularda TOOL_YONLENDIRME
   guclendirme. NOT: UI'da model override (qwen secili) varken router
   mudahalesi etki etmez — kullanici "varsayilan" birakmali.
2. **"Hayir, Furkan" hitabi:** knowledge/casper-hakkinda.md:8 kaynagi.
   Casper tercihi: **"Casper de"** → not duzeltildi.
3. **"dijital ikiz kardesi" ifadesi** (:15): S1'deki "Furkan'in kardesi"
   kendini tanitma hatasinin kaynagi. Casper onayiyla netlestirildi:
   benzetme degil, asistan; kelimenin tam anlami DEGIL notu eklendi.
4. **Gun sayimi off-by-one** (reminders.py:116): saat bileseni farka
   karisiyordu (26 Agustos'a "1 gun kaldi", gercekte 2). Takvim gunu
   farkina cevrildi + 2 test.
5. **Gecmis saatli gorev etiketsizdi**: "[SAATI GECTI]" on etiketi
   eklendi (metindeki "saat HH:MM" ayiklanir) + 2 test.

## Kanit

tests/test_hatirlatma_tarihi.py (4 test) + test_dinamik_araclar.py (4 test)
+ test_yetki_tavani regresyonu yakalandi-duzeltildi (sinyal yazma aracini da
aciyordu -> salt-okunur daraltildi). Tam suite 594 yesil.

## Acik kalan

- FAZ 4 model yukseltmesi: bu triyaj en guclu gerekce oldu — qwen2.5:3b
  araci gozardi ediyor, kisisel bilgiyi yanlis aktariyor.
- Kullanci aliskanlik onerisi: UI'da model secimini "varsayilan" birakmak
  (override router'in bulut kacis yolunu kapatiyor).
