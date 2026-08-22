# GELİŞİM SÜRECİ — Başak'ın tek iş emri

*Son güncelleme: 22 Ağustos 2026*

**Bu dosya tek kapıdır.** Kod yazan ajan buradan başlar, fazları sırayla yürür, her fazın kabul ölçütünü kanıtlar. Dağınık görev dosyası yok — detay gereken fazlar buradan **eke** yönlendirir.

Casper kod yazmıyor. Doğal dille tarif ediyor, kararı o veriyor. Tarifi karara çevirmek ajanın işi.

---

## 0. Bağlayıcı kurallar

1. **Kanıt kapısı.** Faz, kabul ölçütü gösterilmeden kapanmaz. "Yazdım, çalışıyor herhalde" geçersiz.
2. **Sırayla git.** Ana hattaki fazlar birbirine yaslanıyor. Atlama yok.
3. **Durak noktalarında dur.** ⛔ işaretli fazlarda Casper onayı alınmadan devam edilmez. Ajan kendi kendine yetki genişletemez.
4. **Küçük düzeltme yap, dosyayı yeniden yazma** (`AGENTS.md` §5).
5. **Ücretsiz kal.** Ücretli çağrı varsayılan kapalı.
6. **Kapsam büyütme.** Sormadığı özelliği ekleme. Fikir çıkarsa Karar Defteri'ne yaz, Casper onaylamadan uygulama.
7. **Sır asla kayda girmez.** Anahtar, parola — ne commit'e ne deftere.
8. **Türkçe karakter tuzağı.** `ş, ı, ç` içeren dosyada düzenleme aracı eşleşmezse PowerShell `.Replace` ile dosyanın kendi içeriği üzerinden değiştir, `grep` ile doğrula (`AGENTS.md` §8).

---

## 1. Harita

**Ana hat** — sırayla yürünür:

| # | Faz | Ne kazandırır | Durak |
|---|---|---|---|
| 1 | **D** | Kırık olanı onar | |
| 2 | **OD-0** | Ortak defter — bilgi birikmeye başlar | |
| 3 | **Ö-0** | Uydurma cümle çıkışta engellenir | |
| 4 | **Ö-1** | Önce ölç, sonra konuş | |
| 5 | **OD-1** | Defter iki yönlü olur | |
| 6 | **E-1** | Başak projelerini görür | |
| 7 | **E-2** | Gerçek araştırma yapar | |
| 8 | **Ö-2** | İddia defteri + bayatlama | |
| 9 | **E-3** | Sen sormadan da çalışır | ⛔ |
| 10 | **Ö-3** | Kendi kendine gelişmeye başlar | |
| 11 | **OD-2** | Defter büyüse de boğulmaz | |
| 12 | **OD-3** | Çelişkiler görünür olur | |
| 13 | **K-4** | POTA kazananı kurulur | ⛔ |
| 14 | **E-4** | Bilgisayar işleri | ⛔ |

**Yan hatlar** — ana hattı beklemez, paralel yürüyebilir:

| Faz | Ne | Durak |
|---|---|---|
| **POTA-1** | Algoritma damıtma turu (ajan elle yürütür, kod yazmaz) | ⛔ |
| **UI-K** | Arka plandaki küre | |

---

## 2. ANA HAT

### D — Düzeltmeler  ·  *şu an ajanda*

Ölçüm sırasında bulunan üç gerçek arıza. Ayrıntı ve kanıtlar: **`düzenleme.md`**

- **D-1** oturum kimliği isteğe sızıyor, Groq 400 ile reddediyor
- **D-2** `gorevler.json` görünmez işaret yüzünden okunmuyor
- **D-3** gerçek kota kapasitesi ölçülecek (kod değil, ölçüm)

**Kabul:** `düzenleme.md`'deki üç kabul ölçütü de kanıtlanır.

---

### OD-0 — Ortak defter, tek yön

Tasarım: **`ORTAK-DEFTER.md`** (biçim, kurallar, ne girer ne girmez)

