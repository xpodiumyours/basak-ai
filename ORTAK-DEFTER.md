# ORTAK DEFTER — Claude ile Başak'ın buluştuğu yer

*22 Ağustos 2026. Eksikler listesinin 1. maddesi.*

Dosya adı ASCII tutuldu — kod yazan ajanlar Türkçe karakterli adlarda takılabiliyor (`AGENTS.md` §8).

---

## 1. Sorun

Bugün iki ayrı hafıza var ve **kesişimleri sıfır**:

| Kim | Nerede | Ne var |
|---|---|---|
| Claude | `~/.claude/projects/C--Users-Casper/memory/` | 26 dosya — Casper'ın çalışma tarzı, proje kararları, tuzaklar |
| Başak | `data/memory/basak.db` + `knowledge/` | konuşma geçmişi, 4 not dosyası |

Aradaki köprü **Casper'ın kendisi**. Bana anlattığını Başak bilmiyor, Başak'a anlattığını ben bilmiyorum. Bilgiyi ağzıyla taşıyor.

Aylardır canını yakan "kayma"nın kaynaklarından biri tam olarak bu. Ve şu ana kadarki hiçbir planda yoktu.

Üstelik sorun ikimizle sınırlı değil: **Kilo Code ve OpenCode** de kod yazıyor ve onların da hafızası yok. Her ajan her seferinde sıfırdan başlıyor.

## 2. Çözüm — ama posta kutusu değil

Kolay yol şu olurdu: ortak bir klasör açalım, herkes içine yazsın. Bu birkaç hafta içinde çöplüğe döner — biçim kavgası, tekrarlar, birbirini ezen kayıtlar.

Doğru şekil şu: **ortak defter, iki yazarlı bir iddia defteridir.**

`OLCU.md`'de zaten bir iddia defteri var. Ortak defter yeni bir kavram değil — **o defterin ikinci yazara açılmış hâli.** Aynı kurallar geçerli:

- Her kaydın **kaynağı** var
- Her kaydın **ömrü** var
- **Kimse başkasının kaydını düzeltmez.** Katılmıyorsan yeni kayıt yazar, eskisini işaret edersin
- **Çelişki ortalanmaz** — iki kayıt da durur, çelişki görünür olur

Yani defter bir tartışma yeri değil, **birikim yeri**. Silme yok, üzerine yazma yok.

## 3. Yer ve biçim

```
C:\Projects\Başak\defter\
  INDEX.md                          ← tek satırlık özetler
  vixrex-kirala-durumu.md
  basak-kota-gercegi.md
  numeramatch-magaza-kapilari.md
  genel-calisma-duzeni.md
```

Düz klasör, konu önekli dosya adı. Her dosya **tek konu**, kısa.

### Kayıt biçimi

```markdown
---
kim:    claude | basak | casper | kilo | opencode
tarih:  2026-08-22
konu:   vixrex
tip:    olcum | alinti | cikarim | karar | soru
omur:   1s | 6s | 1g | 30g | sonsuz
kaynak: git log | GOREV_LISTESI.md:84 | sohbet | (ölçüm komutu)
---

Tek paragraf. Uzun anlatım yok — uzun anlatım gereken şey belgeye gider,
deftere onun tek cümlelik sonucu yazılır.
```

**Alan açıklamaları:**

- **tip** — `OLCU.md`'deki dört tipin aynısı, artı ikisi: `karar` (Casper'ın verdiği karar — kimse yeniden tartışmaz) ve `soru` (cevaplanmamış, açık duruyor)
- **omur** — `OLCU.md`'deki bayatlama tablosuyla aynı. Süresi geçen kayıt silinmez, **bayat** işaretlenir
- **kaynak** — `tip: olcum` veya `alinti` ise **zorunlu**. Kaynaksız ölçüm kaydı geçersizdir

### Çelişki kaydı

Bir kayıt başka bir kayda karşı çıkıyorsa, eskisi düzeltilmez:

```markdown
---
kim: basak
tip: olcum
celisir: vixrex-kirala-durumu.md
---
Git ölçümü: 12 dosya commit edilmemiş. Yukarıdaki kayıt "tamamlandı" diyor.
```

Bu çelişkiler daha sonra doğrudan **fay kartına** dönüşür. Yani defter, POTA'dan çıkacak motorun da yakıtı olur.

## 4. Kritik tuzak: 5.000 karakter sınırı

Başak şu an `knowledge/` klasörünü **her mesaja** ekliyor ve sınır var:

- `chat.py:27` → `KNOWLEDGE_MAX_CHARS = 5000`
- `AGENTS.md` §2 → *"sınır 12.000 karakter"*

**Bu ikisi çelişiyor** — belge ya eskimiş ya değer düşürülmüş. (Kendisi bir fay örneği; deftere ilk kayıtlardan biri bu olmalı.)

