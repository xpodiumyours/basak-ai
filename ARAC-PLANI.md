# ARAÇ PLANI — Başak'a kalan araçların eklenmesi

**Tarih:** 2026-09-13 · **Karar:** Casper · **Taban dal:** `sadelestirme` (`d9cc686`)

## 0. İş bölümü

| Kim | Ne yapar |
|---|---|
| **Casper** | Kapsamı belirler, karar verir |
| **Claude** | Bu planı yazar, her fazı **doğrular**, `sadelestirme`'ye birleştirme kapısını tutar |
| **ChatGPT** | Kodu yazar, her faz için ayrı dal açar, commit'ler |

**ChatGPT hiçbir fazı kendi birleştirmez.** Dal açar, iter, haber verir. Claude ölçer; geçerse birleşir, geçmezse geri döner.

## 1. Şu anki durum (taban)

`sadelestirme` dalında Başak'ta **altı araç** var, hepsi salt-okunur:

| Araç | Ne yapar |
|---|---|
| `web_search` | DuckDuckGo araması (anahtar istemez) |
| `sayfa_oku` | Sayfa içeriği okur (GET, 5.000 karakter, SSRF korumalı) |
| `read_file` | Dosya okur (ev klasörü + `C:\Projects`, kara liste korumalı) |
| `list_files` | Klasör listeler |
| `git_durum` | Proje dalı/commit/kirli dosya ölçer (4 proje beyaz listede) |
| `image_analyze` | Görüntü inceler (NVIDIA vision) |

**Ölçülmüş taban:** 182 test geçiyor, 7 atlanıyor.

## 2. Eklenecekler — faz sırası

Her faz **ayrı dal, ayrı commit, ayrı doğrulama**. Bir faz geçmeden sonraki başlamaz.

### FAZ 1 — Belge arama (en küçük, boru hattını kanıtlar)

- `tools/olcum.py` içindeki `belge_ara(proje, sorgu)` ve `dosya_bilgi(proje, yol)` **zaten yazılı ve test edilmiş**. Yeni kod yazma.
- Yapılacak: `tools/definitions.py`'ye iki şema, `tools/__init__.py` `calistir()`'a iki dal, `chat/tools.py` `DURUM_METNI`'ne iki etiket.
- `chat/flow.py` `_ARAC_ISARETLERI`'ne tetikleyici ekle: `"planda"`, `"belgede"`, `"dokümanda"`, `"dokumanda"`, `"notlarda"`, `"hangi dosyada"`.

**Kabul kanıtı:** Temiz hafızayla "Vixrex planında matris ne diyor?" → `belge_ara` koşar, gerçek satır döner.

### FAZ 2 — Dosya yazma (`knowledge/` ile sınırlı)

- `tools/file_ops.py` `write_file_ops(yol, icerik, base_dir)` **zaten yazılı**, yol güvenliği testli. Yeni kod yazma.
- Yapılacak: `write_file_tool` şeması + `calistir()` dalı.
- **Sınır:** yalnız `knowledge/` altına yazılabilir. `file_ops.OTOMATIK_YAZMA_KOKLER` şu an `("knowledge", "research-engine")` — bu tabloyu **değiştirme**.
- **Onay kutusu EKLEME.** `knowledge/` zaten güvenli alan; onay katmanı bilerek söküldü.
- `chat/prompts.py` `TOOL_YONLENDIRME`'deki "Yazma, silme ve uygulama açma yetkin YOK" cümlesi güncellenecek: yazma artık var ama yalnız kendi not klasörüne.

**Kabul kanıtı:** (a) `knowledge/deneme.md` yazılır ve diskte görülür; (b) `C:\Windows\test.txt` ve `C:\Projects\vixrex\x.md` denemesi **reddedilir** — dosya oluşmadığı diskte doğrulanır.

### FAZ 3 — Hatırlatmalar ve görev listesi

