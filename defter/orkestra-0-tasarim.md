---
kim:    opencode
tarih:  2026-08-24
konu:   ORKESTRA-0 tasarim belgesi — 10 durumlu muhakeme iskeleti
tip:    karar
omur:   sonsuz
kaynak: kilitli hedef + mevcut master kodu
---

# ORKESTRA-0 — Başak'ın merkez orkestratörü

## İlke
mesaj_isle YENIDEN YAZILMAZ. Orkestra, DOGRULANMIS parçaları durum
makinesine bağlayan açık bir çerçevedir. Her durum, mevcut testli
fonksiyonları çağırır; her koşum bir IZ (trace) bırakır — hangi durum ne
yaptı, hangisi atlandı, neden.

## Durumlar ve v0 eşlemesi (mevcut kod → durum)

| Durum | v0 içeriği | Kaynak fonksiyon |
|---|---|---|
| OBSERVE | metni temizle, konuşmacı etiketini ayıkla, boş kontrol | chat.py satır içi → `observe()` |
| MODEL | bağlam kur: bilgi önbelleği + ilgili anılar + geçmiş penceresi | `_load_knowledge`, `_ilgili_anilar`, `_gecmis_pencere` |
| QUESTION | görev tipi sınıflandır + dinamik araç seti | `secici.siniflandir`, `_dinamik_araclar` |
| HYPOTHESIZE | aday cevap üretimi (v0: TEK aday — beyin.cevapla) | brain.cevapla |
| DIVERSIFY | paralel adaylar | **ATLANDI** (FAY-1 jürisi bekler) |
| CRITICIZE | saldırgan roller | **ATLANMIŞ** (FAY hattı bekler; bugünkü yerini ölçü kapısı tutuyor) |
| EXPERIMENT | tool_calls varsa çok turlu araç koşumu | `_tool_calling_multi` |
| MEASURE | çıkış kapısı: işaretsiz/uydurma elenir; ham ölçüm fallback | `olcu.cikis_kapisi`, `ham_olcum_satirlari` |
| SELECT | adaylar arasından son cevap (v0: tek aday) | mevcut akış |
| LEARN | istatistik (gerçek tokenlar) + episodic anı + karne güncelleme | `istat.kaydet`, `episodik_kaydet`, `karnayi_guncelle` |

## Kurallar
1. Her durum çalıştıktan sonra iz kaydı: {durum, sonuc_ozeti, atlandi}.
2. Atlanan durumlar SEBEPiyle yazılır ("bütçe", "tek aday yeter",
   "ön koşul yok") — sessiz atlama yasak.
3. v0'da davranış bugünküyle EŞDEĞERDIR: aynı girdiye aynı çıktı.
   Yeni yetenekler sonraki dilimlerde durumların İÇİNE eklenir.
4. Üretim anahtarı: orkestra önce gölge modda koşar (paralel iz üretir,
   cevabı değiştirmez); eşdeğerlik kanıtlanınca ana yol olur.
5. LEARN yalnızca ölçüden geçen cevapta çalışır.

## Kabul ölçütleri (ORKESTRA-0)
- Basit soru izinde tam dizi görünür; DIVERSIFY/CRITICIZE sebepiyle
  atlanmış görünür.
- Araç gerektiren soruda EXPERIMENT koşar ve MEASURE kanıtlı cevap verir.
- Aynı girdi için iz deterministiktir (rastgelelik dışında).
- Tüm mevcut testler yeşil kalır (davranış değişmez).

## Sonraki dilimler (bu fazdan sonra)
- Gölge mod → ana yol geçişi (eşdeğerlik raporuyla)
- DIVERSIFY'ı FAY-1 jürisine bağlama
- HYPOTHESIZE'ı Problem Compiler'a yükseltme (kilitli planda henüz %0)