Hangisi doğru olursa olsun sonuç aynı: defter büyüdükçe sınırı aşacak ve `_load_knowledge` kalanı **sessizce kesecek**. O anda Başak, defterin yalnız alfabetik olarak ilk gelen kısmını "biliyor" olacak — ve bunu kimseye söylemeyecek.

Bu, fark edilmesi en zor arıza türü. Bu yüzden:

### Defter her mesaja eklenmeyecek

| Ne | Nasıl |
|---|---|
| `defter/INDEX.md` | **Her mesaja eklenir.** Küçük kalmalı — kayıt başına tek satır |
| Tek tek kayıtlar | **Eklenmez.** Hafıza motorunun aramasıyla, sadece ilgiliyse çekilir |

Hafıza motoru (`memory/engine.py`) zaten hem anlam hem kelime araması yapıyor. Defter oraya indekslenir, gerektiğinde ilgili kayıt çıkar. Sınır sorunu böyle ortadan kalkar.

## 5. Kim nasıl kullanır

| Taraf | Okuma | Yazma |
|---|---|---|
| **Claude** | İşe başlarken `defter/INDEX.md` + ilgili kayıtlar | Doğrudan dosya yazar (kod gerekmez) |
| **Başak** | INDEX her mesajda; kayıtlar aramayla | `save_note` aracı `defter/`e yönlendirilir |
| **Casper** | İsterse elle okur | "bunu deftere yaz" der, Başak yazar |
| **Kilo / OpenCode** | `AGENTS.md`'ye tek satır eklenir | Aynı biçimde yazar |

**Claude tarafında kod yok.** Benim tarafımdaki tek gereklilik: hafızamdaki `MEMORY.md` dosyasına tek satır — *"Başak işinde önce `defter/INDEX.md`'yi oku"*. O dosya her oturumda bana yükleniyor, yani kanca bedava.

## 6. Ne girer, ne girmez

**Girer:**
- Casper'ın verdiği kararlar ve gerekçesi
- Ölçülmüş durum ("şu an gerçekten neredeyiz")
- Denenip **olmayan** şeyler ve neden olmadığı
- Açık sorular

**Girmez:**
- **Anahtar, parola, gizli bilgi** — asla. Pre-commit kontrolü zaten engelliyor, defter bu kuralın istisnası değil
- Uzun konuşma dökümleri
- Kodun kendisi — o git'te duruyor
- Depodan zaten okunabilen şeyler (dosya yapısı, commit geçmişi)
- Benim özel çalışma notlarım — onlar kendi hafızamda kalır

**Sınır cümlesi:** Benim hafızam *Casper'la nasıl çalışılacağını* tutar. Defter *projeler hakkında ikimizin de bildiğini* tutar. İkisi karışmaz.

## 7. Kurulum sırası

### OD-0 — tek yön: Claude yazar, Başak okur *(ilk hedef)*

- `defter/` klasörü + biçim + elle yazılmış `INDEX.md`
- `chat.py`'de `defter/` de okunan kaynaklara eklenir — **ama sadece INDEX**
- `memory/engine.py` indekslemesine `defter/` eklenir

**Kabul ölçütü:** Claude deftere yeni bir kayıt yazar (örn. "Groq günlük kotası dolmuş"). Casper hiçbir şey anlatmadan Başak'a sorar. Başak o bilgiyi kullanarak cevap verir. Kayıt silinir, Başak artık bilmiyor.

### OD-1 — iki yön: Başak da yazar
`save_note` aracı `defter/`e yönlendirilir, biçime uyar (kim/tarih/tip/kaynak).
**Kabul:** Casper Başak'a bir şey söyler, Başak deftere yazar, Claude sonraki oturumda o bilgiyle gelir.

### OD-2 — INDEX otomatik + arama üzerinden çekme
INDEX elle yazılmaktan çıkar, kayıtlardan üretilir. Kayıtlar aramayla gelir.
**Kabul:** 50 kayıtla test — bağlam sınırı aşılmıyor, ilgili kayıt yine de bulunuyor.

### OD-3 — çelişki ve bayatlama
`celisir:` alanı işlenir, ömrü geçen kayıtlar bayat işaretlenir.
**Kabul:** İki çelişen kayıt konur, sistem ikisini de gösterip soruyu sorar — birini seçip diğerini gizlemez.

### Sonraki ajanlar
`AGENTS.md`'ye tek bölüm eklenir: Kilo ve OpenCode da işe başlarken INDEX okur, bitirince kayıt yazar.

## 8. Bu neden ilk madde

Diğer dört eksik (projelere erişim, sayfa okuma, kendi kendine çalışma, bilgisayar işleri) hep **daha fazla bilgi üretiyor**. Defter olmadan o bilginin gidecek yeri yok — her ajan kendi köşesinde üretip unutur.

Defter önce kurulursa, sonraki her eksik kapatıldığında kazanç **birikir**. Sonra kurulursa aradaki her şey kaybolur.
