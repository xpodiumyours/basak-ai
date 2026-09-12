# ARAŞTIRMA — ÖLÜ ÇIKIŞ-KAPISI TEMİZLİĞİ (olcu.py)

Tarih: 2026-09-12
Durum: KANITLANDI — KOD DENEYİNE İZİN
Risk sınıfı: Düşük (ölü kod + birebir taşıma; tek canlı kullanım edge fallback)

## 1. Hedef

`olcu.py` çıkış-kapısı modülünü canlı yoldan tamamen sök, davranış değiştirmeden:
- `olcu.py` silinir (837 satır).
- `_chat_legacy.py` içindeki `from olcu import...` ve iki ölü dict girdisi (`sozlesme_coz`, `sozlesme_kapisi`) kaldırılır.
- Tek canlı kullanılan saf fonksiyon `ham_olcum_satirlari` (+ yardımcısı `_arac_adi`) birebir `chat/gate.py`'ye taşınır; `orkestra_bilesenleri` aynı anahtarla oradan alır.
- `olcu.py`'ye bağımlı 5 kök test dosyası silinir (`pytest tests` bunları toplamıyor).

## 2. Kabul kriteri

- `python -m pytest tests -q` sonucu baseline ile aynı (538 geçti + 1 bilinen sıra-bağımlı flake + 7 skip; gerileme yok).
- `python -m py_compile` düzenlenen dosyalarda temiz.
- `*.py` içinde `olcu` referansı sıfır (AGENTS.md tarihçesi + research/*.md hariç).
- `Orkestra.kos` smoke'u mevcut testlerde yeşil (`test_orkestra.py`, `test_kesif_dayanagi.py`, `test_orkestra_yol.py`).

## 3. Mevcut durum kanıtı (kod satırları)

- Canlı yol: `basak_app.py`/`telegram_bot.py` → `chat.mesaj_isle` → `chat/flow.py:mesaj_isle_yeni` → (`orkestra_ana_yol=true` ise) `_chat_legacy.mesaj_isle_orkestra` → `Orkestra.kos`.
- `cikis_kapisi` / `PROMPT_BLOGU` / `SOZLESME_PROMPTU` çağrısı hiçbir canlı fonksiyonda YOK (repo geneli grep: yalnız `olcu.py` tanımı + `_chat_legacy.py:24-26` importu + kök `test_tum_ozellikler.py:133` kaldı).
- `_chat_legacy.py:400-403`: "çıkış kapısı söküldü — cevap olduğu gibi geçer" (`_kapidan_gecir` kimlik fonksiyonu).
- `_chat_legacy.py:791`: `kimlik_kapisi = lambda metin, o=None: (metin, [])` — Orkestra'nın `olcu_kapisi` girdisi geçişsizdir.
- `brain/orkestra.py:129`: PROMPT_BLOGU canlı yoldan çıkarıldı (yorumda kayıtlı).
- `brain/orkestra.py` `olcu` kaynaklı iki anahtar okur: `olcu_kapisi` (239/266/284 — kimlik, eleme yapmaz) ve `ham_olcum` (302 — yalnız kazanan metin birebir `YEDEK_CUMLE` ise ham satır basar; kimlik kapısıyla bu dal pratikte ölüdür).
- `sozlesme_coz` / `sozlesme_kapisi` dict girdilerini `brain/orkestra.py` HİÇ okumaz (grep: 0 okuma).
- Jüri (`ek_adaylar`) `orkestra_juri=false` iken `[]` döner, kota yemez (`_chat_legacy.py:894-895`, `ayarlar.json`).
- Kök `test_*.py` (5 dosya) `pytest tests` tarafından toplanmaz (gate komutu `pytest tests -q`; collection 555 testin tamamı `tests/` altındadır).

## 4. Sorun kanıtı

- Hedef (Casper 2026-09-12): "modelin doğal akışına dokunma". Kapı grameri (`[Ö]/[A]/[Ç]/[B]`) canlıda zaten geçişsiz; modülün durması ölü ağırlık + yanlış yönlendirme riski (yeni ajan kapıyı canlı sanır).
- `olcu.py` 34 KB + kök test 24 KB ölü kod; `context.py` değil ama `test_tum_ozellikler.py:133` son tüketicidir.

## 5. Dış referans

- OpenAI function-calling: `tool_choice` varsayılan `auto` — model ne zaman araç kullanacağına kendisi karar verir (`platform.openai.com/docs/guides/function-calling`).
- Groq tool-use: akış = istek + tool şeması → model tool_call döner → uygulama koşturur → sonuç modele verilir; model çıktısını cümle-cümle eleyen kapı bu akışta yoktur (`console.groq.com/docs/tool-use`).

## 6. Doğrulanan gerçekler

- Yukarıdaki tüm satır numaraları bu dalda (`feature/task-model-harness-v1-20260912`) okunarak doğrulandı.
- Baseline: `pytest tests -q` = 538 geçti, 1 sıra-bağımlı flake (`test_brain_yapi_ilk_saglayiciya_tasinir` — izolede yeşil, global `_COOLDOWN` kirliliği), 7 skip.

## 7. DOĞRULANAMADI

- Yok. Tüm iddialar kod grep + test koşumuyla doğrulandı.

## 8. İzin verilen kapsam

- `olcu.py` sil.
- `_chat_legacy.py:24-26` importu sil; dict girdileri `sozlesme_coz`/`sozlesme_kapisi` sil; `ham_olcum` girdisi `chat.gate.ham_olcum_satirlari`'ne bağla.
- `chat/gate.py`'ye `ham_olcum_satirlari` + `_arac_adi` birebir taşı (davranış aynı; SELECT fallback metni değişmez).
- Kök 5 test dosyasını sil (`test_brain_cevapla.py`, `test_mesaj_isle.py`, `test_no_embed.py`, `test_ollama_direct.py`, `test_tum_ozellikler.py`).

## 9. Yasak kapsam

- Orkestra akış mantığı, `kimlik_kapisi`, `_kapidan_gecir`, `_SOZLESME_MODU`, `test_sozlesme_duragan.py`, prompt blokları, izin sistemi, tool seti — dokunulmaz.
- `deney`/`fay`/`dunya`/`evrim`/`gerilim`/`is_kuyrugu` modülleri — bu pakette dokunulmaz (ayrı paket).
- AGENTS.md §2 tarihçesi (Ö-0 maddesi) — tarih kaydıdır, değiştirilmez.

## 10. Korunacak davranışlar

- `Orkestra.kos` sözleşmesi (`cevap`/`iz`/`kaynak`); MEASURE/SELECT fallback çıktısı birebir aynı kalır.
- `orkestra_bilesenleri` gerekli anahtar seti (`_GEREKLI_BILESENLER`) eksiksiz kurulur.

## 11. Risk sınıfı

Düşük. Ölü kod silme + saf fonksiyonun birebir taşınması. Tek canlı kullanım edge fallback dalıdır.

## 12. Kabul sensörleri

Ünite test paketi (`pytest tests -q`), `py_compile`, repo geneli `olcu` grep'i, mevcut Orkestra smoke testleri.

## 13. Geri alma koşulu

Herhangi bir test gerilerse, `Orkestra` kurulumu patlarsa veya canlı `olcu` referansı bulunursa paket `git checkout` ile geri alınır.

## 14. Sonuç (2026-09-12 uygulandı)

- `olcu.py` + 5 kök test silindi; `ham_olcum_satirlari`/`_arac_adi` `chat/gate.py`'de; legacy import + 2 ölü dict girdisi kalktı.
- Sensörler: `pytest tests -q` = 545 geçti / 3 hata / 7 skip — **pristine ağaçta da birebir aynı** (stash ile doğrulandı; 3 hata sıra-bağımlı `_COOLDOWN` flake, izolede yeşil). Gerileme yok.
- `*.py` içinde `olcu` referansı sıfır (yorum satırı güncellendi).
- KANITLANDI → paket tamamlandı.