**Yapılacak:**
1. `defter/` klasörü açılır, `INDEX.md` elle yazılır.
2. `chat.py` her mesaja **sadece `defter/INDEX.md`**'yi ekler — tek tek kayıtları değil.
3. `memory/engine.py` indekslemesine `defter/` eklenir.

⚠️ Kayıtların tamamını bağlama ekleme. `chat.py:27` sınırı var (`KNOWLEDGE_MAX_CHARS = 5000`) ve aşılınca **sessizce kesiyor**. Sebebi `ORTAK-DEFTER.md` §4'te.

**Kabul:** Claude deftere bir kayıt yazar. Casper, Başak'a hiçbir şey anlatmadan sorar — Başak o bilgiyle cevap verir. Kayıt silinince artık bilmez.

---

### Ö-0 — Cümle tipleri + çıkış kapısı

Tasarım: **`OLCU.md`** §2

**Yapılacak:** Dört tip (`ölçüm` / `alıntı` / `çıkarım` / `bilmiyorum`), cevap çıkmadan önce denetim, **alıntı doğrulama** — belirtilen dosyada birebir metin araması, eşleşmezse cümle silinir.

**Kabul:** 10 zor soru. (a) Uydurma alıntı **sıfır** — her alıntının kaynağı elle açılıp doğrulanır. (b) Kaynaksız iddia çıkışa hiç ulaşmaz. (c) Cevabı olmayan soruda "bilmiyorum" çıkar, uydurma çıkmaz.

---

### Ö-1 — Önce ölç, sonra konuş

Tasarım: **`OLCU.md`** §3 (çözüm planı + ölçüm izin listesi)

**Yapılacak:** Soru gelince önce "bunu ne çözer" planı çıkarılır, ölçümler çalıştırılır, cevap yalnız çıktılardan kurulur. Plan boşsa cevap: *"Bunu ölçemem, şu ölçülebilirdi..."*

**Kabul:** "VixRex'te durum ne" sorusuna gelen cevabın her cümlesi git/dosya çıktısına dayanıyor; modelin kendi bilgisinden gelen tek cümle yok.

---

### OD-1 — Defter iki yön

**Yapılacak:** `save_note` aracı `defter/`e yönlendirilir ve biçime uyar (kim/tarih/tip/ömür/kaynak).

**Kabul:** Casper Başak'a bir şey söyler → Başak deftere yazar → Claude sonraki oturumda o bilgiyle gelir.

---

### E-1 — Başak projelerini görür

**Sorun (ölçüldü):** `tools/file_ops.py:14` → izinli klasör tek: `knowledge`. `chat.py` yalnız `BASE/knowledge` ve `BASE/Basak` indeksliyor. VixRex, NumeraMatch, Xses Başak için **yok**.

**Yapılacak:** Bu üç proje **salt okunur** kaynak olarak tanımlanır:

| Proje | Yol |
|---|---|
| VixRex | `C:\Projects\vixrex` |
| NumeraMatch | `C:\Users\Casper\source\NumeraMatch` |
| Xses | `C:\Projects\xses` |

