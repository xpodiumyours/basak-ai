# FAZ 1 - Sozlesme altyapisi kuruldu, canli A/B citayi gecmedi, geri alindi

- **kim:** opencode (mimar)
- **tarih:** 2026-08-24
- **konu:** Yapi-garanti kapisi v2 insa edildi; canli kosusta sizinti 4->5 oldugu icin
  onceden kayitli kural geregi sozlesme_modu=kapali cevrildi
- **tip:** karar
- **omur:** sonsuz
- **kaynak:** tests/eval/sonuc.json, olcu.py:497-726, chat.py, brain/brain.py, ANA-PLAN.md

## Insa edilen (cevrimdisi kanitli)

- **FAZ 1.1:** yapi parametresi 10 saglayici adaptorune eklendi; groq response_format,
  ollama format=json kullanir; brain.py self-healing `_YAPI_DENEME` onbelleği.
  10 yeni test.
- **FAZ 1.2:** olcu.py'e sozlesme cekirdegi: SOZLESME_PROMPTU, sozlesme_coz,
  sozlesme_gecerli_mi, sozlesme_kapisi (iddia->kanit yapisal dogrulama +
  daraltilmis guvenlik agi). 22 yeni test; eski kapida sifir gerileme.
- **FAZ 1.3:** chat.py cift-yol entegrasyonu (_kapidan_gecir), iki kapi cagrisi
  birlesti, prompt degisimi, orkestra bilesenleri. 17 yeni test. Tam suite:
  582 yesil (tek kirmizi bayat DURUM.md idi, tools.durum ile duzeltildi).
  Toplam yeni test: 49.

## Canli A/B sonucu (FAZ 1.4, ayni gece kosulu)

| metrik | taban | sozlesme acik | cita |
|---|---|---|---|
| arac disiplini | %33.3 | %33.3 | >=%33.3 OK |
| yanlis iddia sizinti | 4 | **5** | <=4 **GECTI** |
| durust red | %0 | %33.3 | - |

**Karar:** onceden kayitli kural uygulandi -> `ayarlar.json "sozlesme_modu": "kapali"`.
Altyapi yerinde kalir; anahtarla geri acilir.

## Kok neden analizi

1. **Sozlesme yolu hic aktive olmadı:** 12/12 cevap duz metin geldi (JSON 0).
   Gece saglayici firtinasi (glm timeout/429, groq TPM 429 + "tool choice is none"
   400'leri) zinciri zayif halkalara dusurdu; zayif model JSON talimatini yok saydi.
   Yani kapı v2'nin davranisi canlida OLCULMEDI bile — gerilemenin sebebi kapı degil,
   (a) saglayici gurultusu, (b) PROMPT_BLOGU'nun SOZLESME_PROMPTU ile degismesiyle
   [B] uretiminin dusmesi.
2. **Ders:** sozlesme modu zayif/yorgun modellerde JSON uretemiyor; cift yolun
   "dus" blegi tek basina tasimiyor. Gucte garanti icin ya (a) daha guclu model
   (FAZ 4 ile birlestir), ya (b) JSON bozukken marker-promptuna otomatik donus
   (iki promptlu hibrit), ya (c) tool_choice yapisal duzeltmesi sonrasi temiz
   havuzda tekrar olcum gerekir.

## Siradaki kosullar (yeniden deneme citasi)

- Once groq "tool choice is none" 400 sinifi yapilsal duzeltilecek (son turda
  tools=None iken tool_call uretimi engellenecek).
- Temiz kotada (glm ayakta, groq sogumus) arka arkaya A/B: kapali vs acik.
- Kabul: sizinti < taban VE disiplin >= taban. Saglanamazsa FAZ 4 model
  degisimi sonrasina ertiler, altyapi bekler.
