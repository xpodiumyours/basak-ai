---
kim:    opencode
tarih:  2026-08-23
konu:   Arac cagirma disiplini TABAN olcumu (defter madde 3)
tip:    olcum
omur:   30g
kaynak: _taban_olcum.py + _taban_olcum_sonuc.json (gercek zincir)
---

Bekleyen-isler maddesi 3: prompt degisiklikleri kiyaslanamiyordu cunku arac
cagirma disiplininin referans sayisi yoktu. Bu kayit o referansi kurar.

YONTEM: ayni soru ("VixRex'te durum ne?") gercek zincirde 10 kez soruldu,
aralarinda 8 sn bekleme; her turda hangi aracin kostugu executor sarilarak
sayildi. Kanit: _taban_olcum_sonuc.json (tur tur cevaplar).

SONUC (2026-08-23 aksam):
- ARAC CALISTI      : 3/10  (%30)  <- TABAN ORANI
- DURUST RED        : 6/10  — hic olcmedi ama "[B] Bunu olcemedim" diye dogru soyledi
- OLÇUMSUZ BILGI    : 1/10  — Tur 7: "Commit edilmemis iki dosya var..."
                              hic olcmedigi halde BILGI aktardi; bilgiyi o
                              turun gecmisindeki eski git_durum ciktilarindan
                              ezbere soyledi (en tehlikeli tur)
- SAGLAYICI HATASI  : 0/10  — zincir devirdaimi calisti

YAN BULGULAR:
1. groq ilk istekte 413 TPM hatasi verdi: "Requested 9313 / Limit 8000".
   Prompt+bilgi+gecmis yigini artik tek basina groq'un dakikalik sinirini
   asiyor — baglam kucultme ihtiyacini sayisal olarak kanitlar.
2. glm tekrarlayan timeout, cohere tekrarlayan hata — ikisi de her turda
   elendi, yuk nvidia+kilo'ya bindi.
3. Tur suresi 5-56 sn arasi (devirdaim gecikmeleri dahil).

KIYAS KURALI: bundan sonra prompt degisikliginden sonra ayni script kosulur;
yeni oran bu %30 ile karsilastirilir. Hedef: ARAC_CALISTI oranini yukseltmek,
OLCUMSUZ turu sifira indirmek.

Bilinen sinir: orneklem 10 tur tek soru — gun/saglayici dagilimina gore
degisebilir; taban "o andaki gercek durum" olarak okunmali.