- `tools/reminders.py` (298 satır) ve `tools/tasks.py` (148 satır) git geçmişinde hazır: `git checkout 27b03a9 -- tools/reminders.py tools/tasks.py`.
- `tasks.py` eşzamanlı yazma korumalı (`threading.Lock` + atomik `os.replace`) — bu korumayı **bozma**.
- Yapılacak: `get_reminders`, `add_task`, `list_tasks`, `complete_task` şemaları + `calistir()` dalları. `gorevler.json` yolu `tools/__init__.py`'deki `BASE`'ten türetilir.
- Tetikleyiciler: `"hatırlat"`, `"ajanda"`, `"bugün ne var"`, `"görev"`, `"yapılacak"`, `"tamamladım"`.

**Kabul kanıtı:** Görev eklenir → listelenir → tamamlanır; `gorevler.json` diskte üç adımda da doğru içerikte.

### FAZ 4 — Uygulama açma

- `tools/app_launcher.py` (103 satır) geçmişte hazır.
- Yapılacak: `ac_uygulama` şeması + `calistir()` dalı + tetikleyiciler (`"aç"`, `"başlat"`, `"çalıştır"`).
- **Onay katmanı EKLEME** (2026-08-25 Casper kararı: sistem araçları serbest).

**Kabul kanıtı:** "not defterini aç" → gerçekten açılır, süreç listesinde görülür.

### FAZ 5 — Sabah özeti (kendi kendine çalışma)

- `tools/zamanlayici.py` (303 satır) geçmişte hazır: aktif saat 10:00–20:00, kart saatleri 10/12/14/16/18/20, 2 saat tekrar engeli.
- **Sadeleştirilecek:** eski kart hava durumu + hatırlatma + görev + proje durumu topluyordu. Yeni kart yalnız **proje durumu** olsun: dört projede gece ne commit'lendi.
- `basak_app.py` `main()` içine arka plan thread'i geri gelir. `Api.quit()`'e durdurma bloğu eklenir (SQLite açık kalmasın).

**Kabul kanıtı:** Zamanlayıcı elle tetiklenir, kart üretilir, içeriğindeki commit hash'i `git log` ile birebir doğrulanır.

### FAZ 6 — İçerik arama (proje genelinde)

**Neden:** `belge_ara` yalnız proje **kök klasöründeki** `.md` dosyalarına bakıyor (`os.listdir(kok)`, özyinelemeli değil). "Şu satır gerçekten eklenmiş mi", "bu fonksiyon hangi dosyada" sorulamıyor. Ajanın "yaptım" iddiasını doğrulamanın ana yolu bu.

- **Yeni kod gerekir** (geçmişte yok). `tools/olcum.py` içine `icerik_ara(proje, sorgu, uzanti=None)`.
- Beyaz liste `PROJELER`'den gelir (`_kok`), dışına çıkılmaz.
- Atlanacak klasörler: `.git`, `node_modules`, `__pycache__`, `build`, `dist`, `.next`, `venv`.
- Sınırlar: dosya başı 1 MB tavanı, en fazla 8 eşleşme (`_MAX_ESLESME`), çıktı 1.500 karakter (`_MAX_CIKTI`). İkili dosya okunmaz.
- Dönüş: `dosya:satır: içerik` biçiminde.
- Tetikleyiciler: `"hangi dosyada"`, `"geçiyor mu"`, `"var mı"`, `"nerede yazıyor"`, `"ara kodda"`.

**Kabul kanıtı:** Temiz hafızayla "vixrex'te `_guvenli_yolu_coz` hangi dosyada geçiyor?" → gerçek dosya/satır döner; aynı sorgu `grep` ile birebir doğrulanır.

### FAZ 7 — GitHub durumu (PR + CI)

**Neden:** İş akışı PR üzerinden yürüyor. "Birleşti mi", "**CI yeşil mi**" sorusunun nesnel cevabı burada. Ajanın yeşil dediği CI gerçekten yeşil mi, tek kanıt bu.

