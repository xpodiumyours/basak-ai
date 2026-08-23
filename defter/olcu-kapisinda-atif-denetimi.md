---
kim:    claude
tarih:  2026-08-23
konu:   Olcu kapisinda atif denetimi
tip:    olcum
omur:   30g
kaynak: olcum
---

Cikis kapisindaki (olcu.py) atif bosluğu kapatildi. Eski davranis: [O] cumlesi icin alinti O TURUN HERHANGI bir arac ciktisinda geciyorsa yasiyordu — cumlenin adini verdigi arac denetlenmiyordu.

Gercek ariza (2026-08-23 olcumu): "Basak brain klasorunde hangi dosyalar var" sorusunda list_files o klasore bakamiyor (izin yalniz knowledge + research-engine). Buna ragmen Basak uc dosya adi sayip [O] rozeti takti; metin baska bir aracin ciktisinda geciyordu. Gercekte brain klasorunde 17 dosya var. Yani "olctum" rozeti YANLIS cevaba takilabiliyordu.

Duzeltme: chat.py _tool_calling_multi artik (arac_adi, cikti) ciftleri donduruyor; cikis_kapisi bu bicimi alinca atif da denetliyor — cumlenin adini verdigi arac o turda calismamissa ya da alinti o aracin ciktisinda gecmiyorsa cumle eleniyor. Duz metin listesi verilirse eski davranis korunuyor (geri uyum). Aracin hata/izin ciktisini durustce alintilamak mesru sayiliyor. PROMPT_BLOGU'na da kural eklendi.

Yakalanan ikinci hata: normalize dongusunde dongu degiskeni fonksiyonun kendi "metin" parametresini eziyordu — cevap yerine son arac ciktisi denetleniyordu. cikti olarak yeniden adlandirildi.

Kanit: 237/237 test yesil (6 yeni test, tests/test_olcu.py TestAtif). Gercek agda ayni soru tekrar soruldu — Basak artik "brain klasorune erisim iznim yok, sadece knowledge ve research-engine" diyor ([B] ile). Kontrol sorulari (git_durum, list_tasks) bozulmadan calisiyor.
