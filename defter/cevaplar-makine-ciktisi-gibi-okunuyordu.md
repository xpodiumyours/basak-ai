---
kim:    claude
tarih:  2026-08-23
konu:   Cevaplar makine ciktisi gibi okunuyordu
tip:    olcum
omur:   30g
kaynak: olcum
---

Sorun: cikis kapisi dogru calisirken cevaplar makine ciktisi gibi okunuyordu — [O] cumlesi birebir alinti zorunlu kildigi icin model butun arac ciktisini tirnak icine yapistiriyordu. Once yalniz prompt degistirildi (kisa alinti + kendi cumlen); model kurali YOK SAYDI, olcumle dogrulandi. Yani prompt yetmiyor, bicim degisikligi gerekti.

Yapilan uc sey:
1. Yeni isaret [Y] YANIT (olcu.py + OLCU.md + ui/app.js + style.css): ayakta kalan bir [O]/[A] varsa sade Turkce cevap cumlesi de gecer. Yeni olgu tasimaz; dayanagi duserse kendisi de duser. [B] tek basina [Y]yi ayakta tutmaz.
2. Kapi her cumleyi elediginde kullanici bos ekran gormesin: gercekten alinmis olcum varsa ham hali gosteriliyor (olcu.ham_olcum_satirlari + chat.py). Bu satirlari MODEL degil KOD uretiyor, birebirligi tanim geregi kesin.
3. PROMPT_BLOGU ve OLCU_YONLENDIRME: once [Y] cevap, altina kanit satirlari.

Olcum (ayni soru 6 kez, gercek zincir): 4/6 sade cevap + kanit, 2/6 "Bunu olcemedim". 2 basarisiz turda sebep KAPI DEGIL — model git_durum aracini hic cagirmadi, dolayisiyla gosterilecek olcum de yoktu. Bu, Ö-1de yazili bilinen sinirin (arac cagirma prompta bagli) tekrari.

Yeni gozlem, ayri ariza: bir turda nvidia saglayicisi dusunme metnini dogrudan cevaba sizdirdi ("We need to answer with the rules..."). Isaretsiz cevaplar kapidan toptan gectigi icin bu metin kullaniciya ulasti. Ayri is olarak ele alinmali.

Risk notu: promptu uzattim; arac cagirma sikligina etkisini olcmedim (oncesi icin temiz bir taban olcumum yok).

Kanit: 247/247 test yesil (10 yeni test: TestYanit, TestHamOlcum).
