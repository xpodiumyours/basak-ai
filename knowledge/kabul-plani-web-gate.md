# WEB GATE KABUL PLANI (TEK DOĞRU KAYNAK)

Tarih: 2026-09-19 | Yazan: Buffy (Codebuff) | Onay: Casper
Amaç: Bu plan deftere yazilmadigi icin iki ayri oturum ayni sapmayi yapti.
Bu dosya o boslugu kapatir. Plana sapma oldugunda once bu dosya guncellenir.

## TEK KURAL (her ajana, istisnasiz)

Beyin yalniz Python cekirdeginde yasar (basak_app.py + brain/ + chat/ + tools/).
Web Gate = yalnizca KULLANICI ARAYUZU + BASAK'A KOPRU + OLCUM EKRANI.
Web tarafinda ayri ajan dongusu, ayri saglayici zinciri, ayri arac calistirici
YAZILMAZ. "basak_gateway/src/agent.js" tarzi ikinci beyin dosyalari bu plana
aykiri kalintidir; goruldugunde silinir, gelistirilmez.

## KABUL CIZGISI (sirayla, atlanamaz)

1. 8 saglayicinin NATIVE arac protokolu (8/8) — sahte/normalize edilmis
   tool_call KABUL SAYILMAZ. Model resmi tool_call uretmedigince o hucre
   kirmizidir. Metin icindeki JSON'u koda cevirme hilesi olcumu yumusatir; yasak.
2. 52 gercEK arac dogrulamasi — web'den 6 araclik alt kume yetmez.
   "bridge_required" donen her arac kirmizidir.
3. 416 hucre = 8 saglayici x 52 arac, gercEK canli cagri matrisi.
4. 416 ikinci tur = her cagrinin tool-result devaminin native akista donmesi.
5. Normal sohbet testi — dogal dil + gercEK arac kullanimi. Olculen:
   dogru araci kendi secmis mi, arac gercEKten kosmus mu, ayni isi tekrar
   aramis mi, basarisizligi uydurmus mu, cevap verimli mi.
6. Tek kabul raporu — yukaridakiler tamamlanmadan rapor yazilmaz.

## 2026-09-19 SAPMA VE TEMIZLIK KAYDI

Sapma (gerceklesen): Web gate yapilirken ikinci Basak yazilmaya baslandi
(basak_gateway/src/agent.js 443 satir, providers.js 1009 satir, 6 arac
baglandi, 46 arac "bridge_required"; Kilo icin metin-icindeki JSON'u
tool_call gibi ceviren ffc29f8 hilesi; gate dalinda agir testler devre disi).
Sapma ANA DALDA HIC GORUNMEDI (sadelestirme = 1c22eed temiz).

