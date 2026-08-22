# ÖLÇÜ — Başak'ın kanıt zemini

*22 Ağustos 2026. Casper'ın şartı: "varsayım ve tahmin yürütmeden."*

ÖLÇÜ bir özellik değil, **zemin**. POTA'da hangi algoritma kazanırsa kazansın, onun üstünde çalışacağı taban budur. Aday değildir, yarışmaz.

Dosya adı ASCII tutuldu (`OLCU.md`) — kod yazan ajanlar Türkçe karakterli dosya adlarında takılabiliyor (`AGENTS.md` §8).

---

## 1. Tek ilke

Başak'ın söylediği her cümle ölçülmüş olmak zorundadır. Ölçülemeyen cümle ağzından çıkamaz — modelden rica edilerek değil, **çıkışta kapıya takılarak.**

Fark burada: model iyi davranmaya *çalışmıyor*, kötü davranmayı **yapısal olarak beceremiyor.**

---

## 2. Cümle tipleri — dördü dışında tip yok

Başak'ın ürettiği her cümle bir işaret taşır:

| Tip | İşaret | Ne demek | Yanında ne taşır |
|---|---|---|---|
| **ÖLÇÜM** | `[Ö]` | Doğrudan ölçtüm | çalıştırdığı komut + çıktısı |
| **ALINTI** | `[A]` | Bir kaynak böyle diyor | dosya adı + satır |
| **ÇIKARIM** | `[Ç]` | En az iki ölçümden çıkardım | dayandığı ölçümlerin kimlikleri |
| **BİLMİYORUM** | `[B]` | Desteklenemiyor | neyin ölçülmesi gerektiği |

**Tahmin beşinci tip olurdu. Yoktur.** Bu yüzden bir tahmin ancak `[B]` olarak dışarı çıkabilir.

### Çıkış kapısı (mekanizma)

Cevap kullanıcıya gitmeden önce her cümle tek tek denetlenir:

1. **İşaretsiz cümle** → silinir.
2. **`[Ö]` işaretli cümle** → o ölçüm bu turda gerçekten alınmış mı, defterde kaydı var mı? Yoksa silinir.
3. **`[A]` işaretli cümle** → belirtilen dosya:satır **gerçekten o metni içeriyor mu?** Birebir metin araması yapılır. Eşleşmezse silinir. *(Uydurma alıntıyı bitiren şey budur.)*
4. **`[Ç]` işaretli cümle** → dayandığı ölçümlerin ikisi de defterde var mı? Yoksa silinir.
5. Silinen cümlelerin yerine tek satır geçer: *"Bunu ölçemedim."*

Kapı bir yapay zekâ değildir. Metin kontrolü ve dosya aramasıdır. Kandırılamaz.

---

## 3. Önce ölç, sonra konuş

**Şu anki akış:** soru → model → cevap.
**ÖLÇÜ akışı:** soru → *bunu ne kesin olarak çözer?* → ölçümü çalıştır → cevabı **yalnız çıktıdan** üret.

### Çözüm planı

Soru gelince, cevap üretilmeden önce en fazla 5 maddelik bir plan çıkarılır. Her madde izin listesindeki somut bir ölçümdür:

```
soru: "vixrex'te kiralık vitrin işi bitti mi?"
plan:
  1. git -C C:/Projects/vixrex log -1 --format=%h|%ad|%s
  2. git -C C:/Projects/vixrex status --porcelain
  3. GOREV_LISTESI.md içinde "kiralık" geçen satırlar
  4. ilgili dosyalar diskte var mı, ne zaman değişmiş
```

Plan çalıştırılır, çıktılar deftere yazılır, cevap yalnız bunlardan kurulur.

**Plan boş çıkarsa** cevap şudur: *"Bunu ölçemem. Şu ölçülebilirdi: ..."* — bu bir başarısızlık değil, doğru cevaptır.

Model burada "bilen" değil, **tercüman**. İşi ölçüm çıktısını Türkçeye çevirmek.

### Ölçüm izin listesi

Ölçülebilir olan sadece bunlardır. Listede olmayan şey ölçülemez, dolayısıyla iddia edilemez.

