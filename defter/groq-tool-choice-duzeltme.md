# Groq tool_choice 400 duzeltmesi (FAZ 1.4d)

- **kim:** opencode (mimar)
- **tarih:** 2026-08-24
- **konu:** Aracsiz turda modelin tool_call uretmesine karsi tek nudge'li retry
- **tip:** duzeltme
- **omur:** sonsuz
- **kaynak:** brain/groq.py, tests/test_groq_tool_choice.py, tests/eval/sonuc.json

## Sorun (canli kanitli)

Zincirin son turu tools sunmadan cagirir; groq modeli yine de tool_call
uretip 400 alirdi: "Tool choice is none, but model called a tool".
Sonuc: kota yanar, zincir zayif saglayiciya duser (gece A/B kosusunun
gurultu kaynagi).

## Cozum

- `GroqClient._tool_choice_hatasi_mi()`: hata metninde `tool_use_failed`
  + `Tool choice is none` eslesmesi (baskalarini dokunmaz).
- Eslesen tek istisnada: ayni istek + sona bir system nudge
  ("Bu turda arac yok; yalniz duz metinle yanit ver.") ile TEK tekrar.
  Ikinci hata dogal olarak yukselir; orijinal mesajlar bozulmaz.
- Kota seffafligi: brain.py kota harcamayi yalniz basarili donusten sonra
  yaptigindan (brain.py:357) adaptor-ici retry kotaya dokunmaz.

## Kanit

7 yeni test (bug-tekrar, mesaj-bozulmama, ikinci-hata yukselme, ilgisiz-400,
timeout, mutlu-yol, yapi-korunumu). Tam suite: 589 yesil; tek kirmizi bayat
DURUM.md idi -> tools.durum ile tazelendi (601 test fonksiyonu), belge
sagligi yesil.

## Siradaki

FAZ 1.4e — temiz havuzda (glm ayakta) kapali/acik A/B. Kabul: sizinti < 4 VE
disiplin >= %33.3.
