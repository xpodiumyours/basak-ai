# ARAŞTIRMA — BAĞLAM ÖLÜ REFERANS TEMİZLİĞİ

Tarih: 2026-09-12
Durum: KANITLANDI — KOD DENEYİNE İZİN
Risk sınıfı: Düşük (ölü kod; canlı knowledge akışı ve indeksleme aynen korunur)

## 1. Hedef

Olmayan dosyalara (`defter/INDEX.md`, `GOREV_LISTESI.md`) yapılan ölü referansları ve hiç çağrılmayan bağlam kodunu temizle; davranış değişikliği yok:
1. `_chat_legacy._load_knowledge`: `ad_ek` listesinden iki ölü girdiyi çıkar (`AGENTS.md` kalır).
2. `_hafiza_hazirla`: olmayan `defter/` dizinine `indeksle_klasor` çağrısını kaldır (bugün 0 döner, yalnız log toplamına girer).
3. `chat/context.py`: hiç import edilmeyen `load_knowledge`, `KNOWLEDGE_EMBED_CHARS`, `ContextConfig` kaldırılır (canlı `yukle/kaydet/gecmis_pencere/temizle_history/hafiza_al/ilgili_anilar` aynen kalır).

## 2. Kabul kriteri

- `pytest tests -q` baseline ile aynı; `py_compile` temiz.
- `defter/INDEX`, `GOREV_LISTESI`, `ContextConfig`, `context.load_knowledge` dizgileri `*.py` içinde sıfır.
- `basak_app` token göstergesi (`_knowledge_cache`) ve `_model_baglami` çıktısı değişmez (kod yolu aynı).

## 3. Mevcut durum kanıtı

- `defter/`, `GOREV_LISTESI.md` repoda YOK (2026-09-12 `Test-Path` + git tree taraması).
- `_load_knowledge` ek listesi `os.path.exists` korumalıdır — ölü girdiler bugün no-op'tur (`_chat_legacy.py:209`).
- `indeksle_klasor` olmayan dizinde `0` döner (`memory/engine.py:458-459`); `n3` yalnız log toplamına girer (`_chat_legacy.py:659-660`).
- `ContextConfig`/`load_knowledge` importçusu YOK (repo geneli grep: yalnız tanımlar; `chat/__init__` aktarmaz; testler `chat.context`'ten yalnız `yukle/kaydet/hafiza_al` alır).

## 4. Sorun kanıtı

- Ölü referanslar "dosya varmış" izlenimi verir; yeni ajan olmayan defteri arar (P1'de AGENTS.md düzeltildi, kod ayağı bu pakettir).
- `context.load_knowledge` ile legacy `_load_knowledge` ikiz bakımı kafa karıştırır; canlı olan legacy'dir.

## 5. Dış referans

Gerekmez (davranış değişikliği yok; iç kanıt yeterli). Kapı §4'e göre kaynak hiyerarşisinin 1. basamağı (bugünkü kod) yeterlidir.

## 6. Doğrulanan gerçekler

Yukarıdaki satırların tamamı bu dalda okundu; importçu grep'leri çalıştırıldı.

## 7. DOĞRULANAMADI

Yok.

## 8. İzin verilen kapsam

Yukarıdaki 3 madde. `DEFTER_DIR` sabiti bu pakette KALIR (P6'da `dunya_ozet` çağrısıyla birlikte ele alınacak).

## 9. Yasak kapsam

- `_knowledge_cache` içeriği, `_model_baglami`, indeksleme (knowledge/obsidian), `AGENTS.md` eklenmesi — dokunulmaz.
- `dunya`/`bayat`/`notes` modüllerindeki defter dizgileri (docstring) — P6 kapsamı.

## 10. Korunacak davranışlar

- Açılış knowledge önbelleği ve hafıza indeksleme çıktısı birebir aynı.
- `chat/__init__` dışa aktarım listesi değişmez.

## 11. Risk sınıfı

Düşük.

## 12. Kabul sensörleri

`pytest tests -q`, `py_compile`, repo geneli ölü-dizgi grep'i.

## 13. Geri alma koşulu

Test gerilemesi veya canlı knowledge çıktısında fark olursa `git checkout` ile geri alınır.

## 14. Sonuç (2026-09-12 uygulandı)

- Legacy loader ölü girdileri kalktı; defter indeks çağrısı kalktı; `context.py` ölü trio (`load_knowledge`/`KNOWLEDGE_EMBED_CHARS`/`ContextConfig`) silindi.
- Yan bulgu + düzeltme: P4'ün secici ön-seçimi global RNG akışını kaydırıp yapısal `%50` testi (`test_hata_verince_siradaki_gecer`) chalkantıya soktu — ön-seçim RNG-nötr hale getirildi (getstate/setstate). Suite pristine RNG akışına döndü.
- Sensörler: tam paket 603 geçti / 3 flake / 7 skip (pristine ile aynı). Gerileme yok.
- KANITLANDI → paket tamamlandı.
