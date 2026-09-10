---
kim:    opencode
tarih:  2026-09-10
konu:   basak
tip:    karar
omur:   sonsuz
kaynak: Casper karari + canli dogrulama + pytest (514 yesil)
---

Casper "kalip istemiyorum, chatbot oldu" dedi. Budama: TOOL_YONLENDIRME'deki cumle-esleme listesi (HEMEN CAGIR'lar) ve OLCU_YONLENDIRME'deki 6 adimlik zorunlu akis, yetenek+ilke metnine indi (KISILIK'teki "sorarsa bunlari say" listesi de dahil — model listeyi papağan gibi okuyordu). Guvenlik/olcum kodda duruyor, prompta tasinmadi. Kaybolan disiplini koda tasimak icin mekanizma: kesif sorusu gozlemsiz cevapla gelirse TEK durtme (orkestra_bilesenleri.aday_uret; _dosya_islemi_sinyali karar verir, cumle listesi degil). Ayrica kesif fiilleri sinyale eklendi (dolas/gez/gorebiliyorsun/bilgisayarda/etraf). Canli kanit: "dolas" sorusu reddedilmeden gercek gozlemle dondu (knowledge/ 4 dosya, Kaynaklar satirli). Yan bulgu: tam suite bir kosuda 5 threading takilmasi verdi, tekrarda 514 yesil (test_yapi_threading yalniz 2/2). UI onbellek sorunu icin style/app/head baglantilarina surum eklendi (?v=20260910c).
