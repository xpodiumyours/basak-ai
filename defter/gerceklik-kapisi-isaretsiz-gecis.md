---
kim:    opencode
tarih:  2026-08-23
konu:   Gercelik kapisinda isaretsiz gecisin sinirlandirilmasi
tip:    karar
omur:   sonsuz
kaynak: kod incelemesi + tests/test_gerceklik_kapisi.py
---

Casper'in buldugu ucuncu guvenlik acigi: cikis kapisinda hicbir isaret yoksa
metin "sohbet/nezaket" varsayimiyla TAMAMEN denetimsiz geciyordu. Varsayimin
kendisi kontrol edilmiyordu; model isaretsiz uydurma olgu yazarak kapinin
kose tasini dolaşabiliyordu.

Cozum (`olcu.py`): serbest gecis iki istisna ile sikildi —
1. Araç koşan turda serbest gecis YOK: tüm cümleler denetlenir; işaretsiz
   cevap tamamen elenince chat.py zaten ham ölçüm satırlarını basiyor
   (kod üretir, birebirlik garantili).
2. Araçsız turda düz sohbet yaşar AMA cümle ölçü-alanı sinyali taşıyorsa
   elenir: proje adları (vixrex/numeramatch/xses), commit-hash benzeri
   token (7+ hex karakter), eylem iddiası ([B] denetimiyle aynı tablo).

Böylece küçük modelin işaretsiz sohbeti öldürülmeden, kaçak olgu/eylem
cümleleri kapıda kalıyor.

KANIT: 9 yeni test (tests/test_gerceklik_kapisi.py): araçlı turda işaretsiz
cevap elendi; proje adı/hash/eylem iddiası araçsız turda yakalandı; saatli/
planlı sıradan konuşma yanlış pozitif olmadan yaşadı; karışık cevapta
tehlikeli cümle ölüp sohbet satırları kaldı. Bir eski testin örnek cümlesi
(eylem fiili içerdiği için artık eleniyordu) nötr sohbet örneğiyle
güncellendi — iddia zayıflatılmadı. Toplam 287/287 yesil.

Bilinen sinir: sinyal listesi kapalı bir küme — listede olmayan konu adlarında
işaretsiz uydurma hâlâ geçebilir (genel sayı/olgu taraması bilinçli eklenmedi;
sohbeti öldürür). Yeni proje eklendiginde _PROJE_ADLARI güncellenmeli.
