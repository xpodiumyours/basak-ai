---
kim:    opencode
tarih:  2026-09-10
konu:   basak
tip:    karar
omur:   sonsuz
kaynak: Casper onayi ("AC") + pytest (504 yesil) + canli dogrulama (gercek klasor listesi)
---

Casper yeni aklin acilmasina onay verdi. ayarlar.json'da orkestra_ana_yol false'tan true'ya cevrilmistir (geri donus tek satir). Acilis, kapaliyken gorunmeyen bir kural ihlalini ortaya cikardi: orkestra yolu kayitli model adini (qwen2.5:7b) yerelde hicbir sey kurulu degilken bile zincire tasiyordu; tam bulut durumunda zincirin None almasi gerekir (2026-08-24 Ollama-bagimsizlik kurali). _chat_legacy.py'de _yerel_model_sec yardimcisi eklendi, aday_uret ve deney_kos artik onu kullaniyor; ilgili deneme tekrar yesil. Canli dogrulama acik yolda gecti ("Klasor okunuyor... belgeler", 4 klasor dogru). Tam suite 504 yesil, 7 atlanan (canli hat).
