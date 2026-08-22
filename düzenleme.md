# DÜZENLEME — Araya alınan düzeltmeler

*22 Ağustos 2026. Ölçüm sırasında bulunan gerçek arızalar. ÖLÇÜ/POTA/FAY işleri bekliyor, önce bunlar bitecek.*

Hepsi hata kayıtlarından ve koddan **ölçülerek** bulundu, tahmin yok. Her maddede kanıt yazılı.

## Kurallar

- **Küçük düzeltme yap, dosyayı yeniden yazma** (`AGENTS.md` §5).
- Sırayla git: D-1 → D-2 → D-3. Her biri ayrı bitirilir, kanıtı gösterilir.
- D-1 ve D-2 kod düzeltmesi. **D-3 kod değil, ölçüm** — hiçbir dosyayı değiştirme.

---

## D-1 — `oturum` alanı bulut beynini kırıyor  ⚠️ en öncelikli

### Kanıt

`_run.err` satır 2-3:

```
groq hatasi, siradaki deneniyor: Error code: 400 -
  'messages.21' : for 'role:user' the following must be satisfied
  [('messages.21' : property 'oturum' is unsupported)]
```

### Sebep (koddan doğrulandı)

1. `chat.py:309-310` — her mesaj oturum kimliğiyle kaydediliyor:
   ```python
   gecmis += [{"role": "user", "content": text, "oturum": OTURUM_ID},
              {"role": "assistant", "content": cevap, "oturum": OTURUM_ID}]
   ```
2. `chat.py:200-201` — bu geçmiş sonraki soruda geri yükleniyor.
3. `chat.py:322-329` — `_temizle_history` sadece `tool_calls` olan mesajları temizliyor; **normal mesajları olduğu gibi geçiriyor**, yani `oturum` alanı hayatta kalıyor:
   ```python
   else:
       temiz.append(m)          # <-- oturum burada sızıyor
   ```
4. `chat.py:228` — bu geçmiş doğrudan API'ye gidiyor. Groq bilinmeyen alanı reddediyor → **400**.

**Sonuç:** en iyi ücretsiz beynin, geçmiş dolu olduğu her soruda devre dışı kalıyor. Zincir boşuna aşağı iniyor, Gemini'ye yükleniyor, kotalar erken bitiyor.

### Doğru düzeltme

Tek yer: `_temizle_history`. `else` dalı da API'ye uygun alanlara indirsin:

```python
else:
    temiz.append({"role": m.get("role"), "content": m.get("content", "")})
```

### ⚠️ Yanlış düzeltme (yapma)

`_save_and_reply` içinden `OTURUM_ID`'yi **kaldırma.** Oturum kimliği P3'ün parçası, yerel dosyada kalması gerekiyor. Sorun kaydetmekte değil, **gönderirken temizlememekte**. Kayıtta kalsın, çıkışta silinsin.

### Kabul ölçütü

1. Uygulama açılır, **geçmişi dolu** bir sohbette en az 3 soru sorulur.
2. `_run.err` / `data/audit/audit.log` içinde yeni `property 'oturum' is unsupported` satırı **hiç yok**.
3. Audit'te `OK kaynak=groq` görünüyor.
   *Not: `429` (kota) gelirse bu ayrı bir konudur, bu maddeyi çürütmez. Aranan şey `400` hatasının bitmesi.*

---

## D-2 — Görev listesi görünmez işaret yüzünden okunamıyor

### Kanıt

Üç hata kaydında da ilk satır:
```
Gorevler okunamadi: Unexpected UTF-8 BOM (decode using utf-8-sig): line 1 column 1 (char 0)
```

Dosyanın baytları ölçüldü — `gorevler.json`, 7 bayt:
```
EF BB BF 5B 5D 0D 0A     →     [görünmez işaret] [] [satır sonu]
```

Hata kaynağı: `tools/reminders.py:163`. Okuyan satır: `tools/reminders.py:136`.

**Sonuç:** hatırlatma ve görev okuma sessizce boş dönüyor. Hata kullanıcıya gösterilmiyor, sadece kayda düşüyor — yani fark edilmesi zor.