| Kaynak | Ne verir | Sınır |
|---|---|---|
| git (salt okunur) | dal, son commit, commit edilmemiş dosyalar, geçmiş | `log`, `status`, `show`, `diff`, `rev-list` serbest; yazan komutlar yasak |
| dosya sistemi | var mı, ne zaman değişti, boyut, içerik | proje klasörleri |
| hafıza veritabanı | geçmiş konuşmalar, notlar | `data/memory/basak.db` — kopyası okunur |
| belgeler | AGENTS.md, GOREV_LISTESI.md, CONTEXT.md vb. | birebir alıntı |
| canlı site | HTTP durum kodu, sayfa içeriği | yalnız GET |
| ayarlar | model, kota, izin durumu | `ayarlar.json`, `data/provider_limits/` |

---

## 4. Güven hesaplanır, hissedilmez

"%80 eminim" demek zaten tahmindir. ÖLÇÜ'de güven üç **ölçülmüş** sayıdan çıkar:

```
güven = kaynak_sayısı × tazelik × kaynak_karnesi
```

- **kaynak sayısı:** kaç bağımsız kaynak aynı şeyi söyledi (sayılır)
- **tazelik:** ölçüm kaç saat önce alındı (bkz. bölüm 5)
- **kaynak karnesi:** bu kaynak geçmişte kaç kez yanıldı (bkz. bölüm 6)

Sunum üç kelimeden biri olur: **kesin** · **tek kaynak** · **bayat**.

### Çelişki ortalanmaz

İki kaynak farklı şey söylüyorsa Başak **ortasını bulmaz.** Ortalama almak, iki gerçeği birden gizleyen bir yalandır.

Çelişki olduğu gibi raporlanır:

```
[Ö] git: 12 dosya commit edilmemiş
[A] GOREV_LISTESI.md:84 "tamamlandı" diyor
→ Bu ikisi çelişiyor. Hangisi geçerli?
```

---

## 5. Her bilginin ömrü var

Süresi geçmiş bilgi "biliniyor" sayılmaz. Kullanılmadan önce yeniden ölçülür; ölçülemiyorsa **bayat** etiketiyle sunulur.

| Bilgi türü | Ömür | Neden |
|---|---|---|
| git durumu (dal, commit edilmemiş dosya) | 1 saat | dakikalar içinde değişir |
| dosya varlığı / değişim tarihi | 6 saat | |
| canlı site durumu | 1 gün | |
| kota / limit durumu | 1 gün | günlük sıfırlanır |
| proje kararı, kapsam | 30 gün | yavaş değişir ama değişir |
| kişisel sabitler (doğum günü) | süresiz | değişmez |

Bu, Casper'ın geçmişindeki **en sık hatanın** doğrudan panzehiri: eskimiş doğruya göre iş yapmak.

---

## 6. Sürekli gelişen kısım — ve neden bedava

### İddia defteri

Başak'ın kurduğu her cümle deftere yazılır:

```
kimlik · tarih · cümle · tip · kaynak · ölçüm çıktısı · konu · durum · son kontrol
```

`durum` üç değerden biri: **açık** · **doğrulandı** · **çürütüldü**

### Otomatik yeniden sınav

**Kilit fikir: gerçek zaten kendini yeniden ölçüyor.**

Git değişiyor, dosyalar değişiyor, site değişiyor. Her yeni ölçüm alındığında, aynı konudaki **açık iddialar** defterden çekilir ve yeni ölçümle karşılaştırılır:

- yeni ölçüm iddiayı destekliyor → `doğrulandı`
- çürütüyor → `çürütüldü`, ve kaynağın karnesine eksi yazılır
- ilgisiz → dokunulmaz

Bu döngü **bedavadır**, çünkü ölçüm zaten başka bir iş için alınıyordu. Casper'ın oturup "bu doğruydu, bu yanlıştı" demesine gerek yok. Sistem kendi geçmişine sürekli not veriyor.

### Karne

Zamanla ölçülmüş bir bilgi birikir: **hangi kaynak, hangi konuda, ne sıklıkla yanılıyor.**