- **Yeni anahtar GEREKMEZ.** `gh` makinede kurulu ve yetkili (hesap: `xpodiumyours`, ölçüldü 2026-09-13).
- Depo eşlemesi (ölçüldü, uydurulmayacak):

  | proje | depo |
  |---|---|
  | basak | `xpodiumyours/basak-ai` |
  | vixrex | `xpodiumyours/vixrex` |
  | numeramatch | `xpodiumyours/NumeraMatch` |
  | xses | `xpodiumyours/xses` |

- `subprocess` **sabit argv**, `shell=False`, `timeout=20`. Serbest komut YOK — yalnız şu üçü:
  - `gh pr list --repo R --state S --json number,title,state,headRefName`
  - `gh pr view N --repo R --json number,title,state,mergedAt,statusCheckRollup`
  - `gh run list --repo R --limit 5 --json name,status,conclusion,headBranch`
- Model depo adı **veremez**; yalnız proje anahtarı verir, eşleme koddadır.
- Tetikleyiciler: `"pr"`, `"pull request"`, `"ci"`, `"birleşti mi"`, `"test geçti mi"`, `"kontroller"`.

**Kabul kanıtı:** "vixrex'te açık PR var mı" → gerçek liste; aynı sonuç `gh pr list` ile birebir doğrulanır. Uydurma depo adı denemesi reddedilir.

### FAZ 8 — Git geçmişi ve değişenler

**Neden:** `git_durum` yalnız dal + SON commit + kirli dosya sayısı veriyor. "Bu dalda ne değişti", "şu dosyaya en son ne zaman dokunuldu" sorulamıyor.

- `tools/olcum.py`'deki mevcut `_git()` yardımcısı kullanılır (sabit argv, `shell=False`, `timeout=10`) — yeni bir komut çalıştırıcı YAZILMAZ.
- İki fonksiyon:
  - `git_gecmis(proje, dosya=None, adet=10)` → `log --oneline -n <adet> [-- <dosya>]`
  - `git_degisenler(proje, taban="origin/master")` → `diff --stat <taban>...HEAD`
- `adet` üst sınırı 30; `dosya` proje kökü dışına çıkamaz (yol `_kok` içinde çözülür).
- Tetikleyiciler: `"ne değişti"`, `"son commitler"`, `"geçmiş"`, `"kim değiştirdi"`, `"diff"`.

**Kabul kanıtı:** "basak'ta son 5 commit ne" → çıktı `git log --oneline -5` ile birebir aynı.

### BEKLEMEDE — şimdilik yapılmayacak

| Araç | Neden beklemede |
|---|---|
| **Canlı adres kontrolü** (HTTP durum kodu, yanıt süresi) | Faydalı ama `sayfa_oku` çoğu durumu zaten yakalıyor. Sıra 6-8'den sonra. |
| **Test koşturma** (`pytest`) | En güçlü kanıt AMA kod çalıştırıyor — diğer araçların hepsi yalnız okuyor. Onay katmanı tartışmasını geri getirir. Casper ayrıca karar verecek. |

---

## 3. DOKUNULMAZ — bu dosyalar değişirse faz REDDEDİLİR

ChatGPT bu dosyalara dokunmayacak. Dokunulmuşsa Claude birleştirmez, gerekçesiyle geri gönderir.

| Dosya / değer | Neden |
|---|---|
| `brain/` klasörünün tamamı | Ücretsiz model zinciri. Sıra, kota, soğuma, sayaç. Araç işiyle ilgisi yok. |
| `memory/` klasörünün tamamı | Kalıcı hafıza. |
| `tools/file_ops.py` içindeki `_guvenli_yolu_coz` ve kara liste | Yol kaçışı koruması, gerçek Windows junction'la kanıtlanmış. |
| `tools/web_search.py` içindeki `_engelli_ip_nedeni`, `_guvenli_adres`, `_GuvenliYonlendirme` | SSRF savunması. |
| `tools/olcum.py` içindeki `PROJELER` beyaz listesi ve `_git()` | `shell=False`, sabit argv. Buraya serbest komut eklenmeyecek. |
| `tools/definitions.py` `TANINMIS_TOOLLAR` üretimi | Beyaz liste. Elle isim eklenmeyecek, `TOOLS`'tan türetilecek. |

