# GÖREV — POTA Tur 1

Önce `POTA.md`'yi oku (tasarım ve gerekçe). Bu dosya onun Tur 1 uygulamasıdır.

**Bu bir yazılım geliştirme görevi DEĞİL.** Hiç kod yazmayacaksın. Bu bir **araştırma ve ölçüm** görevi. Çıktısı iki markdown dosyası.

---

## Amaç

Casper'ın aylardır biriken gerçek geçmişini bir sınav kâğıdına çevir, aday algoritmaları bu sınava sok, sonucu tek bir karşılaştırma kartına indir.

---

## Mutlak kurallar

1. **Sadece oku.** Hiçbir proje dosyası değiştirilmeyecek. Sadece bu görevin iki çıktı dosyası yazılacak.
2. **Git'e yazma yok.** `status`, `log`, `show`, `diff`, `rev-list` serbest. `fetch`, `pull`, `push`, `commit`, `checkout`, `reset` **yasak**.
3. **Kanıtsız olay yok.** Her olayın dosya adı + satır ya da commit kimliği olacak. Kanıtı bulamadığın olayı haritaya **yazma** — "şüpheli" bölümüne koy, puanlamaya katma.
4. **Uydurma yok.** Bir olayı hatırladığını sanıp yazma. Görmediğin şeyi yazma. Bu görevin tek gerçek başarısızlık biçimi uydurmadır.
5. **Geleceği gösterme.** Sınav yaparken, olayın tarihinden **sonra** yazılmış hiçbir belgeyi kullanma. Bu kurala uymazsan bütün sınav sahte olur.
6. **Ücretsiz kal.** Ücretli model çağrısı yapma.
7. **Sırayla yaz.** Önce `aci-haritasi.md` dosyasını **tamamen bitir ve kaydet**, sonra sınava geç. İş yarıda kalırsa harita kurtulsun.

---

## Külliyat — okunacak yerler (hepsi doğrulandı, 22 Ağustos 2026)

