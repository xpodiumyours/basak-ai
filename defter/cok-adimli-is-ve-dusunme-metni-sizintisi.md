---
kim:    claude
tarih:  2026-08-23
konu:   Cok adimli is ve dusunme metni sizintisi
tip:    olcum
omur:   30g
kaynak: olcum
---

Uc ariza duzeltildi, biri acik kaldi.

1. COK ADIMLI IS (kok sebep bulundu): _tool_calling_multi TEK TUR calisiyordu — araclar bir kez kosuyor, sonra modele tools=None ile soruluyordu. Yani ikinci adim ("bul, sonra kaydet") teknik olarak IMKANSIZDI. Dongu haline getirildi (TUR_SINIRI=3); son turda arac verilmez ki dongu kapansin. 3 yeni test.

2. INGILIZCE DUSUNME METNI SIZINTISI: saglayici kendi dusunme metnini cevap sanip gonderiyordu ("We need to answer...") ve kullaniciya ulasiyordu. Mevcut _dil_kontrol bu isi goremiyor — Turkce harflerin cogu ASCII oldugu icin DUZGUN TURKCE cevabi da Ingilizce sayiyor (test yakaladi; bu fonksiyona bu is icin guvenilmez). Yeni _ingilizce_sizinti_mi: Ingilizce/Turkce islev kelimelerini sayar. Hem araclli hem araciz yolda uygulandi; telkinden sonra da surerse metin kullaniciya verilmiyor.

3. ARACLI YOLDA DIL KONTROLU HIC YOKTU — sizintinin ana kapisi buydu.

ACIK KALAN (yeni olcum): model YAPMADIGI ISI YAPTIM diyebiliyor. Gercek tur: "[B] Bu bilgi VixRex son commit basligiyla deftere kaydedildi" dedi; git status defter/ BOS — hicbir kayit olusmadi. Sebep: [B] cumleleri kapidan serbest geciyor, icerigi denetlenmiyor. [B] "bilmiyorum" icin tasarlandi ama model onu serbest metin olarak kullaniyor. Sonraki is bu.

Kanit: 252/252 test yesil. Gercek agda: sizinti artik gecmiyor, kapi cokunce ham olcum gosteriliyor.