*(Üçü de 22 Ağustos'ta doğrulandı, git depoları yerinde.)*

Kurallar:
- **Yalnız okuma.** Yazma yok, git'e yazan komut yok.
- Belge dosyaları (`*.md`) indekslenir; kod indekslenmez — hafızayı boğar, zaten git'te.
- Her okuma kaynağıyla birlikte kaydedilir (Ö-0'ın alıntı doğrulaması geçerli).

**Kabul:** "VixRex'te kiralık vitrin planı ne diyor" sorusuna Başak, doğru dosya adı ve satırı göstererek cevap verir.

---

### E-2 — Gerçek araştırma

**Sorun (ölçüldü):** `tools/web_search.py:121,138` → arama sonucundan en fazla **2 özet parçası** dönüyor. Sayfa açıp okuma yok, bulduğu hafızaya girmiyor.

**Yapılacak:**
1. Sayfa okuma aracı — bir adresi açıp metnini çıkarır (yalnız `GET`).
2. Araştırma sonucu **deftere kayıt** olarak yazılır: kaynak adres + tarih + tek paragraf sonuç.

**Kabul:** Bir konu araştırılır, sonuç deftere düşer, ertesi gün aynı konu sorulduğunda Başak **yeniden aramadan** kendi kaydından cevap verir.

---

### Ö-2 — İddia defteri + bayatlama

Tasarım: **`OLCU.md`** §5 (ömür tablosu) ve §6 (defter)

**Kabul:** Defter doluyor. Ömrü geçmiş bilgi kullanılmadan önce yeniden ölçülüyor; ölçülemiyorsa "bayat" diye sunuluyor.

---

### E-3 — Sen sormadan çalışma  ⛔ *onay gerekir*

**Sorun (ölçüldü):** Zamanlayıcı/tetikleyici yok. Başak yalnız sorulunca konuşuyor.

**Yapılacak:** Zamanlanmış iş düzeni. **Sessiz saat kuralıyla** — Casper dükkânda çalışıyor, rastgele saatte konuşamaz.

⛔ **Durak:** Ne sıklıkta ve hangi saatlerde konuşacağı Casper'ın kararı. Sormadan varsayma.

**Kabul:** Belirlenen saatte tek bir kart çıkar, fazlası çıkmaz. Cevaplanmazsa dırdır etmez.

---

### Ö-3 — Kendi kendine gelişme

Tasarım: **`OLCU.md`** §6 (otomatik yeniden sınav + karne)

**Kabul:** En az bir eski iddia, Casper hiçbir şey söylemeden, yeni bir ölçümle **otomatik çürütülüyor** — ve o kaynağın karnesi değişiyor.

---

### OD-2 — Defter büyüse de boğulmaz

**Yapılacak:** `INDEX.md` elle yazılmaktan çıkar, kayıtlardan üretilir. Kayıtlar arama yoluyla çekilir.

⚠️ **Erken tetik:** Defter **30 kaydı** geçerse bu faz sıradan öne alınır. Sınırın sessizce kesmesi en tehlikeli arıza.

**Kabul:** 50 kayıtla test — bağlam sınırı aşılmıyor, ilgili kayıt yine de bulunuyor.

---

### OD-3 — Çelişkiler görünür

**Yapılacak:** `celisir:` alanı işlenir; ömrü geçen kayıtlar bayat işaretlenir.

**Kabul:** İki çelişen kayıt konur — sistem ikisini de gösterip soruyu sorar, birini seçip diğerini gizlemez.

---

### K-4 — POTA kazananı  ⛔ *onay gerekir*

POTA turları bitip Casper bir aday seçtiğinde, o algoritma **katman 4** olarak kurulur. Aday FAY çıkarsa ayrıntı `FAY-MOTORU.md` ve aşağıdaki FAY fazlarındadır.

⛔ **Durak:** Kazanan Casper'ın kararıdır. Ajan kendi seçmez.

<details>
<summary>FAY kazanırsa uygulanacak fazlar</summary>

- **FAY-0** tek konu, üç tanık (belge/git/dosya), jürisiz. Kabul: çıkan her çelişki gerçek, uydurma sıfır, en az 1 gerçek çelişki.
- **FAY-1** paralel jüri. **Önce D-3'ün kota ölçümüne bakılır** — kapasite yoksa jüri kurulmaz.
- **FAY-2** gerilim puanı ve dırdır etmeyen kuyruk. Kabul: günde en fazla 1 kart.
- **FAY-3** aktarıcı — kendi külliyatından mekanizma transferi. Kabul: Casper'ın "bunu düşünmemiştim" dediği en az bir aktarım.
- **FAY-4** karne, model seçicisine bağlanır.
</details>

---

### E-4 — Bilgisayar işleri  ⛔ *onay gerekir, en riskli*

Dosya arama/düzenleme, izinli terminal. `GOREV_LISTESI.md` §7'de **en sıkı kuralla en son** açılacağı yazılı — o karar geçerli.

⛔ **Durak:** Her yeni yetki ayrı Casper onayı ister. Komut enjeksiyonu sondası tekrar koşar ve temiz çıkar.

---

### Sonrası

`GOREV_LISTESI.md`'deki **P6** (Başak API, Web UI v2, dosya hafızası, iş kuyruğu) ve **P7** (sesli Jarvis: uyandırma kelimesi, sürekli dinleme) yerinde duruyor. Sırası geldiğinde buraya faz olarak işlenir.

---

## 3. YAN HATLAR

### POTA-1 — Algoritma damıtma turu  ⛔ *onay gerekir*

Ek: **`gorev-pota-tur1.md`** · Tasarım: **`POTA.md`**

Ajan **kod yazmaz** — külliyatı tarar, acı haritasını çıkarır, 9 aday üretir, geriye dönük sınavı uygular, tek karşılaştırma kartı hazırlar.

⛔ **Durak:** Kart Casper'a gider. Kazananı ajan ilan etmez.

**Kabul:** `gorev-pota-tur1.md`'deki 7 maddelik kabul listesi.

---

### UI-K — Arka plandaki küre

Ek: **`gorev-kure.md`**

İnsan silüeti bırakıldı, yerine enerji küresi. **Önce durumu kontrol et** — bu görev daha önce ajana verildi, uygulanıp uygulanmadığı belirsiz. `ui/head.js`'e bakıp `profil()` fonksiyonunun küre mi insan mı ürettiğini gör, ona göre başla veya atla.

---

## 4. Onay noktaları — Casper'ın karar vereceği yerler

| Nerede | Karar |
|---|---|
| POTA-1 sonunda | Hangi aday kazandı |
| E-3 öncesi | Hangi saatlerde, ne sıklıkta konuşsun |
| K-4 öncesi | Kazanan algoritma kurulsun mu |
| E-4'te her yetki | Bu yetki verilsin mi |

**Bekleyen küçük karar:** Fay/durum kartı sesli de okunsun mu, yalnız yazılı mı?

---

## 5. Karar defteri

| Tarih | Karar | Gerekçe |
|---|---|---|
| 2026-08-22 | Motor asla düzeltme uygulamaz | Karar Casper'ın; motor hakem değil, tanık |
| 2026-08-22 | Önce POTA, sonra inşa | FAY Claude'un önerisiydi; gerçekten istenen algoritma olduğu kanıtlanmadı |
| 2026-08-22 | FAY potaya `aday #0` olarak girer, ayrıcalığı yok | Kendi tasarımını sınavdan muaf tutmak motorun varlık sebebine aykırı |
| 2026-08-22 | POTA Tur 1 yazılım yazılmadan, elle yürütülür | Haftalarca kod yazmadan önce değer kanıtlansın |
| 2026-08-22 | Düzeltmeler (D) araya alındı, ana yoldan önce | Kırık zemin üstüne kat çıkılmaz |
| 2026-08-22 | ÖLÇÜ yarışmaz, zemindir | "Varsayım ve tahmin yürütmeden" şartı bir mimari kısıt, özellik değil |
| 2026-08-22 | Ortak defter eksikler listesinde 1. sıra | Diğer eksikler bilgi üretiyor; defter olmadan üretilen bilgi birikmiyor |
| 2026-08-22 | Defter kayıtları her mesaja eklenmez, sadece INDEX | 5.000 karakter sınırı aşılınca sessizce kesiyor — fark edilmesi en zor arıza |
| 2026-08-22 | Projelere erişim salt okunur, kod indekslenmez | Yazma yetkisi ayrı ve riskli bir karar; kod zaten git'te |

---

## 6. Durum tahtası

**İşaretler:** ✅ bitti (kanıtlı) · 🔧 kod var, kanıt yok · ▶ şu an · 📌 sırada · ⏸ bekliyor · ❓ durumu bilinmiyor

| Faz | Durum | Kanıt / not |
|---|---|---|
| D-1 | ✅ bitti (kanıtlı) | Dolu geçmişle (24 mesaj, `oturum` alanlı) canlı zincirde 6 soru: yeni `property 'oturum' is unsupported` satırı **sıfır**; audit'te `OK kaynak=groq` ×9 (14:03–14:08); `_temizle_history` birim kontrolü: sızıntı 0 |
| D-2 | ✅ bitti (kanıtlı) | BOM'lu `gorevler.json` gerçek araç yoluyla okundu (`list_tasks` → cevap geldi); yeni `Gorevler okunamadi` kaydı **sıfır**; elle BOM testi ✓; `pytest` 74/74 yeşil; okuyucular: chat.py, reminders.py, brain.py, kota.py, tasks.py hepsi `utf-8-sig` |
| D-3 | ✅ bitti (kanıtlı) | **`data/kota-gercek.md`** yazıldı — yedi sağlayıcı tabloda, her sayının kaynağı belli. Sonuç: jüri güvenilir havuzu groq+glm+nvidia, günde ~1–2 tur |
| OD-0 | ✅ bitti (kanıtlı) | `defter/` + elle yazılmış INDEX kuruldu; `chat.py` yalnız INDEX'i ekliyor (5.119 karakterlik blokta yer aldı), hafıza motoru `defter/`i indeksliyor. Kanıt (başsız gerçek zincir): kayıt dururken "paralel jüri hangi sağlayıcılar" sorusuna **groq+glm+nvidia, günde 1–2 tur** cevabı defterden geldi; kayıt silinince aynı soruya uydurma genel cevap verdi — defter bilgisi kaynağıydı |
| Ö-0 | 📌 | |
| Ö-1 | 📌 | |
| OD-1 | 📌 | |
| E-1 | 📌 | yollar 22 Ağustos'ta doğrulandı |
| E-2 | 📌 | |
| Ö-2 | 📌 | |
| E-3 | ⏸ onay bekler | |
| Ö-3 | 📌 | |
| OD-2 | 📌 | 30 kayıtta öne alınır |
| OD-3 | 📌 | |
| K-4 | ⏸ POTA sonucu bekler | |
| E-4 | ⏸ onay bekler | |
| POTA-1 | 📌 yan hat | `gorev-pota-tur1.md` |
| UI-K | ❓ önce kontrol et | `gorev-kure.md` |

**Zaten bitmiş olanlar** (`GOREV_LISTESI.md`'den): P1 tepsi/kill switch/audit ✅ · P2 hafıza motoru ✅ · P3 Router v2 🔧 *(D-1'in kırdığı yer giderildi; Casper canlı onayı hâlâ bekliyor)*

---

## 7. Belge haritası

| Dosya | Rolü |
|---|---|
| **`gelişimsüreci.md`** | **Tek kapı.** Sıra, kabul ölçütleri, durum, kararlar |
| `OLCU.md` | Zemin — kanıt kuralları. Yarışmaz |
| `ORTAK-DEFTER.md` | Ortak defterin biçimi ve kuralları |
| `POTA.md` | Algoritma damıtma düzeni |
| `FAY-MOTORU.md` | POTA'nın `aday #0`'ı |
| `düzenleme.md` | D fazının eki |
| `gorev-pota-tur1.md` | POTA-1 fazının eki |
| `gorev-kure.md` | UI-K fazının eki |
| `sema.html` | Görsel özet — https://claude.ai/code/artifact/df04e052-7c87-4ac8-bc7c-c9758e89f127 |
| `AGENTS.md` | Ajan kuralları — çelişirse **o kazanır** |
| `GOREV_LISTESI.md` | Eski ana plan. P1-P3 geçerli; **P4 buradaki ÖLÇÜ+POTA ile değişti**, P5 E-1..E-4 oldu, P6-P7 yerinde |

## 8. Faz bitince

1. Durum tahtası güncellenir, **kanıt yazılır**.
2. `AGENTS.md` §2'ye tek satır işlenir.
3. Ortak deftere kayıt düşülür (OD-0'dan sonra).
4. Sıradaki faza geçilir — ⛔ varsa **durulur ve Casper'a sorulur**.
