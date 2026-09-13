# ARAÇ PLANI — tek iş, tek dal

**Tarih:** 2026-09-13 · **Karar:** Casper · **Taban dal:** `sadelestirme` (`a218f2b`)

> **2026-09-13 güncellemesi:** Bu plan eskiden 8 ayrı faza bölünmüştü ve her faz için Claude'un onayı bekleniyordu. Casper kaldırdı: **ChatGPT durmadan, tek oturumda, hepsini bitirir.** Fazlar arası bekleme yok.

## 0. İş bölümü

| Kim | Ne yapar |
|---|---|
| **Casper** | Kapsamı belirler |
| **Claude** | Bu tarifi yazar, iş bitince **bir kez** doğrular, birleştirir |
| **ChatGPT** | Tek dalda hepsini yazar, **adım başına bir commit** atar, bitince haber verir |

**Tek kural:** adımlar ayrı commit olacak. Tek dev commit KABUL EDİLMEZ — bir şey bozulduğunda hangi adımın bozduğu bulunamaz ve işin tamamı geri gider. Ayrı commit'te yalnız bozulan çıkarılır.

Dal adı: **`arac-tam`**, taban `sadelestirme`.

## 1. Şu anki durum

FAZ 1 bitti ve birleşti (`a218f2b`). Başak'ta **sekiz** araç var, hepsi salt-okunur:
`web_search`, `sayfa_oku`, `read_file`, `list_files`, `git_durum`, `belge_ara`, `dosya_bilgi`, `image_analyze`

**Ölçülmüş taban:** 182 test geçiyor, 7 atlanıyor.

## 2. Yapılacak işler (sırayla, her biri ayrı commit)

> ### Araçlar modele HER ZAMAN sunulur
>
> Kelime listesiyle araç açıp kapatan katman kaldırıldı (`sadelestirme@85107b8`). `chat/flow.py` içinde `_ARAC_ISARETLERI` ve `_arac_gerek()` **artık yok**; araçlar hem tam yola hem akışa her mesajda gidiyor, hangisini kullanacağına **model karar veriyor**.
>
> Bu planın önceki sürümü her iş için tetikleyici kelime eklemeyi istiyordu — **o madde yanlıştı, Claude yazmıştı, kaldırıldı.** ChatGPT onu sorgusuz uyguladı ve `arac-tam` üzerindeki İş 1-3 commitlerinde tetikleyici eklemeleri var; birleştirmeden önce çıkarılacak.
>
> **Yeni araç eklerken kelime/tetikleyici mantığı YAZILMAZ.** Araç şemasının açıklaması ne yaptığını, ne aldığını, ne döndürdüğünü ve sınırını söyler — model seçimini ondan yapar. Açıklamaya davranış koçluğu ("şunu kullanma", "şöyle cevapla") yazılmaz.

### İş 1 — Dosya yazma
- `tools/file_ops.py` `write_file_ops(yol, icerik, base_dir)` **zaten yazılı**, yol güvenliği testli. Yeniden yazma.
- `write_file_tool` şeması + `calistir()` dalı + `DURUM_METNI` etiketi.
- **Sınır:** yalnız `knowledge/` altına. `OTOMATIK_YAZMA_KOKLER` tablosunu değiştirme.
- **Onay kutusu ekleme.**
- `chat/prompts.py` `TOOL_YONLENDIRME`'deki "Yazma, silme ve uygulama açma yetkin YOK" cümlesini güncelle.

### İş 2 — Hatırlatmalar ve görev listesi
- `git checkout 27b03a9 -- tools/reminders.py tools/tasks.py`
- `get_reminders`, `add_task`, `list_tasks`, `complete_task` şemaları + dalları.
- `tasks.py`'deki `threading.Lock` + atomik `os.replace` korumasını bozma.

### İş 3 — Uygulama açma
- `git checkout 27b03a9 -- tools/app_launcher.py`
- `ac_uygulama` şeması + dalı.
- Onay katmanı ekleme (2026-08-25 Casper kararı).

### İş 4 — İçerik arama (proje genelinde) — **yeni kod**
- `belge_ara` yalnız proje **kök** `.md` dosyalarına bakıyor (`os.listdir`, özyinelemeli değil). Ölçüldü: "matris" vixrex kökünde yok ama alt klasörlerde var — bu yüzden gerekiyor.
- `tools/olcum.py` içine `icerik_ara(proje, sorgu, uzanti=None)`.
- Beyaz liste `PROJELER`'den (`_kok`), dışına çıkılmaz.
- Atlanacak klasörler: `.git`, `node_modules`, `__pycache__`, `build`, `dist`, `.next`, `venv`, `.codex-worktrees`.
- Sınırlar: dosya başı 1 MB, en fazla 8 eşleşme, çıktı 1.500 karakter. İkili dosya okunmaz.
- Dönüş: `dosya:satır: içerik`.