## 4. GERİ GELMEYECEK — bunlar bilerek söküldü

Bir faz bunlardan birini geri getirirse **reddedilir**:

- İzin etiketleri tablosu, etiket→politika eşlemesi (`permissions.py`)
- Onay kuyruğu / onay kutusu (`chat/approval.py`, UI onay modalı)
- Ölçü çıkış kapısı, `[Ö]/[A]/[Ç]/[B]` işaretleme (`olcu.py`)
- Orkestra, jüri, gölge mod
- Kapasite hesabı (`mod_kapasite`) ile araç setini daraltma
- Yetki tavanı mantığı
- Ortak defter (`defter/`)

## 5. AYRICA KORUNACAK — sessizce geri alınması en olası şeyler

Bunlar bu gece ölçülerek kazanıldı. Faz diff'inde geri alınmışsa reddedilir:

1. **Tavanlar:** `max_tokens=4096`, `temperature` satırı YOK, `timeout=20.0`. `brain/yayin.py` dahil.
2. **Ölçüm tazeliği** (`chat/flow.py`): araç açıkken (a) `ilgili_anilar` çağrılmaz, (b) geçmiş penceresinden `assistant` mesajları çıkarılır. Ölçülmüş etki: araç koşma oranı %50 → %100.
3. **Tek çıkış kapısı:** cevap her zaman `BasakUI.bitir` ile gider (`reply` doğrudan çağrılmaz).
4. **Kimlik:** `KIMLIK_BLOGU` ve `KISILIK` ikisi de "Başak" der.

## 6. Claude'un doğrulama kapısı — her faz için

Faz dalı hazır denince Claude şunları koşturur. **Hepsi geçmeden birleştirme yok.**

| # | Kapı | Kabul |
|---|---|---|
| 1 | `git diff sadelestirme..<dal>` — satır satır okunur | §3'teki dosyalara dokunulmamış, §4'ten bir şey geri gelmemiş |
| 2 | `python -m pytest tests -q` | Tamamı yeşil **ve test sayısı 182'nin altına düşmemiş** (sessizce silinen test yakalanır) |
| 3 | §5 maddelerinin grep'i | Dördü de yerinde |
| 4 | `python -c "import basak_app"` | Hatasız |
| 5 | Temiz hafızada canlı prova | Fazın kabul kanıtı gerçekten üretilir |
| 6 | Güvenlik testleri | `test_path_guvenligi.py` + `test_ssrf_korumasi.py` yeşil |
| 7 | Yan etki ölçümü | Düz sohbet hâlâ akıyor (araç koşmuyor), ölçüm sorusu hâlâ %100 araç koşuyor |

**Kapı 2'deki sayı önemli:** test silerek yeşile boyamak en kolay sabotaj. Sayı düşerse hangi testin gittiği sorulur.

## 7. Çalışma kuralları (ChatGPT için)

- Dal adı: `arac-faz1`, `arac-faz2`, ... Taban her zaman `sadelestirme`, bir önceki faz birleştikten sonra güncel taban alınır.
- **Bir faz = bir dal = bir commit.** Fazları birleştirme.
- Kodu yeniden yazma — geçmişte hazır olanı `git checkout 27b03a9 -- <dosya>` ile al. Yeniden yazılan güvenlik kodu kabul edilmez.
- `ayarlar.json` commit'e girmez (`.gitignore`'da, öyle kalacak).
- "Çalışıyor" demeden önce uygulamayı gerçekten aç ve dene; konsol çıktısını paylaş.
- Emin olmadığın yerde dur ve sor. Tahminle kod yazma.