| Kaynak | Yol | Ne var |
|---|---|---|
| Casper hafıza notları | `C:\Users\Casper\.claude\projects\C--Users-Casper\memory\` | 26 dosya — en yoğun kaynak, buradan başla |
| Başak hafıza veritabanı | `C:\Projects\Başak\data\memory\basak.db` | 3,3 MB SQLite |
| Başak projesi | `C:\Projects\Başak` | git var, belgeler: `AGENTS.md`, `GOREV_LISTESI.md` |
| VixRex | `C:\Projects\vixrex` | git var, 72 öğe — en çok belge ve en çok kayma geçmişi burada |
| NumeraMatch | `C:\Users\Casper\source\NumeraMatch` | git var, 39 öğe |
| Xses | `C:\Projects\xses` | git var, 18 öğe |

**Veritabanı uyarısı:** `basak.db` yanında `-wal` ve `-shm` dosyaları var, yani Başak açık olabilir. Veritabanını **kopyala, kopyayı oku**. Aslını açma, kilitleme.

---

## Adım 1 — Acı Haritası

Külliyatı tara ve **gerçekten olmuş olayları** çıkar. Bir olayın haritaya girmesi için üçü de gerekir:

1. Bir şeye inanılmıştı (belge, rapor, hatıra)
2. Gerçek farklıydı (git, dosya, sonraki cümleler)
3. Bir bedel ödendi (boşa iş, yanlış zemin, geri dönüş, kayıp zaman)

Hedef: **25-60 olay.** 25'in altında kalırsan daha derin tara (özellikle git geçmişleri ve hafıza veritabanı).

**Nerede bol olay bulunur:** hafıza notlarındaki "yanlış rapor verildi", "commit yok", "doğrulanmadan güvenme", "eskimiş" gibi ifadeler; belgede "tamamlandı" derken git'te karşılığı olmayan işler; uzun süre commit edilmemiş çalışmalar; iki belgenin aynı konuda farklı şey söylemesi.

Her olay bu biçimde yazılır:

```
### O-01
- tarih:    2026-08-20
- proje:    vixrex
- inanılan: "plan kodda uygulandı ve doğrulandı"
- gerçek:   commit yok, push yok
- bedel:    ertesi gün baştan doğrulama, ~1 oturum
- kanıt:    memory/vixrex-nerede-kaldik.md + git log (son commit 5 gün önce)
- tür:      belge-gerçek kayması
```

**tür** alanı önemli — sonunda hangi acının kaç kez tekrarladığını sayacaksın. Türleri sen adlandır, ama tutarlı kullan.

Dosyanın sonuna ekle:
- **Tür sayımı:** hangi tür kaç kez tekrar etmiş, çoktan aza sıralı
- **Şüpheliler:** kanıtı bulunamayan olaylar, ayrı liste, puanlamaya katılmaz
- **Sınav seti:** olayların **en yeni %25'i** işaretlenir. Adaylar bunları görmeyecek

Kaydet: `C:\Projects\Başak\pota\aci-haritasi.md`

---

## Adım 2 — Adaylar

Elde hazır 3 aday var (`POTA.md` bölüm 5): **fay**, **bekçi**, **karne**. Bunların üstüne **6 yeni aday** üret — ikişer tane şu üç yoldan:

- **A (acıdan):** en sık tekrar eden olay türünü doğrudan hedefle
- **B (aktarımdan):** başka bir alanda çalışan bir mekanizmayı buraya taşı
- **C (tersinden):** mevcut kurgudaki bir varsayımı ters çevir

Her aday **tam olarak beş satır**. Uzun anlatım yok:

```
### aday: <tek kelime ad>
- yol:            A / B / C
- ne ölçer:       <tek cümle>
- ne zaman konuşur: <tek cümle>
- ne sorar:       <tek cümle>
- asla yapmaz:    <tek cümle>
```

Adaylar birbirine benzemesin. İkisi aynı şeyi ölçüyorsa birini at, yerine yenisini üret.

---

## Adım 3 — Geriye dönük sınav

Her aday × her olay (sınav seti hariç) için tek soru:

> Bu aday, **bedel ödenmeden önce**, bu olayı yakalar mıydı?

"Yakaladı" sayılması için aday, **yanlış inancı adıyla** işaret edebilmeli. "Genel olarak faydalı olurdu" yakalama değildir.

Her yakalama için hangi sinyalle yakaladığını tek satırda yaz. Yazamıyorsan yakalamamıştır.

### Gürültü ölçümü (atlanamaz)

Olay içermeyen sakin dönemlerden **10 gün** rastgele seç. Her aday için: o gün konuşur muydu? Konuşacaktıysa boşuna konuşmuş olur.

Bu ölçüm olmazsa kazanan hep "her şeye alarm ver" olur — o da bir haftada Casper'ı bıktırır.

### Puan tablosu

Her aday için:

| Puan | Nasıl ölçülür |
|---|---|
| yakalama | kaç olay / toplam olay |
| erkenlik | bedelden ortalama kaç gün önce |
| gürültü | 10 sakin günde kaç kez konuştu |
| emek | haftada kaç dakika Casper'ın dikkatini ister (tahmin, gerekçeli) |
| **sınav seti** | ayrılan %25'te kaç olay yakaladı — **ezberleme kontrolü** |

Sınav setinde belirgin düşüş varsa aday geçmişi ezberlemiş demektir, kartta bunu belirt.

---

## Adım 4 — Kart

En iyi **en fazla 3** adayı tek karta indir. Kart **25 satırı geçmeyecek** ve teknik terim içermeyecek — Casper 10 dakikada okuyup karar verecek.

```
POTA — Tur 1 sonucu

  Elde <N> gerçek olay vardı.

  ADAY "<ad>" → <k> olayı yakalardı, ortalama <g> gün önce
                haftada <n> kez boşuna konuşurdu

  ADAY "<ad>" → ...

  Fark: <tek cümle — bu adaylar arasındaki asıl seçim nedir>

  Soru: (a) <seçenek>
        (b) <seçenek>
        (c) <seçenek>
```

Kartın altına kısa bir **"dikkat çeken"** bölümü ekle: sınav sırasında fark ettiğin, Casper'ın bilmediği bir şey varsa 2-3 satır.

Kaydet: `C:\Projects\Başak\pota\tur1-kart.md`

---

## Kabul ölçütü — bunlar olmadan "bitti" deme

1. `pota\aci-haritasi.md` var, içinde **en az 25** kanıtlı olay var.
2. Rastgele seçilen 3 olayın kanıtı elle doğrulanabiliyor — kaynak dosya/commit gerçekten öyle diyor.
3. `pota\tur1-kart.md` var, **25 satırı geçmiyor**, teknik terim yok.
4. 9 aday da beş satırlık formda yazılmış.
5. Gürültü ölçümü yapılmış — her aday için 10 sakin gün sonucu var.
6. Sınav seti (%25) ayrılmış ve adaylar üzerinde ayrıca ölçülmüş.
7. Hiçbir proje dosyası değişmemiş — `git status` her dört projede de görev öncesiyle aynı.

## Bitirince

Tek paragraf özet ver: kaç olay bulundun, hangi acı türü en çok tekrar etmiş, hangi aday önde çıktı. Karar Casper'ın — sen kazananı ilan etme, veriyi sun.