> ### ⚠️ SIR SIZINTISI — bu maddeyi atlama
>
> **Ölçüldü (2026-09-13):** `C:\Projects\vixrex` içinde gerçek `.env.local` (16 satırda anahtar deseni), `.env.production` (11), `.env.vercel-tesis` (10) ve benzerleri var. `xses`'te de bir tane. `icerik_ara` özyinelemeli tarama yaptığı için bu dosyaları okur ve eşleşen satırlar **ücretsiz bulut modeline gider**. Kilo'nun kartında "gönderilen yazıları kaydedebilir" yazıyor.
>
> `read_file` bu dosyaları zaten engelliyor (`file_ops.YASAK_DOSYA_KALIPLARI` — ölçüldü, `.env.local` ve `.env.production` denendi, ikisi de reddedildi). `icerik_ara` **aynı korumayı kullanmak zorunda**:
>
> 1. `from tools.file_ops import YASAK_DOSYA_KALIPLARI, _yasak_mi` — yeni kara liste YAZMA, mevcudunu kullan. Kalıba uyan dosya hiç açılmaz.
> 2. Buna ek olarak **çıktı maskelenir**: dönen satırlarda `api_key`, `token`, `parola`, `secret`, `sk-`, `ghp_`, `gsk_`, `nvapi-`, `eyJ`, `Bearer` desenleri `***` ile değiştirilir. Hazır kod var: `git show 27b03a9:tools/tool_logger.py` içindeki `_kirmala`. Onu al, yeniden yazma.
> 3. Sebep: kara liste dosya ADINA bakar. Normal adlı bir dosyada (örn. `config.ts`) gömülü anahtar varsa ad koruması yakalamaz — maskeleme ikinci savunma hattıdır.
>
> **Kabul kanıtı (Claude ölçecek):** "vixrex'te SUPABASE geçiyor mu" sorulur. `.env.local` içeriği çıktıda **görünmeyecek**; görünürse iş reddedilir.