### Düzeltme

JSON **okuyan** yerlerde `encoding="utf-8"` → `encoding="utf-8-sig"`. Bu ayar hem işaretli hem işaretsiz dosyayı sorunsuz okur, yani bir daha bu hata olmaz.

Düzeltilecek okuyucular (ölçüldü):

| Dosya | Satır |
|---|---|
| `chat.py` | 171 (`yukle`) |
| `tools/reminders.py` | 136 |
| `brain/brain.py` | 48 |
| `brain/kota.py` | 71 |

Ayrıca `tools/` altında JSON okuyan başka yer var mı diye ara; varsa aynı düzeltmeyi uygula.

**Yazan yerlere dokunma.** `kaydet()` işaretsiz yazıyor, doğrusu bu. Dosya bir kez kaydedilince işaret zaten temizlenir.

### Kabul ölçütü

1. Uygulama açılır, "hatırlatmalarım ne" / "görevlerim ne" sorulur — cevap geliyor.
2. Yeni hata kaydında `Gorevler okunamadi` satırı **yok**.
3. Elle test: başında işaret olan bir JSON dosyası okutulur, hata vermiyor.
4. `pytest` mevcut testleri yeşil kalıyor (`tests/test_tools.py` görev dosyalarına dokunuyor).

---

## D-3 — Gerçek kota kapasitesi (kod değil, ölçüm)

### Neden

FAY ve POTA tasarımlarında *"3 ücretsiz sağlayıcıya aynı anda sor, maliyet sıfır"* deniyor. Hata kayıtları bunu çürüttü:

- **Groq:** günlük 200.000 kelime hakkı **dolmuş** (`Used 197.355 / Limit 200.000`)
- **Gemini:** ücretsiz katman **günde 20 istek** — dolmuş (`limit: 20`)

Yani paralel jüri fikri, elde olmayan bir kapasiteyi varsayıyor. Ölçmeden tasarıma devam edilemez.

### Yapılacak

`data/provider_limits/` sayaçlarından ve hata kayıtlarından **gerçek** tabloyu çıkar. Tek sayfalık not yaz: `data/kota-gercek.md`

| sağlayıcı | gerçek günlük limit | bugün kullanılan | jüriye uygun mu |
|---|---|---|---|

### ⚠️ Kota harcama

**Ölçmek için deneme çağrısı yapma.** Her çağrı zaten kısıtlı olan haktan yer. Sadece mevcut sayaçları ve kayıtları oku.

### Kabul ölçütü

1. `data/kota-gercek.md` var, yedi sağlayıcının hepsi tabloda.
2. Tablodaki her sayının kaynağı belli (hangi kayıt, hangi sayaç).
3. Sonuç tek cümleyle yazılmış: paralel jüri kaç sağlayıcıyla, günde kaç kez kurulabilir.

---

## D-4 — Kapanış hatası *(şimdilik yapılmayacak, sadece kayıt)*

Kapatırken şu satır düşüyor:
```
forrtl: error (200): program aborting due to window-CLOSE event
```

Sayısal bir kütüphaneden geliyor, pencere kapanırken. **Şu an bir zarar vermiyor** — uygulama zaten kapanıyor. Öncelikli değil, buraya sadece unutulmasın diye yazıldı.

---

## Doğrulama kapıları (D-1 ve D-2 için)

| Kapı | Komut |
|---|---|
| Sözdizimi | `python -m py_compile chat.py tools/reminders.py brain/brain.py brain/kota.py` |
| Testler | `pytest` — mevcut testler yeşil kalmalı, kırmızıya döndüren düzeltme kabul edilmez |
| Gerçek çalıştırma | `python basak_app.py` — açıp elle dene, kayda bak |

`git commit --no-verify` kullanma.

## Bitince

`gelişimsüreci.md` durum tahtasına üç satır işlenir (D-1, D-2, D-3 — kanıtıyla). Sonra ana yola dönülür: ÖLÇÜ ve POTA.