Kullanımı somuttur — karnesi düşük bir kaynaktan gelen `[A]` cümlesi tek başına `[Ç]` üretmeye **yetmez**, ikinci bir kaynak ister.

Örnek çıktı (haftalar sonra, veriden türetilmiş):
> *belge kaynağı "tamamlandı" derken git ölçümüyle 7 kez çelişti, 3 kez uyuştu.*

Casper'ın şu an kafasında taşımak zorunda olduğu ders, artık ölçülmüş bir sayı.

### Neden bu Casper'a özel

Çünkü onun dünyası **ölçülebilir**: dört yerel depo, bir canlı site, kendi dosyaları, kendi hafızası. Bulut asistanlarının böyle bir zemini yok — o yüzden hepsi tahmin yürütüyor. Buradaki keskinlik modelden değil, **zeminden** geliyor.

---

## 7. Neyi ölçemez — dürüst sınırlar

ÖLÇÜ her şeyi çözmez. Ölçülemeyen şeyler:

- gelecek (bu iş kaç gün sürer, bu ürün tutar mı)
- niyet (bu müşteri ne ister)
- değer yargısı (bu iyi bir fikir mi, bu kod temiz mi)
- pazar, rekabet, insan davranışı

Bunlarda Başak **fikir üretmeye çalışmaz**. Der ki: *"Bu ölçülemez. Karar senin. Şu ölçülebilenler elimde: ..."*

**Ölçümün kendisi de yanılabilir** — bayat uzak veri, yanlış klasör yolu, kapalı servis. Bu yüzden ölçüm de bir kaynaktır ve onun da karnesi tutulur. Hiçbir kaynak dokunulmaz değildir.

---

## 8. Kurulum sırası

Her faz kanıtla kapanır.

### Ö-0 — Cümle tipleri + çıkış kapısı
Dört tip, işaretleme, çıkış denetimi, **alıntı doğrulama** (birebir metin araması).

**Kabul:** 10 zor soru sorulur. (1) Uydurma alıntı **sıfır** — her `[A]` cümlesinin kaynağı elle açılıp doğrulanır. (2) Kaynaksız iddia çıkışa **hiç** ulaşmaz. (3) Cevabı olmayan soruda `[B]` çıkar, uydurma çıkmaz.

### Ö-1 — Çözüm planı (önce ölç)
Soru → plan → ölçüm → cevap akışı.

**Kabul:** "VixRex'te durum ne" sorusuna gelen cevabın her cümlesi git/dosya çıktısına dayanıyor. Modelin kendi bilgisinden gelen tek cümle yok.

### Ö-2 — İddia defteri + bayatlama
Defter, ömür tablosu, bayat bilgiyi kullanmadan önce yeniden ölçme.

**Kabul:** Defter doluyor. Bayat bir bilgi kullanılmak istendiğinde önce yeniden ölçülüyor; ölçülemiyorsa "bayat" diye sunuluyor.

### Ö-3 — Otomatik yeniden sınav + karne
Yeni ölçüm eski iddiaları sınava sokar; karne birikir; güven hesabına girer.

**Kabul:** En az bir eski iddia, Casper hiçbir şey söylemeden, yeni bir ölçümle **otomatik çürütülüyor** — ve o kaynağın karnesi değişiyor.

---

## 9. Diğer belgelerle ilişkisi

| Belge | Rolü |
|---|---|
| `OLCU.md` (bu dosya) | **Zemin.** Yarışmaz, her şeyin altında |
| `POTA.md` | Algoritma arayan damıtma düzeni. Adaylar bu zemin üstünde yarışır |
| `FAY-MOTORU.md` | POTA'nın adaylarından biri (`aday #0`) |
| `gelişimsüreci.md` | Fazlar, kararlar, durum tahtası |

**Not:** ÖLÇÜ, POTA'yı da güçlendirir. POTA'nın acı haritası ve geriye dönük sınavı zaten ölçülmüş iddialara ihtiyaç duyuyor — ÖLÇÜ kurulduğunda pota daha temiz veriyle çalışır.

Sıra kararı Casper'ın: ÖLÇÜ önce mi kurulsun, POTA Tur 1 sonucu beklensin mi? İkisi birbirini engellemiyor, paralel yürüyebilir.