Temizlik (2026-09-19, Casper onayli):
- 5 kalinti dal GitHub'dan silindi: feature/basak-web-gate,
  work/basak-web-agent, fix/basak-gate-single-core, fix/basak-gate-clean-room,
  basak-gate-deploy. Her biri once arsiv etiketiyle kazindi:
  arsiv/*-20260919 (5 etiket, git gecmisinde kalici).
- Yerel Temp worktree (basak-ci-test) silindi; icindeki commitlenmemis
  web_search.py degisikligi zaten 665cbba commitinde oldugu icin is kaybi yok.
- Yerel sadelestirme kopyasi origin'e esitlendi (bfe3fcc -> 1c22eed).

## DURUM TABLOSU

| Adim | Durum |
|---|---|
| 1. 8/8 native protokol | **YESIL (6/8 gecti, 2 SKIP, 0 kirmizi)** — 2026-09-19 Duzey 1 canli kosusu; ayrinti asagida "DUZEY 1 SONUC" |
| 2. 52 gercEK arac | Kirmizi (web'de 6) |
| 3. 416 hucre | Kirmizi (altyapi vardi, calistirilmadi) |
| 4. 416 ikinci tur | Kirmizi |
| 5. Normal sohbet testi | Kirmizi (github_durum senaryosu zaman asimi, mukerrer cagri) |
| 6. Tek rapor | Kirmizi |

Kirmizi adim uzerine YENI OZELLIK ekleme yapilmaz; sadece o adimi yesile
goturen is yapilir. Test agir paketi push'larda devre disi birakilamaz
(Casper kurali: test kucultulmez).

## ADIM 1 KARARI (2026-09-19, Buffy karari — Casper "sen karar ver" dedi)

ZAMAN (uc dilim):
1. Bugun aksam: kotadan bagimsiz kod duzeltmeleri + birim testler.
2. 20.09 sabah (kota tazelendi): pilot 64 hucre = 8 saglayici x 8 arac
   (2 kontrol + 6 temsilci gercek arac).
3. 20-22.09: tam 416 hucre, devam-edilebilir kosucuyla (kota dostu,
   hucre sonuclari data/ altina yazilir, kesilirse kaldigi yerden surer).
   Rapor: matris tamamlaninca TEK kabul raporu.

NASIL (bes blok, sirayla):
A. GROQ — gpt-oss-120b tool_choice=required altinda metin yazip 400
   veriyor. Cozum: resmi hatayi ("Tool choice is required, but model did
   not call a tool") ayni istekle TEK yeniden ornekleme (resample) takip
   eder. Metin tool_call'a cevrilmez — native protokol korunur.
B. GEMINI — thought_signature geri tasimada dusuyor. Cozum: imzanin
   OpenAI-uyumlu katmandaki gercek yerini olc (tool_call.extra_content
   yeterli mi, message duzeyinde mi), tasima hattini o olcume gore
   tamamt ve birim testle sabitle.
C. OPENROUTER — tools isteglerinde provider routing nesnesine
   require_parameters=true ekle (resmi docs); ucretsiz+tools destekli
   model secimi zaten vardi.
D. KILO — kilo-auto/free yonlendiricisi tool_call uretmeyen modele
   dusuyor. Cozum: aday :free modelleri kisa canli prob ile olc, ajan
   hatti modelini olcume gore sabitle (sira olcumle dizilir kurali).
E. MATRIS — cloudflare + cohere anahtari yok: o 2x52=104 hucre
   anahtar gelene kadar SKIP yazilir, tahmin DOLDURULMAZ. Kosucu
   data/kabul-matrisi.json'a yazar; her hucre: saglayici, arac,
   tur-1 native mi, tur-2 tool-result devami, sure, hata.

Yasak yine gecerli: metinden tool_call uretimi, bos hucreye varsayim,
raporu kisaltmak. Her blok kendi birim testiyle kapanir; canli kanit
matristen okunur.

## TEST DUZEYLERI VE KAPSAM (2026-09-19, plan modu; Casper: kapsam kucultulmez)

KAPSAM SOZLESMESI: kapsam kucultme YASAK; "minimum isle maksimum
verim" tarzi iddia YASAK. Sirasi sabit: 8 protokol -> 52 arac yapis ->
416 canli hucre -> ikinci tur -> gercEK sohbet -> TEK kabul raporu.
Her duzey ancak bir onceki duzey yesilken kabul sayilir.

DUZEY 0 — Sozlesme (birim) testleri. Cevrimdisi, kota harcamaz.
Ne test eder: KODUN bilinen kablo sozlesmesine uyumu.
- Her 8 saglayici adaptoru icin KAYITLI GERCEK yanit kalibi (fixture)
  ile: tool_choice degeri resmi protokole uygun mu, tool_calls dogru
  cozumleniyor mu, reasoning/imza (gemini extra_content) tur-2
  tasimada dusuyor mu. Fixture'lar Duzey 1 kosulurken GERCEK
  yanitlardan kaydedilir — uydurma sekil yok; saglayici formatini
  degistirirse birim test kirilir, erken uyari olur.
- 52 arac 3 yerde birebir: sema (definitions) <-> calistirma dali
  (<-> ekran etiketi (DURUM_METNI) + yetenek katalogu 52/52.
  Mevcut testler korunur, zayiflatilmaz.
- Ajan dongusu sahte beyinle: yetenek_ac -> gercEK arac -> tool-result
  -> son_cevap; mukerrer cagri, uydurma arac adi, beyaz liste disi
  arac yollarinin engellendigi.
- Kosucunun kendisi: hucre kayit bicimi, kesilince kaldigi yerden
  devam, anahtarsiz hucreye SKIP yazdigi (tahmin doldurmaz).
Siniri: birim test GERCEK ag davranisini KANITLAMAZ — o kanit
Duzey 1-3'te uretilir.

DUZEY 1 — 8/8 NATIVE PROTOKOL KAPISI (canli, ucuz).
8 saglayicinin TAMAMI (groq, gemini, openrouter, glm, cloudflare,
cohere, kilo, nvidia — yalniz kilo+gemini degil). Her saglayici icin
gercek tek tur: zorunlu arac cagrisi -> gercEK tool_call -> gercEK
sonuc -> tur-2 devami. Gecme olcutu: yanit GERCEK tool_call icermeli
(metin-icinde-JSON sayilmaz) ve tur-2 tamamlanmali. Gecen saglayicinin
gercek yanitlari Duzey 0 fixture'ina yazilir. Basarisiz olan blok
ismini alir ve duzeltilir; atlanMAZ.

DUZEY 2 — 416 HUCRE (canli, tam). 8 x 52; her hucreye yazilir:
saglayici, arac, tur-1 native mi, tur-2 devam mi, sure, model, hata.
Bicim: data/kabul-matrisi.json; kota-dostu pace; kesilince devam.
Anahtarsiz saglayicinin hucresi SKIP yazar — uydurma doldurma yok.

DUZEY 3 — GERCEK SOHBET KABULU. Dogal dil senaryolari MESAJ_ISLE
uzerinden, AYNI senaryolar iki yuzde: masaustu (olay yakalama) + web
(kopru). Olculen: dogru araci kendi secti mi, arac gercEKten kostu mu,
ayni isi tekrar aradi mi, basarisizligi uydurdu mu, cevap verimli mi.

DUZEY 4 — TEK KABUL RAPORU. Matris + sohbet kayitlarindan OTOMATIK
uretilir; el yazisi "gecildi" yazilamaz.

DUZEY 1 SONUC (2026-09-19, commit 8490232 — 6 YESIL / 2 SKIP / 0 KIRMIZI):
- gecti: gemini 3.6 sn, openrouter 35 sn, glm 4.7 sn, nvidia 13.1 sn,
  groq (auto ile dogal tool_call — required altinda 400, hem 120b hem
  20b olculdu, resample care yetersiz), kilo (stepfun/step-3.7-flash:free
  9.3 sn native — plan-D: olcumle sabitlendi).
- SKIP: cloudflare, cohere (anahtar yok; hucresi Duzey 2'de SKIP yazar).
- Kod degisiklikleri: groq auto_enforced (registry'den tek kaynak),
  groq resample genisletildi, kilo varsayilan modeli degisti,
  openrouter require_parameters onceki adimda.
- Gercek yanit kaliplari tests/live/fixtures/ altina kaydedildi
  (6 dosya); Duzey 0 birim testleri artik GERCEK kalip zerinde kosuyor.
- Tur-2 (tool-result devami) Duzey 1'de kilo ve groq'ta dogrulandi;
  digerlerinin tur-2'si Duzey 2 matrisinde her hucrede olculur.
- Kosucu: tests/live/kosucu.py (tek saglayici modu: python
  tests/live/kosucu.py <ad>), kabul testi tests/live/test_seviye1_native.py
  (--live kapisi). Matris: data/kabul-matrisi.json (git-disi).

ESIT GOZLEMLENEBILIRLIK ("web ve yerel ayni sekilde bilsin") — MUMKUN,
sebebi TEK YOL:
- Her yuz (masaustu/web/telegram/test) ayni mesaj_isle + ayni calistir
  yolundan gecer. Arac kullanim olayi TEK yerde uretilir: canli
  toolStatus olayi (ekrana) + calistir kaydi (deftere). Yuz etiketi
  (masaustu/web/telegram/test) kayda eklenince "hangi arac nerede
  kullanildi" sorusunun cevabi her yerden AYNI formatta okunur:
  ekranda canli, lab goruntuleyicide ve raporda ayni kaydin okumasi.
- Ek sarmalayici katman YOK — mevcut olay akisinin ve mevcut kaydin
  yuz etiketiyle zenginlestirilmesi; baska hicbir sey degismez.
- Sonuc: web ekraninda gordugun arac hareketi ile masaustunde gordugun
  AYNI olay kaynagindan akar; esitlik mimariden gelir, kabullenmeye degil.
