---
kim:    opencode
tarih:  2026-08-24
konu:   Arac logu kirmalama — hassas icerik artik loga girmiyor
tip:    karar
omur:   sonsuz
kaynak: tools/tool_logger.py + tests/test_log_kirmalama.py
---

Casper'in bulgusu: tool_logger ilk 200 karakteri HAM yaziyordu — save_note
icerigi, deftere_kaydet metni, read_file sonucu (dosyanin kendisi!) ve
URL icindeki anahtarlar arac.log'a dusuyordu.

Cozum iki katman (`tools/tool_logger.py`):
1. ALAN MASKELEMESI: hassas araclarin serbest metin alanlari deger olarak
   DEGIL "<N karakter>" uzunluk bilgisiyle yazilir:
   - save_note: title+content
   - deftere_kaydet: title+content
   - write_file_tool: content (path gorunur kalir)
   - read_file: SONUC'un tamami maskelenir (dosya govdesi asla loglanmaz)
2. DESEN KIRMALAMA (_kirmala): her satirda api_key/token/parola/sifre/
   secret/anahtar atamalari, sk-... ve ghp_/github_pat_ anahtarlari,
   Bearer basliklari maskelemir.

Debug degeri korunur: arac adi, gizli olmayan argümanlar (proje adı,
path), hata mesajlari ve olcum ciktilari aynen görünür.

KANIT: 10 yeni test (tests/test_log_kirmalama.py): not icerigi logda yok,
uzunluk var; dosya govdesi gizli; hata mesaji gorunur; desen kirmalamasi
4 cesit anahtari yakalarken normal metne dokunmuyor. Toplam 362/362 yesil.

Not: eski tarihli arac.log kayitlari duzeltmeden ONCE yazilmis ham icerik
tasiyabilir — dosya yereldir, commit'e girmez; Casper istersen dondurulur.