### İş 5 — GitHub durumu (PR + CI)
- `gh` kurulu ve yetkili (`xpodiumyours`, ölçüldü). Yeni anahtar gerekmez.
- Depo eşlemesi **kodda sabit** (ölçüldü, `git remote`'tan alındı). Model depo adı **veremez**, yalnız proje anahtarı verir:

  | proje | depo |
  |---|---|
  | basak | `xpodiumyours/basak-ai` |
  | vixrex | `xpodiumyours/vixrex` |
  | numeramatch | `xpodiumyours/NumeraMatch` |
  | xses | `xpodiumyours/xses` |

- `subprocess` **sabit argv**, `shell=False`, `timeout=20`. Yalnız şu üçü:
  - `gh pr list --repo R --state S --json number,title,state,headRefName`
  - `gh pr view N --repo R --json number,title,state,mergedAt,statusCheckRollup`
  - `gh run list --repo R --limit 5 --json name,status,conclusion,headBranch`

### İş 6 — Git geçmişi ve değişenler
- Mevcut `_git()` yardımcısı kullanılır — yeni komut çalıştırıcı yazma.
- `git_gecmis(proje, dosya=None, adet=10)` → `log --oneline -n`
- `git_degisenler(proje, taban="origin/master")` → `diff --stat <taban>...HEAD`
- `adet` tavanı 30; `dosya` proje kökü dışına çıkamaz.

### İş 7 — Canlı adres kontrolü
- `tools/web_search.py` içindeki mevcut SSRF savunmasını (`_guvenli_adres`) **kullan**, yenisini yazma.
- `adres_kontrol(url)` → HTTP durum kodu + yanıt süresi + son yönlendirme adresi. Gövde indirilmez (HEAD, olmazsa kısa GET).

### İş 8 — Test koşturma ⚠️
**Bu, kod ÇALIŞTIRAN tek araç.** Diğer on bir tanesi yalnız okuyor. Casper bilerek istedi.

- `testleri_kos(proje)` → komut **kodda sabit tablodan** gelir, model komut veremez:

  | proje | komut | durum |
  |---|---|---|
  | basak | `python -m pytest tests -q` | doğrulandı, çalışıyor |
  | vixrex / numeramatch / xses | **ChatGPT ölçecek** — depoda gerçek test komutu ne, bak ve yaz. Bulamazsan o projeyi tabloya ekleme, "bu projede test komutu tanımlı değil" döndür. Uydurma. |

- `shell=False`, sabit argv, `timeout=300`, çıktı son 2.000 karakterle sınırlı.
- Çalışma dizini `PROJELER`'deki kök; başka dizinde koşmaz.

---

## 3. DOKUNULMAZ — değişirse iş reddedilir

| Dosya / değer | Neden |
|---|---|
| `brain/` klasörünün tamamı | Ücretsiz model zinciri: sıra, kota, soğuma, sayaç |
| `memory/` klasörünün tamamı | Kalıcı hafıza |
| `tools/file_ops.py` → `_guvenli_yolu_coz` + kara liste | Yol kaçışı koruması, Windows junction ile kanıtlı |
| `tools/web_search.py` → `_engelli_ip_nedeni`, `_guvenli_adres`, `_GuvenliYonlendirme` | SSRF savunması |
| `tools/olcum.py` → `PROJELER`, `_kok()`, `_git()` | Beyaz liste + sabit argv. Serbest komut eklenmez |
| `tools/definitions.py` → `TANINMIS_TOOLLAR` üretimi | `TOOLS`'tan türetilir, elle isim yazılmaz |

## 4. GERİ GELMEYECEK — bilerek söküldü

İzin etiketleri tablosu · onay kuyruğu/kutusu · ölçü çıkış kapısı (`[Ö]/[A]/[Ç]/[B]`) · orkestra · jüri · gölge mod · kapasite hesabıyla araç daraltma · yetki tavanı · ortak defter (`defter/`)

## 5. SESSİZCE GERİ ALINMASI EN OLASI DÖRT ŞEY

Bunlar ölçülerek kazanıldı. Diff'te geri alınmışsa iş reddedilir:

1. **Tavanlar:** `max_tokens=4096`, `temperature` satırı YOK, `timeout=20.0` — `brain/yayin.py` dahil.
2. **Ölçüm tazeliği** (`chat/flow.py`): araç açıkken (a) `ilgili_anilar` çağrılmaz, (b) geçmiş penceresinden `assistant` mesajları çıkarılır. Ölçülmüş etki: %50 → %100.
3. **Tek çıkış kapısı:** cevap her zaman `BasakUI.bitir` (doğrudan `reply` yok).
4. **Kimlik:** `KIMLIK_BLOGU` ve `KISILIK` ikisi de "Başak".

## 6. Claude'un doğrulaması — iş bitince BİR KEZ

| # | Kapı | Kabul |
|---|---|---|
| 1 | `git diff sadelestirme..arac-tam` satır satır | §3'e dokunulmamış, §4'ten bir şey gelmemiş |
| 2 | `python -m pytest tests -q` | Yeşil **ve sayı 182'nin altına düşmemiş** |
| 3 | §5'in dördü | Hepsi yerinde |
| 4 | `python -c "import basak_app"` | Hatasız |
| 5 | Temiz hafızada canlı prova | Her araç gerçekten koşar; çıktısı bağımsız komutla doğrulanır |
| 6 | Güvenlik testleri | Yol kaçışı + SSRF yeşil |
| 7 | Yan etki | Düz sohbet hâlâ akıyor; ölçüm sorusu hâlâ araç koşturuyor |
| 8 | **Yazma sınırı** | `knowledge/` dışına yazma denemesi reddedilir — dosyanın oluşmadığı **diskte** doğrulanır |
| 9 | **Sır sızıntısı** | "vixrex'te SUPABASE geçiyor mu" sorulur; `.env` içeriği çıktıda görünmemeli |
| 10 | **GitHub salt-okunur** | `gh` çağrılarında yalnız `pr list` / `pr view` / `run list` var; `merge`, `create`, `close`, `delete` YOK |
| 11 | **Test komutu sabit** | `testleri_kos` model argümanı almıyor; komut kodda tablodan geliyor |

Bir commit kapıdan geçmezse **yalnız o commit** geri alınır, gerisi birleşir.

## 7. Çalışma kuralları

- **Casper'ın klasöründe (`C:\Users\Casper\Projects\basak-ai`) doğrudan çalışma.** Orada Başak açık çalışıyor ve Claude ölçüm yapıyor. 13 Eylül gecesi aynı klasörde 294 dosya kaydedilmeden silindi. Kendi kopyanda çalış, dalı GitHub'a it.
- **Bir adım = bir commit.** Commit mesajı hangi adım olduğunu yazsın.
- Kodu yeniden yazma — geçmişte hazır olanı `git checkout 27b03a9 -- <dosya>` ile al. Yeniden yazılan güvenlik kodu kabul edilmez.
- Her yeni araç için üç yer: şema (`definitions.py`) + dal (`tools/__init__.py`) + durum etiketi (`chat/tools.py` `DURUM_METNI`). Üçü birden yapılmazsa araç sessizce ölü kalır.
- `ayarlar.json` commit'e girmez.
- Emin olmadığın yerde **dur ve sor**. Tahminle kod yazma, komut uydurma.
