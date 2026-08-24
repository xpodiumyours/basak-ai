---
kim:    opencode
tarih:  2026-08-24
konu:   ANA YOLA GEÇİŞ — orkestra_ana_yol açıldı (Casper kararı)
tip:    karar
omur:   sonsuz
kaynak: chat.py mesaj_isle + brain/orkestra.py kos(sistem=...) + ayarlar.json
---

ORKESTRA artık ÜRETİM ANA YOLU. "orkestra_ana_yol": true.

Dürüst kayıt: gölge mod ilkesi "birkaç günlük benzerlik dağılımı toplanır"
diyordu; Casper geçişi bilerek öne aldı (2026-08-24, aynı gün). Gölge
log'u o günden itibaren yine de birikmez — ana yolda golge_kos sessizce
atlanır (öz-eşdeğerlik ölçümü anlamsız).

Geçişten ÖNCE kapatılan iki üretim boşluğu:
1. Anahtar hiçbir yere bağlı değildi — mesaj_isle artık orkestra_aktif_mi()
   ile durum makinesine yöneliyor (test_orkestra_yol.py 3 yeni test).
2. Kişilik promptu modele gitmiyordu (sabit "SYS") — kos(sistem=...)
   ile KISILIK aynen taşınıyor; canlı prova: "Ben Başak, Furkan'ın
   kardeşi..." kimlikli cevap groq üzerinden geldi.

GERİ DÖNÜŞ: ayarlar.json'da "orkestra_ana_yol": false — tek satır,
eski yol kodda duruyor.

KANIT: 496+ test yeşil; canlı prova çıktısı deftere işlendi.
