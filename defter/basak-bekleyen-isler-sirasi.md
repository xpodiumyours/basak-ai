---
kim:    claude
tarih:  2026-08-23
konu:   Basak bekleyen isler sirasi
tip:    karar
omur:   30g
kaynak: olcum
---

23 Agustos 2026 aksami itibariyla Basak icin bekleyen isler, oncelik sirasiyla. Sira olcumden cikti, tahminden degil.

1. [B] CUMLELERI DENETLENMIYOR — GUVEN ISI, EN ONCELIKLI.
Model yapmadigi isi "yaptim" diyebiliyor. Gercek tur: "[B] Bu bilgi VixRex son commit basligiyla deftere kaydedildi" dedi; git status defter/ BOS, hicbir kayit yoktu. Sebep: [B] "bilmiyorum" icin tasarlandi, kapidan serbest geciyor, icerigi denetlenmiyor; model onu serbest metin gibi kullaniyor. Cozum yonu: [B] cumlesi bir EYLEM iddiasi tasiyorsa (kaydedildi, eklendi, silindi, gonderildi) o turda ilgili aracin GERCEKTEN calistigi dogrulanmali; calismadiysa cumle elenmeli.

2. MODEL ARACI HIC CAGIRMIYOR (turlarin bir kismi).
Ayni soru 6 kez soruldu: 4 turda git_durum cagrildi, 2 turda hic cagrilmadi ve cevap "Bunu olcemedim" oldu. Kapi dogru davraniyor, sorun modelin arac disiplini. Ö-1de yazili bilinen sinir: arac cagirma yapisal degil, prompta bagli.

3. TABAN OLCUMU YOK — PROMPT UZADI.
Bugun PROMPT_BLOGU ve OLCU_YONLENDIRME uzatildi. Bunun arac cagirma sikligina etkisi OLCULMEDI, cunku degisiklikten onceki temiz taban elde yok. Once taban olcumu alinmali (ayni soru N kez, arac cagrildi mi sayilmali), sonra prompt sadelestirilip karsilastirilmali.

4. KILO ZINCIRDE AMA FIILEN KULLANILMIYOR.
Kilo baglandi ve gercek cagriyla dogrulandi, ancak gunluk kullanimda hep groq/glm/nvidia one geciyor. Kilonun kotasi en genis olan; sira mantiginin bunu degerlendirip degerlendirmedigi olculmedi.

5. LIST_FILES DAR.
Yalniz knowledge ve research-engine gorunuyor. Olcum araclari (git_durum, belge_ara, dosya_bilgi) proje klasorlerini gorebiliyor ama list_files goremiyor; bu tutarsizlik "brain klasorunde ne var" gibi dogal sorulari cevapsiz birakiyor. Genisletme karari Casperin.

6. KOZMETIK: gunluk kart saat 14:00te de "Gunaydin" diyor.

BUGUN KAPANANLAR (tekrar acilmasin diye): olcum rozetinin yanlis araca atfedilmesi (31c12f3), cevaplarin makine ciktisi gibi okunmasi (91ffed9), cok adimli isin teknik olarak imkansiz olmasi + Ingilizce dusunme metni sizintisi (3ce42e3), Kilo Gateway baglantisi (29fc257).
